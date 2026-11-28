"""Data size / features / rules -> peak memory and time, from measured checkpoints (read-only).

Inputs : main run + no-limit supplementary checkpoints (timing.peak_rss_mb, wall/LEM2 seconds,
         rows.rule_count, rows.train_rows), SOURCE.json / source.pkl (rows, feature types, category counts).
Outputs: D:/Desk/LEM2_expanded_resume/memory_analysis/
         MODEL_MEASUREMENTS.csv   one row per completed model
         DATASET_SUMMARY.csv      one row per dataset (188)
         FIT.json                 peak-memory model fitted on completed models
Run in WSL with the project venv from /home/user/lem2_expanded.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/lem2_expanded")
from experiments.expanded_42seeds_20261120.run import selected_registry  # noqa: E402

RUNS = Path("/home/user/lem2_runs")
LANES = {"main_2700s": RUNS / "expanded_188_42seeds", "accel_nolimit": RUNS / "expanded_accel_nolimit"}
OUT = Path("/mnt/d/Desk/LEM2_expanded_resume/memory_analysis")
OUT.mkdir(parents=True, exist_ok=True)


def source_profile(dsdir: Path) -> dict:
    meta = json.loads((dsdir / "SOURCE.json").read_text())
    prof = {"used_rows": meta.get("used_rows"), "n_features": len(meta["features"]),
            "n_continuous": len(meta["continuous"]), "n_categorical": len(meta["categorical"]),
            "category_values_total": 0, "category_values_max": 0}
    try:
        with (dsdir / "source.pkl").open("rb") as fh:
            frame = pickle.load(fh).frame
        card = [int(frame[c].nunique(dropna=False)) for c in meta["categorical"]]
        prof["category_values_total"] = int(sum(card))
        prof["category_values_max"] = int(max(card)) if card else 0
        prof["n_classes"] = int(frame[meta["target"]].nunique())
    except Exception as exc:  # report, never hide
        prof["profile_error"] = repr(exc)[:120]
    return prof


def main():
    _, reg = selected_registry()
    models, datasets = [], []
    main_ck = LANES["main_2700s"] / "checkpoints"
    for item in reg.to_dict("records"):
        ds = item["dataset"]
        dsdir_name = ds.replace(":", "__")
        prof = source_profile(main_ck / dsdir_name)
        lane_stats = {}
        for lane, root in LANES.items():
            d = root / "checkpoints" / dsdir_name
            ok = fail = 0
            if d.exists():
                for f in sorted(d.glob("seed??__*.json")):
                    if f.name.endswith(".failure.json"):
                        fail += 1
                        continue
                    rec = json.loads(f.read_text())
                    t, r0 = rec["timing"], rec["rows"][0]
                    ok += 1
                    models.append({"dataset": ds, "lane": lane, "seed": t["seed"], "scenario": t["scenario"],
                                   "train_rows": r0["train_rows"], "rule_count": r0["rule_count"],
                                   "peak_rss_mb": t.get("peak_rss_mb"), "wall_seconds": t["wall_seconds"],
                                   "lem2_seconds": t["lem2_seconds"], "support_context_seconds": t["support_context_seconds"],
                                   "predict_seconds": t["predict_seconds"], **{k: prof.get(k) for k in (
                                       "used_rows", "n_features", "n_continuous", "n_categorical",
                                       "category_values_total", "category_values_max")}})
            lane_stats[lane] = (ok, fail)
        datasets.append({"dataset": ds, "name": item.get("name"), "cohort": item.get("cohort"),
                         "original_rows": item.get("original_rows"), **prof,
                         "main_ok": lane_stats["main_2700s"][0], "main_timeout": lane_stats["main_2700s"][1],
                         "nolimit_ok": lane_stats["accel_nolimit"][0], "nolimit_fail": lane_stats["accel_nolimit"][1]})
    m = pd.DataFrame(models)
    m.to_csv(OUT / "MODEL_MEASUREMENTS.csv", index=False)
    # prefer no-limit measurements for datasets that only completed there
    agg = m.sort_values("lane").groupby("dataset").agg(
        models_measured=("rule_count", "size"), train_rows_median=("train_rows", "median"),
        rules_median=("rule_count", "median"), rules_max=("rule_count", "max"),
        peak_rss_mb_median=("peak_rss_mb", "median"), peak_rss_mb_max=("peak_rss_mb", "max"),
        wall_s_median=("wall_seconds", "median"), wall_s_max=("wall_seconds", "max"),
        lem2_s_max=("lem2_seconds", "max")).reset_index()
    d = pd.DataFrame(datasets).merge(agg, on="dataset", how="left")
    d["status"] = np.select(
        [d.main_timeout.eq(0) & d.main_ok.eq(168), d.nolimit_ok.eq(168), d.main_ok.add(d.nolimit_ok).eq(0)],
        ["COMPLETE_MAIN", "COMPLETE_ACCEL_NOLIMIT", "NO_RESULT"], default="PARTIAL")
    d.to_csv(OUT / "DATASET_SUMMARY.csv", index=False)

    # peak memory model on completed models: RSS ~ a + b * (rules x train_rows) [dense support matrix bytes]
    fit_df = m.dropna(subset=["peak_rss_mb"]).copy()
    fit_df["support_mb"] = fit_df.rule_count * fit_df.train_rows / 1e6
    X = np.c_[np.ones(len(fit_df)), fit_df.support_mb, fit_df.train_rows / 1e3]
    coef, *_ = np.linalg.lstsq(X, fit_df.peak_rss_mb, rcond=None)
    pred = X @ coef
    ss_res = float(((fit_df.peak_rss_mb - pred) ** 2).sum())
    ss_tot = float(((fit_df.peak_rss_mb - fit_df.peak_rss_mb.mean()) ** 2).sum())
    fit = {"model": "peak_rss_mb = a + b*(rules*train_rows/1e6) + c*(train_rows/1e3)",
           "a": coef[0], "b_per_MB_of_rules_x_rows": coef[1], "c_per_1000_train_rows": coef[2],
           "r2": 1 - ss_res / ss_tot, "n_models": int(len(fit_df)),
           "max_support_mb_observed": float(fit_df.support_mb.max()),
           "max_peak_rss_mb_observed": float(fit_df.peak_rss_mb.max())}
    (OUT / "FIT.json").write_text(json.dumps(fit, indent=1))
    print(json.dumps(fit, indent=1))
    print(d.status.value_counts().to_string())
    print(f"models measured: {len(m)}")


if __name__ == "__main__":
    main()
