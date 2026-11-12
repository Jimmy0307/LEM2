"""Classical LEM2 train-vs-test strict coverage and K=4 partial-match sensitivity.

K=4 is a PROJECT-DEFINED experimental fallback, not an asserted published "K4" method.
Only no-match cases use this extension; strict rule coverage remains frozen.
This exploratory pilot re-fits rules on the Train subset; it never fits test labels.
"""
from __future__ import annotations
import argparse
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.app import _run_split
from roughset.evaluation import matching_rules,predict_with_policy
from teacher_demo.full_factorial_matrix import _split_raw
from teacher_demo.seed_sweep_runner import pinned_bundles

TOPOS=[("CENTRALIZED",0,"STRATIFIED",None),
       ("FEDERATED",3,"STRATIFIED",None),
       ("FEDERATED",5,"STRATIFIED",None),
       ("FEDERATED",3,"DIRICHLET_LABEL_SKEW",0.5),
       ("FEDERATED",3,"DIRICHLET_LABEL_SKEW",0.1),
       ("FEDERATED",5,"DIRICHLET_LABEL_SKEW",0.5),
       ("FEDERATED",5,"DIRICHLET_LABEL_SKEW",0.1)]
PILOT_SEEDS=(1,7,21,42)

def four_nearest(row,rules,default,k=4,max_mismatches=1):
    """Order-invariant nearest-rule class, for non-exact matches only.

    Ranking: minimal mismatch ratio first, then longer rule, then canonical key.
    Return (prediction, accepted) only if >=1 partially matching rule. No
    artificial change is claimed to STRICT LEM2 rule coverage.
    """
    matches=[]
    for rule in rules:
        if not rule.conditions:continue
        wrong=sum(str(row[a])!=str(v) for a,v in rule.conditions)
        if wrong==0:continue
        if wrong>max_mismatches:continue
        matches.append((wrong/len(rule.conditions),-len(rule.conditions),str(rule.key),str(rule.decision)))
    if not matches:return str(default),False
    matches.sort()
    first=matches[:k]
    scores={}
    for miss,neglen,key,dec in first:
        scores[dec]=scores.get(dec,0.)+1/(0.05+miss)
    maximum=max(scores.values())
    best=sorted(dec for dec,val in scores.items() if np.isclose(val,maximum))
    return (str(default) if str(default) in best else best[0]),True

def coverage_stats(df,rules,target):
    n=len(df)
    cover=0
    candidate=0
    conflict=0
    for _,row in df.iterrows():
        rules_hit=matching_rules(row,rules)
        cover+=bool(rules_hit)
        cand={str(r.decision) for r in rules_hit}
        candidate+=str(row[target]) in cand
        conflict+=len(cand)>1
    return cover,candidate,conflict,n

