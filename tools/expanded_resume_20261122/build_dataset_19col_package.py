"""Build complete dataset-aware 19-column and accuracy/coverage reporting from a frozen 42-seed interim package.

Inputs are already published in docs/research/expanded_188_42seeds/interim.
This script never modifies scientific computations or runs models.
It refuses to present partial-seed results as complete.
Usage:
 python tools/expanded_resume_20261122/build_dataset_19col_package.py \
   --snapshot docs/research/expanded_188_42seeds/interim \
   --registry docs/research/full_scale_20261118/REGISTRY.csv \
   --output ./dataset_19col_report_20261123
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

FULL19 = [
    "dataset", "seed", "distribution", "dirichlet_alpha", "split_mode",
    "system", "client_count", "selection_policy", "train_rows", "test_rows",
    "rule_count", "no_match_count", "covered_count", "test_coverage_pct",
    "true_in_candidate_count", "candidate_coverage_pct", "accuracy_pct",
    "balanced_accuracy_pct", "conflict_rate_pct",
]
POLICIES = [
    "FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH",
    "POPULATION_STANDARD", "POPULATION_GLOBAL",
]
SCENARIOS = ["CENTRALIZED", "FED_IID", "FED_A05", "FED_A01"]
VARIANTS = ["A_ALL_RULES", "B2_TRUE_AS_FALLBACK"]
METRICS = [
    "accuracy_pct", "balanced_accuracy_pct", "test_coverage_pct",
    "candidate_coverage_pct", "conflict_rate_pct", "rule_count",
    "train_rows", "test_rows", "no_match_count", "covered_count",
    "true_in_candidate_count",
]
TIE_TOL = 1e-9


def scenario_of(row):
    if row["system"] == "CENTRALIZED":
        return "CENTRALIZED"
    if row["system"] != "FEDERATED":
        raise ValueError("Unrecognized system: " + str(row["system"]))
    if row["distribution"] == "IID":
        return "FED_IID"
    alpha = float(row["dirichlet_alpha"])
    if abs(alpha - 0.5) < 1e-8:
        return "FED_A05"
    if abs(alpha - 0.1) < 1e-8:
        return "FED_A01"
    raise ValueError("Unexpected Dirichlet alpha: " + str(alpha))


def metadata(registry, status):
    reg = registry[registry.status != "EXCLUDED_SAME_SOURCE"].copy()
    if reg.dataset.nunique() != 188:
        raise ValueError("Registry must contain exactly 188 eligible dataset tasks")
    cols = [
        "cohort", "dataset", "name", "source_url", "original_rows",
        "used_rows", "original_features", "used_features", "used_feature_names",
        "n_classes", "dropped_classes", "minority_share", "feature_type",
        "size_class", "continuous_fraction", "same_source_as", "related_source",
    ]
    for c in cols:
        if c not in reg.columns:
            reg[c] = pd.NA
    result = reg[cols].copy()
    result["class_labels"] = "NOT_AVAILABLE_IN_AGGREGATED_METADATA"
    result["target_column"] = "VERIFY_PER_SOURCE_JSON"
    result = result.merge(status[["dataset", "complete_models", "expected_models", "status"]],
                          on="dataset", how="left", validate="one_to_one")
    result.rename(columns={"status": "status_42seed",
                           "complete_models": "completed_models_42seed",
                           "expected_models": "expected_models_42seed"}, inplace=True)
    return result.sort_values("dataset")


def prepare_results(frame):
    missing = [c for c in FULL19 + ["rule_variant"] if c not in frame]
    if missing:
        raise ValueError("Required 19-column contract missing: " + str(missing))
    frame = frame.copy()
    frame["scenario"] = frame.apply(scenario_of, axis=1)
    if set(frame["rule_variant"].dropna()) - set(VARIANTS):
        raise ValueError("Unexpected rule variant")
    if set(frame["selection_policy"].dropna()) - set(POLICIES):
        raise ValueError("Unexpected policy")
    if frame.duplicated(["dataset", "seed", "scenario", "rule_variant", "selection_policy"]).any():
        raise ValueError("Duplicate model result")
    for c in ["test_coverage_pct", "candidate_coverage_pct", "accuracy_pct",
              "balanced_accuracy_pct", "conflict_rate_pct"]:
        if frame[c].isna().any() or not frame[c].between(0, 100).all():
            raise ValueError("Metric bounds violated: " + c)
    if not ((frame["covered_count"] + frame["no_match_count"]) == frame["test_rows"]).all():
        raise ValueError("Invalid coverage counts")
    if not (frame["true_in_candidate_count"] <= frame["covered_count"]).all():
        raise ValueError("Invalid candidate counts")
    return frame


def per_policy(frame, completeness):
    keys = ["dataset", "scenario", "rule_variant", "selection_policy"]
    a = frame.groupby(keys, as_index=False).agg(
        n_seeds=("seed", "nunique"),
        **{"avg_" + metric: (metric, "mean") for metric in METRICS},
    )
    a = a.merge(completeness[["dataset", "status"]],
                on="dataset", how="left", validate="many_to_one")
    a.rename(columns={"status": "dataset_completion"}, inplace=True)
    a["complete_42seeds"] = (a.n_seeds == 42) & (a.dataset_completion == "COMPLETE")
    return a.sort_values(keys)


def best_by_scenario(policy):
    result = []
    keys = ["dataset", "scenario", "rule_variant"]
    for key, g in policy.groupby(keys, sort=True):
        if set(g.selection_policy) != set(POLICIES):
            raise ValueError("Missing a policy for: " + str(key))
        acc = float(g.avg_accuracy_pct.max())
        ba = float(g.avg_balanced_accuracy_pct.max())
        winner_a = sorted(g.loc[np.abs(g.avg_accuracy_pct - acc) <= TIE_TOL, "selection_policy"])
        winner_b = sorted(g.loc[np.abs(g.avg_balanced_accuracy_pct - ba) <= TIE_TOL, "selection_policy"])
        first = g.iloc[0]
        result.append({
            "dataset": key[0], "scenario": key[1], "rule_variant": key[2],
            "n_seeds": int(g.n_seeds.min()),
            "dataset_completion": first.dataset_completion,
            "complete_42seeds": bool(g.complete_42seeds.all()),
            "accuracy_best_pct": acc, "accuracy_best_methods": ";".join(winner_a),
            "balanced_accuracy_best_pct": ba, "balanced_accuracy_best_methods": ";".join(winner_b),
            "accuracy_ba_winners_agree": winner_a == winner_b,
            "accuracy_method_spread_pp": acc - float(g.avg_accuracy_pct.min()),
            # Structure metrics are policy-independent per (dataset, seed, scenario, variant).
            "test_coverage_pct": float(first.avg_test_coverage_pct),
            "candidate_coverage_pct": float(first.avg_candidate_coverage_pct),
            "conflict_rate_pct": float(first.avg_conflict_rate_pct),
            "rule_count": float(first.avg_rule_count),
            "mean_train_rows": float(first.avg_train_rows),
            "mean_test_rows": float(first.avg_test_rows),
            "mean_covered_count": float(first.avg_covered_count),
            "mean_no_match_count": float(first.avg_no_match_count),
            "mean_true_in_candidate_count": float(first.avg_true_in_candidate_count),
        })
    return pd.DataFrame(result)


def overall_winners(best):
    out = []
    for dataset, g in best.groupby("dataset", sort=True):
        # Includes partial groups only as explicitly flagged in the output.
        top = float(g.accuracy_best_pct.max())
        winners = g[np.abs(g.accuracy_best_pct - top) <= TIE_TOL]
        out.append({
            "dataset": dataset,
            "full_dataset_42seeds": bool(g.complete_42seeds.all()) and len(g) == 8,
            "n_available_scenario_variants": int(len(g)),
            "overall_best_accuracy_pct": top,
            "winning_scenario_variant_policy": " | ".join(
                f"{r.scenario}/{r.rule_variant}/{r.accuracy_best_methods}" for r in winners.itertuples()
            ),
            "note": "CONFIRMATORY_SUBSET_ONLY" if bool(g.complete_42seeds.all()) and len(g) == 8
                    else "PARTIAL_OBSERVED_RESULTS_NOT_FINAL",
        })
    return pd.DataFrame(out)


def write_new(frame, path, *, compression=None):
    if path.exists():
        raise FileExistsError("Will not overwrite: " + str(path))
    frame.to_csv(path, index=False, compression=compression, encoding="utf-8-sig" if compression is None else "utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    snap = args.snapshot
    status = json.loads((snap / "STATUS.json").read_text(encoding="utf-8"))
    complete = pd.read_csv(snap / "COMPLETENESS.csv")
    reg = pd.read_csv(args.registry)
    raw = pd.read_csv(snap / "RESULTS.csv.gz", compression="gzip")
    if len(raw) != status["complete_rows"]:
        raise ValueError("Snapshot RESULTS rows and STATUS disagree")
    data = prepare_results(raw)
    if data.dataset.nunique() > 188 or data.seed.nunique() > 42:
        raise ValueError("Source contract out of range")
    if len(data) % 12:
        raise ValueError("Results must have 12 rows per successful model")
    master = metadata(reg, complete)
    p = per_policy(data, complete)
    best = best_by_scenario(p)
    overall = overall_winners(best)
    args.output.mkdir(parents=True, exist_ok=True)
    for variant in VARIANTS:
        file = args.output / f"FULL42_19COL_{variant}.csv.gz"
        write_new(data.loc[data.rule_variant == variant, FULL19], file, compression="gzip")
    write_new(master, args.output / "DATASET_CATALOG_188.csv")
    write_new(p, args.output / "DATASET_POLICY_METRICS_42SEED.csv")
    write_new(best, args.output / "DATASET_SCENARIO_BEST_42SEED.csv")
    write_new(overall, args.output / "DATASET_OVERALL_WINNER_42SEED.csv")
    receipt = {
        "status": status["status"], "complete_models": status["complete_models"],
        "expected_models": status["expected_models"],
        "complete_datasets": status["complete_datasets"],
        "expected_datasets": status["datasets"],
        "result_rows": len(data), "catalog_rows": len(master),
        "dataset_policy_rows": len(p), "scenario_best_rows": len(best),
        "overall_winner_rows": len(overall),
        "source_snapshot": (snap / "SNAPSHOT_STAMP").read_text().strip(),
        "source_42seed": str(snap / "RESULTS.csv.gz"),
        "source_metadata": str(args.registry),
        "warning": "42-seed INCOMPLETE; class label identities not in aggregated metadata",
    }
    (args.output / "BUILD_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
