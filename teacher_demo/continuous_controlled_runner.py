"""A: controlled numerical binning; C: guarded-router sensitivity, SAME frozen rules.

A compares each binning to EW3 with fixed sources and partitions. Both
inner validation and held-out test are reported for same fit. C policies
are evaluated on EW3 without re-inducing rules. ALL training of boundaries
and router fits from Development/Validation; Test read for FINAL metrics only.

20 UCI real prepared sources; max 6 prespecified columns; this is a research
prototype, not an automated treatment recommender or federated-private
quantile protocol. Exact original baseline G4 is asserted on EW3.
"""
from __future__ import annotations
import argparse
import json
import time
from contextlib import nullcontext
from functools import partial
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from roughset.app import _run_split
from roughset.evaluation import evaluate_rule_model
from roughset.preprocessing import apply_preprocessor
from roughset.splitting import stratified_train_test_split
from teacher_demo.continuous_binning_methods import MODES,fit_mode
from teacher_demo.conflict_aware_coverage_pilot import load_bundle
from teacher_demo.full_factorial_matrix import POLICIES,_split_raw
from teacher_demo.g4_rule_conflict_router import (
    POLICY_ORDER,REGIMES,DEFAULT_BASE,SEEDS,measured,rule_buckets,
    select_router,apply_router
)
from teacher_demo.public_20_registry import REGISTRY

ORIGINAL=Path("docs/research/teacher_dashboard/data/G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv")
TARGET_SCENARIOS=("NONIID_05","NONIID_01")
BASELINE="EQUAL_WIDTH_3"
BINS=tuple(MODES)
GUARDS={
 "ORIGINAL_G4":{"min_cases":10,"net_correct":2,"min_ba":.002,"acc_loss":.005,"max_switches":2},
 "GUARD_RELAXED":{"min_cases":5,"net_correct":1,"min_ba":0.,"acc_loss":.01,"max_switches":3},
 "GUARD_STRICT":{"min_cases":20,"net_correct":3,"min_ba":.005,"acc_loss":0.,"max_switches":1},
 "GUARD_NOSWITCH":{"min_cases":10**9,"net_correct":10**9,"min_ba":1.,"acc_loss":0.,"max_switches":0},
}
def guard_select(y,preds,buckets,base,settings):
    labs=np.asarray(y,dtype=object)
    pred={p:np.asarray(x,dtype=object) for p,x in preds.items()}
    original=pred[base].copy();current=original.copy()
    score=measured(labs,current)
    baseline_acc=score["accuracy"];selected={}
    for bucket in ("TWO_CLASS_FEW_RULES","TWO_CLASS_MANY_RULES","THREE_PLUS_CLASSES"):
        if len(selected)>=settings["max_switches"]:break
        mask=np.asarray(buckets)==bucket
        if int(mask.sum())<settings["min_cases"]:continue
        options=[]
        for policy in POLICY_ORDER:
            if policy==base:continue
            trial=current.copy();trial[mask]=pred[policy][mask]
            metric=measured(labs,trial)
            wins=int(((trial[mask]==labs[mask])&(current[mask]!=labs[mask])).sum())
            losses=int(((trial[mask]!=labs[mask])&(current[mask]==labs[mask])).sum())
            allowed=(wins-losses>=settings["net_correct"] and
                     metric["balanced_accuracy"]-score["balanced_accuracy"]>=settings["min_ba"] and
                     metric["accuracy"]>=baseline_acc-settings["acc_loss"])
            if allowed:options.append((metric["balanced_accuracy"]-score["balanced_accuracy"],
                                      wins-losses,-POLICY_ORDER.index(policy),policy,trial,metric))
        if options:
            win=max(options,key=lambda t:t[:3])
            selected[bucket]=win[3];current=win[4];score=win[5]
    return selected,current

def audit(frame,rules,target):
    b,candidates,covered,conflict=rule_buckets(frame,rules)
    truth=frame[target].astype(str).to_numpy()
    assert len(frame)>0
    correct=np.array([v in cand for v,cand in zip(truth,candidates)])
    return {
      "buckets":b,
      "coverage_pct":float(covered.mean()*100),
      "conflict_pct":float(conflict.mean()*100),
      "correct_candidate_pct":float(correct.mean()*100),
      "no_match_pct":float((~covered).mean()*100)
    }

def root_config(seed,regime):
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    strategy,alpha=REGIMES[regime]
    cfg["evaluation"].update(mode="HOLDOUT",seed=seed)
    cfg["experiment"].update(run_centralized=False,run_federated=True)
    cfg["federated"].update(n_clients=3,partition=strategy,
        dirichlet_alpha=alpha,run_client_sweep=False,order_sensitivity_max_permutations=1)
    return cfg

