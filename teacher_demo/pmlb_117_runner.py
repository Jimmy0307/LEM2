"""PMLB 117 candidate study: six Classical LEM2 rule-resolution strategies.

Prespecified PMLB upstream commit, named benchmark tables (NOT 117 independent
source domains). Upload only SHA + metrics, not raw third-party data. Stable
64/16/20 Train/Validation/Test; one frozen rule set per data/scenario.
Supports IID, Dirichlet label skew alpha 0.5 and 0.1. No test-based switching.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import io
import json
import math
import os
import resource
import sys
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
from urllib.request import Request,urlopen

from roughset.adapters import DatasetBundle
from roughset.app import _run_split
from roughset.evaluation import evaluate_rule_model
from roughset.federated import partition_clients
from roughset.schema import DatasetSchema
from roughset.preprocessing import apply_preprocessor
from roughset.splitting import stratified_train_test_split
from teacher_demo.full_factorial_matrix import _split_raw,POLICIES
from teacher_demo.adaptive_six_policy_runner import POLICY_ORDER

SPEC=Path("teacher_demo/pmlb_117_source_registry.json")
MAX_COMPRESSED_BYTES=55_000_000
MAX_ROWS=900
MAX_FEATURES=6
SCENARIOS=(("IID","STRATIFIED",None),("NONIID_05","DIRICHLET_LABEL_SKEW",.5),
           ("NONIID_01","DIRICHLET_LABEL_SKEW",.1))
THRESHOLD_JS=.10
THRESHOLD_CONFLICT=.10
THRESHOLD_BA_GAIN=.02
MIN_TRAIN_CLASS=3

def specs():
    manifest=json.loads(SPEC.read_text(encoding="utf-8"))
    assert manifest["candidate_count"]==117
    entries={v["name"]:v for v in manifest["datasets"]}
    assert len(entries)==117
    return entries

def download(spec):
    # Source fixed to published registry; no CLI/remote injected arbitrary URL.
    url=spec["raw_url"]
    assert url.startswith("https://media.githubusercontent.com/media/EpistasisLab/pmlb/")
    t=time.perf_counter()
    with urlopen(Request(url,headers={"User-Agent":"LEM2-research-source-audit/1.0"}),timeout=100) as response:
        chunks=[];total=0
        while True:
            c=response.read(1<<20)
            if not c:break
            total+=len(c)
            if total>MAX_COMPRESSED_BYTES:raise ValueError("SOURCE_TOO_LARGE_COMPRESSED")
            chunks.append(c)
    blob=b"".join(chunks)
    if blob[:2]!=b"\x1f\x8b":
        raise ValueError("SOURCE_NOT_GZIP_DATA_MAY_BE_GIT_LFS_POINTER")
    return blob,time.perf_counter()-t

def prepare(name):
    spec=specs()[name]
    blob,download_s=download(spec)
    # Inspect header without decompressing all features into memory.
    columns=pd.read_csv(io.BytesIO(blob),sep="\t",compression="gzip",nrows=0).columns.tolist()
    if "target" not in columns:raise ValueError("MISSING_TARGET_COLUMN")
    x=[c for c in columns if c!="target" and not str(c).lower().startswith(("unnamed:","__row_id__"))]
    if len(x)<2:raise ValueError("FEWER_THAN_TWO_PREDICTORS")
    selected=x[:MAX_FEATURES]
    df=pd.read_csv(io.BytesIO(blob),sep="\t",compression="gzip",usecols=[*selected,"target"])
    n_before=len(df)
    # Do not use test labels to choose features or tune the model:
    # feature selection is fixed by published column order.
    df=df.dropna(subset=["target"]).copy()
    for c in selected:
        # PMLB preprocessed benchmarks are numeric; prevent missing predictors
        # from being silently interpreted as matching observed numeric values.
        if df[c].isna().any():
            df[c]=df[c].fillna(df[c].median() if pd.api.types.is_numeric_dtype(df[c]) else "__MISSING__")
    df["target"]=df["target"].astype(str)
    counts=df["target"].value_counts()
    if len(counts)<2 or len(counts)>12:raise ValueError("TARGET_CLASSES_OUTSIDE_2_TO_12")
    rng=np.random.default_rng(20261114)
    if len(df)>MAX_ROWS:
        # Stable class-stratified CAP, independent of the prediction evaluation
        # seed; feasibility test, not whole-dataset scale evaluation.
        quotas=(counts*MAX_ROWS/len(df)).round().astype(int)
        quotas=np.maximum(quotas,1)
        while quotas.sum()>MAX_ROWS:
            j=(quotas-1).idxmax()
            quotas[j]-=1
        while quotas.sum()<MAX_ROWS:
            j=(counts-quotas).idxmax()
            quotas[j]+=1
        indices=[]
        for label,k in quotas.items():
            src=np.flatnonzero(df["target"].to_numpy()==str(label))
            indices.extend(rng.choice(src,size=int(k),replace=False).tolist())
        df=df.iloc[sorted(indices)].copy()
    if min(df.target.value_counts())<8:raise ValueError("TOO_FEW_INSTANCES_FOR_STRATIFIED_64_16_20")
    features={name_i:f"f{i}" for i,name_i in enumerate(selected)}
    df=df.rename(columns={**features,"target":"class"})[[*features.values(),"class"]]
    # Per-column continuous detection is TRAIN-only inside app._feature_types.
    for c in features.values():
        if df[c].dtype==object:
            df[c]=df[c].astype(str)
    frame=df.reset_index(drop=True)
    feat=list(features.values())
    schema=DatasetSchema(target="class",features=feat,continuous=[],categorical=[])
    b=DatasetBundle(name,frame,feat,"class",schema,
                    f"PMLB:EpistasisLab/pmlb@7c1f4bdc0013/{name}")
    prepared_sha=hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()
    metadata={
      "dataset":name,"family":spec["family"],"source_kind":spec["kind"],
      "pmlb_original_rows":spec["upstream_rows"],
      "pmlb_original_features":spec["upstream_features"],
      "source_url":spec["source_url"],"source_commit":"7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68",
      "source_gzip_sha256":hashlib.sha256(blob).hexdigest(),
      "prepared_sha256":prepared_sha,
      "read_rows":n_before,"available_rows":len(frame),
      "selected_features_count":len(feat),
      "feature_contract":"FIRST_SIX_OR_LESS_IN_PMLB_ORIGINAL_SOURCE_ORDER",
      "class_count":frame["class"].nunique(),
      "minority_share":float(frame["class"].value_counts(normalize=True).min()),
      "majority_share":float(frame["class"].value_counts(normalize=True).max()),
      "download_seconds":round(download_s,6),
      "redistributed_source_rows":False
    }
    return b,metadata

def client_skew_profile(train,bundle,cfg):
    if cfg["federated"]["partition"]=="STRATIFIED" or cfg["federated"]["partition"]=="DIRICHLET_LABEL_SKEW":
        clients=partition_clients(
            train,bundle.target,n_clients=3,
            seed=int(cfg["evaluation"]["seed"]),
            strategy=cfg["federated"]["partition"],
            dirichlet_alpha=float(cfg["federated"]["dirichlet_alpha"]),
            dirichlet_max_retries=int(cfg["federated"]["dirichlet_max_retries"])
        )
    else:raise AssertionError("unexpected partition")
    ys=train[bundle.target].astype(str)
    cls=sorted(ys.unique())
    g=np.asarray([(ys==c).mean() for c in cls])
    js=[];missing=[];sizes=[]
    for block in clients.values():
        sizes.append(len(block))
        t=block[bundle.target].astype(str)
        q=np.asarray([(t==c).mean() for c in cls])
        m=.5*(g+q)
        kl=lambda a,b:float((a[a>0]*np.log(a[a>0]/b[a>0])).sum())
        js.append((kl(g,m)+kl(q,m))/(2*math.log(2)))
        missing.append(float((q==0).mean()))
    z=np.asarray(sizes,dtype=float)
    return {"client_label_js":float(np.mean(js)),
            "client_label_missing_rate":float(np.mean(missing)),
            "client_row_cv":float(z.std()/z.mean()),
            "client_min_rows":int(z.min()),
            "client_max_rows":int(z.max())}

def structural_validation(art,rules):
    total=len(art.test);cov=conflict=correct=0
    for _,row in art.test.iterrows():
        matches=[r for r in rules if all(str(row[k])==str(v) for k,v in r.conditions)]
        labels={str(r.decision) for r in matches}
        cov+=bool(matches)
        conflict+=len(labels)>1
        correct+=str(row[art.target]) in labels
    return {"validation_coverage":cov/total,"validation_conflict":conflict/total,
            "validation_correct_candidate":correct/total}

def choose_validation(values,obj="balanced_accuracy"):
    key="validation_"+obj
    return max(POLICY_ORDER,key=lambda p:(values[p][key],-POLICY_ORDER.index(p)))

def guarded_switch(values,profile):
    gs=values["GLOBAL_STRENGTH"]["validation_balanced_accuracy"]
    sv=values["SIMPLE_VOTING"]["validation_balanced_accuracy"]
    good=(profile["client_label_js"]>=THRESHOLD_JS
          and profile["validation_conflict"]>=THRESHOLD_CONFLICT
          and sv>=gs+THRESHOLD_BA_GAIN)
    return "SIMPLE_VOTING" if good else "GLOBAL_STRENGTH"

def evaluate(bundle,source_meta,seed,scenario,strategy,alpha):
    train,test=_split_raw(bundle,"HOLDOUT_80_20",seed,.20)
    dev,val=stratified_train_test_split(train,bundle.target,test_ratio=.2,seed=1000+seed)
    ids=[set(x.__row_id__.astype(int)) for x in (dev,val,test)]
    assert not(ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2])
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    cfg["evaluation"].update(mode="HOLDOUT",seed=int(seed))
    cfg["experiment"].update(run_centralized=False,run_federated=True)
    cfg["federated"].update(n_clients=3,partition=strategy,
                             dirichlet_alpha=alpha if alpha is not None else .5,
                             run_client_sweep=False,order_sensitivity_max_permutations=1)
    if min(dev[bundle.target].value_counts())<2:
        raise ValueError("INDUCTION_RARE_CLASS_LT2")
    skew=client_skew_profile(dev,bundle,cfg)
    start=time.perf_counter()
    fit=_run_split(bundle,dev,val,cfg,quiet=True,prediction_policies=POLICIES,fold=1)
    runtime_fit=time.perf_counter()-start
    art=fit["structural_artifact"]
    r=art.global_rules
    weights=art.global_rule_weights;supports=art.global_rule_support_sets
    default=art.default_class;classes=art.global_class_sizes
    stat=structural_validation(art,r)
    profile={**skew,**stat}
    scores={}
    for policy in POLICIES:
        v=fit["policy_results"][policy]["federated"]
        scores[policy]={"validation_"+o:float(v[o]) for o in ("accuracy","balanced_accuracy","macro_f1")}
    selected=choose_validation(scores)
    guarded=guarded_switch(scores,profile)
    # Freeze policy selection BEFORE any Test evaluations.
    test=apply_preprocessor(test,fit["preprocessor"],bundle.target)
    entries=[]
    t0=time.perf_counter()
    for policy in POLICIES:
        result=evaluate_rule_model(test,r,default,bundle.target,
                                   prediction_policy=policy,
                                   rule_weights=weights,rule_support_sets=supports,class_sizes=classes)
        entries.append({
          "dataset":bundle.name,"family":source_meta["family"],
          "source_kind":source_meta["source_kind"],"seed":seed,"scenario":scenario,
          "dirichlet_alpha":alpha if alpha is not None else None,
          "policy":policy,"selected_validation_best":int(policy==selected),
          "selected_heterogeneity_guard":int(policy==guarded),
          **scores[policy],
          "test_accuracy":float(result["accuracy"]),
          "test_balanced_accuracy":float(result["balanced_accuracy"]),
          "test_macro_f1":float(result["macro_f1"]),
          "test_coverage":float(result["coverage"]),
          "dev_rows":len(art.train),"validation_rows":len(art.test),"test_rows":len(test),
          "number_rules":len(r),"original_features":source_meta["pmlb_original_features"],
          "selected_features_count":source_meta["selected_features_count"],
          "train_num_classes":int(dev[bundle.target].nunique()),
          "train_minority_share":float(dev[bundle.target].value_counts(normalize=True).min()),
          "train_continuous_fraction":float(sum(pd.api.types.is_numeric_dtype(dev[c]) and dev[c].nunique()>10 for c in bundle.features)/len(bundle.features)),
          **profile,
          "source_gzip_sha256":source_meta["source_gzip_sha256"],
          "prepared_sha256":source_meta["prepared_sha256"],
          "fit_seconds":float(runtime_fit),
          "method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2_SIX_RESOLVERS",
          "leakage_protocol":"64_16_20_NO_REFIT_TRAIN_ONLY_SELECTOR"
        })
    elapsed=time.perf_counter()-t0
    for e in entries:
        e["six_policy_test_seconds"]=float(elapsed)
        e["maxrss_mb"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    assert len(entries)==6
    return entries

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",required=True,choices=sorted(specs()))
    p.add_argument("--seeds",default="42")
    p.add_argument("--scenarios",default="IID,NONIID_05,NONIID_01")
    p.add_argument("--output",default="outputs/pmlb")
    a=p.parse_args()
    t=time.perf_counter()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    errors=[];rows=[];meta=None
    try:
        bundle,meta=prepare(a.dataset)
        print("PMLB_SOURCE_PASS",a.dataset,"rows",meta["available_rows"],
              "source",meta["source_gzip_sha256"][:12],flush=True)
    except Exception as exc:
        errors.append({"dataset":a.dataset,"phase":"SOURCE","error":str(exc)[:550]})
    if meta is not None:
        scenarios={s[0]:s for s in SCENARIOS}
        for seed in [int(x) for x in a.seeds.split(",")]:
            for sn in a.scenarios.split(","):
                if sn not in scenarios:raise ValueError(sn)
                (_,strategy,alpha)=scenarios[sn]
                try:
                    z=evaluate(bundle,meta,seed,sn,strategy,alpha)
                    rows.extend(z)
                    print("PMLB_CONFIG_PASS",a.dataset,seed,sn,"BA_GS",
                          round(next(x["test_balanced_accuracy"] for x in z if x["policy"]=="GLOBAL_STRENGTH"),4),flush=True)
                except Exception as exc:
                    print("PMLB_CONFIG_FAIL",a.dataset,seed,sn,type(exc).__name__,str(exc)[:350],flush=True)
                    errors.append({"dataset":a.dataset,"seed":seed,"scenario":sn,"phase":"MODEL",
                                   "error_type":type(exc).__name__,"error":str(exc)[:550]})
    if rows:
        pd.DataFrame(rows).to_csv(out/f"BENCHMARK_{a.dataset}.csv",index=False)
    receipt={
      "name":a.dataset,
      "dataset_source":meta,"results_count":len(rows),
      "configs_passed":len(rows)//6,
      "requested_seeds":a.seeds,"requested_scenarios":a.scenarios,
      "failures":errors,
      "wall_seconds":time.perf_counter()-t,
      "research_status":"PARTIAL" if errors and rows else "PASS" if rows else "NO_VALID_MODEL"
    }
    (out/f"RECEIPT_{a.dataset}.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("PMLB_DATASET_COMPLETE",a.dataset,receipt["research_status"],"valid",len(rows),flush=True)

if __name__=="__main__":main()
