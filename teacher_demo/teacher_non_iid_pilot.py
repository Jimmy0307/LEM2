"""Isolated non-IID sensitivity pilot: same holdout, different client allocation."""
from __future__ import annotations
import argparse, json
from copy import deepcopy
from pathlib import Path
import pandas as pd
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _run_block, _split_raw
from roughset.federated import partition_clients

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--output",default="outputs/teacher_non_iid_pilot")
    args=parser.parse_args()
    if not 1<=args.seed<=42:raise ValueError("seed must be between 1 and 42")
    base=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    base["evaluation"]["seed"]=args.seed
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    records=[];client_distributions=[]
    for bundle in pinned_bundles():
        train, test=_split_raw(bundle,"HOLDOUT_80_20",args.seed,0.2)
        reference=train[bundle.target].astype(str).value_counts(normalize=True).to_dict()
        for c in (3,5):
            for alpha in (0.5,0.1):
                cfg=deepcopy(base)
                cfg["federated"]["partition"]="DIRICHLET_LABEL_SKEW"
                cfg["federated"]["dirichlet_alpha"]=alpha
                cfg["federated"]["dirichlet_max_retries"]=100
                try:
                    clients=partition_clients(train,target_col=bundle.target,n_clients=c,seed=args.seed,
                        strategy="DIRICHLET_LABEL_SKEW",dirichlet_alpha=alpha,dirichlet_max_retries=100)
                    for label,frame in clients.items():
                        observed=frame[bundle.target].astype(str).value_counts(normalize=True).to_dict()
                        keys=set(reference)|set(observed)
                        tv=.5*sum(abs(reference.get(k,0.)-observed.get(k,0.)) for k in keys)
                        client_distributions.append({"dataset":bundle.name,"seed":args.seed,
                            "client_count":c,"alpha":alpha,"client":label,"rows":len(frame),
                            "total_variation_from_train_class_distribution":tv,
                            "class_distribution_json":json.dumps(observed,sort_keys=True)})
                    rows=_run_block(bundle,cfg,split_mode="HOLDOUT_80_20",system="FEDERATED",client_count=c)
                    assert len(rows)==7
                    for row in rows:
                        row.update({"partition":"DIRICHLET_LABEL_SKEW","alpha":alpha,"status":"PASS"})
                        records.append(row)
                    print("NON_IID_PASS",bundle.name,"C",c,"alpha",alpha,flush=True)
                except ValueError as error:
                    # An allocation with empty clients is not valid; record it without fabricating metrics.
                    records.append({"dataset":bundle.name,"seed":args.seed,
                       "system":"FEDERATED","split_mode":"HOLDOUT_80_20",
                       "client_count":c,"selection_policy":"NONE",
                       "partition":"DIRICHLET_LABEL_SKEW","alpha":alpha,
                       "status":"INVALID_PARTITION","error":str(error)})
                    print("NON_IID_INVALID_PARTITION",bundle.name,c,alpha,str(error),flush=True)
    df=pd.DataFrame(records)
    df.to_csv(out/f"NON_IID_seed{args.seed:02d}.csv",index=False)
    pd.DataFrame(client_distributions).to_csv(out/f"CLIENT_DISTRIBUTIONS_seed{args.seed:02d}.csv",index=False)
    assert len(df)>0
    print("NON_IID_PILOT_FINISHED",args.seed,"valid",int((df.status=="PASS").sum()),flush=True)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
