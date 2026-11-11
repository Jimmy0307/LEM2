"""Hayes-Roth external validation: original 132/28 UCI split vs grouped-feature holdout.

Kept separate from the frozen 8,820 rows. No group may occur in both
training and test for GROUP_HOLDOUT_80_20. This tests unseen-feature-pattern
generalization, NOT an independently sourced dataset.
"""
from __future__ import annotations
import argparse
import json
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.app import _run_split
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import POLICIES, _candidate_diagnostics

ROOT=Path("research/seed_sweep_inputs")
FEATURES=("hobby","age","educational level","marital status")

def external_rows():
    p=ROOT/"uci_44_hayes_roth_official_test.data"
    raw=pd.read_csv(p,header=None,dtype=str,names=[*FEATURES,"class"])
    assert raw.shape==(28,5) and not raw.isna().any().any()
    return raw

def grouped_split(source,seed,frac=0.20):
    frame=source.copy().reset_index(drop=True)
    keys=frame[list(FEATURES)].astype(str).agg("\x1f".join,axis=1)
    groups=list(keys.unique())
    # Repeatable seeded search: keep all classes represented where feasible.
    rng=np.random.default_rng(seed)
    n=len(frame);desired=round(frac*n)
    candidates=[]
    labels=set(frame["class"].astype(str))
    for _ in range(250):
        order=rng.permutation(len(groups))
        chosen=set()
        count=0
        for j in order:
            group=groups[int(j)]
            group_count=int((keys==group).sum())
            if count+group_count<=desired+2 or (not chosen and count==0):
                chosen.add(group);count+=group_count
            if count>=desired-2:break
        test_mask=keys.isin(chosen)
        tr=frame.loc[~test_mask].copy()
        te=frame.loc[test_mask].copy()
        if len(tr)<10 or len(te)<10:continue
        if not labels.issubset(set(tr["class"].astype(str))):continue
        if not labels.issubset(set(te["class"].astype(str))):continue
        candidates.append((abs(len(te)-desired),tr,te))
        if abs(len(te)-desired)==0:break
    if not candidates:
        raise RuntimeError("No eligible disjoint-class group split at this seed.")
    _,train,test=min(candidates,key=lambda v:v[0])
    train_set=set(train[list(FEATURES)].astype(str).agg("|".join,axis=1))
    test_set=set(test[list(FEATURES)].astype(str).agg("|".join,axis=1))
    assert train_set.isdisjoint(test_set)
    assert len(train)+len(test)==len(frame)
    return train,test

def run(seed,protocol):
    bundles=pinned_bundles()
    bundle=next(b for b in bundles if b.name=="Hayes-Roth")
    raw=bundle.frame.copy().reset_index(drop=True)
    raw["__row_id__"]=np.arange(len(raw))
    if protocol=="UCI_OFFICIAL_132_28":
        train=raw
        test=external_rows()
        test.columns=[c.replace(" ","_") for c in test.columns]
        assert set(bundle.features).issubset(set(test.columns))
        test["__row_id__"]=np.arange(len(raw),len(raw)+len(test))
        test=test[[*bundle.features,bundle.target,"__row_id__"]]
        assert len(train)==132 and len(test)==28
    elif protocol=="GROUP_HOLDOUT_80_20":
        train,test=grouped_split(raw,seed)
    else:raise ValueError(protocol)
    base=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    records=[]
    for c in (0,2,3,4,5):
        cfg=deepcopy(base)
        cfg["evaluation"]["seed"]=seed
        cfg["evaluation"]["mode"]="HOLDOUT_80_20"
        cfg["experiment"]["run_centralized"]=c==0
        cfg["experiment"]["run_federated"]=c!=0
        cfg["federated"]["run_client_sweep"]=False
        cfg["federated"]["n_clients"]=c
        cfg["federated"]["order_sensitivity_max_permutations"]=1
        result=_run_split(bundle,train,test,cfg,quiet=True,prediction_policies=POLICIES,fold=1)
        which="centralized" if c==0 else "federated"
        artifact=result["structural_artifact"]
        diagn=_candidate_diagnostics(artifact,"CENTRALIZED" if c==0 else "FEDERATED")
        for policy in POLICIES:
            output=result["policy_results"][policy][which]
            assert len(output["predictions"])==len(test)
            records.append({
                "dataset":"Hayes-Roth","protocol":protocol,"seed":seed,
                "system":"CENTRALIZED" if c==0 else "FEDERATED",
                "client_count":c,"selection_policy":policy,
                "train_rows":len(train),"evaluation_rows":len(test),
                "accuracy":output["accuracy"],
                "balanced_accuracy":output["balanced_accuracy"],
                "macro_f1":output["macro_f1"],
                "conflict_resolution_accuracy":output.get("conflict_resolution_accuracy"),
                **diagn,
                "rule_count":len(artifact.central_rules if c==0 else artifact.global_rules)
            })
        print("HAYES_PROTOCOL",seed,protocol,c,"PASS",flush=True)
    return records

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",required=True,type=int)
    p.add_argument("--output",default="outputs/hayes_protocols")
    a=p.parse_args()
    if not 1<=a.seed<=42:raise ValueError("seed 1..42")
    rows=[]
    for protocol in ("UCI_OFFICIAL_132_28","GROUP_HOLDOUT_80_20"):
        rows.extend(run(a.seed,protocol))
    assert len(rows)==60
    dest=Path(a.output);dest.mkdir(parents=True,exist_ok=True)
    f=dest/f"HAYES_PROTOCOL_seed{a.seed:02d}.csv"
    pd.DataFrame(rows).to_csv(f,index=False)
    print("HAYES_PROTOCOLS_PASS",a.seed,len(rows),f,flush=True)
if __name__=="__main__":
    main()
