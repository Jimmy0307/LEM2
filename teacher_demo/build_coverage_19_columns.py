"""One 19-column audit table (NOT nineteen tables), plus per-dataset policy wins.

Train rule-match coverage is unavailable in archived 42-seed summaries: leave NA.
Never substitute FULL_DATA resubstitution for Train coverage of the holdout model.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import numpy as np

DATA=Path("docs/research/teacher_dashboard/data")
OUT=Path("docs/research/teacher_dashboard/coverage_research")
BASE=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
NON=DATA/"NONIID_42_RESULTS.csv"
EVIDENCE=DATA/"TEST_COVERAGE_IID_42SEEDS.csv"
KEY=["dataset","seed","split_mode","system","client_count","selection_policy"]
COLUMNS=[
 "dataset", "seed", "distribution", "dirichlet_alpha", "split_mode",
 "system", "client_count", "selection_policy", "train_rows", "test_rows",
 "rule_count", "train_rule_coverage_pct", "test_rule_coverage_pct",
 "test_minus_train_coverage_pp", "test_candidate_coverage_pct",
 "test_conflict_rate_pct", "test_conflict_only_accuracy_pct",
 "test_overall_accuracy_pct", "test_covered_only_accuracy_pct"
]
assert len(COLUMNS)==19
POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL")
OBJECTIVES={"overall_accuracy":"accuracy","balanced_accuracy":"balanced_accuracy","macro_f1":"macro_f1","conflict_only_accuracy":"conflict_resolution_accuracy"}

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    iid=pd.read_csv(BASE)
    iid=iid[(iid.split_mode=="HOLDOUT_80_20")&(iid.selection_policy!="NONE")].copy()
    assert len(iid)==3780
    iid["distribution"]="IID_STRATIFIED"
    iid["dirichlet_alpha"]=np.nan
    non=pd.read_csv(NON)
    non=non[non.selection_policy!="NONE"].copy()
    assert len(non)==6048
    non["distribution"]="NONIID_DIRICHLET"
    non["dirichlet_alpha"]=non["dirichlet_alpha"].astype(float)
    allrows=pd.concat([iid,non],ignore_index=True,sort=False)
    # Verified row-level exact audit is only available for IID.
    trace=pd.read_csv(EVIDENCE)
    trace=trace[trace.split_mode=="HOLDOUT_80_20"]
    assert len(trace)==3780
    needed=KEY+["covered_only_accuracy_pct"]
    assert not trace.duplicated(KEY).any()
    allrows=allrows.merge(trace[needed],on=KEY,how="left",validate="many_to_one",suffixes=("","_from_trace"),indicator=True)
    assert allrows[allrows.distribution=="IID_STRATIFIED"]._merge.eq("both").all()
    assert allrows[allrows.distribution=="NONIID_DIRICHLET"]._merge.eq("both").all()
    # Important: despite row matching, non-IID has distinct rules; never inherit
    # IID's covered-only classification from exact traces.
    allrows["test_covered_only_accuracy_pct"]=np.where(
      allrows.distribution=="IID_STRATIFIED",allrows.covered_only_accuracy_pct,np.nan
    )
    allrows["test_rows"]=allrows.evaluation_rows
    allrows["test_rule_coverage_pct"]=100*allrows.covered_count/allrows.evaluation_rows
    allrows["test_candidate_coverage_pct"]=100*allrows.true_in_candidate_count/allrows.evaluation_rows
    allrows["test_conflict_rate_pct"]=100*allrows.conflict_case_count/allrows.evaluation_rows
    allrows["test_conflict_only_accuracy_pct"]=100*allrows.conflict_resolution_accuracy
    allrows["test_overall_accuracy_pct"]=100*allrows.accuracy
    allrows["train_rule_coverage_pct"]=np.nan
    allrows["test_minus_train_coverage_pp"]=np.nan
    # The original frozen matrix does not include matched-rule Train coverage
    # for each HOLDOUT model. Dedicated train-only replay is required.
    assert allrows[COLUMNS].shape[1]==19
    assert len(allrows)==9828
    assert allrows.test_rule_coverage_pct.between(0,100).all()
    assert allrows.test_candidate_coverage_pct.le(allrows.test_rule_coverage_pct+1e-8).all()
    assert allrows.test_conflict_rate_pct.le(allrows.test_rule_coverage_pct+1e-8).all()
    assert allrows.train_rule_coverage_pct.isna().all()
    allrows[COLUMNS].sort_values(["dataset","distribution","seed","client_count","selection_policy"]).to_csv(
      OUT/"COVERAGE_19_COLUMNS_42SEEDS.csv",index=False,float_format="%.10f")
    # Win frequencies: compare six policies within one dataset/seed/distribution/
    # alpha/topology. No leakage between IID and non-IID or different clients.
    group=["dataset","distribution","dirichlet_alpha","seed","client_count"]
    wins=[]
    for name,col in OBJECTIVES.items():
        for key,block in allrows.groupby(group,dropna=False):
            if len(block)!=6 or set(block.selection_policy)!=set(POLICIES):
                raise AssertionError("Missing policy matchup "+str(key))
            numeric=pd.to_numeric(block[col],errors="coerce")
            # Conflict-only accuracy is undefined if zero conflict cases.
            if numeric.isna().all():
                continue
            if numeric.isna().any():raise AssertionError("Inconsistent undefined metric within rule set")
            best=float(numeric.max())
            leaders=block.loc[np.isclose(numeric,best,rtol=1e-10,atol=1e-12),"selection_policy"].tolist()
            for p in POLICIES:
                wins.append({**dict(zip(group,key)),"objective":name,"selection_policy":p,
                  "tied_winner":int(p in leaders),"sole_win":int(p in leaders and len(leaders)==1),
                  "fractional_win":1/len(leaders) if p in leaders else 0,
                  "tied_methods":len(leaders),"observed_metric":float(numeric[block.selection_policy.eq(p)].iloc[0])})
    wins=pd.DataFrame(wins)
    wins.to_csv(OUT/"POLICY_WIN_EVENTS_BY_DATASET.csv",index=False,float_format="%.10f")
    w=wins.groupby(["dataset","distribution","dirichlet_alpha","client_count","objective","selection_policy"],dropna=False).agg(
        evaluated_matchups=("sole_win","size"),
        sole_wins=("sole_win","sum"),
        ties_included_wins=("tied_winner","sum"),
        fractional_wins=("fractional_win","sum")).reset_index()
    w.to_csv(OUT/"POLICY_WIN_COUNTS_BY_DATASET.csv",index=False,float_format="%.10f")
    # Dataset+distribution summary across topologies keeps topology stratification visible.
    by_dataset=w.groupby(["dataset","distribution","dirichlet_alpha","objective","selection_policy"],dropna=False).agg(
        evaluated_matchups=("evaluated_matchups","sum"),
        sole_wins=("sole_wins","sum"),
        ties_included_wins=("ties_included_wins","sum"),
        fractional_wins=("fractional_wins","sum")).reset_index()
    by_dataset.to_csv(OUT/"POLICY_WIN_COUNTS_SUMMARY.csv",index=False,float_format="%.10f")
    manifest={
      "contract":"19 HEADERS in ONE table, not 19 separate tables",
      "columns":COLUMNS,"column_count":19,"configurations":len(allrows),
      "method":"Classical positive-region reduct + LEM2; IID 42, non-IID 42",
      "train_coverage_evidence":"UNAVAILABLE from frozen holdout result; intentionally null",
      "covered_accuracy_evidence":"IID row-level verified; non-IID unavailable, null",
      "win_count":"Within same dataset, seed, distribution, alpha, client count, across six policies. Ties tracked separately and split fractional credit. No extra data sets claimed.",
      "outputs":["COVERAGE_19_COLUMNS_42SEEDS.csv","POLICY_WIN_EVENTS_BY_DATASET.csv",
                 "POLICY_WIN_COUNTS_BY_DATASET.csv","POLICY_WIN_COUNTS_SUMMARY.csv"]
    }
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("COVERAGE_19_HEADERS_AND_WIN_COUNTS_PASS",len(allrows),len(wins),len(w),flush=True)

if __name__=="__main__":run()
