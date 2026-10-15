"""Build old-vs-new, result tables, resolver winners and structural associations.

Usage: python analyze.py <audit_dir>
  <audit_dir>/PRE_FIX_BASELINE/batch_runs/PRE_FIX_5e649ef   pre-fix rerun (main @ 5e649ef)
  <audit_dir>/UCI3_HOLDOUT42_FINAL/batch_runs/FINAL           post-fix rerun
  evidence/20261014_162216                                     PRE_AUDIT_REFERENCE_RUN (subset of tables)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
KEY = ["dataset", "client_count"]
POLICIES = ["FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"]
DATASETS = ["Hayes-Roth", "Car Evaluation", "Balance Scale"]
METRICS = [
    "accuracy", "balanced_accuracy", "macro_f1", "coverage",
    "conflict_resolution_accuracy", "conflict_balanced_accuracy", "conflict_macro_f1",
    "disagreement_vs_first_match", "conflict_disagreement_vs_first_match",
    "order_sensitivity_rate", "order_balanced_accuracy_mean", "order_balanced_accuracy_std",
    "order_balanced_accuracy_min", "order_balanced_accuracy_max",
    "central_accuracy", "central_balanced_accuracy", "central_macro_f1", "central_coverage",
]


def read(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def local_reducts(run: Path) -> pd.DataFrame:
    frames = []
    for folder in sorted((run / "structural").iterdir()):
        f = folder / "local_reducts.csv"
        if f.exists():
            frames.append(read(f))
    t = pd.concat(frames, ignore_index=True)
    t["selected"] = t["selected_reduct"].map(lambda s: "+".join(json.loads(s)) or "EMPTY")
    return (
        t.sort_values(["dataset", "client_count", "client_id"])
        .groupby(KEY)["selected"].agg(lambda s: " | ".join(s)).rename("local_reducts").reset_index()
    )


def local_rule_counts(run: Path) -> pd.DataFrame:
    frames = []
    for folder in sorted((run / "structural").iterdir()):
        f = folder / "rule_metrics.csv"
        if f.exists():
            frames.append(read(f))
    t = pd.concat(frames, ignore_index=True)
    t = t[t["scope"] == "LOCAL"].sort_values(["dataset", "client_count", "client_id"])
    return t.groupby(KEY)["rule_count"].agg(lambda s: " | ".join(str(int(x)) for x in s)).rename("local_rule_counts").reset_index()


def structural(run: Path) -> pd.DataFrame:
    s = read(run / "structural_summary.csv")
    s = s.merge(local_reducts(run), on=KEY).merge(local_rule_counts(run), on=KEY)
    s["central_reduct"] = s["central_reduct"].map(lambda v: "+".join(json.loads(v)) or "EMPTY")
    s["covered_conflict_rate"] = s["pre_resolution_conflict_case_rate"] / s["coverage"]
    return s


def compare_frames(a: pd.DataFrame, b: pd.DataFrame, key, skip=()):
    a = a.sort_values(key).reset_index(drop=True)
    b = b.sort_values(key).reset_index(drop=True)
    diffs = []
    for c in a.columns:
        if c in skip or c not in b.columns:
            continue
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            same = np.isclose(x.astype(float), y.astype(float), rtol=0, atol=1e-12, equal_nan=True)
        else:
            same = (x.astype(str) == y.astype(str)).to_numpy()
        for i in np.where(~same)[0]:
            diffs.append({**{k: a.loc[i, k] for k in key}, "column": c, "old": x[i], "new": y[i]})
    return pd.DataFrame(diffs)


def main(audit: Path):
    pre = audit / "PRE_FIX_BASELINE" / "batch_runs" / "PRE_FIX_5e649ef"
    fin = audit / "UCI3_HOLDOUT42_FINAL" / "batch_runs" / "FINAL"
    ref = ROOT / "evidence" / "20261014_162216"
    out = audit

    # 1. reproduction of the reference by the pre-fix rerun, and structural identity pre vs final
    timing = [c for c in read(ref / "structural_summary.csv").columns if "seconds" in c]
    repro = pd.concat([
        compare_frames(read(ref / "structural_summary.csv"), read(pre / "structural_summary.csv"), ["dataset", "fold", "client_count"], timing).assign(table="structural_summary"),
        compare_frames(read(ref / "research_chain_summary.csv"), read(pre / "research_chain_summary.csv"), ["dataset", "fold", "client_count"]).assign(table="research_chain_summary"),
    ])
    s_pre, s_fin = structural(pre), structural(fin)
    struct_diff = compare_frames(s_pre, s_fin, KEY, timing + ["fold"])
    checks = {
        "reference_vs_prefix_rerun_nontiming_differences": int(len(repro)),
        "prefix_vs_final_structural_differences": int(len(struct_diff)),
    }
    struct_diff.to_csv(out / "structural_prefix_vs_final_diff.csv", index=False)

    # 2. old_vs_new.csv
    r_pre = read(pre / "resolver_summary.csv")
    r_fin = read(fin / "resolver_summary.csv")
    chain_ref = read(ref / "research_chain_summary.csv")
    ref_rows = []
    for _, row in chain_ref.iterrows():
        for p in POLICIES:
            ref_rows.append({"dataset": row["dataset"], "client_count": row["client_count"], "policy": p,
                             "reference_20261014_balanced_accuracy": row[f"{p}_balanced_accuracy"],
                             "reference_20261014_conflict_balanced_accuracy": row[f"{p}_conflict_balanced_accuracy"]})
    ref_long = pd.DataFrame(ref_rows)
    keyp = KEY + ["policy"]
    m = r_pre[keyp + METRICS].merge(r_fin[keyp + METRICS], on=keyp, suffixes=("_old", "_new"))
    m = ref_long.merge(m, on=keyp, how="right")
    for c in METRICS:
        m[f"{c}_delta"] = m[f"{c}_new"] - m[f"{c}_old"]
    sf = s_fin[KEY + ["central_reduct", "local_reducts", "central_rule_count", "local_rule_counts",
                      "global_rule_count", "pre_resolution_conflict_case_rate"]]
    sp = s_pre[KEY + ["central_reduct", "local_reducts", "global_rule_count", "pre_resolution_conflict_case_rate"]]
    sp = sp.rename(columns={c: f"{c}_old" for c in sp.columns if c not in KEY})
    m = m.merge(sf, on=KEY).merge(sp, on=KEY)
    m["reference_matches_old"] = np.isclose(m["reference_20261014_balanced_accuracy"], m["balanced_accuracy_old"], rtol=0, atol=1e-12) & np.isclose(
        m["reference_20261014_conflict_balanced_accuracy"], m["conflict_balanced_accuracy_old"], rtol=0, atol=1e-12, equal_nan=True)
    core_cols = ["accuracy", "balanced_accuracy", "macro_f1", "coverage", "conflict_resolution_accuracy",
                 "conflict_balanced_accuracy", "conflict_macro_f1", "disagreement_vs_first_match",
                 "conflict_disagreement_vs_first_match", "order_sensitivity_rate"]
    m["any_metric_changed"] = ~np.all(
        [np.isclose(m[f"{c}_old"], m[f"{c}_new"], rtol=0, atol=1e-12, equal_nan=True) for c in core_cols], axis=0)
    m["dataset"] = pd.Categorical(m["dataset"], DATASETS, ordered=True)
    m["policy"] = pd.Categorical(m["policy"], POLICIES, ordered=True)
    m = m.sort_values(["dataset", "client_count", "policy"])
    order = keyp + ["any_metric_changed", "reference_matches_old",
                    "reference_20261014_balanced_accuracy", "reference_20261014_conflict_balanced_accuracy"]
    for c in METRICS:
        order += [f"{c}_old", f"{c}_new", f"{c}_delta"]
    order += [c for c in m.columns if c not in order]
    m[order].to_csv(out / "old_vs_new.csv", index=False)
    changed = m[m["any_metric_changed"]]
    checks["changed_rows_by_policy"] = {str(k): int(v) for k, v in changed["policy"].value_counts().items() if v}
    checks["reference_matches_old_all_rows"] = bool(m["reference_matches_old"].all())
    for p in POLICIES:
        checks[f"{p}_unchanged"] = bool((~m.loc[m["policy"] == p, "any_metric_changed"]).all())

    # 3. result tables for 05
    s_cols = ["dataset", "client_count", "central_reduct", "central_reduct_size", "central_dependency",
              "local_reducts", "mean_local_reduct_size", "reduct_instability", "mean_local_central_reduct_jaccard",
              "rule_heterogeneity", "central_rule_count", "local_rule_counts", "mean_local_rule_count", "global_rule_count",
              "coverage", "pre_resolution_conflict_case_rate", "covered_conflict_rate", "exact_conflict_antecedent_rate",
              "conflict_cases_count", "mean_matching_rules_per_conflict_case"]
    st = s_fin[s_cols].copy()
    st["dataset"] = pd.Categorical(st["dataset"], DATASETS, ordered=True)
    st = st.sort_values(["dataset", "client_count"])
    st.to_csv(out / "uci3_structural_table.csv", index=False)
    rt = r_fin.copy()
    rt["dataset"] = pd.Categorical(rt["dataset"], DATASETS, ordered=True)
    rt["policy"] = pd.Categorical(rt["policy"], POLICIES, ordered=True)
    rt = rt.sort_values(["dataset", "client_count", "policy"])
    rt[keyp + METRICS].to_csv(out / "uci3_resolver_table.csv", index=False)

    # 4. resolver winners
    wins = []
    for (d, c), g in rt.groupby(["dataset", "client_count"], observed=True):
        row = {"dataset": d, "client_count": c}
        for metric in ("balanced_accuracy", "conflict_balanced_accuracy", "macro_f1"):
            best = g[metric].max()
            row[f"best_{metric}"] = best
            row[f"winners_{metric}"] = "+".join(str(p) for p in g.loc[np.isclose(g[metric], best, rtol=0, atol=1e-12), "policy"])
        wins.append(row)
    pd.DataFrame(wins).to_csv(out / "resolver_winners.csv", index=False)

    # 5. structural associations (12 observations) + per-dataset trajectories
    obs = s_fin.copy()
    pairs = [
        ("client_count", "reduct_instability"),
        ("client_count", "rule_heterogeneity"),
        ("client_count", "pre_resolution_conflict_case_rate"),
        ("reduct_instability", "rule_heterogeneity"),
        ("rule_heterogeneity", "pre_resolution_conflict_case_rate"),
        ("reduct_instability", "pre_resolution_conflict_case_rate"),
    ]
    rows = []
    for scope, frame in [("POOLED_12", obs)] + [(d, obs[obs["dataset"] == d]) for d in DATASETS]:
        for x, y in pairs:
            a, b = frame[x].astype(float), frame[y].astype(float)
            const = a.nunique() < 2 or b.nunique() < 2
            rows.append({
                "scope": scope, "x": x, "y": y, "n": len(frame),
                "pearson_r": np.nan if const else a.corr(b, method="pearson"),
                "spearman_rho": np.nan if const else a.rank().corr(b.rank(), method="pearson"),  # Spearman = Pearson on average ranks
                "note": "undefined: a variable is constant in this scope" if const else "",
                "label": "EXPLORATORY DESCRIPTIVE ASSOCIATION ONLY (small n, single seed, no inference)",
            })
    pd.DataFrame(rows).to_csv(out / "structural_associations.csv", index=False)
    traj = []
    for d in DATASETS:
        f = obs[obs["dataset"] == d].sort_values("client_count")
        for col in ("reduct_instability", "rule_heterogeneity", "pre_resolution_conflict_case_rate", "coverage", "global_rule_count"):
            v = f[col].astype(float).to_numpy()
            dif = np.diff(v)
            shape = ("constant" if np.allclose(dif, 0) else "non-decreasing" if (dif >= -1e-12).all()
                     else "non-increasing" if (dif <= 1e-12).all() else "non-monotonic")
            traj.append({"dataset": d, "metric": col, **{f"C{int(c)}": val for c, val in zip(f["client_count"], v)}, "shape_C2_to_C5": shape})
    pd.DataFrame(traj).to_csv(out / "structural_trajectories.csv", index=False)

    (out / "analysis_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
