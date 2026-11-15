"""B: categorical missing-token intervention, without altering source/split/clients.

Only two prepared UCI sources contain selected-feature missing markers:
adult_income and bank_marketing. This is NOT a raw UCI missingness study.

Treatments:
 PRESERVE: canonical literal category markers
 TRAIN_MODE: categorical per-feature mode FIT ON DEV ONLY
 INDICATOR: preserve marker plus a new binary feature fitted as fixed sentinel
            (note: increases feature dimensionality and influences reduct).
The missing label identities are public-source data conventions, not proof
of unknown underlying raw data. For all cases use G4 64/16/20 splits and
same seed client partition; no Test label used in fitting or policy selection.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.adapters import DatasetBundle
from roughset.app import _run_split
from roughset.evaluation import evaluate_rule_model
from roughset.preprocessing import apply_preprocessor
from roughset.schema import DatasetSchema
from roughset.splitting import stratified_train_test_split
from teacher_demo.full_factorial_matrix import _split_raw,POLICIES
from teacher_demo.conflict_aware_coverage_pilot import load_bundle
from teacher_demo.g4_rule_conflict_router import (
   REGIMES,DEFAULT_BASE,SEEDS,rule_buckets,measured,select_router,apply_router
)
from teacher_demo.adaptive_six_policy_runner import POLICY_ORDER

DATASETS=("adult_income","bank_marketing")
SCENARIOS=("NONIID_05","NONIID_01")
TREATMENTS=("PRESERVE","TRAIN_MODE","INDICATOR")
TOKENS={"","?","__missing_feature__","__missing__","na","n/a","none","null","nan","<na>"}
G4=Path("docs/research/teacher_dashboard/data/G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv")

def identify(df,columns):
    return {c:int(df[c].astype(str).str.strip().str.lower().isin(TOKENS).sum()) for c in columns}
def transform(bundle,dev,val,test,method):
    cat=list(bundle.schema.categorical)
    all_known=identify(bundle.frame,cat)
    relevant=[k for k,v in all_known.items() if v>0]
    assert relevant,(bundle.name,"none in prepared CSV")
    work=[x.copy() for x in (dev,val,test)]
    training_decisions={}
    if method=="TRAIN_MODE":
        for col in relevant:
            values=work[0][col].astype(str).str.strip()
            bad=values.str.lower().isin(TOKENS)
            candidates=values[~bad]
            if candidates.empty:raise ValueError("NO_NONMISSING_TRAIN_MODE:"+col)
            counts=candidates.value_counts()
            # stable tie-break; original categorical values may be multi-language
            best=sorted(counts[counts==counts.max()].index,key=str)[0]
            training_decisions[col]=str(best)
            for table in work:
                mask=table[col].astype(str).str.strip().str.lower().isin(TOKENS)
                table.loc[mask,col]=str(best)
    elif method=="INDICATOR":
        for col in relevant:
            new=col+"__was_missing"
            assert new not in bundle.features
            training_decisions[col]="BINARY_MISSING_INDICATOR_ONLY"
            for table in work:
                bad=table[col].astype(str).str.strip().str.lower().isin(TOKENS)
                table[new]=np.where(bad,"1","0")
    elif method!="PRESERVE":raise ValueError(method)
    extra=[c+"__was_missing" for c in relevant] if method=="INDICATOR" else []
    features=list(bundle.features)+extra
    schema=DatasetSchema(target=bundle.target,features=features,
           continuous=list(bundle.schema.continuous),
           categorical=list(bundle.schema.categorical)+extra)
    newbundle=DatasetBundle(bundle.name,bundle.frame,features,bundle.target,schema,bundle.source)
    assert all(len(x)==len(y) for x,y in zip(work,(dev,val,test)))
    assert all(work[0][bundle.target].astype(str).equals(dev[bundle.target].astype(str)) for _ in [0])
    return newbundle,*work,all_known,training_decisions

def coverage(frame,rules):
    _,candidates,matched,conflict=rule_buckets(frame,rules)
    return float(100*matched.mean()),float(100*conflict.mean())

def run(name,out):
    bundle,sha=load_bundle(name)
    selected_categorical=list(bundle.schema.categorical)
    marker_count=sum(identify(bundle.frame,selected_categorical).values())
    assert marker_count>0
    raw=pd.read_csv(G4)
    raw=raw[raw.dataset.eq(name)]
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    outrows=[];errors=[]
    for seed in SEEDS:
        rawtrain,rawtest=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
        dev,val=stratified_train_test_split(rawtrain,bundle.target,test_ratio=.2,seed=1000+seed)
        for scenario in SCENARIOS:
            strategy,alpha=REGIMES[scenario]
            for variant in TREATMENTS:
                try:
                    adjusted,d,v,t,origmarkers,mode_decisions=transform(bundle,dev,val,rawtest,variant)
                    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
                    cfg["evaluation"].update(mode="HOLDOUT",seed=seed)
                    cfg["experiment"].update(run_centralized=False,run_federated=True)
                    cfg["federated"].update(n_clients=3,partition=strategy,
                        dirichlet_alpha=alpha,run_client_sweep=False,order_sensitivity_max_permutations=1)
                    fit=_run_split(adjusted,d,v,cfg,quiet=True,prediction_policies=POLICIES,fold=1)
                    a=fit["structural_artifact"]
                    transformed=apply_preprocessor(t,fit["preprocessor"],adjusted.target)
                    d_cov,d_conf=coverage(a.train,a.global_rules)
                    v_cov,v_conf=coverage(a.test,a.global_rules)
                    t_cov,t_conf=coverage(transformed,a.global_rules)
                    labels_val=a.test[a.target].astype(str).to_numpy()
                    labels_test=transformed[a.target].astype(str).to_numpy()
                    valp={p:np.asarray(fit["policy_results"][p]["federated"]["predictions"],dtype=object)
                          for p in POLICIES}
                    testp={}
                    for p in POLICIES:
                        e=evaluate_rule_model(transformed,a.global_rules,a.default_class,a.target,
                            prediction_policy=p,rule_weights=a.global_rule_weights,
                            rule_support_sets=a.global_rule_support_sets,
                            class_sizes=a.global_class_sizes)
                        testp[p]=np.asarray(e["predictions"],dtype=object)
                    val_scores={p:measured(labels_val,valp[p])["balanced_accuracy"] for p in POLICIES}
                    best=max(POLICY_ORDER,key=lambda p:(val_scores[p],-POLICY_ORDER.index(p)))
                    valb,_,_,_=rule_buckets(a.test,a.global_rules)
                    testb,_,_,_=rule_buckets(transformed,a.global_rules)
                    switches,_,_=select_router(labels_val,valp,valb,DEFAULT_BASE[scenario])
                    rp=apply_router(testp,testb,DEFAULT_BASE[scenario],switches)
                    candidates={**testp,"VALIDATION_BEST":testp[best],"CONFLICT_BUCKET_ROUTER_V1":rp}
                    for policy,pred in candidates.items():
                        score=measured(labels_test,pred)
                        row={"dataset":name,"seed":seed,"scenario":scenario,"missing_treatment":variant,
                          "method":policy,"source_sha256":sha,"input_missing_marker_cells":marker_count,
                          "categorical_missing_columns":";".join(k for k,n in origmarkers.items() if n>0),
                          "fitted_train_mode_json":json.dumps(mode_decisions,sort_keys=True),
                          "dev_rows":len(d),"val_rows":len(v),"test_rows":len(t),
                          "selected_features":len(adjusted.features),"rule_count":len(a.global_rules),
                          "dev_coverage_pct":d_cov,"val_coverage_pct":v_cov,
                          "test_coverage_pct":t_cov,"test_conflict_pct":t_conf,
                          "test_ba_pct":score["balanced_accuracy"]*100,
                          "test_accuracy_pct":score["accuracy"]*100,
                          "test_macro_f1_pct":score["macro_f1"]*100,
                          "validation_best_policy":best,
                          "router_buckets_switched":len(switches),
                          "test_used_for_fit":False}
                        outrows.append(row)
                    if variant=="PRESERVE":
                        original=raw[(raw.seed==seed)&raw.scenario.eq(scenario)]
                        assert len(original)==9
                        baseline=original[original.method.eq("CONFLICT_BUCKET_ROUTER_V1")].iloc[0]
                        got=outrows[-1]
                        assert abs(got["test_ba_pct"]-100*baseline.outer_test_balanced_accuracy)<2e-7
                        assert abs(t_cov-100*baseline.outer_test_coverage)<2e-7
                    print("B_MISSING_TREATMENT_PASS",name,seed,scenario,variant,
                          "rules",len(a.global_rules),flush=True)
                except Exception as e:
                    errors.append({"dataset":name,"seed":seed,"scenario":scenario,
                                   "treatment":variant,"type":type(e).__name__,"reason":str(e)[:500]})
                    print("B_MISSING_TREATMENT_FAIL",name,seed,scenario,variant,
                           type(e).__name__,str(e)[:250],flush=True)
    pd.DataFrame(outrows).to_csv(output/f"ABLATION_B_{name}.csv",index=False)
    summary={"dataset":name,"source_sha256":sha,
       "input_missing_marker_cells":marker_count,
       "expected_models":len(SEEDS)*len(SCENARIOS)*len(TREATMENTS),
       "successful_models":len(outrows)//8,"failures":errors,
       "semantics":"NOT_RAW_SOURCE_UCI_MISSINGNESS",
       "caution":"Missing-as-indicator changes feature count and is not isolated solely to value imputation",
       "test_label_tuning":False}
    (output/f"RECEIPT_B_{name}.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("B_MISSING_DATA_CONTROLLED_DONE",name,summary["successful_models"],flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--dataset",required=True,choices=DATASETS)
    p.add_argument("--output",default="outputs/controlled_missing")
    a=p.parse_args();run(a.dataset,a.output)

if __name__=="__main__":main()
