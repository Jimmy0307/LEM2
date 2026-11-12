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
 "zoo":{"id":111,"name":"Zoo first 10 of 16 features","cap_rows":None,"max_features":10,"feature_mode":"ALL_CATEGORICAL","url":"https://archive.ics.uci.edu/dataset/111/zoo"},
 "online_shoppers":{"id":468,"name":"Online Shoppers Conversion (stratified public subset 1600)","cap_rows":1600,"max_features":6,"feature_mode":"EXPLICIT_MIXED","target_column":"revenue",
   "feature_columns":["productrelated","productrelated_duration","bouncerates","exitrates","visitortype","weekend"],
   "continuous_columns":["productrelated","productrelated_duration","bouncerates","exitrates"],
   "url":"https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset",
   "doi":"10.24432/C5F88Q","license":"CC BY 4.0","data_kind":"PUBLIC_SESSION_OBSERVATIONS",
   "feature_note":"Predeclared 6 of 17 original predictors; PageValues excluded to avoid transaction-derived proxy"},
 "ai4i_maintenance":{"id":601,"name":"AI4I Synthetic Predictive Maintenance (stratified public subset 2400)","cap_rows":2400,"max_features":6,"feature_mode":"EXPLICIT_MIXED","target_column":"machine_failure",
   "feature_columns":["type","air_temperature","process_temperature","rotational_speed","torque","tool_wear"],
   "continuous_columns":["air_temperature","process_temperature","rotational_speed","torque","tool_wear"],
   "url":"https://archive.ics.uci.edu/dataset/601/ai4i",
   "doi":"10.24432/C5HS5C","license":"CC BY 4.0","data_kind":"PUBLIC_SYNTHETIC_INDUSTRIAL",
   "feature_note":"Only 6 legitimate predictors; device identifiers and all TWF/HDF/PWF/OSF/RNF failure diagnosis targets excluded"}
}
# Independent registry: twenty NEW publicly sourced datasets; keep historical
# pilot's original seven and two previous business/industrial datasets separate.
from teacher_demo.public_20_registry import REGISTRY as NEW_PUBLIC_20
if set(NEW_PUBLIC_20)&set(REGISTRY):raise ValueError("new dataset collides with existing pilot")
REGISTRY.update(NEW_PUBLIC_20)

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
    Y.columns=[clean_column_name(x) for x in Y.columns]
    wanted=cfg.get("target_column")
    if wanted is not None:
        if wanted not in Y.columns:
            raise ValueError(f"{name}: required target {wanted!r} absent from {Y.columns.tolist()}")
        Y=Y[[wanted]]
    elif Y.shape[1]!=1:
        raise ValueError(f"{name}: expected one target, found {Y.shape[1]}")
    X.columns=[clean_column_name(x) for x in X.columns]
    if len(set(X.columns))!=len(X.columns):raise ValueError("Column collision after normalization")
    raw_feature_count=len(X.columns)
    chosen=list(cfg["feature_columns"]) if cfg.get("feature_columns") else list(X.columns[:cfg["max_features"]])
    missing=set(chosen)-set(X.columns)
    if missing:raise ValueError(f"{name}: missing explicitly selected features {sorted(missing)}")
    if not chosen or len(chosen)>MAX_EXACT_REDUCT_FEATURES:raise ValueError("Invalid exact-reduct feature count")
    if wanted is not None and wanted in chosen:raise ValueError("Target leakage: target selected as feature")
    # For high-dimensional datasets, a documented prespecified prefix feature set
    # is an ENGINEERING FEASIBILITY SUBSET, not the full original feature space.
    X=X[chosen].copy()
    y=Y.iloc[:,0].astype("string").fillna("__MISSING_TARGET__")
    if cfg.get("label_transform")=="adult_income_strip_period":
        y=y.str.strip().str.removesuffix(".")
    if (y=="__MISSING_TARGET__").any():raise ValueError("Target missing")
    if cfg["feature_mode"]=="EXPLICIT_MIXED":
        cont=list(cfg["continuous_columns"])
        if not set(cont).issubset(set(chosen)):raise ValueError("Continuous columns outside selected features")
    elif cfg["feature_mode"]=="CMC_MIXED":
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
      "feature_mode":cfg["feature_mode"],"fixed_sampling_seed":20261112,
      "doi":cfg.get("doi"),"license":cfg.get("license") or cfg.get("source_license_claim"),
      "data_kind":cfg.get("data_kind"),"research_trait":cfg.get("research_trait"),
      "domain":cfg.get("domain"),"source_license_claim":cfg.get("source_license_claim"),
      "source_feature_contract":cfg.get("fixed_feature_contract"),
      "label_transform":cfg.get("label_transform"),
      "feature_selection_note":cfg.get("feature_note"),
      "excluded_target_columns":[x for x in ["twf","hdf","pwf","osf","rnf"] if x in [clean_column_name(c) for c in dataset.data.targets.columns]]
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
        if dataset in {"online_shoppers","ai4i_maintenance"}:
            # Compare exact same HOLDOUT-fitted rules on train vs unseen test.
            train_matches=sum(bool(matching_rules(row,rules)) for _,row in art.train.iterrows())
            base["train_rule_coverage_pct"]=100*train_matches/len(art.train)
            base["test_rule_coverage_pct"]=100*float(base["coverage"])
            base["test_minus_train_coverage_pp"]=base["test_rule_coverage_pct"]-base["train_rule_coverage_pct"]
            base["train_no_match_count"]=len(art.train)-train_matches
            base["target_minority"]=str(bundle.frame["class"].value_counts().idxmin())
            base["source_license"]=meta["license"]
            base["source_doi"]=meta["doi"]
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
        covered_flags=[]
        for pos,(_,v) in enumerate(art.test.iterrows()):
            matched=matching_rules(v,rules)
            cand={str(r.decision) for r in matched}
            cs.append((len(cand)>1,str(v[art.target]) in cand))
            covered_flags.append(bool(matched))
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
            match_flags=np.asarray(covered_flags,dtype=bool)
            good_flags=np.asarray([a and b for a,b in cs],dtype=bool)
            if dataset in {"online_shoppers","ai4i_maintenance"}:
                minority=base["target_minority"]
                rare=(truth==minority)
                row["minority_test_count"]=int(rare.sum())
                row["minority_recall"]=float((preds[rare]==minority).mean()) if rare.any() else np.nan
                row["minority_predicted_count"]=int((preds==minority).sum())
                row["minority_precision"]=float(((preds==minority)&rare).sum()/(preds==minority).sum()) if (preds==minority).any() else np.nan
                row["covered_only_accuracy"]=float((preds[match_flags]==truth[match_flags]).mean()) if match_flags.any() else np.nan
                row["fallback_correct_count"]=int((preds[~match_flags]==truth[~match_flags]).sum())
                row["fallback_accuracy"]=float((preds[~match_flags]==truth[~match_flags]).mean()) if (~match_flags).any() else np.nan
            row["correct_in_resolvable_conflict"]=int((preds[good_flags]==truth[good_flags]).sum())
            row["accuracy_in_resolvable_conflict"]=(
                float((preds[good_flags]==truth[good_flags]).mean()) if good_flags.any() else np.nan
            )
        rows.extend(row_data)
        print("STRESS_CONFIG_PASS",dataset,scenario,seed,system,clients,len(rules),flush=True)
    if len(rows)!=5*7:raise AssertionError("Expected 35 outcomes")
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    if dataset in {"online_shoppers","ai4i_maintenance"}:
        # A prepared public subset for peer review. No IDs or answer-derived features.
        # Same sample across seeds; the SHA is checked across all experiment jobs.
        bundle.frame.to_csv(path/f"PUBLIC_DATASET_{dataset}.csv",index=False)
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
