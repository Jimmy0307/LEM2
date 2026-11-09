"""Exact client-order permutation sensitivity for FIRST_MATCH on a fixed LEM2 model."""
from __future__ import annotations
import argparse,json
from copy import deepcopy
from pathlib import Path
import pandas as pd
from roughset.app import _run_split
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _split_raw

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--output",default="outputs/teacher_client_order_pilot")
    args=ap.parse_args()
    if args.seed not in range(1,43):raise ValueError("seed 1..42 required")
    base=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    base["evaluation"]["seed"]=args.seed
    base["evaluation"]["mode"]="HOLDOUT_80_20"
    base["experiment"]["run_centralized"]=False
    base["experiment"]["run_federated"]=True
    base["federated"]["run_client_sweep"]=False
    base["federated"]["order_sensitivity_max_permutations"]=120
    ordered=[]; summaries=[]
    for bundle in pinned_bundles():
        train,test=_split_raw(bundle,"HOLDOUT_80_20",args.seed,0.20)
        for c in (2,3,4,5):
            cfg=deepcopy(base);cfg["federated"]["n_clients"]=c
            result=_run_split(bundle,train,test,cfg,quiet=True,
                              prediction_policies=["FIRST_MATCH"],fold=1)
            fed=result["policy_results"]["FIRST_MATCH"]["federated"]
            table=fed["order_distribution_table"].copy()
            if table.empty:raise AssertionError(("No permutations",bundle.name,c))
            total={2:2,3:6,4:24,5:120}[c]
            if len(table)!=total or not fed["order_sampling_complete"]:
                raise AssertionError(("Not exhaustive",bundle.name,c,len(table)))
            table.insert(0,"client_count",c);table.insert(0,"dataset",bundle.name)
            table.insert(0,"seed",args.seed);table.insert(0,"split_mode","HOLDOUT_80_20")
            ordered.append(table)
            summaries.append({"dataset":bundle.name,"seed":args.seed,"client_count":c,
               "possible_permutations":total,"checked_permutations":len(table),
               "prediction_order_sensitive_rate":fed["order_sensitivity_rate"],
               "conflict_case_order_sensitive_rate":fed["order_sensitivity_conflict_rate"],
               "accuracy_min":float(table.accuracy.min()),
               "accuracy_max":float(table.accuracy.max()),
               "BA_min":float(table.balanced_accuracy.min()),
               "BA_max":float(table.balanced_accuracy.max()),
               "spread_accuracy_pp":100*float(table.accuracy.max()-table.accuracy.min())})
            print("ORDER_EXHAUSTIVE_PASS",bundle.name,args.seed,c,total,flush=True)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    pd.concat(ordered,ignore_index=True).to_csv(out/f"CLIENT_ORDER_PERMUTATIONS_seed{args.seed:02d}.csv",index=False)
    pd.DataFrame(summaries).to_csv(out/f"CLIENT_ORDER_SUMMARY_seed{args.seed:02d}.csv",index=False)
    assert len(ordered)==12
    return 0
if __name__=="__main__":
    raise SystemExit(main())
