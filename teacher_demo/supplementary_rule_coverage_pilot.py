"""Independent feasibility POC: train-only one-condition-drop supplementary rules.

NOT a reproduction of Inuiguchi & Washimi's MLEM2 supplementary-rule algorithm.
Same frozen original Classical reduct + LEM2 rules. Additional rules are
generated, validated and scored solely on the SAME TRAIN split.
Evaluation on holdout TEST never affects rule selection or scoring.

Use for causality: exact rule coverage, augmentation coverage, no-match fallback
and accuracy must all be measured separately; more matches != more correctness.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from roughset.app import _run_split
from roughset.core import Rule
from roughset.evaluation import matching_rules, classification_accuracy, balanced_accuracy, macro_f1_score
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _split_raw

@dataclass(frozen=True)
class Supplement:
    conditions: tuple
    decision: str
    support: int
    correct: int
    purity: float
    source_rules: int

def generate(train, original_rules, target, min_support=5, min_purity=.9, max_candidates=500):
    """Relax exactly one antecedent; validate precision using TRAIN ONLY."""
    if not 0.0<min_purity<=1.0:raise ValueError("Bad purity threshold")
    candidates=defaultdict(set)
    for i,r in enumerate(original_rules):
        if len(r.conditions)<2:continue
        for drop in range(len(r.conditions)):
            condition=tuple(sorted(r.conditions[:drop]+r.conditions[drop+1:]))
            if not condition:continue
            candidates[(condition,str(r.decision))].add(i)
    scored=[]
    for (conds,label),source_ids in candidates.items():
        mask=np.ones(len(train),dtype=bool)
        for feature,value in conds:
            mask&=train[feature].astype(str).to_numpy()==str(value)
        n=int(mask.sum())
        if n<min_support:continue
        truth=train[target].astype(str).to_numpy()
        correct=int((truth[mask]==label).sum())
        purity=correct/n
        if purity+1e-12<min_purity:continue
        scored.append(Supplement(conds,label,n,correct,purity,len(source_ids)))
    scored.sort(key=lambda r:(-r.purity,-r.correct,-len(r.conditions),r.decision,str(r.conditions)))
    return scored[:max_candidates],len(candidates)

def match_supp(row,supp):
    return all(str(row[a])==str(v) for a,v in supp.conditions)

def extend_predict(data,original_rules,supplements,orig_preds,default_class,target):
    exact_matches=[bool(matching_rules(row,original_rules)) for _,row in data.iterrows()]
    final=list(map(str,orig_preds))
    rescued=np.zeros(len(data),dtype=bool)
    changed=np.zeros(len(data),dtype=bool)
    new_conflicts=np.zeros(len(data),dtype=bool)
    for pos,(_,row) in enumerate(data.iterrows()):
        if exact_matches[pos]:continue
        ms=[rule for rule in supplements if match_supp(row,rule)]
        if not ms:continue
        rescued[pos]=True
        # Predefined score, with a rule-precision priority, then train-support.
        scores={}
        for cand in ms:
            old=scores.get(cand.decision,(-1,-1))
            scores[cand.decision]=max(old,(cand.purity,cand.correct))
        high=max(scores.values())
        winners=sorted(label for label,score in scores.items() if
                       np.isclose(score[0],high[0]) and score[1]==high[1])
        final[pos]=str(default_class) if str(default_class) in winners else winners[0]
        new_conflicts[pos]=len(scores)>1
        changed[pos]=final[pos]!=str(orig_preds[pos])
    truth=data[target].astype(str).to_numpy()
    exact=np.asarray(exact_matches,dtype=bool)
    n=len(data)
    accepted=exact|rescued
    sel_correct=(np.asarray(final,dtype=str)==truth)
    baseline_correct=(np.asarray(orig_preds,dtype=str)==truth)
    return {
      "original_exact_covered":int(exact.sum()),
      "augmented_covered":int(accepted.sum()),
      "rescued_count":int(rescued.sum()),
      "rescued_correct":int(np.sum(sel_correct&rescued)),
      "rescued_original_fallback_correct":int(np.sum(baseline_correct&rescued)),
      "rescued_new_conflict_count":int(np.sum(new_conflicts&rescued)),
      "changed_prediction_count":int(changed.sum()),
      "original_exact_coverage":float(exact.mean()),
      "augmented_coverage":float(accepted.mean()),
      "added_coverage_pp":float(100*rescued.mean()),
      "original_no_match_count":int(n-exact.sum()),
      "remaining_unmatched_count":int(n-accepted.sum()),
      "postaugmentation_reject_if_abstain_pct":float(100*(1-accepted.mean())),
      "baseline_accuracy":classification_accuracy(truth,orig_preds),
      "new_accuracy":classification_accuracy(truth,final),
      "baseline_balanced_accuracy":balanced_accuracy(truth,orig_preds),
      "new_balanced_accuracy":balanced_accuracy(truth,final),
      "baseline_macro_f1":macro_f1_score(truth,orig_preds),
      "new_macro_f1":macro_f1_score(truth,final),
      "augmented_accepted_only_accuracy":float(sel_correct[accepted].mean()) if accepted.any() else float("nan"),
      "baseline_accepted_only_accuracy":float(baseline_correct[exact].mean()) if exact.any() else float("nan"),
      "accuracy_gain_pp":float(100*(sel_correct.mean()-baseline_correct.mean())),
      "balanced_accuracy_gain_pp":float(100*(balanced_accuracy(truth,final)-balanced_accuracy(truth,orig_preds))),
      "n":n
    }

def run_one(bundle,seed,architecture,clients,params):
    config=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    config["evaluation"]["seed"]=seed
    config["evaluation"]["mode"]="HOLDOUT_80_20"
    config["federated"]["partition"]="STRATIFIED"
    config["federated"]["run_client_sweep"]=False
    config["federated"]["order_sensitivity_max_permutations"]=1
    config["experiment"]["run_centralized"]=architecture=="CENTRALIZED"
    config["experiment"]["run_federated"]=architecture=="FEDERATED"
    config["federated"]["n_clients"]=clients
    train,test=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
    r=_run_split(bundle,train,test,config,quiet=True,prediction_policies=("GLOBAL_STRENGTH",))
    art=r["structural_artifact"]
    assert not set(train["__row_id__"])&set(test["__row_id__"])
    rules=art.central_rules if architecture=="CENTRALIZED" else art.global_rules
    default=art.central_default_class if architecture=="CENTRALIZED" else art.default_class
    key="centralized" if architecture=="CENTRALIZED" else "federated"
    original_preds=r["policy_results"]["GLOBAL_STRENGTH"][key]["predictions"]
    out=[]
    for purity in params:
        sp,ncandidate=generate(art.train,rules,art.target,min_support=5,min_purity=purity)
        test_metrics=extend_predict(art.test,rules,sp,original_preds,default,art.target)
        # Train baseline predictions must come from FROZEN rules, not test objects.
        # For coverage we need only whether ANY rule antecedent matches each train case.
        tr_cov=np.mean([bool(matching_rules(row,rules)) for _,row in art.train.iterrows()])
        out.append({
         "dataset":bundle.name,"seed":seed,"system":architecture,"client_count":clients,
         "method":"CLASSICAL_LEM2_TRAIN_ONLY_SUPPLEMENTAL_POC","baseline_policy":"GLOBAL_STRENGTH",
         "split_mode":"HOLDOUT_80_20","min_purity":purity,"min_support":5,
         "candidate_proposals":ncandidate,"supplemental_rules":len(sp),"original_rules":len(rules),
         "train_rows":len(art.train),"test_rows":len(art.test),"train_original_exact_coverage":tr_cov,
         **test_metrics
        })
        assert out[-1]["original_exact_covered"]<=out[-1]["augmented_covered"]
        assert out[-1]["augmented_covered"]<=out[-1]["test_rows"]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,required=True)
    ap.add_argument("--output",default="outputs/supplementary_rule_pilot")
    opt=ap.parse_args()
    if opt.seed not in (1,42):raise ValueError("pilot accepts only seeds 1 and 42")
    records=[]
    for bundle in pinned_bundles():
        for system,c in (("CENTRALIZED",0),("FEDERATED",3)):
            records+=run_one(bundle,opt.seed,system,c,[1.0,0.9])
            print("SUPPLEMENTAL_CONFIG_PASS",bundle.name,opt.seed,system,c,flush=True)
    assert len(records)==3*2*2
    out=Path(opt.output);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(records).to_csv(out/f"SUPPLEMENTARY_RESULTS_seed{opt.seed:02}.csv",index=False)
    print("SUPPLEMENTARY_TRAIN_ONLY_PILOT_PASS",opt.seed,len(records),flush=True)

if __name__=="__main__":
    main()