def engine(bundle,dev,val,test,seed,regime,mode):
    cfg=root_config(seed,regime)
    ctx=nullcontext() if mode==BASELINE else patch(
        "roughset.app.fit_shared_preprocessor",partial(fit_mode,mode=mode))
    start=time.perf_counter()
    with ctx:
        fitted=_run_split(bundle,dev,val,cfg,quiet=True,
                          prediction_policies=POLICIES,fold=1)
    elapsed=time.perf_counter()-start
    art=fitted["structural_artifact"]
    transformed=apply_preprocessor(test,fitted["preprocessor"],bundle.target)
    t=art.target;rules=art.global_rules
    val_y=art.test[t].astype(str).to_numpy()
    tst_y=transformed[t].astype(str).to_numpy()
    valp={policy:np.asarray(fitted["policy_results"][policy]["federated"]["predictions"],dtype=object)
          for policy in POLICIES}
    testp={}
    for policy in POLICIES:
        prediction=evaluate_rule_model(transformed,rules,art.default_class,t,
            prediction_policy=policy,rule_weights=art.global_rule_weights,
            rule_support_sets=art.global_rule_support_sets,
            class_sizes=art.global_class_sizes)
        testp[policy]=np.asarray(prediction["predictions"],dtype=object)
    d=audit(art.train,rules,t)
    v=audit(art.test,rules,t)
    x=audit(transformed,rules,t)
    score={p:measured(val_y,valp[p])["balanced_accuracy"] for p in POLICIES}
    validation_best=max(POLICY_ORDER,key=lambda p:(score[p],-POLICY_ORDER.index(p)))
    orig_policy=DEFAULT_BASE[regime]
    selected,events,val_router=select_router(val_y,valp,v["buckets"],orig_policy)
    tst_router=apply_router(testp,x["buckets"],orig_policy,selected)
    assert all(len(z)==len(transformed) for z in testp.values())
    # Original G4 labels and effective rule edges reproduced exactly.
    decision={p:testp[p] for p in POLICIES}
    decision["VALIDATION_BEST"]=testp[validation_best]
    decision["CONFLICT_BUCKET_ROUTER_V1"]=tst_router
    core={
     "seed":seed,"scenario":regime,"discretizer":mode,
     "dev_rows":len(art.train),"val_rows":len(art.test),"test_rows":len(transformed),
     "n_rules":len(rules),"structural_fit_seconds":elapsed,
     "selected_feature_count":len(bundle.features),
     "continuous_features":len(bundle.schema.continuous),
     "categorical_features":len(bundle.schema.categorical),
     "test_coverage_pct":x["coverage_pct"],"dev_coverage_pct":d["coverage_pct"],
     "val_coverage_pct":v["coverage_pct"],
     "test_conflict_pct":x["conflict_pct"],"dev_conflict_pct":d["conflict_pct"],
     "val_conflict_pct":v["conflict_pct"],
     "test_correct_candidate_pct":x["correct_candidate_pct"],
     "test_no_match_pct":x["no_match_pct"],
     "train_val_fit_only":True,
     "source_client_quantiles_private_protocol":False if mode.startswith("EQUAL_FREQUENCY") or mode.startswith("ROBUST") else True,
     "effective_bins_mean":np.mean([len(fitted["preprocessor"]["bin_labels"][k])
                                      for k in bundle.schema.continuous])
            if bundle.schema.continuous else 0,
     "induction_full_POS_fraction":None
    }
    rows=[]
    for method,pred in decision.items():
        metrics=measured(tst_y,pred)
        rows.append({**core,"method":method,
            "test_ba_pct":100*metrics["balanced_accuracy"],
            "test_accuracy_pct":100*metrics["accuracy"],
            "test_macro_f1_pct":100*metrics["macro_f1"],
            "val_best_policy":validation_best,
            "router_selected_buckets":len(selected),
            "router_selection_json":json.dumps(selected,sort_keys=True),
            "router_val_ba_pct":100*measured(val_y,val_router)["balanced_accuracy"]})
    guards=[]
    if mode==BASELINE:
        for guard,params in GUARDS.items():
            which,training_prediction=guard_select(val_y,valp,v["buckets"],orig_policy,params)
            if guard=="ORIGINAL_G4":
                assert which==selected
                assert np.array_equal(training_prediction,val_router)
            pred=apply_router(testp,x["buckets"],orig_policy,which)
            scores=measured(tst_y,pred)
            guards.append({**core,"guard":guard,"gate_config":json.dumps(params,sort_keys=True),
              "selected_buckets":len(which),"selected_map":json.dumps(which,sort_keys=True),
              "test_ba_pct":100*scores["balanced_accuracy"],
              "test_accuracy_pct":100*scores["accuracy"],
              "test_macro_f1_pct":100*scores["macro_f1"],
              "val_ba_pct":100*measured(val_y,training_prediction)["balanced_accuracy"],
              "val_best_ba_pct":100*score[validation_best],
              "validation_best_policy":validation_best,
              "test_validation_best_ba_pct":100*measured(tst_y,testp[validation_best])["balanced_accuracy"]})
    return rows,guards

