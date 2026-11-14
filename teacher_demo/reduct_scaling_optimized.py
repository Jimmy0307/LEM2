"""G8 CPU resource study: reference exact vs POS partition cache vs greedy.

High-dimensional approximate reduct can preserve Train POS but it is NEVER
called an exact minimum-cardinality reduct. Reuse source-pinned PMLB data,
compare on the SAME stratified sample with an immutable class target.
One outer wall clock includes source preparation, but selection_seconds
excludes download. No claims about full pipeline/GPU/enterprise throughput.
"""
from __future__ import annotations
import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.reduct import _positive_region_size,select_minimum_reduct
from roughset.reduct_fast import exact_cached,greedy_pos
from teacher_demo.pmlb_117_runner import prepare

DATASETS=("connect_4","mnist","spambase","adult")
ROW_BUDGETS=(600,1600,3200,6400)
FEATURE_BUDGETS=(4,6,8,12,16,24)

def subset_bundle(b,n,k):
    if n>len(b.frame) or k>len(b.features):return None
    rng=np.random.default_rng(20261115+n+k)
    ys=b.frame[b.target].astype(str)
    counts=ys.value_counts().sort_index()
    quotas=(counts*n/len(b.frame)).round().astype(int).clip(lower=1)
    while quotas.sum()>n:
        possible=quotas[quotas>1]
        if possible.empty:raise AssertionError("Bad budget")
        quotas[possible.idxmax()]-=1
    while quotas.sum()<n:
        room=(counts-quotas)
        quotas[room.idxmax()]+=1
    idx=[]
    for label,qty in quotas.items():
        src=np.flatnonzero(ys.to_numpy()==label)
        if len(src)<qty:raise AssertionError("Sample quota exceeds source class")
        idx.extend(rng.choice(src,int(qty),replace=False).tolist())
    data=b.frame.iloc[sorted(idx)][list(b.features[:k])+[b.target]].reset_index(drop=True)
    assert len(data)==n
    return data

def run(name,outdir):
    start=time.perf_counter()
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    meta=None;rows=[];missing=[];errors=[]
    try:
        bundle,meta=prepare(name,max_rows=max(ROW_BUDGETS),max_features=max(FEATURE_BUDGETS))
        for n in ROW_BUDGETS:
            for k in FEATURE_BUDGETS:
                if n>len(bundle.frame) or k>len(bundle.features):
                    missing.append({"rows":n,"features":k,"reason":"SOURCE_BUDGET_NOT_AVAILABLE"})
                    continue
                try:
                    df=subset_bundle(bundle,n,k)
                    features=list(df.columns[:-1])
                    result={"dataset":name,"rows":n,"features":k,
                            "kind":"CPU_REDUCT_STAGE_ONLY","reference_status":"NOT_RUN_HIGH_DIMENSION",
                            "reference_seconds":None,"reference_selected_size":None,
                            "exact_cache_seconds":None,"exact_cache_selected_size":None,
                            "exact_cache_candidates":None}
                    target=df.columns[-1]
                    if k<=8 and n<=3200:
                        st=time.perf_counter()
                        old=select_minimum_reduct(df,features,target)
                        dt=time.perf_counter()-st
                        result.update(reference_status="REFERENCE_EXACT_PASS",
                          reference_seconds=dt,reference_selected_size=len(old.selected_reduct))
                        fast=exact_cached(df,features,target,max_features=8)
                        assert fast.selected==old.selected_reduct
                        assert fast.candidate_count==old.candidate_count
                        assert fast.positive_region==int(old.selected_dependency*len(df)) or (
                            fast.positive_region==_positive_region_size(df,old.selected_reduct,target))
                        result.update(exact_cache_seconds=fast.selection_seconds,
                            exact_cache_selected_size=fast.reduct_size,
                            exact_cache_candidates=fast.candidate_count)
                    approximate=greedy_pos(df,features,target)
                    full_pos=_positive_region_size(df,features,target)
                    assert approximate.positive_region==full_pos
                    result.update(approximate_type="GREEDY_NOT_MIN_CARDINALITY",
                        approximate_seconds=approximate.selection_seconds,
                        approximate_selected_size=approximate.reduct_size,
                        approximate_selected_attributes=";".join(approximate.selected),
                        approximate_train_positive_region=approximate.positive_region,
                        full_train_positive_region=full_pos,
                        actual_positive_region_equal=True,
                        approximate_is_minimum_claim=False,
                        greedy_pos_queries=approximate.positive_region_queries,
                        greedy_cache_entries=approximate.cache_entries,
                        peak_rss_mb_since_process_start=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                        source_gzip_sha256=meta["source_gzip_sha256"],
                        prepared_sha256=meta["prepared_sha256"])
                    rows.append(result)
                    print("G8_FAST_REDUCT_PASS",name,n,k,"ref",result["reference_seconds"],
                        "greedy",round(approximate.selection_seconds,3),flush=True)
                except Exception as exc:
                    errors.append({"rows":n,"features":k,"error":type(exc).__name__+":"+str(exc)[:300]})
                    print("G8_FAST_REDUCT_FAIL",name,n,k,type(exc).__name__,str(exc)[:200],flush=True)
    except Exception as exc:
        errors.append({"phase":"SOURCE","error":type(exc).__name__+":"+str(exc)[:300]})
    if rows:pd.DataFrame(rows).to_csv(out/f"REDUCT_FAST_{name}.csv",index=False)
    receipt={"dataset":name,"source_metadata":meta,
        "requested_configs":len(ROW_BUDGETS)*len(FEATURE_BUDGETS),
        "successful":len(rows),"unsupported_source_budgets":missing,
        "failures":errors,"wall_seconds":time.perf_counter()-start,
        "scope":"REAL_CPU_REDUCT_STAGE_ONLY_NOT_FULL_LEM2",
        "disclaimer":"Greedy preserves Train POS exactly but not minimum cardinality and not Test performance"}
    (out/f"REDUCT_FAST_RECEIPT_{name}.json").write_text(
        json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("G8_FAST_SOURCE_DONE",name,len(rows),"valid",len(missing),"unavailable",len(errors),"errors",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",required=True,choices=DATASETS)
    p.add_argument("--output",default="outputs/fast_reduct")
    a=p.parse_args();run(a.dataset,a.output)

if __name__=="__main__":main()
