"""Dataset-stratified investigation of LEM2 expanded 42-seed interim snapshot.

Read-only scientific results; creates presentation-safe CSVs without SHA256 fields.
Snapshot is pinned to 20261123T114229. Descriptive stratification, NOT causal inference.
Usage: python tools/expanded_resume_20261122/build_grouped_research_review.py
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/research/expanded_188_42seeds"
SNAP=BASE/"interim"
ART=BASE/"report_catalog/20261123T114229"
FULL=ART/"full42_generated"
OUT=ART/"grouped_analysis"
SCENARIOS=["CENTRALIZED","FED_IID","FED_A05","FED_A01"]
POLICIES=["FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING",
          "GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"]
VARIANTS=["A_ALL_RULES","B2_TRUE_AS_FALLBACK"]
COLS=["accuracy_pct","balanced_accuracy_pct","test_coverage_pct",
      "candidate_coverage_pct","conflict_rate_pct","rule_count"]
DIMENSIONS=["cohort","feature_type_group","size_group","class_group",
            "binary_imbalance_group","feature_retention_group"]
SHORT={"CENTRALIZED":"Centralized","FED_IID":"Federated IID",
       "FED_A05":"Dirichlet α=0.5","FED_A01":"Dirichlet α=0.1"}


def ensure(cond, message):
    if not cond:
        raise RuntimeError(message)


def summarize(series):
    x=pd.to_numeric(series,errors="coerce").dropna()
    return float(x.mean()) if len(x) else np.nan


def seg_setup(meta):
    m=meta.copy()
    m["n_classes_int"]=pd.to_numeric(m.n_classes, errors="coerce")
    m["original_rows"]=pd.to_numeric(m.original_rows, errors="coerce")
    m["used_rows"]=pd.to_numeric(m.used_rows, errors="coerce")
    m["original_features"]=pd.to_numeric(m.original_features, errors="coerce")
    m["used_features"]=pd.to_numeric(m.used_features, errors="coerce")
    m["minority_share"]=pd.to_numeric(m.minority_share, errors="coerce")
    m["feature_type_group"]=m.feature_type.fillna("UNCLASSIFIED")
    m["size_group"]=pd.cut(m.original_rows,[0,500,5000,50000,float("inf")],
          labels=["<500","500–4,999","5,000–49,999",">=50,000"],right=False).astype(str)
    m["class_group"]=pd.cut(m.n_classes_int,[-.1,2.5,5.5,float("inf")],
          labels=["2","3–5","6+"],right=True).astype(str)
    m["binary_imbalance_group"]=np.select(
       [(m.n_classes_int==2)&(m.minority_share<.05),
        (m.n_classes_int==2)&(m.minority_share>=.05)&(m.minority_share<.2),
        (m.n_classes_int==2)&(m.minority_share>=.2)&(m.minority_share<.4),
        (m.n_classes_int==2)&(m.minority_share>=.4)],
       ["binary minority <5%","binary minority 5–<20%",
        "binary minority 20–<40%","binary minority >=40%"],
        default="multiclass (not binary comparable)")
    m["feature_retention_pct"]=100*m.used_features/m.original_features
    m["feature_retention_group"]=pd.cut(m.feature_retention_pct,
        [-.1,25,50,99.99999,float("inf")],
        labels=["<25%","25–<50%","50–<100%","100%"],
        right=False).astype(str)
    m["rows_retention_pct"]=100*m.used_rows/m.original_rows
    return m


def add_group_rows(df,dimensions=DIMENSIONS):
    records=[df.assign(dimension="ALL",group_value="ALL")]
    for key in dimensions:
        records.append(df.assign(dimension=key,group_value=df[key].fillna("UNCLASSIFIED").astype(str)))
    return pd.concat(records,ignore_index=True)


def aggregate_paired(frame):
    grouped=add_group_rows(frame)
    rows=[]
    for (dimension,gval,sc,variant,policy),g in grouped.groupby(
          ["dimension","group_value","scenario","rule_variant","selection_policy"],sort=True):
        rec={"dimension":dimension,"group_value":gval,"scenario":sc,
             "rule_variant":variant,"selection_policy":policy,
             "n_datasets":int(len(g))}
        for m in COLS:
            vals=g[m+"_delta"]
            rec[m+"_delta_mean"]=float(vals.mean())
            rec[m+"_delta_median"]=float(vals.median())
        rec["accuracy_delta_negative_n"]=int((g.accuracy_pct_delta< -1e-9).sum())
        rec["accuracy_delta_positive_n"]=int((g.accuracy_pct_delta>1e-9).sum())
        rec["ba_delta_positive_n"]=int((g.balanced_accuracy_pct_delta>1e-9).sum())
        rec["acc_negative_ba_positive_n"]=int(((g.accuracy_pct_delta<-1e-9)
                                               &(g.balanced_accuracy_pct_delta>1e-9)).sum())
        rec["accuracy_delta_q25"]=float(g.accuracy_pct_delta.quantile(.25))
        rec["accuracy_delta_q75"]=float(g.accuracy_pct_delta.quantile(.75))
        rows.append(rec)
    return pd.DataFrame(rows)


def make_winners(best,meta):
    b=best.merge(meta[["dataset",*DIMENSIONS]],on="dataset",how="inner",validate="many_to_one")
    expanded=add_group_rows(b)
    rows=[]
    for (dim,group,sc,variant),g in expanded.groupby(
          ["dimension","group_value","scenario","rule_variant"],sort=True):
        n=len(g)
        counts={p:0 for p in POLICIES}
        contains={p:0 for p in POLICIES}
        for names in g.accuracy_best_methods:
            winners=[p for p in str(names).split(";") if p]
            ensure(winners and set(winners).issubset(set(POLICIES)),
                   f"Malformed winner list: {names}")
            for p in winners:
                counts[p]+=1/len(winners)
                contains[p]+=1
        for p in POLICIES:
            rows.append({"dimension":dim,"group_value":group,"scenario":sc,
              "rule_variant":variant,"selection_policy":p,"n_datasets":n,
              "fractional_wins":counts[p],"inclusive_winner_n":contains[p],
              "fractional_win_share_pct":100*counts[p]/n,
              "mean_dataset_best_accuracy_pct":float(g.accuracy_best_pct.mean()),
              "mean_test_coverage_pct":float(g.test_coverage_pct.mean()),
              "mean_conflict_pct":float(g.conflict_rate_pct.mean()),
              "note":"POST_HOC_TEST_SET_ORACLE_FOR_DESCRIPTIVE_RANKING_ONLY"})
    return pd.DataFrame(rows)


def descriptive(df):
    rows=[]
    for scen,g in df.groupby("scenario"):
        rows.append({"scenario":scen,"n_datasets":len(g),
           **{f"mean_{k}":float(g[k].mean()) for k in
              ["accuracy_best_pct","balanced_accuracy_best_pct",
               "test_coverage_pct","candidate_coverage_pct","conflict_rate_pct","rule_count"]},
           "mean_candidate_given_coverage_pct":
               float((100*g.candidate_coverage_pct/
                 g.test_coverage_pct.replace(0,np.nan)).mean()),
           "n_testcov_ge80":int((g.test_coverage_pct>=80).sum()),
           "n_conflict_ge50":int((g.conflict_rate_pct>=50).sum()),
           "n_accuracy_BA_gap_ge20":int(((g.accuracy_best_pct-g.balanced_accuracy_best_pct)>=20).sum())
        })
    return pd.DataFrame(rows).set_index("scenario").reindex(SCENARIOS).reset_index()


def build_cases(meta,policy,best):
    fixed=policy[(policy.rule_variant=="A_ALL_RULES")&(policy.selection_policy=="STANDARD_VOTING")]
    measures=["avg_"+x for x in COLS]
    wide=fixed.pivot(index="dataset",columns="scenario",values=measures)
    wide.columns=[f"{sc}__{m.replace('avg_','')}" for (m,sc) in wide.columns]
    wide=wide.reset_index()
    r=meta.merge(wide,on="dataset",validate="one_to_one",how="inner")
    winners=best[best.rule_variant=="A_ALL_RULES"]
    winwide=winners.pivot(index="dataset",columns="scenario",values=["accuracy_best_pct","accuracy_best_methods"])
    winwide.columns=[f"{sc}__best_{m}" for m,sc in winwide.columns]
    r=r.merge(winwide.reset_index(),on="dataset",how="inner",validate="one_to_one")
    for sc in SCENARIOS[1:]:
        r[f"{sc}__accuracy_delta_standard_pp"]=r[f"{sc}__accuracy_pct"]-r["CENTRALIZED__accuracy_pct"]
        r[f"{sc}__ba_delta_standard_pp"]=r[f"{sc}__balanced_accuracy_pct"]-r["CENTRALIZED__balanced_accuracy_pct"]
        r[f"{sc}__coverage_delta_pp"]=r[f"{sc}__test_coverage_pct"]-r["CENTRALIZED__test_coverage_pct"]
        r[f"{sc}__conflict_delta_pp"]=r[f"{sc}__conflict_rate_pct"]-r["CENTRALIZED__conflict_rate_pct"]
    r["a05_acc_down_ba_up"]=(r.FED_A05__accuracy_delta_standard_pp<0)&(r.FED_A05__ba_delta_standard_pp>0)
    r["a01_cov_up20_acc_down5"]=(r.FED_A01__coverage_delta_pp>=20)&(r.FED_A01__accuracy_delta_standard_pp<=-5)
    r["a01_cov_ge80_conflict_ge50"]=(r.FED_A01__test_coverage_pct>=80)&(r.FED_A01__conflict_rate_pct>=50)
    r["a01_acc_high_ba_low"]=(r.FED_A01__best_accuracy_best_pct>=90)&(r.FED_A01__balanced_accuracy_pct<=60)
    r["a01_candidate_coverage_gap_pp"]=r.FED_A01__test_coverage_pct-r.FED_A01__candidate_coverage_pct
    r["a01_rule_count_less_than_iid"]=r.FED_A01__rule_count<r.FED_IID__rule_count
    r["a01_conflict_gt_iid"]=r.FED_A01__conflict_rate_pct>r.FED_IID__conflict_rate_pct
    r["iid_best_accuracy_gain_pp"]=r.FED_IID__best_accuracy_best_pct-r.CENTRALIZED__best_accuracy_best_pct
    r["a01_best_accuracy_change_pp"]=r.FED_A01__best_accuracy_best_pct-r.CENTRALIZED__best_accuracy_best_pct
    return r


def main():
    ensure((SNAP/"SNAPSHOT_STAMP").read_text().strip()=="20261123T114229",
           "Only snapshot 20261123T114229 may be published by this review")
    rc=json.loads((FULL/"BUILD_RECEIPT.json").read_text())
    ensure(rc["complete_datasets"]==179 and rc["result_rows"]==360936,
           "Source receipt not matching frozen snapshot")
    meta=pd.read_csv(FULL/"DATASET_CATALOG_188.csv",encoding="utf-8-sig")
    complete=meta.loc[meta.status_42seed=="COMPLETE","dataset"].tolist()
    ensure(len(meta)==188 and len(complete)==179,"Unmatched registry size")
    meta=seg_setup(meta)
    p=pd.read_csv(FULL/"DATASET_POLICY_METRICS_42SEED.csv",encoding="utf-8-sig")
    best=pd.read_csv(FULL/"DATASET_SCENARIO_BEST_42SEED.csv",encoding="utf-8-sig")
    p=p[(p.dataset.isin(complete))&(p.n_seeds==42)].copy()
    b=best[(best.dataset.isin(complete))&(best.n_seeds==42)].copy()
    ensure(len(p)==179*4*2*6 and len(b)==179*4*2,
           f"Unexpected primary complete records: {len(p)} and {len(b)}")
    ensure(all(p.groupby(["dataset","scenario","rule_variant"]).size()==6),
           "Missing strategy within complete dataset scenario")
    # Coverage, candidate coverage, conflict, rule count should not vary by policy
    for metric in ["avg_test_coverage_pct","avg_candidate_coverage_pct",
                   "avg_conflict_rate_pct","avg_rule_count"]:
        g=p.groupby(["dataset","scenario","rule_variant"])[metric]
        ensure(float((g.max()-g.min()).abs().max())<1e-6,
               f"Unexpected policy-dependent structure: {metric}")
    baseline=p[p.scenario=="CENTRALIZED"].copy()
    key=["dataset","rule_variant","selection_policy"]
    keep=key+["avg_"+x for x in COLS]
    base=baseline[keep].rename(columns={"avg_"+x:x+"_central" for x in COLS})
    fed=p[p.scenario!="CENTRALIZED"].merge(base,on=key,how="inner",validate="many_to_one")
    ensure(len(fed)==179*3*2*6,"Unpaired complete rows")
    for x in COLS:
        fed[x+"_delta"]=fed["avg_"+x]-fed[x+"_central"]
    fed=fed.merge(meta[["dataset",*DIMENSIONS]],on="dataset",how="left",validate="many_to_one")
    by_group=aggregate_paired(fed)
    by_winner=make_winners(b,meta)
    overview=descriptive(b[b.rule_variant=="A_ALL_RULES"])
    cases=build_cases(meta.loc[meta.dataset.isin(complete)].copy(),p,b)
    ensure(len(cases)==179,"Diagnostics missing datasets")
    # Original dataset names are human readable; internal IDs are kept solely for linking.
    view=meta.copy()
    view["display_name"]=np.where(view.cohort=="OML51",
       view.name.fillna("").astype(str)+" (OpenML #"+view.dataset.str.extract(r"openml_(\d+)")[0].fillna("?")+")",
       view.name.fillna("").astype(str))
    g5=pd.read_csv(ROOT/"docs/research/redesign_20261116/data/CONFIRMATORY_SOURCE_REGISTRY.csv")
    fam=g5[["did","family","name","version"]].drop_duplicates("did")
    fam["dataset"]="OML51:openml_"+fam.did.astype(str)
    view=view.merge(fam[["dataset","family","version"]],on="dataset",how="left",validate="one_to_one")
    # No raw hashes, prepared hashes, model digests or audit secrets in public-facing tables.
    keepcols=["dataset","display_name","cohort","family","version","original_rows","used_rows",
              "rows_retention_pct","original_features","used_features",
              "feature_retention_pct","used_feature_names","n_classes_int",
              "minority_share","feature_type_group","size_group",
              "class_group","binary_imbalance_group","feature_retention_group",
              "source_url","status_42seed","completed_models_42seed","expected_models_42seed"]
    view=view[keepcols].rename(columns={"n_classes_int":"n_classes","status_42seed":"completion_42seed"})
    nohash=lambda frame: ensure(not any("sha" in str(x).lower() for x in frame.columns),
      "Presentation table includes SHA field")
    for frame in [view,by_group,by_winner,overview,cases]:
        nohash(frame)
    OUT.mkdir(parents=True,exist_ok=False)
    view.to_csv(OUT/"DATASET_CATALOG_HUMAN_188.csv",index=False,encoding="utf-8-sig")
    by_group.to_csv(OUT/"STRATIFIED_PAIRED_EFFECTS.csv",index=False,encoding="utf-8-sig")
    by_winner.to_csv(OUT/"STRATIFIED_WINNER_COUNTS.csv",index=False,encoding="utf-8-sig")
    overview.to_csv(OUT/"SCENARIO_OVERVIEW_179.csv",index=False,encoding="utf-8-sig")
    cases.to_csv(OUT/"DATASET_DIAGNOSTICS_179.csv",index=False,encoding="utf-8-sig")
    diag={
      "n_complete":179,
      "n_incomplete":9,
      "n_binary":int((meta.n_classes_int==2).sum()),
      "n_multiclass":int((meta.n_classes_int>2).sum()),
      "n_feature_retention_below25_all":int((meta.feature_retention_pct<25).sum()),
      "n_feature_retention_below25_complete":int((cases.feature_retention_pct<25).sum()),
      "n_a05_acc_down_ba_up_standard":int(cases.a05_acc_down_ba_up.sum()),
      "n_a01_cov_up20_acc_down5_standard":int(cases.a01_cov_up20_acc_down5.sum()),
      "n_a01_coverage80_conflict50":int(cases.a01_cov_ge80_conflict_ge50.sum()),
      "n_a01_high_acc_low_ba":int(cases.a01_acc_high_ba_low.sum()),
      "n_a01_rules_less_than_iid":int(cases.a01_rule_count_less_than_iid.sum()),
      "n_a01_conflict_greater_than_iid":int(cases.a01_conflict_gt_iid.sum()),
      "n_iid_best_accuracy_better":int((cases.iid_best_accuracy_gain_pp>1e-9).sum()),
      "n_a01_best_accuracy_worse":int((cases.a01_best_accuracy_change_pp<-1e-9).sum()),
      "correlation_a01_conflict_vs_accuracy_drop_standard_spearman":
        float(cases["FED_A01__conflict_rate_pct"].corr(
             cases["FED_A01__accuracy_delta_standard_pp"],method="spearman")),
      "correlation_a01_coverage_vs_accuracy_drop_standard_spearman":
        float(cases["FED_A01__test_coverage_pct"].corr(
             cases["FED_A01__accuracy_delta_standard_pp"],method="spearman")),
    }
    (OUT/"DIAGNOSTIC_COUNTS.json").write_text(json.dumps(diag,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    # For human-facing contrast, choose fixed STANDARD_VOTING, rather than test-selected best policy.
    std=by_group[(by_group.rule_variant=="A_ALL_RULES")&
                 (by_group.selection_policy=="STANDARD_VOTING")&
                 (by_group.scenario.isin(["FED_IID","FED_A05","FED_A01"]))]
    records=[]
    for dimension in DIMENSIONS:
        for _,r in std[std.dimension==dimension].iterrows():
            if r.n_datasets<5:
                continue
            records.append({"dimension":dimension,"group":r.group_value,"scenario":r.scenario,
                 "n":int(r.n_datasets),"Accuracy Δ pp":round(r.accuracy_pct_delta_mean,3),
                 "Balanced Accuracy Δ pp":round(r.balanced_accuracy_pct_delta_mean,3),
                 "Coverage Δ pp":round(r.test_coverage_pct_delta_mean,3),
                 "Candidate Coverage Δ pp":round(r.candidate_coverage_pct_delta_mean,3),
                 "Conflict Δ pp":round(r.conflict_rate_pct_delta_mean,3),
                 "Accuracy下降且BA上升 n":int(r.acc_negative_ba_positive_n)})
    condensed=pd.DataFrame(records)
    condensed.to_csv(OUT/"GROUPED_TEACHER_TABLE_STANDARD_VOTING.csv",index=False,encoding="utf-8-sig")
    top=cases[["dataset","name","cohort","original_rows","n_classes_int",
        "feature_type_group","minority_share","FED_A01__accuracy_delta_standard_pp",
        "FED_A01__ba_delta_standard_pp","FED_A01__coverage_delta_pp",
        "FED_A01__conflict_rate_pct","a01_cov_up20_acc_down5"]].copy()
    top.sort_values("FED_A01__accuracy_delta_standard_pp").head(15).to_csv(
        OUT/"CASE_STUDIES_LARGEST_A01_ACCURACY_LOSS.csv",index=False,encoding="utf-8-sig")
    top.sort_values("FED_A01__accuracy_delta_standard_pp",ascending=False).head(15).to_csv(
        OUT/"CASE_STUDIES_A01_COUNTEREXAMPLES.csv",index=False,encoding="utf-8-sig")
    receipt={"snapshot":"20261123T114229","complete_datasets":179,
             "input_policy_rows":len(p),"input_best_rows":len(b),
             "group_effects_rows":len(by_group),"winner_rows":len(by_winner),
             "case_studies":len(cases),"diagnostics":diag,
             "limitations":["nonrandom incomplete datasets","source family dependence",
              "first-six feature policy","test-selected best method is descriptive only",
              "OpenML original target-label identities not available in registry"]}
    (OUT/"RECEIPT.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
