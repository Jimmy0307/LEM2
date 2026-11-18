"""Produce professor-facing dataset-wise accuracy, BA, F1 and cost evidence.

Two *separate* cohorts, no raw-client access and no cross-cohort pooled estimate:
- historical PMLB 109 successful sources, 3 seeds, 6 fixed policies + val-selected policy;
- G5 OpenML 51 sources, 10 seeds, 5 non-CART arms with B2 and validation-selected policy.
CSV snapshots and SHA manifest are written under the existing Dashboard data whitelist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs/research/teacher_dashboard/data"
G5 = ROOT / "docs/research/redesign_20261116/data"
COST = ROOT / "docs/research/server_rule_cost_20261118"
OUT = DATA / "cost_accuracy_20261118"
SCENARIOS = ("IID", "NONIID_05", "NONIID_01")
ARMS = {"M1": "EQUAL_WIDTH_3", "R3": "EQUAL_WIDTH_5",
        "R2": "MDLP_HIST", "M2": "FED_MD_HIST", "M3": "FED_MD_XC"}
POLICIES = {"FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING",
            "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL"}
KEYS = ["dataset", "seed", "regime", "discretizer"]


def required(df: pd.DataFrame, cols: list[str], source: str) -> None:
    absent = set(cols) - set(df.columns)
    if absent:
        raise AssertionError(f"{source}: missing {sorted(absent)}")
    if df[cols].isna().any().any():
        raise AssertionError(f"{source}: null required values")


def pmlb() -> pd.DataFrame:
    original = pd.read_csv(DATA / "PMLB_117_3SEED_SIX_POLICY_RAW.csv", low_memory=False)
    required(original, ["dataset", "seed", "scenario", "policy", "test_accuracy",
                        "test_balanced_accuracy", "test_macro_f1", "test_coverage",
                        "validation_conflict", "fit_seconds", "number_rules",
                        "selected_validation_best"], "PMLB raw")
    audit = pd.read_csv(DATA / "PMLB_117_3SEED_SOURCE_AUDIT.csv")
    passed = audit.loc[audit.status.eq("PASS"), ["dataset", "family",
                                                   "source_kind", "actual_sample_rows"]]
    assert len(passed) == 109 and passed.dataset.nunique() == 109
    assert len(original) == 109 * 3 * 3 * 6
    assert set(original.dataset) == set(passed.dataset)
    assert set(original.scenario) == set(SCENARIOS)
    assert set(original.policy) == POLICIES
    assert set(original.seed) == {1, 7, 42}
    assert not original.duplicated(["dataset", "seed", "scenario", "policy"]).any()
    assert original["selected_validation_best"].isin([0, 1]).all()
    assert original["test_accuracy"].between(0, 1).all()
    assert original["test_balanced_accuracy"].between(0, 1).all()

    # One val-selected policy per dataset/regime/seed, never a TEST-based oracle.
    selected = original.loc[original.selected_validation_best.eq(1)].copy()
    assert len(selected) == 109 * 3 * 3
    assert not selected.duplicated(["dataset", "seed", "scenario"]).any()
    selected["policy"] = "VALIDATION_BEST"
    both = pd.concat([original, selected], ignore_index=True)
    g = both.groupby(["dataset", "scenario", "policy"], as_index=False).agg(
        accuracy=("test_accuracy", "mean"),
        balanced_accuracy=("test_balanced_accuracy", "mean"),
        macro_f1=("test_macro_f1", "mean"),
        coverage=("test_coverage", "mean"),
        validation_conflict=("validation_conflict", "mean"),
        rules=("number_rules", "mean"),
        fit_seconds=("fit_seconds", "mean"),
        seeds=("seed", "nunique"),
    )
    assert len(g) == 109 * 3 * 7 and g.seeds.eq(3).all()
    g = g.merge(passed, on="dataset", how="left", validate="many_to_one")
    assert g.family.notna().all()
    g["cohort"] = "PMLB_HISTORICAL"
    g["communication_status"] = "NOT_MEASURED_IN_THIS_COHORT"
    g["conflict_scope"] = "INNER_VALIDATION"
    g["accuracy_scope"] = "OUTER_TEST"
    g["rule_variant"] = "HISTORICAL_UNION"
    g["method_semantics"] = "SIX_FIXED_OR_VAL_SELECTED_POLICY"
    g["seed_ids"] = "1;7;42"
    g = g.rename(columns={"scenario": "regime", "policy": "method",
                          "actual_sample_rows": "used_rows"})
    g["communication_mean_numbers"] = float("nan")
    g["communication_max_numbers"] = float("nan")
    g["effective_coverage"] = float("nan")
    g["conflict"] = float("nan")  # test Conflict is not present; do not relabel val!
    g.to_csv(OUT / "PMLB_109_ACCURACY_BY_DATASET.csv", index=False, float_format="%.12g")
    return g


def openml() -> pd.DataFrame:
    costs = pd.read_csv(COST / "G5_51_SOURCES_PER_DATASET_COST.csv")
    policies = pd.read_csv(
        G5 / "REDESIGN_G5_CONFIRMATORY_POLICIES.csv",
        usecols=KEYS + ["rule_variant", "method", "test_accuracy",
                        "test_ba", "test_macro_f1", "selected_policy", "val_ba"],
        low_memory=False,
    )
    cfg = pd.read_csv(G5 / "REDESIGN_G5_CONFIRMATORY_CONFIG.csv",
                      usecols=KEYS + ["binning_communication_numbers_per_client"])
    # B2 TRUE fallback is held constant across the five candidate discretizers.
    pol = policies.loc[
        policies.discretizer.isin(ARMS.values())
        & policies.rule_variant.eq("B2_TRUE_AS_FALLBACK")
        & policies.method.eq("VALIDATION_BEST")
    ].copy()
    assert len(pol) == 51 * 3 * 10 * 5
    assert not pol.duplicated(KEYS).any()
    assert pol.test_accuracy.between(0, 1).all()
    assert pol.test_ba.between(0, 1).all()
    grouped = pol.groupby(["dataset", "regime", "discretizer"], as_index=False).agg(
        accuracy=("test_accuracy", "mean"),
        balanced_accuracy=("test_ba", "mean"),
        macro_f1=("test_macro_f1", "mean"),
        seeds=("seed", "nunique"),
        validation_ba=("val_ba", "mean"),
    )
    assert len(grouped) == 51 * 3 * 5 and grouped.seeds.eq(10).all()
    max_comm = cfg.loc[cfg.discretizer.isin(ARMS.values())].groupby(
        ["dataset", "regime", "discretizer"], as_index=False
    ).agg(communication_max_numbers=("binning_communication_numbers_per_client", "max"))
    grouped = grouped.merge(max_comm, on=["dataset", "regime", "discretizer"],
                            how="left", validate="one_to_one")
    keys = ["dataset", "regime", "discretizer"]
    assert not costs.duplicated(keys).any()
    merged = costs.merge(grouped, on=keys, how="inner", validate="one_to_one")
    assert len(merged) == 765
    assert set(merged.dataset) == set(costs.dataset)
    assert merged.seeds.eq(10).all()
    merged = merged.rename(columns={
        "source_name": "dataset_name", "arm": "method",
        "comm_numbers": "communication_mean_numbers",
        "fit_time_proxy_sec": "fit_seconds",
        "ba": "cost_matrix_ba",
    })
    assert ((merged.balanced_accuracy - merged.cost_matrix_ba).abs() <= 1e-9).all(), (
        "G5 BA differs from frozen cost matrix"
    )
    merged["cohort"] = "OPENML_CONFIRMATORY"
    merged["conflict_scope"] = "OUTER_TEST"
    merged["accuracy_scope"] = "OUTER_TEST"
    merged["rule_variant"] = "B2_TRUE_AS_FALLBACK"
    merged["method_semantics"] = "VALIDATION_BEST_ON_EACH_SEED"
    merged["communication_status"] = "SIMULATED_NUMBERS_PER_CLIENT_NOT_WIRE_BYTES"
    merged["seed_ids"] = "1001-1010"
    merged["used_rows"] = float("nan")
    merged["validation_conflict"] = float("nan")
    merged.to_csv(OUT / "OPENML_51_ACCURACY_COST_BY_DATASET.csv",
                  index=False, float_format="%.12g")
    return merged


def inventory() -> pd.DataFrame:
    master = pd.read_csv(DATA / "TEACHER_DATASET_MASTER_20261114.csv")
    assert len(master) == 161
    keep = ["cohort", "id", "name", "status", "original_rows", "used_rows",
            "original_features", "used_features", "classes", "domain_family",
            "source_kind", "source_url"]
    required(master, ["cohort", "id", "name", "status"], "master")
    out = master[keep].copy()
    out.to_csv(OUT / "HISTORICAL_161_SOURCE_INVENTORY.csv",
               index=False, float_format="%.12g")
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ph = pmlb()
    gh = openml()
    inv = inventory()
    assert ph.dataset.nunique() == 109 and gh.dataset.nunique() == 51
    assert ph.groupby(["dataset", "regime"]).size().eq(7).all()
    assert gh.groupby(["dataset", "regime"]).size().eq(5).all()
    assert inv.id.nunique() == 161

    filenames = ("PMLB_109_ACCURACY_BY_DATASET.csv",
                 "OPENML_51_ACCURACY_COST_BY_DATASET.csv",
                 "HISTORICAL_161_SOURCE_INVENTORY.csv")
    hashes = {p: hashlib.sha256((OUT / p).read_bytes()).hexdigest() for p in filenames}
    meta = {
        "version": "2026-11-18",
        "status": "MIXED_EVIDENCE_LEVELS_DO_NOT_POOL",
        "pmlb_source_count": 109,
        "pmlb_policy_source_regime_rows": len(ph),
        "pmlb_original_policy_seed_rows": 5886,
        "openml_source_count": 51,
        "openml_source_regime_arm_rows": len(gh),
        "historical_registry_count": 161,
        "non_independent_cohort_warning": "Historical and OpenML sources can overlap",
        "pmlb_conflict_is_validation_not_test": True,
        "openml_communication_is_simulated_not_network_bytes": True,
        "pmlb_communication_is_unmeasured": True,
        "pmlb_seeds": [1, 7, 42],
        "openml_seeds": 10,
        "source_files": {
            "PMLB": "docs/research/teacher_dashboard/data/PMLB_117_3SEED_SIX_POLICY_RAW.csv",
            "OPENML": "docs/research/redesign_20261116/data/REDESIGN_G5_CONFIRMATORY_POLICIES.csv",
            "COST": "docs/research/server_rule_cost_20261118/G5_51_SOURCES_PER_DATASET_COST.csv",
            "HISTORICAL_REGISTRY": "docs/research/teacher_dashboard/data/TEACHER_DATASET_MASTER_20261114.csv",
        },
        "sha256": hashes,
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
