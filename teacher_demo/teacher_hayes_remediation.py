"""Hayes–Roth remedial evaluation: official fixed 132/28 and group-disjoint 80:20.

Source: UCI dataset 44, https://doi.org/10.24432/C5501T.
Keeps the frozen 8820 experiment intact. The official file has five columns:
hobby, age, educational_level, marital_status, class; training .data adds an ID.
Each run uses the same project's _run_split (train-only preprocessing, reduct, LEM2,
client partition, full rule union, matching, six policies). No speculative scores.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.app import _run_split
from roughset.evaluation import matching_rules
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import POLICIES

DATA = Path("research/seed_sweep_inputs/uci_44_hayes_roth_official28.test")
OUTPUT_ROOT = Path("outputs/teacher_hayes_remediation")
EXPECTED_SHA256 = "" # Provenance recorded at runtime; do not fabricate an expected checksum.

def source_bundle():
    b=[b for b in pinned_bundles() if b.name=="Hayes-Roth"]
    assert len(b)==1
    return b[0]

def official_partition(bundle):
    original=bundle.frame.copy().reset_index(drop=True)
    original["__row_id__"]=np.arange(132,dtype=int)
    test=pd.read_csv(DATA,header=None, dtype="int64",
                     names=["hobby","age","educational_level","marital_status","class"])
    assert test.shape==(28,5),test.shape
    assert len(original)==132
    assert set(bundle.features)==set(test.columns)-{"class"}
    test=test[bundle.features+[bundle.target]].copy()
    assert test.notna().all().all()
    test["__row_id__"]=np.arange(132,160,dtype=int)
    return original,test

def grouped_partition(bundle,seed):
    """Select complete feature-pattern groups for test; disjoint by construction.

    Shuffle groups with a fixed generator; greedy loss penalizes differences from
    each class's 20% target and total size. Group IDs include all four modeled
    attributes, and *not* the label or subject identifier. Never split a group.
    """
    df=bundle.frame.copy().reset_index(drop=True)
    df["__row_id__"]=np.arange(132,dtype=int)
    grouped=[(tuple(str(v) for v in key),g.index.to_numpy(dtype=int))
             for key,g in df.groupby(bundle.features,dropna=False,sort=False)]
    rng=np.random.default_rng(seed)
    rng.shuffle(grouped)
    target=df[bundle.target].value_counts().sort_index()
    classes=target.index.tolist()
    desired=target.to_numpy(dtype=float)*.2
    desired_total=round(len(df)*.2)
    selected=[];remaining=list(grouped); totals=np.zeros(len(classes),dtype=float)
    def score(counts):
        return sum(abs((counts-desired)/(desired+1.)))+0.60*abs(sum(counts)-desired_total)/(desired_total+1.)
    while remaining and sum(totals)<desired_total-2:
        candidates=[]
        for i,(key,ix) in enumerate(remaining):
            c=df.loc[ix,bundle.target].value_counts()
            delta=np.asarray([int(c.get(k,0)) for k in classes])
            new=totals+delta
            if sum(new)>desired_total+5:continue
            candidates.append((score(new),i,delta))
        if not candidates:break
        candidates.sort(key=lambda x:(x[0],x[1]))
        _,idx,delta=candidates[0]
        selected.extend(int(i) for i in remaining.pop(idx)[1]);totals+=delta
    test=df.iloc[sorted(selected)].copy();train=df.drop(df.index[sorted(selected)]).copy()
    assert 18<=len(test)<=32,(seed,len(test))
    assert train[bundle.target].nunique()==3 and test[bundle.target].nunique()>=2,(seed,len(train),len(test))
    tr=set(map(tuple,train[bundle.features].astype(str).to_numpy()))
    te=set(map(tuple,test[bundle.features].astype(str).to_numpy()))
    assert not(tr&te),"group leakage detected"
    assert len(set(train.__row_id__) & set(test.__row_id__))==0
    return train,test

def stats_of_cases(artifact, rules, predictions, policy, default_class):
    rows=[]
    y=artifact.test[artifact.target].astype(str).tolist()
    for pos,(_,r) in enumerate(artifact.test.iterrows()):
        matched=matching_rules(r,rules)
        candidates={str(rr.decision) for rr in matched}
        truth=y[pos];chosen=str(predictions[pos])
        conflict=len(candidates)>1
        if not matched:state="NO_MATCH"
        elif truth not in candidates:state="MATCH_TRUE_ABSENT"
        elif conflict:state="MATCH_TRUE_PRESENT_CONFLICT"
        else:state="MATCH_TRUE_PRESENT_NONCONFLICT"
        rows.append({"state":state,"conflict":int(conflict),
             "correct":int(chosen==truth),"candidate_contains_truth":int(truth in candidates),
             "predicted":chosen,"truth":truth,"match_count":len(matched)})
    a=pd.DataFrame(rows);n=len(a)
    conflict=a[a.conflict==1]
    return {
        "no_match":int((a.state=="NO_MATCH").sum()),
        "matched_true_absent":int((a.state=="MATCH_TRUE_ABSENT").sum()),
        "matched_true_present_nonconflict":int((a.state=="MATCH_TRUE_PRESENT_NONCONFLICT").sum()),
        "matched_true_present_conflict":int((a.state=="MATCH_TRUE_PRESENT_CONFLICT").sum()),
        "conflict_true_absent":int((conflict.candidate_contains_truth==0).sum()),
        "conflict_true_present_wrong_selection":int(((conflict.candidate_contains_truth==1)&(conflict.correct==0)).sum()),
        "conflict_true_present_correct_selection":int(((conflict.candidate_contains_truth==1)&(conflict.correct==1)).sum()),
        "no_match_fallback_correct":int(((a.state=="NO_MATCH")&(a.correct==1)).sum()),
        "no_match_fallback_wrong":int(((a.state=="NO_MATCH")&(a.correct==0)).sum()),
        "no_conflict_true_absent":int(((a.state=="MATCH_TRUE_ABSENT")&(a.conflict==0)).sum()),
        "total_correct":int(a.correct.sum()),
        "n_evaluated":n,
        "conflict_cases":len(conflict),
    }

def run_seed(seed,outdir):
    b=source_bundle()
    c=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    c["evaluation"]["seed"]=seed
    c["evaluation"]["mode"]="HOLDOUT_80_20"
    c["federated"]["run_client_sweep"]=False
    c["federated"]["order_sensitivity_max_permutations"]=1
    results=[]
    for mode in ("OFFICIAL_132_28","GROUP_DISJOINT_80_20"):
        train,test=official_partition(b) if mode=="OFFICIAL_132_28" else grouped_partition(b,seed)
        for clients in (0,2,3,4,5):
            cfg=deepcopy(c)
            cfg["experiment"]["run_centralized"]=clients==0
            cfg["experiment"]["run_federated"]=clients>0
            cfg["federated"]["n_clients"]=clients
            res=_run_split(b,train,test,cfg,quiet=True,prediction_policies=POLICIES,fold=1)
            artifact=res["structural_artifact"]
            key="centralized" if clients==0 else "federated"
            rules=artifact.central_rules if clients==0 else artifact.global_rules
            default=artifact.central_default_class if clients==0 else artifact.default_class
            for policy in POLICIES:
                obs=res["policy_results"][policy][key]
                cnt=stats_of_cases(artifact,rules,obs["predictions"],policy,default)
                assert sum(cnt[k] for k in ("no_match","matched_true_absent","matched_true_present_nonconflict","matched_true_present_conflict"))==len(test)
                assert cnt["conflict_true_absent"]+cnt["conflict_true_present_wrong_selection"]+cnt["conflict_true_present_correct_selection"]==cnt["conflict_cases"]
                assert cnt["total_correct"]==sum(str(a)==str(z) for a,z in zip(artifact.test[b.target].tolist(),obs["predictions"]))
                assert abs(cnt["total_correct"]/len(test)-float(obs["accuracy"]))<1e-12
                results.append({
                    "dataset":"Hayes-Roth","seed":seed,"holdout_protocol":mode,
                    "system":"CENTRALIZED" if clients==0 else "FEDERATED",
                    "client_count":clients,"policy":policy,
                    "train_rows":len(train),"test_rows":len(test),
                    "rule_count":len(rules),
                    "accuracy":float(obs["accuracy"]),
                    "balanced_accuracy":float(obs["balanced_accuracy"]),
                    "macro_f1":float(obs["macro_f1"]),
                    "coverage":1-cnt["no_match"]/len(test),
                    "true_in_candidate":1-cnt["no_match"]/len(test)-cnt["matched_true_absent"]/len(test),
                    "conflict_rate":cnt["conflict_cases"]/len(test),
                    **cnt,
                })
            print("EVALUATED",mode,"seed",seed,"C",clients,"train",len(train),"test",len(test),flush=True)
    frame=pd.DataFrame(results)
    assert len(frame)==2*5*6
    outdir.mkdir(parents=True,exist_ok=True)
    frame.to_csv(outdir/f"HAYES_REMEDIATION_seed{seed:02d}.csv",index=False)
    return frame

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",type=int,nargs="+",required=True)
    parser.add_argument("--output",default=str(OUTPUT_ROOT))
    args=parser.parse_args()
    out=Path(args.output)
    frames=[run_seed(seed,out) for seed in args.seeds]
    h=hashlib.sha256(DATA.read_bytes()).hexdigest()
    print("OFFICIAL_TEST_SHA256",h,flush=True)
    print("HAYES_SEEDS_PASS",len(frames),sum(len(x) for x in frames),flush=True)
if __name__=="__main__":
    main()
