"""Real source-pinned CPU scaling staircase, independent of >100-table sweep.

Source downloaded once; 3 row budgets x 3 feature budgets per selected source.
All values are real runtime measurements; failures/timeouts explicitly recorded.
NOT evidence for 700GB or GPU inference.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import resource
import time
from pathlib import Path
import numpy as np
import pandas as pd

from roughset.adapters import DatasetBundle
from roughset.schema import DatasetSchema
from teacher_demo.pmlb_117_runner import prepare,evaluate

ROW_COUNTS=(600,1600,3200)
FEATURE_COUNTS=(4,6,8)
DATASETS=("adult","magic","connect_4","spambase")

def subbundle(b,rows,k):
    if len(b.frame)<rows:raise ValueError("INSUFFICIENT_ROWS_FOR_BUDGET")
    columns=b.features[:k]
    if len(columns)<k:raise ValueError("INSUFFICIENT_FEATURES_FOR_BUDGET")
    rng=np.random.default_rng(20261114+rows)
    original=b.frame
    target=b.target
    quotas=original[target].value_counts()
    take=(quotas*rows/len(original)).round().astype(int).clip(lower=2)
    while take.sum()>rows:take[take.idxmax()]-=1
    while take.sum()<rows:take[(quotas-take).idxmax()]+=1
    indices=[]
    for label,count in take.items():
        ix=np.flatnonzero(original[target].to_numpy()==label)
        indices.extend(rng.choice(ix,size=int(count),replace=False).tolist())
    frame=original.iloc[sorted(indices)].copy().reset_index(drop=True)
    f=list(columns)
    schema=DatasetSchema(target=target,features=f,continuous=[],categorical=[])
    return DatasetBundle(b.name,frame[f+[target]],f,target,schema,b.source)

def run(dataset,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    source_meta=None;rows=[];errors=[]
    try:
        bundle,source_meta=prepare(dataset,max_rows=max(ROW_COUNTS),max_features=max(FEATURE_COUNTS))
        for n in ROW_COUNTS:
            for k in FEATURE_COUNTS:
                start=time.perf_counter()
                try:
                    b=subbundle(bundle,n,k)
                    current=evaluate(b,source_meta,seed=42,scenario="IID",
                                     strategy="STRATIFIED",alpha=None)
                    assert len(current)==6
                    observation=current[0]
                    rows.append({
                       "dataset":dataset,"rows":n,"features":k,
                       "training_rows":observation["dev_rows"],
                       "validation_rows":observation["validation_rows"],
                       "test_rows":observation["test_rows"],
                       "rules":observation["number_rules"],
                       "fit_seconds":observation["fit_seconds"],
                       "six_policy_test_seconds":observation["six_policy_test_seconds"],
                       "wall_seconds":time.perf_counter()-start,
                       "maxrss_mb":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                       "source_gzip_sha256":source_meta["source_gzip_sha256"],
                       "protocol":"REAL_CLASSICAL_LEM2_FIXED_64_16_20_IID_CPU"
                    })
                    print("RESOURCE_STAIRCASE_PASS",dataset,n,k,
                          round(observation["fit_seconds"],3),"s",flush=True)
                except Exception as exc:
                    errors.append({"rows":n,"features":k,"error":str(exc)[:600]})
                    print("RESOURCE_STAIRCASE_FAIL",dataset,n,k,
                          str(exc)[:300],flush=True)
    except Exception as exc:
        errors.append({"phase":"SOURCE","error":str(exc)[:600]})
    if rows:pd.DataFrame(rows).to_csv(out/f"SCALING_{dataset}.csv",index=False)
    (out/f"SCALING_RECEIPT_{dataset}.json").write_text(json.dumps({
       "dataset":dataset,"source":source_meta,"successful":len(rows),
       "planned":len(ROW_COUNTS)*len(FEATURE_COUNTS),
       "errors":errors,"hardware":"GitHub Actions Ubuntu runner CPU, no GPU"
    },indent=2,allow_nan=False),encoding="utf-8")
    print("RESOURCE_STAIRCASE_DONE",dataset,len(rows),"/9",flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--dataset",choices=DATASETS,required=True)
    p.add_argument("--output",default="outputs/pmlb_resource")
    x=p.parse_args();run(x.dataset,x.output)

if __name__=="__main__":main()
