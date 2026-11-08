"""Exact client-arrival permutation pilot, FIRST_MATCH only, seeds 1 and 42."""
from pathlib import Path
import argparse,json
from copy import deepcopy
import pandas as pd
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _split_raw
from roughset.app import _run_split

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",required=True,type=int)
    ap.add_argument("--output",default="outputs/client_order_pilot")
    x=ap.parse_args()
    assert x.seed in (1,42)
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    cfg["evaluation"]["seed"]=x.seed
    cfg["evaluation"]["mode"]="HOLDOUT_80_20"
    cfg["experiment"]["run_centralized"]=False
    cfg["experiment"]["run_federated"]=True
    cfg["federated"]["run_client_sweep"]=False
    cfg["federated"]["partition"]="STRATIFIED"
    cfg["federated"]["order_sensitivity_max_permutations"]=120
    summaries=[];distributions=[]
    for bundle in pinned_bundles():
        tr,te=_split_raw(bundle,"HOLDOUT_80_20",x.seed,0.2)
        for c in (2,3,4,5):
            config=deepcopy(cfg);config["federated"]["n_clients"]=c
            r=_run_split(bundle,tr,te,config,quiet=True,prediction_policies=["FIRST_MATCH"])
            output=r["policy_results"]["FIRST_MATCH"]["federated"]
            prefix=dict(dataset=bundle.name,seed=x.seed,split_mode="HOLDOUT_80_20",client_count=c,
                        policy="FIRST_MATCH")
            summaries.append({**prefix,"orderings_checked":output.get("orderings_checked"),
                              "total_possible_orderings":output.get("total_possible_orderings"),
                              "order_sampling_complete":output.get("order_sampling_complete"),
                              "order_sensitivity_rate":output.get("order_sensitivity_rate"),
                              "order_balanced_accuracy_mean":output.get("order_balanced_accuracy_mean"),
                              "order_balanced_accuracy_min":output.get("order_balanced_accuracy_min"),
                              "order_balanced_accuracy_max":output.get("order_balanced_accuracy_max"),
                              "order_accuracy_mean":output.get("order_accuracy_mean"),
                              "order_accuracy_min":output.get("order_accuracy_min"),
                              "order_accuracy_max":output.get("order_accuracy_max")})
            t=output["order_distribution_table"].copy()
            assert len(t)=={2:2,3:6,4:24,5:120}[c],(bundle.name,c,len(t))
            assert output.get("order_sampling_complete") is True
            for k,v in prefix.items(): t[k]=v
            distributions.append(t)
            print("ORDER_PILOT_PASS",x.seed,bundle.name,c,len(t),flush=True)
    out=Path(x.output);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(summaries).to_csv(out/f"ORDER_SUMMARY_seed{x.seed:02d}.csv",index=False)
    pd.concat(distributions,ignore_index=True).to_csv(out/f"ORDER_DISTRIBUTION_seed{x.seed:02d}.csv",index=False)
    print("ORDER_COMPLETE",x.seed, "configurations",len(summaries),"order_rows",sum(len(t) for t in distributions))
    return 0
if __name__=="__main__":raise SystemExit(main())
