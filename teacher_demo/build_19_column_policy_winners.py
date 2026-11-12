"""Corrected user-facing format: ONE 19-header comparison table, plus dataset wins.

The previously published conflict_19/ directory contains 19 analytical VIEWS.
It is retained for audit, not presented as the requested 19-column comparison.
This script uses the canonical IID and separately validated non-IID 42-Seed CSVs.
Conflict is policy-independent, measured once per shared rule set.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
NONIID=Path("docs/research/teacher_dashboard/data/NONIID_42_RESULTS.csv")
OUT=Path("docs/research/teacher_dashboard/data")
TARGET_COLUMNS=(
 "dataset","regime","dirichlet_alpha","seed","split_mode","system","client_count",
 "selection_policy","train_rows","test_rows","rule_count","accuracy_pct",
 "balanced_accuracy_pct","macro_f1_pct","coverage_pct","no_match_pct",
 "true_candidate_pct","conflict_resolution_accuracy_pct","conflict_rate_pct")
KEYS=["dataset","regime","dirichlet_alpha","seed","split_mode","system","client_count"]
METRICS=("accuracy_pct","balanced_accuracy_pct","macro_f1_pct",
         "conflict_resolution_accuracy_pct")
POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH",
          "POPULATION_STANDARD","POPULATION_GLOBAL")
def load():
    iid=pd.read_csv(BASE)
    noniid=pd.read_csv(NONIID)
    assert len(iid)==8820 and len(noniid)==7056
    for df in (iid,noniid):
        assert set(df.seed)==set(range(1,43))
        assert df.coverage.between(0,1).all()
        assert df.conflict_case_rate.between(0,1).all()
    iid["regime"]="STRATIFIED_IID";iid["dirichlet_alpha"]=np.nan
    noniid["regime"]="DIRICHLET_NON_IID"
    noniid["dirichlet_alpha"]=noniid["dirichlet_alpha"].astype(float)
    merged=pd.concat((iid,noniid),ignore_index=True)
    assert len(merged)==15876
    assert set(merged.selection_policy)=={"NONE",*POLICIES}
    # Real source file columns only, no fabricated result.
    cols={
       "dataset":merged.dataset,
       "regime":merged.regime,
       "dirichlet_alpha":merged.dirichlet_alpha,
       "seed":merged.seed.astype(int),
       "split_mode":merged.split_mode,
       "system":merged.system,
       "client_count":merged.client_count.astype(int),
       "selection_policy":merged.selection_policy,
       "train_rows":merged.train_rows.astype(int),
       "test_rows":merged.evaluation_rows.astype(int),
       "rule_count":merged.rule_count.astype(int),
       "accuracy_pct":merged.accuracy*100,
       "balanced_accuracy_pct":merged.balanced_accuracy*100,
       "macro_f1_pct":merged.macro_f1*100,
       "coverage_pct":merged.coverage*100,
       "no_match_pct":merged.no_match_rate*100,
       "true_candidate_pct":merged.true_in_candidate_rate*100,
       "conflict_resolution_accuracy_pct":merged.conflict_resolution_accuracy*100,
       "conflict_rate_pct":merged.conflict_case_rate*100,
    }
    out=pd.DataFrame(cols,columns=list(TARGET_COLUMNS))
    assert len(out.columns)==19 and out.columns[-1]=="conflict_rate_pct"
    assert out["conflict_rate_pct"].between(0,100).all()
    assert out["coverage_pct"].between(0,100).all()
    assert np.allclose(out.coverage_pct+out.no_match_pct,100,atol=1e-7)
    assert out[out.selection_policy=="NONE"].accuracy_pct.isna().all()
    out.sort_values(["regime","dataset","dirichlet_alpha","seed","system",
                     "client_count","split_mode","selection_policy"],na_position="first").to_csv(
                       OUT/"POLICY_COMPARISON_19_HEADERS_42SEEDS.csv",
                       index=False,float_format="%.8f")
    return out

def winners(table):
    # Never compare in-sample and out-of-sample, or across datasets/client setups.
    valid=table[(table.selection_policy!="NONE")&
                (table.split_mode=="HOLDOUT_80_20")].copy()
    results=[]
    grouped=valid.groupby(KEYS,dropna=False,sort=True)
    for group_key,sub in grouped:
        if len(sub)!=6 or set(sub.selection_policy)!=set(POLICIES):
            raise AssertionError("Missing paired policies: "+repr(group_key))
        base=dict(zip(KEYS,group_key))
        # Ranking within ONE rule set, one dataset, seed and split.
        for metric in METRICS:
            x=sub[sub[metric].notna()].copy()
            if x.empty:continue
            high=x[metric].max()
            win=x[np.isclose(x[metric].to_numpy(dtype=float),high,
                             rtol=1e-9,atol=1e-8)]
            assert len(win)>=1
            for _,r in win.iterrows():
                results.append({**base,"metric":metric,
                   "winning_policy":r.selection_policy,
                   "winning_score_pct":float(r[metric]),
                   "co_winners":len(win),
                   "fractional_win":1/len(win),
                   "shared_rule_set":True})
    detail=pd.DataFrame(results)
    assert not detail.empty
    detail.to_csv(OUT/"POLICY_WINNERS_PER_CONFIGURATION.csv",index=False,float_format="%.8f")
    expected=valid.groupby(KEYS,dropna=False).size()
    assert expected.eq(6).all()
    # Every group with defined metric allocates exactly ONE fractional win.
    check=detail.groupby(KEYS+["metric"],dropna=False).fractional_win.sum()
    assert np.allclose(check.to_numpy(),1,atol=1e-10)
    by=["dataset","regime","dirichlet_alpha","metric","winning_policy"]
    summary=detail.groupby(by,dropna=False).agg(
        winning_configuration_count=("fractional_win","size"),
        fractional_wins=("fractional_win","sum"),
        win_score_mean_pct=("winning_score_pct","mean"),
        split_ties=("co_winners",lambda x:int((x>1).sum())),
    ).reset_index().sort_values(by,na_position="first")
    # Unique experiment group/metric, not number of tied winner records.
    tot=(detail.drop_duplicates(KEYS+["metric"])
         .groupby(["dataset","regime","dirichlet_alpha","metric"],dropna=False)
         .size().rename("opportunities").reset_index())
    summary=summary.merge(tot,on=["dataset","regime","dirichlet_alpha","metric"],
                          how="left",validate="many_to_one")
    summary["fractional_win_share_pct"]=100*summary.fractional_wins/summary.opportunities
    summary.to_csv(OUT/"POLICY_WINS_BY_DATASET.csv",index=False,float_format="%.8f")
    return detail,summary

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    table=load()
    wins,summary=winners(table)
    manifest={
     "format":"ONE_TABLE_19_HEADERS_PLUS_DATASET_WINS",
     "metric_unit":"percent 0..100; percent-point differences are signed pp",
     "method":"Classical positive-region reduct + LEM2",
     "canonical_rows":8820,"noniid_rows":7056,"total_rows":len(table),
     "nineteenth_header":TARGET_COLUMNS[-1],"headers":list(TARGET_COLUMNS),
     "winning_metric_scope":"HOLDOUT_80_20 within same dataset, seed, regime, client count, split and exact same rules",
     "wins_counting":"co-wins count each tied policy; fractional wins split 1/N between exact/close ties; avoid pretending 2 equal policies are independent wins",
     "winners_rows":len(wins),"summary_rows":len(summary),
     "note":"19 analytical CSV views in conflict_19 are archived separately and are NOT the requested 19 headers.",
     "data_files":[
        "POLICY_COMPARISON_19_HEADERS_42SEEDS.csv",
        "POLICY_WINS_BY_DATASET.csv",
        "POLICY_WINNERS_PER_CONFIGURATION.csv"]
    }
    (OUT/"POLICY_19_HEADERS_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("POLICY_19_HEADERS_AND_WINS_PASS",len(table),len(wins),len(summary))

if __name__=="__main__": main()
