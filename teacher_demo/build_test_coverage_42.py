"""Evidence-gated 42-seed Test Data Coverage diagnosis.

Source contracts:
- frozen 8,820-row Classical IID baseline, where NONE defines structural matching;
- row-level exact-conflict evidence with verified per-policy fallback correctness;
- independently published 7,056-row Classical non-IID 42-seed extension.

No pseudo per-object outcomes: non-IID does not have published row traces, so
covered-only accuracy/fallback accuracy/selection efficiency remain NA there.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

KEY=["dataset","seed","split_mode","system","client_count","selection_policy"]
BASE=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
EXACT=Path("docs/research/teacher_dashboard/data/CONFLICT_EXACT_42SEEDS.csv")
NONIID=Path("docs/research/teacher_dashboard/data/NONIID_42_RESULTS.csv")
DEST=Path("docs/research/teacher_dashboard/data")
POLICIES={"FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"}
TARGET_COLUMNS=["dataset","seed","client_count","selection_policy","evaluation_rows",
  "covered_count","no_match_count","true_in_candidate_count","conflict_case_count","accuracy"]

def assert_eq(a,b,reason):
    if a!=b:raise AssertionError(reason+f" ({a} vs {b})")

def safe_ratio(num,den):
    a=pd.to_numeric(num,errors="coerce").astype(float)
    b=pd.to_numeric(den,errors="coerce").astype(float)
    return (100*a/b).where(b>0,np.nan)

def attach_structural_rates(df):
    N=df.evaluation_rows.astype(int)
    df["test_rows_denominator"]=N
    df["test_covered_count"]=N-df.no_match_count.astype(int)
    assert (df["test_covered_count"]>=0).all()
    assert (df["test_covered_count"]<=N).all()
    assert (df.true_in_candidate_count<=df.test_covered_count).all()
    assert (df.conflict_case_count<=df.test_covered_count).all()
    df["test_coverage_pct"]=safe_ratio(df.test_covered_count,N)
    df["test_no_match_pct"]=safe_ratio(df.no_match_count,N)
    df["candidate_coverage_pct"]=safe_ratio(df.true_in_candidate_count,N)
    df["candidate_given_covered_pct"]=safe_ratio(df.true_in_candidate_count,df.test_covered_count)
    df["conflict_rate_pct"]=safe_ratio(df.conflict_case_count,N)
    df["conflict_given_covered_pct"]=safe_ratio(df.conflict_case_count,df.test_covered_count)
    df["overall_accuracy_pct"]=100*pd.to_numeric(df.accuracy)
    assert np.allclose(df.test_coverage_pct+df.test_no_match_pct,100,atol=1e-9)
    assert np.allclose(df.test_coverage_pct/100,df.coverage,atol=1e-10)
    assert np.allclose(df.candidate_coverage_pct/100,df.true_in_candidate_rate,atol=1e-10)
    assert np.allclose(df.conflict_rate_pct/100,df.conflict_case_rate,atol=1e-10)
    return df

def load_iid():
    frozen=pd.read_csv(BASE)
    exact=pd.read_csv(EXACT)
    assert_eq(len(frozen),8820,"Frozen baseline rows")
    assert_eq(len(exact),7560,"Exact row-trace config rows")
    base=frozen.loc[frozen.selection_policy.ne("NONE")].copy()
    assert_eq(len(base),7560,"Predictive rows")
    assert set(base.selection_policy)==POLICIES
    assert not base.duplicated(KEY).any()
    assert not exact.duplicated(KEY).any()
    merged=base.merge(exact,on=KEY,validate="one_to_one",suffixes=("","_audit"),indicator=True)
    assert set(merged._merge)=={"both"}
    assert np.array_equal(merged.evaluation_rows.to_numpy(),merged.evaluation_rows_audit.to_numpy())
    assert np.array_equal(merged.no_match_count.to_numpy(),merged.no_match_count_audit.to_numpy())
    assert np.array_equal(merged.conflict_case_count.to_numpy(),merged.conflict_total_count.to_numpy())
    assert np.array_equal(merged.true_in_candidate_count.to_numpy(),
      (merged.single_candidate_true_count+merged.conflict_true_candidate_count).to_numpy())
    assert np.array_equal(merged.overall_correct_count.to_numpy(),
      np.rint(merged.accuracy*merged.evaluation_rows).astype(int).to_numpy())
    assert np.array_equal(merged.fallback_correct_count+merged.fallback_wrong_count,
      merged.no_match_count)
    merged["regime"]="IID_STRATIFIED_CLASSICAL"
    merged["alpha"]=np.nan
    merged=attach_structural_rates(merged)
    merged["covered_correct_count"]=merged.overall_correct_count-merged.fallback_correct_count
    assert np.array_equal(merged.covered_correct_count,
      merged.single_candidate_true_correct_count+merged.conflict_true_correct_count)
    assert (merged.covered_correct_count<=merged.true_in_candidate_count).all()
    merged["covered_only_accuracy_pct"]=safe_ratio(merged.covered_correct_count,merged.test_covered_count)
    merged["no_match_fallback_accuracy_pct"]=safe_ratio(merged.fallback_correct_count,merged.no_match_count)
    merged["selection_given_candidate_pct"]=safe_ratio(merged.covered_correct_count,merged.true_in_candidate_count)
    merged["winner_selection_error_count"]=merged.true_in_candidate_count-merged.covered_correct_count
    merged["candidate_oracle_ceiling_pct"]=safe_ratio(merged.true_in_candidate_count+merged.fallback_correct_count,merged.evaluation_rows)
    merged["candidate_oracle_gain_pp"]=merged.candidate_oracle_ceiling_pct-merged.overall_accuracy_pct
    assert (merged.candidate_oracle_gain_pp>-1e-8).all()
    return merged.drop(columns=["_merge"])

def load_noniid():
    n=pd.read_csv(NONIID)
    assert_eq(len(n),7056,"Complete 42-seed non-IID")
    n=n[n.selection_policy.ne("NONE")].copy()
    assert_eq(len(n),6048,"Non-IID policy configs")
    assert set(n.selection_policy)==POLICIES
    assert not n.duplicated(KEY+["dirichlet_alpha"]).any()
    assert set(n.seed)==set(range(1,43))
    n["regime"]="NONIID_DIRICHLET_CLASSICAL"
    n["alpha"]=n.dirichlet_alpha.astype(float)
    n=attach_structural_rates(n)
    # Row-level correct/wrong fallback cannot be recovered from aggregate
    # Overall Accuracy and NoMatch counts; leave these unavailable.
    for field in ("fallback_correct_count","fallback_wrong_count","overall_correct_count",
                  "covered_correct_count","covered_only_accuracy_pct",
                  "no_match_fallback_accuracy_pct","selection_given_candidate_pct",
                  "winner_selection_error_count","candidate_oracle_ceiling_pct",
                  "candidate_oracle_gain_pp"):
        n[field]=np.nan
    return n

def make_summary(views):
    group=["regime","alpha","dataset","client_count","selection_policy"]
    cols=["test_coverage_pct","test_no_match_pct","candidate_coverage_pct","candidate_given_covered_pct",
          "conflict_rate_pct","conflict_given_covered_pct","overall_accuracy_pct","covered_only_accuracy_pct",
          "no_match_fallback_accuracy_pct","selection_given_candidate_pct",
          "candidate_oracle_ceiling_pct","candidate_oracle_gain_pp"]
    rows=[]
    for key,d in views.groupby(group,dropna=False):
        record=dict(zip(group,key))
        record["seeds"]=int(d.seed.nunique())
        record["configurations"]=len(d)
        record["test_object_evaluations"]=int(d.evaluation_rows.sum())
        record["test_covered_count"]=int(d.test_covered_count.sum())
        record["candidate_count"]=int(d.true_in_candidate_count.sum())
        for m in cols:
            # Equal-weight per-seed mean; not a pooled-object percentage.
            series=d[m].dropna().astype(float)
            record[m]=float(series.mean()) if len(series) else None
            record[m+"_sd"]=float(series.std(ddof=1)) if len(series)>1 else None
        rows.append(record)
    # Dataset ALL is the equal mean of three datasets in each Seed, then mean over Seeds.
    for key,d in views.groupby(["regime","alpha","client_count","selection_policy"],dropna=False):
        regime,alpha,client_count,policy=key
        obj={"regime":regime,"alpha":alpha,"dataset":"ALL_EQUAL_DATASETS","client_count":client_count,
             "selection_policy":policy,"seeds":int(d.seed.nunique()),
             "configurations":int(len(d)),"test_object_evaluations":int(d.evaluation_rows.sum()),
             "test_covered_count":int(d.test_covered_count.sum()),
             "candidate_count":int(d.true_in_candidate_count.sum())}
        for m in cols:
            per_seed=d.groupby("seed")[m].mean()
            s=per_seed.dropna().astype(float)
            obj[m]=float(s.mean()) if len(s) else None
            obj[m+"_sd"]=float(s.std(ddof=1)) if len(s)>1 else None
        rows.append(obj)
    return pd.DataFrame(rows).sort_values(["regime","dataset","client_count","selection_policy"])

def run():
    iid=load_iid()
    non=load_noniid()
    hold=iid[iid.split_mode.eq("HOLDOUT_80_20")].copy()
    assert_eq(len(hold),3780,"IID holdout policy results")
    assert_eq(len(non),6048,"non-IID holdout policy results")
    allhold=pd.concat([hold,non],ignore_index=True)
    summary=make_summary(allhold)
    assert summary.groupby(["regime","alpha","dataset","client_count","selection_policy"],dropna=False).size().eq(1).all()
    assert summary.seeds.eq(42).all()
    DEST.mkdir(parents=True,exist_ok=True)
    iid.to_csv(DEST/"TEST_COVERAGE_IID_42SEEDS.csv",index=False,float_format="%.10f")
    non.to_csv(DEST/"TEST_COVERAGE_NONIID_42SEEDS.csv",index=False,float_format="%.10f")
    summary.to_csv(DEST/"TEST_COVERAGE_42SEED_SUMMARY.csv",index=False,float_format="%.10f")
    records=[]
    for row in summary.to_dict(orient="records"):
        # HTML frontend receives explicit null for unavailable non-IID row-level metrics.
        records.append({k:(None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v) for k,v in row.items()})
    overview={"method":"Classical positive-region reduct + LEM2",
      "protocol":"HOLDOUT_80_20","random_seeds":42,"dataset_count":3,
      "iid_predictive_rows_all_splits":len(iid),"iid_predictive_holdout_rows":len(hold),
      "noniid_predictive_rows":len(non),
      "full_data_warning":"Full Data resubstitution excluded from cross-regime ranking.",
      "missingness_warning":"non-IID lacks independent row-level correct/fallback evidence. Covered-only accuracy and selection efficiency are null, NOT zero.",
      "definitions":{
        "Test Coverage (%)":"100 * (Ntest - no_match_count) / Ntest",
        "Candidate Coverage (%)":"100 * true_in_candidate_count / Ntest",
        "Candidate given covered (%)":"100 * true_in_candidate_count / covered_count",
        "Covered-only Accuracy (%)":"100 * covered_correct_count / covered_count",
        "No-match fallback Accuracy (%)":"100 * fallback_correct_count / no_match_count",
        "Selection given candidate (%)":"100 * covered_correct_count / true_in_candidate_count",
        "Conflict given covered (%)":"100 * conflict_case_count / covered_count",
        "Oracle ceiling":"100 * (candidate_count + fallback_correct_count) / Ntest, assuming perfect selection within candidate set while keeping fallback fixed",
        "undefined denominator":"report null, not 0",
        "aggregation":"per-seed average within dataset; ALL = 3 datasets equally weighted in each seed, then 42 seeds mean"},
      "summary":records}
    (DEST/"TEST_COVERAGE_OVERVIEW.json").write_text(json.dumps(overview,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    print("TEST_COVERAGE_42SEEDS_AUDIT_PASS",len(iid),len(hold),len(non),len(summary),flush=True)

if __name__=="__main__":run()
