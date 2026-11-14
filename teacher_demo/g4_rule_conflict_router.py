"""G4 prospective conflict-structure policy router on new outer test seeds.

This is a NEW exploratory test, seeded 11/23, independent of earlier 1/7/42
split assignments (same public source tables, so not independent domains).
Uses no TEST labels for parameter selection. Baseline SV under nonIID and GS
under IID fixed from PRIOR benchmark; not discovered from this target test.

The six resolvers all use the identical original reduct/LEM2 rules. Routing
only changes predictions for pre-resolution multi-decision conflicts; exact
coverage and original conflict counts CANNOT change. No-Match is majority
fallback, not rejection. No claim of new rule induction or causal benefit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.app import _run_split
from roughset.evaluation import (
    balanced_accuracy, macro_f1_score,matching_rules,evaluate_rule_model
)
from roughset.preprocessing import apply_preprocessor
from roughset.splitting import stratified_train_test_split
from teacher_demo.full_factorial_matrix import POLICIES,_split_raw
from teacher_demo.conflict_aware_coverage_pilot import load_bundle
from teacher_demo.adaptive_six_policy_runner import POLICY_ORDER

SEEDS=(11,23)
REGIMES={"IID":("STRATIFIED",.5),
 "NONIID_05":("DIRICHLET_LABEL_SKEW",.5),
 "NONIID_01":("DIRICHLET_LABEL_SKEW",.1)}
DEFAULT_BASE={"IID":"GLOBAL_STRENGTH","NONIID_05":"SIMPLE_VOTING","NONIID_01":"SIMPLE_VOTING"}
MIN_CASES=10
MIN_EXTRA_CORRECT=2
MIN_BA_GAIN=0.002    # 0.2 percentage points on INNER validation only
MAX_VALIDATION_ACC_LOSS=.005
MAX_SWITCHES=2


def rule_buckets(frame,rules):
    buckets=[];candidate=[];coverage=[];conflict=[]
    for _,row in frame.iterrows():
        matched=matching_rules(row,rules)
        n=len(matched);d={str(x.decision) for x in matched}
        coverage.append(bool(n));candidate.append(d);conflict.append(len(d)>1)
        if len(d)<=1:buckets.append("NO_CONFLICT")
        elif len(d)>=3:buckets.append("THREE_PLUS_CLASSES")
        elif n>=4:buckets.append("TWO_CLASS_MANY_RULES")
        else:buckets.append("TWO_CLASS_FEW_RULES")
    return np.asarray(buckets),candidate,np.asarray(coverage),np.asarray(conflict)

def measured(y,pred):
    y=np.asarray(y,dtype=str);p=np.asarray(pred,dtype=str)
    assert len(y)==len(p) and len(y)>0
    return {"balanced_accuracy":float(balanced_accuracy(y,p)),
            "accuracy":float(np.mean(y==p)),"macro_f1":float(macro_f1_score(y,p))}

def select_router(y,validation_predictions,buckets,base):
    """Greedy guarded policy switch on up to 2 conflict-type buckets.

    Gate uses validation labels ONLY. It explicitly does NOT trade Coverage
    against Conflict; those are invariant for fixed rule sets.
    """
    assert set(validation_predictions)==set(POLICY_ORDER)
    preds={k:np.asarray(v,dtype=str) for k,v in validation_predictions.items()}
    labels=np.asarray(y,dtype=str)
    original=preds[base].copy();current=original.copy()
    score=measured(labels,current)
    selection={};receipts=[]
    for bucket in ("TWO_CLASS_FEW_RULES","TWO_CLASS_MANY_RULES","THREE_PLUS_CLASSES"):
        if len(selection)>=MAX_SWITCHES:break
        mask=np.asarray(buckets)==bucket
        n=int(mask.sum())
        if n<MIN_CASES:
            receipts.append({"bucket":bucket,"val_n":n,"accepted":False,
                            "reason":"INSUFFICIENT_VALIDATION_CONFLICT_CASES","selected":base})
            continue
        alternatives=[]
        for policy in POLICY_ORDER:
            if policy==base:continue
            trial=current.copy();trial[mask]=preds[policy][mask]
            gain=measured(labels,trial)
            new_correct=(trial[mask]==labels[mask]) & (current[mask]!=labels[mask])
            new_wrong=(trial[mask]!=labels[mask]) & (current[mask]==labels[mask])
            wins=int(new_correct.sum());losses=int(new_wrong.sum())
            allowed=(wins-losses>=MIN_EXTRA_CORRECT
                and gain["balanced_accuracy"]-score["balanced_accuracy"]>=MIN_BA_GAIN
                and gain["accuracy"]>=measured(labels,original)["accuracy"]-MAX_VALIDATION_ACC_LOSS)
            alternatives.append((allowed,gain["balanced_accuracy"]-score["balanced_accuracy"],
                                 wins-losses,-POLICY_ORDER.index(policy),policy,trial,gain,wins,losses))
        candidates=[v for v in alternatives if v[0]]
        if candidates:
            winning=max(candidates,key=lambda x:x[1:4])
            _,margin,net,_,policy,new_pred,new_score,wins,losses=winning
            selection[bucket]=policy;current=new_pred;score=new_score
            receipts.append({"bucket":bucket,"val_n":n,"accepted":True,
                "reason":"POSITIVE_VALIDATION_BA_AND_DISCORDANT_CASE_GATE",
                "selected":policy,"validation_gain_ba_pp":100*float(margin),
                "discordant_improved":wins,"discordant_harmed":losses})
        else:
            receipts.append({"bucket":bucket,"val_n":n,"accepted":False,
                            "reason":"NO_SUPPORTED_VALIDATION_GAIN","selected":base})
    assert not np.any((current!=original)&(np.asarray(buckets)=="NO_CONFLICT"))
    return selection,receipts,current

def apply_router(predictions,buckets,base,selection):
    result=np.asarray(predictions[base],dtype=str).copy()
    for bucket,policy in selection.items():
        mask=np.asarray(buckets)==bucket
        result[mask]=np.asarray(predictions[policy],dtype=str)[mask]
    assert not np.any((result!=np.asarray(predictions[base],dtype=str))&
                      (np.asarray(buckets)=="NO_CONFLICT"))
    return result

def evaluate_one(name,seed,regime,output):
    bundle,source_sha=load_bundle(name)
    train,test=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
    dev,val=stratified_train_test_split(train,bundle.target,test_ratio=.2,seed=1000+seed)
    sets=[set(x.__row_id__.astype(int)) for x in (dev,val,test)]
    assert not(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    part,alpha=REGIMES[regime]
    cfg["evaluation"].update(mode="HOLDOUT",seed=seed)
    cfg["experiment"].update(run_centralized=False,run_federated=True)
    cfg["federated"].update(n_clients=3,partition=part,
        dirichlet_alpha=alpha,run_client_sweep=False,order_sensitivity_max_permutations=1)
    fit=_run_split(bundle,dev,val,cfg,quiet=True,prediction_policies=POLICIES,fold=1)
    art=fit["structural_artifact"];rules=art.global_rules
    base=DEFAULT_BASE[regime]
    vb,vcan,vcover,vconf=rule_buckets(art.test,rules)
    val_preds={p:np.asarray(fit["policy_results"][p]["federated"]["predictions"],dtype=str)
               for p in POLICIES}
    yval=art.test[art.target].astype(str).to_numpy()
    assert all(len(p)==len(yval) for p in val_preds.values())
    val_scores={p:measured(yval,val_preds[p])["balanced_accuracy"] for p in POLICIES}
    val_best=max(POLICY_ORDER,key=lambda p:(val_scores[p],-POLICY_ORDER.index(p)))
    selection,events,final_val=select_router(yval,val_preds,vb,base)
    outer=apply_preprocessor(test,fit["preprocessor"],bundle.target)
    tb,tcan,tcover,tconf=rule_buckets(outer,rules)
    test_preds={}
    for policy in POLICIES:
        result=evaluate_rule_model(outer,rules,art.default_class,art.target,
            prediction_policy=policy,rule_weights=art.global_rule_weights,
            rule_support_sets=art.global_rule_support_sets,class_sizes=art.global_class_sizes)
        test_preds[policy]=np.asarray(result["predictions"],dtype=str)
    ytest=outer[art.target].astype(str).to_numpy()
    selected_pred=apply_router(test_preds,tb,base,selection)
    test_oracle=max(POLICY_ORDER,key=lambda p:measured(ytest,test_preds[p])["balanced_accuracy"])
    comparisons={**{("FIXED_"+policy):test_preds[policy] for policy in POLICIES},
        "VALIDATION_BEST":test_preds[val_best],
        "CONFLICT_BUCKET_ROUTER_V1":selected_pred,
        "TEST_ORACLE_DIAGNOSTIC":test_preds[test_oracle]}
    result_rows=[]
    for method,preds in comparisons.items():
        m=measured(ytest,preds)
        result_rows.append({
         "dataset":name,"seed":seed,"scenario":regime,"method":method,
         "base_policy":base,
         "selected_policy":val_best if method=="VALIDATION_BEST" else (
             test_oracle if method=="TEST_ORACLE_DIAGNOSTIC" else (
                 method.removeprefix("FIXED_") if method.startswith("FIXED_") else "BUCKET_ROUTER")),
         "validation_selected_bucket_rules":json.dumps(selection,sort_keys=True),
         "selected_bucket_count":len(selection),
         "validation_router_ba":measured(yval,final_val)["balanced_accuracy"],
         "inner_validation_conflict":float(vconf.mean()),
         "inner_validation_coverage":float(vcover.mean()),
         "outer_test_conflict":float(tconf.mean()),
         "outer_test_coverage":float(tcover.mean()),
         "outer_test_candidate_correct":float(np.mean([truth in labels for truth,labels in zip(ytest,tcan)])),
         "outer_test_balanced_accuracy":m["balanced_accuracy"],
         "outer_test_accuracy":m["accuracy"],"outer_test_macro_f1":m["macro_f1"],
         "dev_rows":len(art.train),"inner_rows":len(art.test),"outer_rows":len(outer),
         "rules":len(rules),"source_sha256":source_sha,
         "protocol":"NESTED_64_16_20_NOT_SAME_AS_PREVIOUS_3SEED_RESULTS",
         "is_deployable":method!="TEST_ORACLE_DIAGNOSTIC"
        })
    assert len(result_rows)==9
    folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(result_rows).to_csv(folder/f"G4_ROUTER_{name}_seed{seed}_{regime}.csv",index=False)
    (folder/f"G4_EVENTS_{name}_seed{seed}_{regime}.json").write_text(
        json.dumps({"dataset":name,"seed":seed,"scenario":regime,
           "selection":selection,"validation_gate_events":events,
           "source_sha256":source_sha},ensure_ascii=False,indent=2),encoding="utf-8")
    print("G4_CONFLICT_ROUTER_ACTUAL_PASS",name,seed,regime,
          "val_conflict",round(vconf.mean(),3),"test_base",
          round(measured(ytest,test_preds[base])["balanced_accuracy"],4),
          "test_router",round(measured(ytest,selected_pred)["balanced_accuracy"],4),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",required=True)
    p.add_argument("--seeds",default="11,23")
    p.add_argument("--scenarios",default="IID,NONIID_05,NONIID_01")
    p.add_argument("--output",default="outputs/g4_router")
    a=p.parse_args()
    for seed in map(int,a.seeds.split(",")):
        if seed not in SEEDS:raise ValueError("Only predetermined fresh seeds")
        for regime in a.scenarios.split(","):
            if regime not in REGIMES:raise ValueError("Bad regime")
            evaluate_one(a.dataset,seed,regime,a.output)
if __name__=="__main__":main()