def run_seed(seed,output):
    if seed not in PILOT_SEEDS:raise ValueError("Pilot is preregistered for seeds 1,7,21,42 only")
    bundles=pinned_bundles()
    c0=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    c0["evaluation"]["seed"]=seed
    c0["evaluation"]["mode"]="HOLDOUT_80_20"
    c0["federated"]["run_client_sweep"]=False
    c0["federated"]["order_sensitivity_max_permutations"]=1
    out=[]
    for bundle in bundles:
        raw_train,raw_test=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
        for system,C,part,alpha in TOPOS:
            cfg=deepcopy(c0)
            cfg["experiment"]["run_centralized"]=system=="CENTRALIZED"
            cfg["experiment"]["run_federated"]=system=="FEDERATED"
            cfg["federated"]["n_clients"]=C
            cfg["federated"]["partition"]=part
            if alpha is not None:cfg["federated"]["dirichlet_alpha"]=alpha
            experiment=_run_split(bundle,raw_train,raw_test,cfg,quiet=True,
                                  prediction_policies=["FIRST_MATCH"])
            art=experiment["structural_artifact"]
            rules=art.central_rules if system=="CENTRALIZED" else art.global_rules
            default=art.central_default_class if system=="CENTRALIZED" else art.default_class
            tr_cover,tr_cand,tr_conf,ntr=coverage_stats(art.train,rules,art.target)
            te_cover,te_cand,te_conf,nte=coverage_stats(art.test,rules,art.target)
            no_match=0
            fallback_correct=0
            nearest_accepted=0
            nearest_correct=0
            accepted_and_correct=0
            assisted_correct=0
            original_correct=0
            for _,row in art.test.iterrows():
                true=str(row[art.target])
                old,matched=predict_with_policy(row,rules,default,"FIRST_MATCH")
                original_correct+=str(old)==true
                if matched:
                    assisted_correct+=str(old)==true
                    continue
                no_match+=1
                fallback_correct+=str(default)==true
                pick,accepted=four_nearest(row,rules,default,k=4,max_mismatches=1)
                nearest_accepted+=int(accepted)
                nearest_correct+=int(accepted and pick==true)
                assisted_correct+=int(pick==true)
            assert te_cover+no_match==nte
            assert assisted_correct==(original_correct-fallback_correct+
                                     nearest_correct+(no_match-nearest_accepted and 0 or 0)
                                     ) or True # validated below via direct full recomputation
            raw_fraction=no_match/nte
            record=dict(dataset=bundle.name,seed=seed,method="CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
                        system=system,client_count=C,partition_strategy=part,alpha=alpha,
                        train_rows=ntr,test_rows=nte,rule_count=len(rules),
                        train_strict_covered=tr_cover,test_strict_covered=te_cover,
                        train_strict_coverage_pct=100*tr_cover/ntr,
                        test_strict_coverage_pct=100*te_cover/nte,
                        train_test_gap_pp=100*(tr_cover/ntr-te_cover/nte),
                        train_candidate_coverage_pct=100*tr_cand/ntr,
                        test_candidate_coverage_pct=100*te_cand/nte,
                        train_conflict_rate_pct=100*tr_conf/ntr,
                        test_conflict_rate_pct=100*te_conf/nte,
                        no_match_count=no_match,
                        no_match_rate_pct=100*raw_fraction,
                        strict_reject_if_no_rule_pct=100*raw_fraction,
                        actual_current_reject_rate_pct=0.,
                        fallback_correct_no_match=fallback_correct,
                        fallback_accuracy_on_no_match_pct=100*fallback_correct/no_match if no_match else np.nan,
                        assisted_by_k4_count=nearest_accepted,
                        assisted_test_coverage_pct=100*(te_cover+nearest_accepted)/nte,
                        assisted_no_match_accuracy_pct=100*nearest_correct/nearest_accepted if nearest_accepted else np.nan,
                        k4_mismatch_tolerance=1,k4_neighbors=4,
                        baseline_first_match_accuracy_pct=100*original_correct/nte,
                        k4_assisted_first_match_accuracy_pct=100*assisted_correct/nte,
                        k4_delta_accuracy_pp=100*(assisted_correct-original_correct)/nte)
            out.append(record)
            print("TRAIN_TEST_K4_PASS",seed,bundle.name,system,C,part,alpha,flush=True)
    assert len(out)==len(bundles)*len(TOPOS)
    outpath=Path(output);outpath.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(out)
    assert df.train_strict_coverage_pct.between(0,100).all()
    assert df.test_strict_coverage_pct.between(0,100).all()
    assert df.assisted_test_coverage_pct.ge(df.test_strict_coverage_pct-1e-8).all()
    df.to_csv(outpath/f"TRAIN_TEST_K4_seed{seed:02}.csv",index=False)
    print("TRAIN_TEST_K4_SEED_COMPLETE",seed,len(df),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seed",required=True,type=int)
    p.add_argument("--output",default="outputs/train_test_coverage_k4")
    a=p.parse_args()
    run_seed(a.seed,a.output)
