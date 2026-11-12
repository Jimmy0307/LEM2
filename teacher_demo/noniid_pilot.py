"""Independent non-IID Dirichlet seed runner; NOT part of canonical 8,820 rows.

Pilot workflow keeps seeds 1/42; an independent 42-seed workflow may use 1..42.
"""
import argparse,json
from copy import deepcopy
from pathlib import Path
import pandas as pd
import numpy as np
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _split_raw,_base_row,_none_row,_policy_row,POLICIES
from roughset.app import _run_split

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--seed",required=True,type=int)
 ap.add_argument("--output",default="outputs/noniid_pilot")
 args=ap.parse_args()
 assert 1 <= args.seed <= 42, 'seed must be between 1 and 42'
 cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
 cfg["evaluation"]["seed"]=args.seed
 cfg["evaluation"]["mode"]="HOLDOUT_80_20"
 cfg["experiment"]["run_centralized"]=False
 cfg["experiment"]["run_federated"]=True
 cfg["federated"]["run_client_sweep"]=False
 cfg["federated"]["partition"]="DIRICHLET_LABEL_SKEW"
 cfg["federated"]["order_sensitivity_max_permutations"]=1
 records=[];errors=[]
 for b in pinned_bundles():
  tr,te=_split_raw(b,"HOLDOUT_80_20",args.seed,0.2)
  for C in (2,3,4,5):
   for alpha in (0.5,0.1):
    config=deepcopy(cfg)
    config["federated"]["n_clients"]=C
    config["federated"]["dirichlet_alpha"]=alpha
    params=dict(seed=args.seed,dataset=b.name,split_mode="HOLDOUT_80_20",system="FEDERATED",
                client_count=C,partition_strategy="DIRICHLET_LABEL_SKEW",dirichlet_alpha=alpha)
    try:
     res=_run_split(b,tr,te,config,quiet=True,prediction_policies=POLICIES)
     art=res["structural_artifact"]
     base=_base_row(bundle=b,split_mode="HOLDOUT_80_20",system="FEDERATED",client_count=C,artifact=art)
     models=[_none_row(base)]+[_policy_row(base,p,res["policy_results"][p]["federated"]) for p in POLICIES]
     clients=art.train if not art.local_rules else art.local_rules
     client_tables=art.pre_resolution_conflicts.get("clients") if isinstance(art.pre_resolution_conflicts,dict) else None
     for model in models:
      records.append({**params,**model})
     print("NONIID_OK",args.seed,b.name,C,alpha,flush=True)
    except (ValueError,RuntimeError) as e:
     errors.append({**params,"error":f"{type(e).__name__}: {e}"})
     print("NONIID_SKIPPED",args.seed,b.name,C,alpha,type(e).__name__,str(e),flush=True)
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 pd.DataFrame(records).to_csv(out/f"NONIID_RESULTS_seed{args.seed:02d}.csv",index=False)
 pd.DataFrame(errors,columns=list(params)+["error"]).to_csv(out/f"NONIID_ERRORS_seed{args.seed:02d}.csv",index=False)
 assert records or errors
 print("NONIID_PILOT_VERDICT=PASS","result_rows",len(records),"failed_configurations",len(errors))
 return 0

if __name__=="__main__":raise SystemExit(main())