def run(name,output):
    dataset,sha=load_bundle(name)
    reg=REGISTRY[name]
    continuous=bool(dataset.schema.continuous)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    observed=[]
    gate=[]
    failures=[]
    original=pd.read_csv(ORIGINAL)
    original=original[original.dataset.eq(name)]
    for seed in SEEDS:
        rawtrain,rawtest=_split_raw(dataset,"HOLDOUT_80_20",seed,.2)
        dev,val=stratified_train_test_split(rawtrain,dataset.target,test_ratio=.2,seed=1000+seed)
        for regime in TARGET_SCENARIOS:
            expected=original[(original.seed==seed)&original.scenario.eq(regime)]
            assert len(expected)==9,(name,seed,regime)
            modes=BINS if continuous else (BASELINE,)
            for method in modes:
                try:
                    rows,guards=engine(dataset,dev,val,rawtest,seed,regime,method)
                    assert len(rows)==8
                    for r in rows:
                        r.update(dataset=name,source_sha256=sha,
                            selected_continuous_ratio=len(dataset.schema.continuous)/len(dataset.features),
                            study_track="A_DISCRETIZATION")
                    for r in guards:
                        r.update(dataset=name,source_sha256=sha,study_track="C_GUARD_ABLATION")
                    if method==BASELINE:
                        for r in rows:
                            if r["method"]=="CONFLICT_BUCKET_ROUTER_V1":
                                baseline=expected[expected.method.eq("CONFLICT_BUCKET_ROUTER_V1")].iloc[0]
                                assert abs(r["test_ba_pct"]-100*baseline.outer_test_balanced_accuracy)<2e-7
                                assert abs(r["test_coverage_pct"]-100*baseline.outer_test_coverage)<2e-7
                                assert abs(r["test_conflict_pct"]-100*baseline.outer_test_conflict)<2e-7
                        assert len(guards)==4
                    observed.extend(rows);gate.extend(guards)
                    print("A_BINS_C_GATES_PASS",name,seed,regime,method,
                        "n_rule",rows[0]["n_rules"],"cov",round(rows[0]["test_coverage_pct"],2),
                        "ba",round(rows[0]["test_ba_pct"],2),flush=True)
                except Exception as e:
                    failures.append({"seed":seed,"scenario":regime,"mode":method,
                         "type":type(e).__name__,"message":str(e)[:500]})
                    print("A_BINS_C_GATES_FAIL",name,seed,regime,method,
                          type(e).__name__,str(e)[:500],flush=True)
    df=pd.DataFrame(observed)
    if len(df):df.to_csv(out/f"ABLATION_A_{name}.csv",index=False)
    if gate:pd.DataFrame(gate).to_csv(out/f"ABLATION_C_{name}.csv",index=False)
    receipt={"dataset":name,"source_sha256":sha,
        "selected_feature_mode":f"{len(dataset.schema.continuous)}_NUMERIC_{len(dataset.schema.categorical)}_CATEGORICAL",
        "source_rows":len(dataset.frame),"continuous_experiment":continuous,
        "expected_models":len(SEEDS)*len(TARGET_SCENARIOS)*(len(BINS) if continuous else 1),
        "successful_models":len(observed)//8,
        "expected_guard_configs":len(SEEDS)*len(TARGET_SCENARIOS)*len(GUARDS),
        "actual_guard_configs":len(gate),
        "failures":failures,
        "warning":["Global quantiles use pooled raw development client values; no actual federated privacy protocol",
          "No Test labels are used for selecting preprocessing modes or router guard",
          "No supervised discretization in this exploratory A test",
          "Per method source feature count fixed; bins and learned rules change",
          "Do not select post hoc winner from Test as a deployable model"]}
    (out/f"RECEIPT_A_C_{name}.json").write_text(
        json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print("A_C_SOURCE_DONE",name,receipt["successful_models"],"of",
          receipt["expected_models"],"fails",len(failures),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--dataset",choices=sorted(REGISTRY),required=True)
    p.add_argument("--output",default="outputs/controlled_ablation")
    a=p.parse_args();run(a.dataset,a.output)
if __name__=="__main__":main()
