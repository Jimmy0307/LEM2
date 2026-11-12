"""Holdout-only train/test rule coverage gap and fixed partial-match rescue pilot.

No test-time fitting: rule system, support weights and defaults are trained once
on train only; the threshold is predeclared, NOT chosen by looking at test.
This is a new experimental fallback, not VC-DRSA or original MLEM2 supplements.
"""
from __future__ import annotations
import argparse
import json
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.app import _run_split
from roughset.evaluation import matching_rules
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _split_raw

THRESHOLDS=(0.5,0.75)
STRUCTURES=(("CENTRALIZED",0),("FEDERATED",3),("FEDERATED",5))

def match_fraction(row, rule):
    if not rule.conditions:return 1.0
    return sum(str(row[a])==str(v) for a,v in rule.conditions)/len(rule.conditions)

def propose_partial(row,rules,support,default,threshold):
    """Rule-level antecedent similarity; tie-break using TRAIN supports only."""
    ranked=[]
    for r in rules:
        s=match_fraction(row,r)
        if s+1e-12<threshold:continue
        weight=len(support.get(r.key,()))
        ranked.append((s,weight,str(r.decision)))
    if not ranked:return None
    highest=max(s for s,_,_ in ranked)
    top=[(w,c) for s,w,c in ranked if abs(s-highest)<1e-12]
    byclass={}
    for weight,clazz in top:byclass[clazz]=byclass.get(clazz,0)+weight
    vmax=max(byclass.values())
    winners=sorted([x for x in byclass if byclass[x]==vmax])
    return str(default) if str(default) in winners else winners[0]

def flags(table,rules,target):
    n=len(table);match=[];candidate=[]
    for _,row in table.iterrows():
        m=matching_rules(row,rules)
        match.append(bool(m))
        candidate.append(str(row[target]) in {str(r.decision) for r in m})
    return np.array(match,dtype=bool),np.array(candidate,dtype=bool)

def compute(bundle,seed,system,client_count,cfg):
    train,test=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
    config=deepcopy(cfg)
    config["evaluation"]["seed"]=seed
    config["evaluation"]["mode"]="HOLDOUT"
    config["experiment"]["run_centralized"]=system=="CENTRALIZED"
    config["experiment"]["run_federated"]=system=="FEDERATED"
    config["federated"]["n_clients"]=client_count
    config["federated"]["partition"]="STRATIFIED"
    config["federated"]["run_client_sweep"]=False
    config["federated"]["order_sensitivity_max_permutations"]=1
    result=_run_split(bundle,train,test,config,quiet=True,prediction_policies=("GLOBAL_STRENGTH",))
    a=result["structural_artifact"]
    rules=a.central_rules if system=="CENTRALIZED" else a.global_rules
    supports=a.central_rule_support_sets if system=="CENTRALIZED" else a.global_rule_support_sets
    default=a.central_default_class if system=="CENTRALIZED" else a.default_class
    train_has,train_candidate=flags(a.train,rules,a.target)
    test_has,test_candidate=flags(a.test,rules,a.target)
    original=result["policy_results"]["GLOBAL_STRENGTH"]["centralized" if system=="CENTRALIZED" else "federated"]
    truth=a.test[a.target].astype(str).to_numpy()
    old=np.array([str(x) for x in original["predictions"]])
    base={
      "dataset":bundle.name,"seed":seed,"split_mode":"HOLDOUT_80_20",
      "method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
      "system":system,"client_count":client_count,
      "train_rows":len(a.train),"test_rows":len(a.test),"rule_count":len(rules),
      "train_rule_coverage_pct":100*train_has.mean(),"test_rule_coverage_pct":100*test_has.mean(),
      "test_minus_train_coverage_pp":100*(test_has.mean()-train_has.mean()),
      "train_candidate_coverage_pct":100*train_candidate.mean(),
      "test_candidate_coverage_pct":100*test_candidate.mean(),
      "test_no_match_count":int((~test_has).sum()),
      "test_no_match_pct":100*(~test_has).mean(),
      "test_conflict_pct":100*float(original["conflict_case_rate"]),
      "baseline_accuracy_pct":100*(old==truth).mean(),
      "baseline_fallback_correct_count":int(((~test_has)&(old==truth)).sum()),
      "baseline_fallback_accuracy_pct":100*((old[~test_has]==truth[~test_has]).mean()) if (~test_has).any() else np.nan
    }
    rows=[]
    for threshold in THRESHOLDS:
        preds=old.copy();accepted=test_has.copy();rescued=0;rescued_correct=0
        for i,(_,row) in enumerate(a.test.iterrows()):
            if test_has[i]:continue
            candidate=propose_partial(row,rules,supports,default,threshold)
            if candidate is None:continue
            preds[i]=candidate;accepted[i]=True;rescued+=1
            rescued_correct+=int(candidate==truth[i])
        rows.append({**base,"rescue":"PARTIAL_RULE_MATCH_TRAIN_SUPPORT",
          "match_threshold":threshold,
          "after_coverage_pct":100*accepted.mean(),
          "coverage_gain_pp":100*(accepted.mean()-test_has.mean()),
          "remaining_reject_count":int((~accepted).sum()),
          "remaining_reject_pct":100*(~accepted).mean(),
          "newly_accepted_count":rescued,
          "newly_accepted_accuracy_pct":100*rescued_correct/rescued if rescued else np.nan,
          "all_test_accuracy_pct":100*(preds==truth).mean(),
          "accuracy_delta_pp":100*((preds==truth).mean()-(old==truth).mean()),
          "accepted_only_accuracy_pct":100*(preds[accepted]==truth[accepted]).mean() if accepted.any() else np.nan,
          "status":"PILOT_NOT_VALIDATED_THRESHOLD"
        })
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,required=True,choices=(1,7,42))
    p.add_argument("--output",default="outputs/coverage_rescue")
    args=p.parse_args()
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    results=[];errors=[]
    for b in pinned_bundles():
        for system,c in STRUCTURES:
            try:
                results.extend(compute(b,args.seed,system,c,cfg))
                print("COVERAGE_GAP_PILOT_PASS",b.name,args.seed,system,c,flush=True)
            except (ValueError,RuntimeError) as exc:
                errors.append({"dataset":b.name,"seed":args.seed,"system":system,"client_count":c,"error":str(exc)})
                print("COVERAGE_GAP_PILOT_INVALID",b.name,args.seed,system,c,str(exc),flush=True)
    dest=Path(args.output);dest.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(results).to_csv(dest/f"COVERAGE_RESCUE_seed{args.seed:02d}.csv",index=False)
    pd.DataFrame(errors,columns=["dataset","seed","system","client_count","error"]).to_csv(dest/f"COVERAGE_RESCUE_ERRORS_seed{args.seed:02d}.csv",index=False)
    assert len(results)+2*len(errors)==3*3*2
    print("COVERAGE_RESCUE_PILOT_COMPLETE",args.seed,len(results),len(errors),flush=True)

if __name__=="__main__":main()
