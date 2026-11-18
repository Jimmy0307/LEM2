"""Post-hoc source-level analysis: policy spread / router value conditional on TRUE rules.

Reads the frozen Gate 5 full per-task CSV, without retraining or rewriting it.
Outputs are EXPLORATORY, NOT an extra preregistered confirmatory hypothesis.
Never write into the frozen source data directory.

Run:
 python -m experiments.g4_g8_closure_20261118.posthoc_policy_conditions --out /tmp/g4g8_audit
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "docs/research/redesign_20261116/data"
SIX = (
    "FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING",
    "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL",
)
VARIANTS = ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK")
KEYS = ["dataset", "seed", "regime", "rule_variant"]
CONFIG_KEYS = ["dataset", "seed", "regime", "discretizer"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(out: Path) -> dict:
    if FROZEN.resolve() in (out.resolve(), *out.resolve().parents):
        raise ValueError("Output must not be the frozen confirmatory data directory or its parent")
    for name in ("POSTHOC_G4_POLICY_CONDITIONAL_20261118.csv",
                 "POSTHOC_G4_POLICY_SOURCE_LEVEL_20261118.csv", "POSTHOC_G4_MANIFEST.json"):
        if (out / name).exists():
            raise FileExistsError(f"Refusing to overwrite previously published analysis: {out / name}")

    ps = FROZEN / "REDESIGN_G5_CONFIRMATORY_POLICIES.csv"
    cs = FROZEN / "REDESIGN_G5_CONFIRMATORY_CONFIG.csv"
    p = pd.read_csv(ps, usecols=KEYS + ["discretizer", "method", "test_ba"])
    c = pd.read_csv(cs, usecols=CONFIG_KEYS + ["true_rules", "single_class_clients", "label_skew_tv"])
    p = p.loc[
        (p["discretizer"] == "EQUAL_WIDTH_3")
        & p["rule_variant"].isin(VARIANTS)
        & p["method"].isin(SIX + ("VALIDATION_BEST", "CONFLICT_BUCKET_ROUTER_V1"))
    ].copy()
    c = c.loc[c["discretizer"] == "EQUAL_WIDTH_3"].copy()
    if p.empty or c.empty:
        raise AssertionError("Frozen Gate 5 EW3 policy/config rows missing")
    c = c.drop(columns=["discretizer"])
    if c.duplicated(["dataset", "seed", "regime"]).any():
        raise AssertionError("Duplicate frozen config keys")
    if p.duplicated(KEYS + ["method"]).any():
        raise AssertionError("Duplicate frozen policy keys")

    # Six fixed policies: per frozen ruleset, compute *within-run* Test BA spread.
    fixed = p[p["method"].isin(SIX)]
    per_config = fixed.groupby(KEYS, as_index=False).agg(
        n_fixed_methods=("method", "size"),
        policy_spread_pp=("test_ba", lambda x: 100 * (float(x.max()) - float(x.min()))),
    )
    if (per_config.n_fixed_methods != 6).any():
        raise AssertionError("Expected six fixed policies per ruleset")

    # Condition every strategy comparison on EXACTLY same effective rules / dataset.
    chosen = p[p["method"].isin(("VALIDATION_BEST", "CONFLICT_BUCKET_ROUTER_V1",
                                 "SIMPLE_VOTING", "GLOBAL_STRENGTH"))]
    wide = chosen.pivot(index=KEYS, columns="method", values="test_ba").reset_index()
    if wide[["VALIDATION_BEST", "CONFLICT_BUCKET_ROUTER_V1",
             "SIMPLE_VOTING", "GLOBAL_STRENGTH"]].isna().any().any():
        raise AssertionError("Missing comparison policies")
    merged = per_config.merge(wide, on=KEYS, how="inner", validate="one_to_one")
    merged = merged.merge(c, on=["dataset", "seed", "regime"], how="inner", validate="many_to_one")
    if len(merged) != len(per_config):
        raise AssertionError("Unmatched Gate5 policy rows")
    for method in ("CONFLICT_BUCKET_ROUTER_V1", "SIMPLE_VOTING", "GLOBAL_STRENGTH"):
        merged[f"{method}_minus_validation_pp"] = 100 * (merged[method] - merged["VALIDATION_BEST"])
    merged["has_true_rule"] = merged["true_rules"] > 0
    if ((merged["single_class_clients"] > 0) & ~merged["has_true_rule"]).any():
        raise AssertionError("Single-class client cannot have no TRUE rule under frozen classical LEM2")
    if merged.dataset.nunique() != 51 or merged.seed.nunique() != 10:
        raise AssertionError("Frozen G5 source / seed count changed")
    if len(merged) != 51 * 10 * 3 * 2:
        raise AssertionError("Expected 51*10*3*2 = 3060 source/seed/regime/variant comparisons")

    values = ["policy_spread_pp", "CONFLICT_BUCKET_ROUTER_V1_minus_validation_pp",
              "SIMPLE_VOTING_minus_validation_pp", "GLOBAL_STRENGTH_minus_validation_pp",
              "true_rules", "single_class_clients"]
    # Dataset, not seed, is the statistical unit. Both TRUE-status buckets can
    # contain the same dataset; this is descriptive stratification, not random assignment.
    source = merged.groupby(["dataset", "regime", "rule_variant", "has_true_rule"], as_index=False).agg(
        n_seeds=("seed", "size"), **{k:(k,"mean") for k in values}
    )
    summary = source.groupby(["regime", "rule_variant", "has_true_rule"], as_index=False).agg(
        n_source_units=("dataset", "nunique"),
        n_source_bucket_rows=("dataset", "size"),
        n_seed_configs=("n_seeds", "sum"),
        **{f"mean_{k}":(k,"mean") for k in values},
    )
    summary = summary.sort_values(["regime", "rule_variant", "has_true_rule"])
    assert sum(summary.n_seed_configs) == len(merged)
    assert summary.n_source_units.max() <= 51
    if not np.isfinite(summary["mean_policy_spread_pp"]).all():
        raise AssertionError("Non-finite policy spread")

    out.mkdir(parents=True, exist_ok=True)
    summary_file = out / "POSTHOC_G4_POLICY_CONDITIONAL_20261118.csv"
    source_file = out / "POSTHOC_G4_POLICY_SOURCE_LEVEL_20261118.csv"
    summary.to_csv(summary_file, index=False, float_format="%.12g")
    source.to_csv(source_file, index=False, float_format="%.12g")
    manifest = {
        "status": "POST_HOC_EXPLORATORY_DIAGNOSTIC_NOT_CONFIRMATORY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_git_branch": "research/federated-rule-degeneracy-redesign-20261116",
        "inputs_sha256": {ps.name: sha256(ps), cs.name: sha256(cs)},
        "n_datasets": 51,
        "n_seeds": 10,
        "n_regimes": 3,
        "n_rule_variants": 2,
        "paired_rule_config_rows": len(merged),
        "unit_of_analysis": "dataset; seeds averaged first, split by observed has_true_rule",
        "conditioning_note": "has_true_rule is post-treatment rule property correlated with label skew; causal effect not identified",
        "selection_note": "Policy scores from frozen OUTER TEST are used ONLY to describe; NO test-driven selector is deployed or fitted",
        "caution": "Do not treat a nonsignificant difference as equivalence or source/seed rows as independent samples",
        "output_sha256": {summary_file.name: sha256(summary_file), source_file.name: sha256(source_file)},
    }
    (out / "POSTHOC_G4_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("POSTHOC_G4_G5_POLICY_CONDITIONAL_PASS", json.dumps({
        "models": len(merged), "sources": merged.dataset.nunique(),
        "summary_rows": len(summary), "output": str(out),
    }), flush=True)
    print(summary.to_csv(index=False, float_format="%.6g"), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.out)


if __name__ == "__main__":
    main()
