"""Reproducible external UCI stress tests using the repository's REAL Classical LEM2.

Unlike the 8,820 canonical baseline, these scenarios are external validation.
No new class labels are inferred by a language model. All run metadata,
sampling, feature truncation and controlled TRAIN-only corruption is explicit.

Launch with: python -m teacher_demo.extreme_dataset_runner
  --dataset tictactoe --seed 1 --scenario BASE --output outputs/external_stress
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.adapters import DatasetBundle
from roughset.schema import DatasetSchema, clean_column_name
from roughset.app import _run_split
from roughset.evaluation import matching_rules
from teacher_demo.full_factorial_matrix import POLICIES, _base_row, _none_row, _policy_row
from teacher_demo.full_factorial_matrix import _split_raw

# Capped row and feature sets are honestly named, not represented as full UCI tests.
REGISTRY={
 "tictactoe":{"id":101,"name":"Tic-Tac-Toe Endgame","cap_rows":None,"max_features":9,"feature_mode":"ALL_CATEGORICAL","url":"https://archive.ics.uci.edu/dataset/101/tic+tac+toe+endgame"},
 "cmc":{"id":30,"name":"Contraceptive Method Choice","cap_rows":None,"max_features":9,"feature_mode":"CMC_MIXED","url":"https://archive.ics.uci.edu/dataset/30/contraceptive+method+choice"},
 "glass":{"id":42,"name":"Glass Identification","cap_rows":None,"max_features":9,"feature_mode":"ALL_CONTINUOUS","url":"https://archive.ics.uci.edu/dataset/42/glass+identification"},
 "nursery":{"id":76,"name":"Nursery capped at 1800","cap_rows":1800,"max_features":8,"feature_mode":"ALL_CATEGORICAL","url":"https://archive.ics.uci.edu/dataset/76/nursery"},
 "wisconsin_original":{"id":15,"name":"Wisconsin Breast Cancer Original","cap_rows":None,"max_features":9,"feature_mode":"ALL_CATEGORICAL","url":"https://archive.ics.uci.edu/dataset/15/breast+cancer+wisconsin+original"},
 "voting_records":{"id":105,"name":"Congressional Voting first 10 of 16 features","cap_rows":None,"max_features":10,"feature_mode":"ALL_CATEGORICAL","url":"https://archive.ics.uci.edu/dataset/105/congressional+voting+records"},
 "zoo":{"id":111,"name":"Zoo first 10 of 16 features","cap_rows":None,"max_features":10,"feature_mode":"ALL_CATEGORICAL","url":"https://archive.ics.uci.edu/dataset/111/zoo"}
}
SCENARIOS=("BASE","TRAIN_LABEL_FLIP20")
MODE="HOLDOUT_80_20"
# Exact reduct combinatorial search: cap features to 10 for safe reproducibility.
MAX_EXACT_REDUCT_FEATURES=10
SYSTEMS=(("CENTRALIZED",0),("FEDERATED",2),("FEDERATED",3),("FEDERATED",4),("FEDERATED",5))

def stable_seed(*args):
    raw="|".join(map(str,args)).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")%(2**32)

def read_external(name):
    from ucimlrepo import fetch_ucirepo
    cfg=REGISTRY[name]
    dataset=fetch_ucirepo(id=cfg["id"])
    X=dataset.data.features.copy().reset_index(drop=True)
    Y=dataset.data.targets.copy().reset_index(drop=True)
    if isinstance(Y,pd.Series):Y=Y.to_frame("class")
    if Y.shape[1]!=1:raise ValueError(f"{name}: expected one target, found {Y.shape[1]}")
    X.columns=[clean_column_name(x) for x in X.columns]
    if len(set(X.columns))!=len(X.columns):raise ValueError("Column collision after normalization")
    raw_feature_count=len(X.columns)
    chosen=list(X.columns[:cfg["max_features"]])
    if not chosen:raise ValueError("No features")
    # For high-dimensional datasets, a documented prespecified prefix feature set
    # is an ENGINEERING FEASIBILITY SUBSET, not the full original feature space.
    X=X[chosen].copy()
    y=Y.iloc[:,0].astype("string").fillna("__MISSING_TARGET__")
    if (y=="__MISSING_TARGET__").any():raise ValueError("Target missing")
    if cfg["feature_mode"]=="CMC_MIXED":
        cont=[f for f in chosen if f in ("wife_age","num_children")]
    elif cfg["feature_mode"]=="ALL_CONTINUOUS":
        cont=chosen[:]
    else:cont=[]
    cat=[f for f in chosen if f not in cont]
    for f in cont:
        X[f]=pd.to_numeric(X[f],errors="raise")
        if X[f].isna().any():raise ValueError("Continuous features contain missing values: "+f)
    for f in cat:
        # A missing token is a separate categorical LEVEL, not target-informed imputation.
        X[f]=X[f].astype("string").fillna("__MISSING_FEATURE__").astype(str)
    frame=X.copy();frame["class"]=y.astype(str)
    raw_rows=len(frame)
    if cfg["cap_rows"] is not None and len(frame)>cfg["cap_rows"]:
        cap=int(cfg["cap_rows"])
        # Fixed stratified downsampling BEFORE random train/test: same dataset
        # is used for all seeds, and source rows remain in original index order.
        counts=frame["class"].value_counts()
        share=counts/counts.sum()*cap
        desired=np.floor(share).astype(int)
        desired=desired.clip(lower=2)
        for idx in (share-desired).sort_values(ascending=False).index:
            if desired.sum()>=cap:break
            desired.loc[idx]+=1
        while desired.sum()>cap:
            idx=desired[desired>2].idxmax()
            desired.loc[idx]-=1
        rng=np.random.default_rng(20261112)
        selected=[]
        for label,count in desired.items():
            ids=frame.index[frame["class"].eq(label)].to_numpy()
            if len(ids)<count:raise ValueError("Cannot allocate cap across tiny classes")
            selected.extend(rng.choice(ids,size=count,replace=False).tolist())
        frame=frame.loc[sorted(selected)].reset_index(drop=True)
    if int(frame["class"].value_counts().min())<2:
        raise ValueError("Too few examples in rarest class for stratified holdout")
    schema=DatasetSchema(target="class",features=chosen,continuous=cont,categorical=cat)
    bundle=DatasetBundle(cfg["name"],frame,chosen,"class",schema,f"uci_id:{cfg['id']}")
    sha=hashlib.sha256(frame.to_csv(index=False,float_format="%.12g").encode()).hexdigest()
    status={
      "dataset_key":name,"dataset":cfg["name"],"uci_id":cfg["id"],"source_url":cfg["url"],
      "source_rows":raw_rows,"used_rows":len(frame),"source_feature_count":raw_feature_count,
      "used_feature_count":len(chosen),"feature_columns":chosen,
      "reduced_feature_space":len(chosen)<raw_feature_count,"capped_source_rows":len(frame)<raw_rows,
      "sha256_prepared_csv":sha,"class_counts":frame["class"].value_counts().sort_index().to_dict(),
      "min_class_count":int(frame["class"].value_counts().min()),
      "source_missing_token":"__MISSING_FEATURE__",
      "feature_mode":cfg["feature_mode"],"fixed_sampling_seed":20261112
    }
    return bundle,status

def inject_train_noise(raw_train,seed,name,scenario):
    train=raw_train.copy()
    if scenario=="BASE":return train,0
    if scenario!="TRAIN_LABEL_FLIP20":raise ValueError("Unknown scenario")
    rng=np.random.default_rng(stable_seed(name,scenario,seed))
    classes=sorted(train["class"].astype(str).unique())
    if len(classes)<2:raise ValueError("Only one training class")
    ids=np.asarray(train.index)
    n=int(round(len(ids)*.20))
    selected=rng.choice(ids,size=n,replace=False)
    for ix in selected:
        old=str(train.at[ix,"class"])
        candidates=[v for v in classes if v!=old]
        train.at[ix,"class"]=str(candidates[int(rng.integers(len(candidates)))])
    return train,n

def run(dataset,seed,scenario,output):
    if dataset not in REGISTRY:raise ValueError(f"Unknown dataset {dataset}")
    if not 1<=seed<=42:raise ValueError("Seed must be 1..42")
    if scenario not in SCENARIOS:raise ValueError("Unknown scenario")
    bundle,meta=read_external(dataset)
    raw_train,raw_test=_split_raw(bundle,MODE,seed,.2)
    corrupted,nflip=inject_train_noise(raw_train,seed,dataset,scenario)
    # Raw test retains the CLEAN UCI labels. Never corrupt or fit on test.
    from copy import deepcopy
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    cfg["evaluation"]["seed"]=seed
    cfg["evaluation"]["mode"]=MODE
    cfg["federated"]["partition"]="STRATIFIED"
    cfg["federated"]["run_client_sweep"]=False
    cfg["federated"]["order_sensitivity_max_permutations"]=1
    rows=[]
    for system,clients in SYSTEMS:
        x=deepcopy(cfg)
        x["experiment"]["run_centralized"]=system=="CENTRALIZED"
        x["experiment"]["run_federated"]=system=="FEDERATED"
        x["federated"]["n_clients"]=clients
        result=_run_split(bundle,corrupted,raw_test,x,quiet=True,prediction_policies=POLICIES,fold=1)
        art=result["structural_artifact"]
        rules=art.central_rules if system=="CENTRALIZED" else art.global_rules
        pre={
            "ext_dataset_key":dataset,"scenario":scenario,"noise_flips_train":nflip,
            "reduced_feature_space":bool(meta["reduced_feature_space"]),
            "capped_source_rows":bool(meta["capped_source_rows"]),
            "source_rows":int(meta["source_rows"]),
            "original_feature_count":int(meta["source_feature_count"]),
            "used_feature_count":len(bundle.features),"source_sha256":meta["sha256_prepared_csv"]
        }
        base={**_base_row(bundle=bundle,split_mode=MODE,system=system,
                  client_count=clients,artifact=art),**pre}
        row_data=[_none_row(base)]
        policy_outputs={}
        for policy in POLICIES:
            key="centralized" if system=="CENTRALIZED" else "federated"
            out=result["policy_results"][policy][key]
            if out is None:raise RuntimeError("Missing "+policy)
            policy_outputs[policy]=out
            row_data.append(_policy_row(base,policy,out))
        # True class is in candidate, and conflict exists: only this subset
        # can actually be fixed by changing the resolution policy alone.
        cs=[]
        for pos,(_,v) in enumerate(art.test.iterrows()):
            matched=matching_rules(v,rules)
            cand={str(r.decision) for r in matched}
            cs.append((len(cand)>1,str(v[art.target]) in cand))
        possible=sum(c and good for c,good in cs)
        impossible=sum(c and not good for c,good in cs)
        for row in row_data:
            row["conflict_resolvable_count"]=possible
            row["conflict_unresolvable_count"]=impossible
            row["conflict_resolvable_rate"]=possible/len(cs)
            row["train_label_noise_pct"]=100*nflip/len(raw_train)
            row["source_dataset_id"]=meta["uci_id"]
        for row in row_data[1:]:
            preds=np.asarray(policy_outputs[row["selection_policy"]]["predictions"]).astype(str)
            truth=art.test[art.target].astype(str).to_numpy()
            good_flags=np.asarray([a and b for a,b in cs],dtype=bool)
            row["correct_in_resolvable_conflict"]=int((preds[good_flags]==truth[good_flags]).sum())
            row["accuracy_in_resolvable_conflict"]=(
                float((preds[good_flags]==truth[good_flags]).mean()) if good_flags.any() else np.nan
            )
        rows.extend(row_data)
        print("STRESS_CONFIG_PASS",dataset,scenario,seed,system,clients,len(rules),flush=True)
    if len(rows)!=5*7:raise AssertionError("Expected 35 outcomes")
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(path/f"STRESS_{dataset}_{scenario}_seed{seed:02d}.csv",index=False)
    meta.update({"seed":seed,"scenario":scenario,"train_rows":len(raw_train),
                 "test_rows":len(raw_test),"noise_flips_train":nflip,
                 "method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
                 "reduct":"EXACT_MINIMUM_CARDINALITY","iid_partition":"STRATIFIED",
                 "evaluation":"HOLDOUT_80_20","policy_results":len(rows)})
    (path/f"PROFILE_{dataset}_{scenario}_seed{seed:02d}.json").write_text(
        json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print("EXTERNAL_UCI_STRESS_PASS",dataset,seed,scenario,len(rows),flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",required=True,choices=REGISTRY)
    ap.add_argument("--seed",required=True,type=int)
    ap.add_argument("--scenario",required=True,choices=SCENARIOS)
    ap.add_argument("--output",default="outputs/external_stress")
    a=ap.parse_args()
    run(a.dataset,a.seed,a.scenario,a.output)

if __name__=="__main__":
    main()
