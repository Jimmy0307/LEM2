"""Exploratory finite-sample regime/turning-point diagnostics; NO causal or physics claim.

Two evidence levels:
 (1) 179 independent registry tasks with paired 42-seed scenario deltas.
 (2) 2026-11-18 scale ladder: selected 26 large sources, seed=1001, 1800/10000/full;
     scale subsets are independently drawn, NOT nested, and only one seed.
The script NEVER changes training code, and preserves fixed snapshot IDs.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/research/expanded_188_42seeds/report_catalog/20261123T114229"
IN=BASE/"grouped_analysis/DATASET_DIAGNOSTICS_179.csv"
LADDER=ROOT/"docs/research/full_scale_20261118/SCALE_LADDER.csv"
OUT=BASE/"regime_exploration"
SNAP="20261123T114229"
SCENARIOS=["FED_IID","FED_A05","FED_A01"]
METRICS=["accuracy","ba","coverage","conflict","rule_count"]
BINS=[0,500,5000,50000,float("inf")]
BIN_LABELS=["<500","500–4,999","5,000–49,999",">=50,000"]


def ols(x,y):
    b=np.linalg.lstsq(x,y,rcond=None)[0]
    return b, float(np.mean(np.square(y-x@b)))


def controls(frame):
    cols=["cohort","feature_type_group"]
    dummy=pd.get_dummies(frame[cols].astype(str),drop_first=True).astype(float)
    ncls=np.log1p(pd.to_numeric(frame.n_classes_int,errors="coerce")).to_numpy()
    min_share=np.log10(np.maximum(pd.to_numeric(frame.minority_share,errors="coerce").to_numpy(),.00001))
    retention=pd.to_numeric(frame.feature_retention_pct,errors="coerce").to_numpy()/100
    # No features are computed from performance or Test labels.
    z=np.column_stack([np.ones(len(frame)),dummy.to_numpy(),ncls,min_share,retention])
    if not np.isfinite(z).all():
        raise ValueError("Non-finite adjustment covariates")
    return z


def fit_hinge(z,x,y,minimum=25):
    candidates=np.sort(np.unique(x))
    candidates=[float(t) for t in candidates if np.sum(x<=t)>=minimum
                and np.sum(x>t)>=minimum]
    if not candidates:
        return None
    best=None
    for t in candidates:
        X=np.column_stack([z,x,np.maximum(0,x-t)])
        coef,mse=ols(X,y)
        if best is None or mse<best["mse"]:
            best={"cut_log10":t,"cut_rows":10**t,"mse":mse,"coef":coef}
    return best


def cv_quality(z,x,y,minimum=20,folds=5,seeds=(19,43,103)):
    base_err,hinge_err=[],[]
    n=len(x)
    for seed in seeds:
        rng=np.random.default_rng(seed)
        inds=rng.permutation(n)
        buckets=np.array_split(inds,folds)
        for test in buckets:
            train=np.setdiff1d(np.arange(n),test)
            X=np.column_stack([z[train],x[train]])
            beta,_=ols(X,y[train])
            pred=np.column_stack([z[test],x[test]])@beta
            base_err.extend(np.square(pred-y[test]).tolist())
            hinge=fit_hinge(z[train],x[train],y[train],minimum=minimum)
            if hinge is None:
                pred2=pred
            else:
                Xt=np.column_stack([z[test],x[test],np.maximum(0,x[test]-hinge["cut_log10"])])
                pred2=Xt@hinge["coef"]
            hinge_err.extend(np.square(pred2-y[test]).tolist())
    return (float(np.sqrt(np.mean(base_err))),float(np.sqrt(np.mean(hinge_err))))


def bootstrap_slope(z,x,y,iterations=300):
    rng=np.random.default_rng(20261123)
    slopes=[]
    for _ in range(iterations):
        take=rng.integers(0,len(y),len(y))
        b,_=ols(np.column_stack([z[take],x[take]]),y[take])
        slopes.append(b[-1])
    b,_=ols(np.column_stack([z,x]),y)
    return float(b[-1]),float(np.quantile(slopes,.025)),float(np.quantile(slopes,.975))


def bootstrap_cut(z,x,y,iterations=120):
    rng=np.random.default_rng(19261123)
    cuts=[]
    for _ in range(iterations):
        take=rng.integers(0,len(y),len(y))
        h=fit_hinge(z[take],x[take],y[take],minimum=25)
        if h:
            cuts.append(h["cut_rows"])
    return ([float(np.quantile(cuts,q)) for q in [.25,.5,.75]] if cuts
            else [None]*3)


def combined_size_bins(df):
    rows=[]
    df=df.copy()
    df["size_band"]=pd.cut(df.original_rows,BINS,labels=BIN_LABELS,right=False)
    for scenario in SCENARIOS:
        for band,g in df.groupby("size_band",observed=True):
            rec={"scenario":scenario,"size_band":str(band),"n_datasets":len(g),
                 "min_rows":int(g.original_rows.min()),"max_rows":int(g.original_rows.max()),
                 "median_rows":float(g.original_rows.median())}
            for key,column in [
                ("accuracy_delta_pp",f"{scenario}__accuracy_delta_standard_pp"),
                ("ba_delta_pp",f"{scenario}__ba_delta_standard_pp"),
                ("conflict_delta_pp",f"{scenario}__conflict_delta_pp"),
                ("coverage_delta_pp",f"{scenario}__coverage_delta_pp"),
                ("absolute_conflict_pct",f"{scenario}__conflict_rate_pct"),
                ("absolute_coverage_pct",f"{scenario}__test_coverage_pct")]:
                rec[key+"_mean"]=float(g[column].mean())
                rec[key+"_median"]=float(g[column].median())
                rec[key+"_q25"]=float(g[column].quantile(.25))
                rec[key+"_q75"]=float(g[column].quantile(.75))
            rec["conflict_ge50_n"]=int((g[f"{scenario}__conflict_rate_pct"]>=50).sum())
            rec["accuracy_drop_ge5pp_n"]=int((g[f"{scenario}__accuracy_delta_standard_pp"]<=-5).sum())
            rows.append(rec)
    return pd.DataFrame(rows)


def size_quantiles(df):
    frame=df.copy()
    frame["quantile"]=pd.qcut(frame.original_rows,6,duplicates="drop")
    rows=[]
    for sc in SCENARIOS:
        for interval,g in frame.groupby("quantile",observed=True):
            rows.append({"scenario":sc,"rows_range":str(interval),
               "n":len(g),"median_rows":float(g.original_rows.median()),
               "mean_conflict_delta_pp":float(g[f"{sc}__conflict_delta_pp"].mean()),
               "median_conflict_delta_pp":float(g[f"{sc}__conflict_delta_pp"].median()),
               "mean_accuracy_delta_pp":float(g[f"{sc}__accuracy_delta_standard_pp"].mean()),
               "mean_ba_delta_pp":float(g[f"{sc}__ba_delta_standard_pp"].mean())})
    return pd.DataFrame(rows)


def threshold_analysis(df):
    x=np.log10(df.original_rows.to_numpy(dtype=float))
    z=controls(df)
    results=[]
    for sc in SCENARIOS:
        for metric,column in [
            ("conflict_delta_pp",f"{sc}__conflict_delta_pp"),
            ("accuracy_delta_pp",f"{sc}__accuracy_delta_standard_pp"),
            ("coverage_delta_pp",f"{sc}__coverage_delta_pp")]:
            y=df[column].to_numpy(dtype=float)
            if not np.isfinite(y).all():raise ValueError("NAN response")
            s,low,high=bootstrap_slope(z,x,y)
            cut=fit_hinge(z,x,y)
            base_rmse,hinge_rmse=cv_quality(z,x,y)
            q1,q2,q3=bootstrap_cut(z,x,y,iterations=120) if metric=="conflict_delta_pp" else (None,None,None)
            results.append({
                "scenario":sc,"metric":metric,"n_datasets":len(df),
                "adjusted_slope_per_10x_rows_pp":s,
                "adjusted_slope_bootstrap_95ci_low":low,
                "adjusted_slope_bootstrap_95ci_high":high,
                "candidate_cut_rows_descriptive":cut["cut_rows"] if cut else np.nan,
                "candidate_cut_boot_q25":q1,
                "candidate_cut_boot_median":q2,
                "candidate_cut_boot_q75":q3,
                "out_of_sample_linear_rmse_pp":base_rmse,
                "out_of_sample_hinge_rmse_pp":hinge_rmse,
                "hinge_rmse_improvement_pp":base_rmse-hinge_rmse,
                "evidence_note":"EXPLORE_ONLY; 5-fold repeated CV; adjusted for cohort, feature type, n_classes, class minority share, feature retention",
            })
    return pd.DataFrame(results)


def ladder_compare():
    d=pd.read_csv(LADDER)
    f=d[(d.seed.astype(str)=="1001")&
        (d.selection_policy=="STANDARD_VOTING")&
        (d.rule_variant=="A_ALL_RULES")&
        (d.scenario.isin(["FED_IID","FED_A01"]))].copy()
    key=["dataset","scenario","scale"]
    if f.duplicated(key).any():raise ValueError("Ladder has duplicate dataset/scenario/scale")
    expected={"1800","10000","FULL"}
    records=[]
    for (dataset,sc),g in f.groupby(["dataset","scenario"]):
        scale=set(g.scale.astype(str))
        rec={"dataset":dataset,"scenario":sc,"seeds":1,
             "complete_3_levels":expected.issubset(scale),"levels_seen":len(g)}
        if not rec["complete_3_levels"]:
            records.append(rec);continue
        d=g.set_index(g.scale.astype(str))
        rec.update({
            "rows_1800":float(d.loc["1800","scale_used_rows"]),
            "rows_10000":float(d.loc["10000","scale_used_rows"]),
            "rows_full":float(d.loc["FULL","scale_used_rows"])
        })
        vals={}
        for metric,col in [("conflict","conflict_rate_pct"),("coverage","test_coverage_pct"),
                           ("accuracy","accuracy_pct"),("ba","balanced_accuracy_pct"),
                           ("rules","rule_count")]:
            arr=[float(d.loc[level,col]) for level in ["1800","10000","FULL"]]
            for level,v in zip(["1800","10000","FULL"],arr):
                rec[f"{metric}_{level}"]=v
            rec[f"{metric}_delta_1_to_2"]=arr[1]-arr[0]
            rec[f"{metric}_delta_2_to_3"]=arr[2]-arr[1]
            if metric=="rules":eps=1.
            else:eps=1.
            a,b=arr[1]-arr[0],arr[2]-arr[1]
            if a>eps and b< -eps:shape="PEAK"
            elif a< -eps and b>eps:shape="VALLEY"
            elif a>eps and b>eps:shape="INCREASE"
            elif a< -eps and b< -eps:shape="DECREASE"
            else:shape="PLATEAU_OR_SINGLE_STEP"
            rec[f"{metric}_shape"]=shape
        records.append(rec)
    return pd.DataFrame(records)


def write(d,path):
    d.to_csv(path,index=False,encoding="utf-8-sig")


def md_table(frame,cols,formats=None):
    formats=formats or {}
    rows=["| "+" | ".join(cols)+" |","| "+" | ".join(["---"]*len(cols))+" |"]
    for row in frame.itertuples(index=False):
        d=row._asdict()
        vals=[]
        for col in cols:
            val=d.get(col,"")
            vals.append(str(round(val,2)) if isinstance(val,float) and np.isfinite(val) else str(val))
        rows.append("| "+" | ".join(vals)+" |")
    return "\n".join(rows)


def main():
    snapshot=(BASE.parent.parent/"interim/SNAPSHOT_STAMP").read_text().strip()
    if snapshot!=SNAP:raise ValueError("Unexpected snapshot "+snapshot)
    frame=pd.read_csv(IN,encoding="utf-8-sig")
    if len(frame)!=179 or not (frame.status_42seed=="COMPLETE").all():
        raise ValueError("Expected exactly 179 complete datasets")
    frame.original_rows=pd.to_numeric(frame.original_rows)
    coarse=combined_size_bins(frame)
    quant=size_quantiles(frame)
    threshold=threshold_analysis(frame)
    ladder=ladder_compare()
    OUT.mkdir(parents=True,exist_ok=False)
    for d,path in [
        (coarse,"SIZE_REGIMES_179.csv"),
        (quant,"SIZE_QUANTILES_179.csv"),
        (threshold,"EXPLORATORY_CHANGEPOINT_CV.csv"),
        (ladder,"WITHIN_SOURCE_SCALE_LADDER_1SEED.csv")]:
        write(d,OUT/path)
    shape=[]
    for sc in ["FED_IID","FED_A01"]:
        sample=ladder[(ladder.scenario==sc)&(ladder.complete_3_levels==True)]
        for metric in ["conflict","accuracy","coverage"]:
            x=sample[f"{metric}_shape"].value_counts().to_dict()
            shape.append({"scenario":sc,"metric":metric,"n_three_levels":len(sample),
                          **{k:int(x.get(k,0)) for k in
                          ["DECREASE","INCREASE","PEAK","VALLEY","PLATEAU_OR_SINGLE_STEP"]}})
    shapes=pd.DataFrame(shape);write(shapes,OUT/"LADDER_SHAPE_COUNTS.csv")
    corr=[]
    for sc in SCENARIOS:
        a=frame[f"{sc}__conflict_delta_pp"].rank()
        b=frame[f"{sc}__accuracy_delta_standard_pp"].rank()
        size=frame.original_rows.rank()
        corr.append({"scenario":sc,"n":len(frame),
         "spearman_rows_conflict_delta":float(size.corr(a)),
         "spearman_rows_accuracy_delta":float(size.corr(b)),
         "spearman_conflict_delta_accuracy_delta":float(a.corr(b))})
    cor=pd.DataFrame(corr);write(cor,OUT/"SPEARMAN_DESCRIPTIVE.csv")
    receipt={"snapshot":SNAP,"complete_datasets":len(frame),
      "ladder_sources":int(ladder.dataset.nunique()),"three_level_A01":
      int(shapes[(shapes.scenario=="FED_A01")&(shapes.metric=="conflict")].n_three_levels.iloc[0]),
      "three_level_IID":int(shapes[(shapes.scenario=="FED_IID")&(shapes.metric=="conflict")].n_three_levels.iloc[0]),
      "primary_statistic":"dataset-level paired mean of 42-seed differences",
      "inference":"candidate threshold exploratory; no significance or physical phase transition asserted",
      "limitations":["unbalanced source families","missing large/timeout cases","scale ladder seed 1001 only",
         "scale ladder subsets not necessarily nested","first six features","candidate selection per outcome"]}
    (OUT/"RECEIPT.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    size=coarse[coarse.scenario=="FED_A01"]
    t=threshold[threshold.scenario=="FED_A01"]
    shapeA=shapes[shapes.scenario=="FED_A01"]
    lines=[
        "# LEM2 data-size regimes, conflicts, and non-monotonicity",
        "",
        "**EXPLORATORY / NOT A PROVEN PHASE TRANSITION.** 42-seed primary snapshot "+SNAP,
        "179 completely paired datasets. All outcomes use A_ALL_RULES and fixed STANDARD_VOTING.",
        "",
        "## Predefined original-row-size bands",
        "",
        "| Size | n | Δ Conflict pp (FED_A01 - Central) | Δ Accuracy pp | Absolute FED_A01 Conflict % | >=50% conflict datasets |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in size.itertuples(index=False):
        lines.append(f"| {r.size_band} | {r.n_datasets} | {r.conflict_delta_pp_mean:.2f} | {r.accuracy_delta_pp_mean:.2f} | {r.absolute_conflict_pct_mean:.2f} | {r.conflict_ge50_n} |")
    lines+=["","**Cross-dataset trend is a size association, not a within-dataset threshold.**",
      "Some of the largest datasets are missing due to timeout; class and domain mixes vary by size.",
      "",
      "## Exploratory adjusted change-point fits (candidate, NOT established)",
      "",
      "| Outcome | Per 10× rows adjusted slope (bootstrap 95% CI) | Candidate cut rows | Cut IQR (bootstrap, conflict only) | 5-fold linear RMSE | 5-fold hinge RMSE |",
      "|---|---:|---:|---:|---:|---:|"]
    for r in t.itertuples(index=False):
        lines.append(f"| {r.metric} | {r.adjusted_slope_per_10x_rows_pp:+.2f} [{r.adjusted_slope_bootstrap_95ci_low:+.2f}, {r.adjusted_slope_bootstrap_95ci_high:+.2f}] | {r.candidate_cut_rows_descriptive:,.0f} | {r.candidate_cut_boot_q25 or float('nan'):,.0f}–{r.candidate_cut_boot_q75 or float('nan'):,.0f} | {r.out_of_sample_linear_rmse_pp:.2f} | {r.out_of_sample_hinge_rmse_pp:.2f} |")
    lines+=["",
      "Hinge breakpoint optimized inside train folds and evaluated on held-out folds. Apparent cut points are data-driven and subject to source-family confounding. Do not interpret a particular row number as a physical phase transition.",
      "",
      "## Within-source three-level ladder (only one seed, selected large datasets)",
      "",
      "| Scenario | Metric | 3-level datasets | decreasing | increasing | peak | valley | other |",
      "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in shapes.itertuples(index=False):
        lines.append(f"| {r.scenario} | {r.metric} | {r.n_three_levels} | {r.DECREASE} | {r.INCREASE} | {r.PEAK} | {r.VALLEY} | {r.PLATEAU_OR_SINGLE_STEP} |")
    lines+=["",
       "The scale ladder uses different sampled datasets at 1,800, 10,000 and FULL. It is not a controlled nested expansion. One seed cannot establish replicable thresholds.",
       "",
       "## Verification path",
       "",
       "- `SIZE_REGIMES_179.csv`: 4 predefined bins × 3 scenarios, within-bin dispersion and conflict >=50 counts",
       "- `SIZE_QUANTILES_179.csv`: 6 data-driven size quantiles for visualizing smooth or nonmonotone curves",
       "- `EXPLORATORY_CHANGEPOINT_CV.csv`: adjusted coefficients, bootstrap intervals, train-selected hinge and out-of-sample RMSE",
       "- `WITHIN_SOURCE_SCALE_LADDER_1SEED.csv`: full per-source 3-level curves with shape labels",
       "- `LADDER_SHAPE_COUNTS.csv`: aggregated falling/rising/peak/valley counts",
       "- `SPEARMAN_DESCRIPTIVE.csv`: rank relationships",
       "",
       "## Next experimental controls before a threshold claim",
       "",
       "1. Select and preregister candidate row budgets (e.g. 500, 1,800, 5,000, 10,000, 25,000, FULL).",
       "2. Re-run the **same datasets** at each row budget with nested, class-stratified samples, fixed identical feature selection and 5+ seeds.",
       "3. Measure conflict rate, rule count, candidate coverage, class-wise recall, TRUE-rule incidence, min client-class support, throughput, timeouts and memory.",
       "4. Use held-out datasets or previously unexamined seeds to validate a candidate threshold rather than selecting and testing on the same cases.",
       "5. Compare one-hinge, monotone and no-threshold baselines; report uncertainty and subgroup disagreements.",
       "",
       "### Bias to avoid",
       "",
       "The 'best Accuracy' obtained by selecting a voting policy using TEST labels is a post-hoc oracle, not deployable performance; this analysis uses a fixed voting policy to avoid it.",
       "",
    ]
    (OUT/"REGIME_EXPLORATORY_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"receipt":receipt,"threshold":t.to_dict("records"),
        "ladder_shapes":shapes.to_dict("records"),"spearman":cor.to_dict("records")},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
