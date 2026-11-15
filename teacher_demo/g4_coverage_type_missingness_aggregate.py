"""Audit dataset type, prepared missingness, frozen Train/Val/Test coverage.

Primary factual result is ASSOCIATION, not an effect of original-source NA.
All 161 entries receive a source-level completeness census; only 20 UCI can
be compared against the same 120 fixed-G4 rule models with seed11/23.
Dataset is the averaging unit, NOT the 1,080 policy rows.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

IN=Path("g4_split_audit_incoming")
OUT=Path("docs/research/teacher_dashboard/data")
SCENARIOS=("IID","NONIID_05","NONIID_01")
ROUTER="CONFLICT_BUCKET_ROUTER_V1"
VALIDATION="VALIDATION_BEST"
TYPES=("ALL_CONTINUOUS","ALL_CATEGORICAL","EXPLICIT_MIXED")

def fail(x,msg):assert bool(x),msg

def permutation_spearman(x,y,seed=20261115,n_permutations=1999):
    """Average-rank Spearman plus unadjusted Monte Carlo permutation p.

    Used ONLY as exploratory diagnostic; repeated/source-related domains and
    27 predictor scans prevent confirmatory claims.
    """
    a=pd.Series(x).rank(method="average").to_numpy(dtype=float)
    b=pd.Series(y).rank(method="average").to_numpy(dtype=float)
    if np.std(a)<1e-12 or np.std(b)<1e-12:
        return float("nan"),float("nan")
    rho=float(np.corrcoef(a,b)[0,1])
    rng=np.random.default_rng(seed)
    count=0
    for _ in range(n_permutations):
        perm=float(np.corrcoef(a,rng.permutation(b))[0,1])
        count+=int(abs(perm)+1e-12>=abs(rho))
    return rho,float((1+count)/(n_permutations+1))

def main():
    source=json.loads((OUT/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    master=json.loads((OUT/"TEACHER_DATASET_MASTER_20261114.json").read_text(encoding="utf-8"))
    assert master["record_count"]==161 and len(master["data"])==161
    names={x["key"]:x for x in source["datasets"]}
    assert len(names)==20
    all_profiles=[];runs=[]
    for name in sorted(names):
        p=IN/f"PROFILE_G4_{name}.json"
        c=IN/f"COVERAGE_G4_{name}.csv"
        fail(p.exists() and c.exists(),"Missing independent audit source "+name)
        meta=json.loads(p.read_text(encoding="utf-8"))
        assert meta["dataset"]==name
        assert meta["prepared_file_sha256"]==names[name]["published_file_sha256"]
        assert meta["used_rows"]==names[name]["used_rows"]
        assert meta["feature_mode"] in TYPES
        frame=pd.read_csv(c)
        assert len(frame)==6 and set(frame.seed)=={11,23}
        assert set(frame.scenario)==set(SCENARIOS)
        assert frame.groupby(["seed","scenario"]).size().eq(1).all()
        assert frame.source_sha256.eq(meta["prepared_file_sha256"]).all()
        assert frame.validation_test_matches_published_g4.eq(True).all()
        assert frame.dev_rows.add(frame.validation_rows).add(frame.test_rows).eq(meta["used_rows"]).all()
        for col in ["dev_coverage_pct","val_coverage_pct","test_coverage_pct",
                    "dev_conflict_pct","val_conflict_pct","test_conflict_pct",
                    "dev_candidate_correct_pct","val_candidate_correct_pct",
                    "test_candidate_correct_pct"]:
            assert frame[col].between(0,100).all(),col
        assert frame.dev_coverage_pct.add(frame.dev_no_match_pct).sub(100).abs().lt(1e-7).all()
        assert frame.test_coverage_pct.add(frame.test_no_match_pct).sub(100).abs().lt(1e-7).all()
        assert frame.n_declared_continuous.eq(meta["n_numeric_continuous"]).all()
        assert frame.n_declared_categorical.eq(meta["n_declared_categorical"]).all()
        all_profiles.append(meta)
        runs.append(frame)
    measurements=pd.concat(runs,ignore_index=True)
    assert len(measurements)==120
    raw=pd.read_csv(OUT/"G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv")
    assert len(raw)==1080 and raw.groupby(["dataset","scenario","seed"]).size().eq(9).all()
    selected=raw[raw.method.isin([ROUTER,VALIDATION])]
    piv=selected.pivot(index=["dataset","scenario","seed"],columns="method",
                       values=["outer_test_balanced_accuracy","outer_test_accuracy","outer_test_macro_f1"])
    assert len(piv)==120 and piv.notna().all().all()
    byseed=measurements.copy()
    for metric,name in [("outer_test_balanced_accuracy","delta_ba_pp"),
                         ("outer_test_accuracy","delta_accuracy_pp"),
                         ("outer_test_macro_f1","delta_macro_f1_pp")]:
        dif=(100*(piv[(metric,ROUTER)]-piv[(metric,VALIDATION)])).rename(name)
        byseed=byseed.merge(dif.reset_index(),on=["dataset","scenario","seed"],validate="one_to_one")
    assert len(byseed)==120
    byseed["split_gap_absolute_pp"]=byseed.train_minus_test_cov_pp.abs()
    profile_df=pd.DataFrame(all_profiles)
    for col in ["prepared_null_sentinel_cells","prepared_unknown_literal_cells"]:
        assert profile_df[col].ge(0).all()
    cls={k:np.asarray(list(v["observed_classes"].values()),dtype=int) for k,v in names.items()}
    profile_df["minority_share_pct"]=profile_df["dataset"].map(
        lambda n:100*float(min(cls[n]))/int(sum(cls[n])))
    profile_df["class_count"]=profile_df["dataset"].map(lambda n:len(cls[n]))
    profile_df["original_source_rows"]=profile_df["dataset"].map(lambda n:names[n]["source_rows"])
    profile_df["source_missingness_verified"]=False
    profile_df["prepared_marker_rate_pct"]=100*profile_df.prepared_null_sentinel_cells/profile_df.prepared_feature_cells
    profile_df["prepared_unknown_rate_pct"]=100*profile_df.prepared_unknown_literal_cells/profile_df.prepared_feature_cells
    byseed=byseed.merge(profile_df[["dataset","n_numeric_continuous","n_declared_categorical",
            "class_count","minority_share_pct","prepared_null_sentinel_cells",
            "prepared_unknown_literal_cells","prepared_marker_rate_pct","prepared_unknown_rate_pct"]],
            on="dataset",validate="many_to_one")
    # One row per source/scenario, seed-paired mean, never treat seeds as new domains.
    numeric=["delta_ba_pp","delta_accuracy_pp","delta_macro_f1_pp",
        "dev_coverage_pct","val_coverage_pct","test_coverage_pct",
        "dev_no_match_pct","val_no_match_pct","test_no_match_pct",
        "dev_conflict_pct","val_conflict_pct","test_conflict_pct",
        "dev_candidate_correct_pct","val_candidate_correct_pct","test_candidate_correct_pct",
        "val_covered_wrong_candidate_pct","test_covered_wrong_candidate_pct",
        "train_minus_test_cov_pp","val_minus_test_cov_pp","val_minus_test_conflict_pp",
        "split_gap_absolute_pp","n_rules"]
    dataset_summary=(byseed.groupby(["dataset","scenario","feature_mode"],sort=True)[numeric]
        .mean().reset_index().merge(profile_df[["dataset","n_features","n_numeric_continuous",
        "n_declared_categorical","class_count","minority_share_pct","prepared_null_sentinel_cells",
        "prepared_unknown_literal_cells","prepared_marker_rate_pct",
        "prepared_unknown_rate_pct","research_trait","source_domain"]],
        on="dataset",validate="many_to_one"))
    assert len(dataset_summary)==60
    # Group equal weight per DATASET rather than by configuration or row count.
    grouped=(dataset_summary.groupby(["scenario","feature_mode"],sort=True)
             .agg(sources=("dataset","nunique"),
               mean_router_minus_validation_ba_pp=("delta_ba_pp","mean"),
               mean_train_coverage_pct=("dev_coverage_pct","mean"),
               mean_validation_coverage_pct=("val_coverage_pct","mean"),
               mean_test_coverage_pct=("test_coverage_pct","mean"),
               mean_train_test_gap_pp=("train_minus_test_cov_pp","mean"),
               mean_test_conflict_pct=("test_conflict_pct","mean"),
               mean_test_correct_candidate_pct=("test_candidate_correct_pct","mean"),
               mean_null_markers=("prepared_null_sentinel_cells","mean"),
               datasets_with_null_marker=("prepared_null_sentinel_cells",lambda a:int((a>0).sum())),
               datasets_with_unknown=("prepared_unknown_literal_cells",lambda a:int((a>0).sum()))
             ).reset_index())
    assert len(grouped)==9
    cors=[]
    xcols=("test_conflict_pct","test_coverage_pct","train_minus_test_cov_pp",
        "val_minus_test_cov_pp","minority_share_pct","n_rules","prepared_marker_rate_pct",
        "prepared_unknown_rate_pct","n_numeric_continuous")
    for scenario,src in dataset_summary.groupby("scenario"):
        assert len(src)==20
        for field in xcols:
            if src[field].nunique()<2:
                rho,p=float("nan"),float("nan")
            else:
                rho,p=permutation_spearman(src[field],src["delta_ba_pp"])
            cors.append({"scenario":scenario,"predictor":field,"sources":20,
                "spearman_rho":float(rho),"unadjusted_permutation_p_value":float(p),
                "causal_evidence":False,
                "warnings":"Monte Carlo 1999 permutation p, unadjusted; exploratory association, correlated predictors, small subgroups, NO multiple-comparison adjustment"})
    inventory=[]
    for cohort,group in pd.DataFrame(master["data"]).groupby("cohort"):
        inventory.append({
          "cohort":cohort,"registered_records":int(len(group)),
          "passed_records":int(group.status.astype(str).str.startswith("PASS").sum()),
          "original_rows_known":int(group.original_rows.notna().sum()),
          "used_rows_known":int(group.used_rows.notna().sum()),
          "original_features_known":int(group.original_features.notna().sum()),
          "raw_file_sha_known":int(group.source_sha256.fillna("").astype(str).str.len().ge(64).sum()),
          "prepared_sha_known":int(group.prepared_sha256.fillna("").astype(str).str.len().ge(64).sum()),
          "raw_source_missingness_verified":False,
          "comparable_in_this_G4_study":cohort=="UCI_NEW20"
        })
    inventory_df=pd.DataFrame(inventory)
    assert inventory_df.registered_records.sum()==161
    OUT.mkdir(parents=True,exist_ok=True)
    for name,data in [
      ("G4_20_SOURCES_PREPARED_MISSINGNESS_PROFILE.csv",profile_df),
      ("G4_TRAIN_VAL_TEST_COVERAGE_120_CONFIGS.csv",byseed),
      ("G4_TRAIN_TEST_TYPE_AND_SELECTOR_60_DATASET_SCENARIOS.csv",dataset_summary),
      ("G4_SELECTOR_BY_FEATURE_TYPE_9_GROUPS.csv",grouped),
      ("G4_SELECTOR_EXPLORATORY_ASSOCIATIONS.csv",pd.DataFrame(cors)),
      ("ALL_161_SOURCE_DATA_QUALITY_CENSUS.csv",inventory_df)
    ]:
        data.to_csv(OUT/name,index=False,float_format="%.10f")
    manifest={"status":"PASS_161_SOURCE_CENSUS_AND_20_UCI_G4_SPLIT_MISSINGNESS_AUDIT",
      "original_g4_result_rows":len(raw),"actual_split_rule_fits":len(measurements),
      "datasets":20,"seeds":[11,23],"scenario_count":3,
      "dataset_scenario_rows":len(dataset_summary),"subgroups":len(grouped),
      "total_registered_records":161,"not_independent_domains":True,
      "accuracy_paired_by_dataset_and_seed":True,
      "split_protocol":"64/16/20; same dev-fitted rules evaluated on train, val, unseen test",
      "full_split_metric_parity_with_previous_G4":True,
      "input_feature_type_prespecified":True,
      "original_raw_UCI_missingness_known":False,
      "prepared_sentinel_markers_are_not_proof_of_raw_missing":True,
      "unknown_literals_are_NOT_automatically_missing":True,
      "warning":[
        "N=20 domains; categorical N=3 and mixed N=4 are small",
        "PMLB117+UCI20+other cohorts have overlap; 161 are NOT independent",
        "Association between input format and selector delta cannot establish causation",
        "Only G4 UCI20 has within-source 3-split re-fitted structural coverage in this audit",
        "No individual full 161-source raw missingness audit was executed",
        "Dataset seed profiles use test labels for observation only, never selection or induction"],
      "files":["G4_20_SOURCES_PREPARED_MISSINGNESS_PROFILE.csv",
         "G4_TRAIN_VAL_TEST_COVERAGE_120_CONFIGS.csv",
         "G4_TRAIN_TEST_TYPE_AND_SELECTOR_60_DATASET_SCENARIOS.csv",
         "G4_SELECTOR_BY_FEATURE_TYPE_9_GROUPS.csv",
         "G4_SELECTOR_EXPLORATORY_ASSOCIATIONS.csv",
         "ALL_161_SOURCE_DATA_QUALITY_CENSUS.csv"]}
    (OUT/"G4_COVERAGE_TYPE_MISSINGNESS_MANIFEST.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("G4_ALL_161_CENSUS_20UCI_120_SPLIT_PARITY_PASS",flush=True)
    print(grouped.to_string(index=False),flush=True)

if __name__=="__main__":main()
