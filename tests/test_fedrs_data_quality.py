"""Schema / duplicate / missing-value checks on every raw redesign experiment table (Gates 1-5).

Read-only: these tests never rewrite data. A failure means the published evidence is
internally inconsistent and must be investigated, not "fixed" by editing the CSV.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

D = Path(__file__).resolve().parents[1] / "docs" / "research" / "redesign_20261116" / "data"
EXPERIMENTS = ("G1_DEGENERACY", "G2_DISCRETIZATION", "G2_DISCRETIZATION_MEMORY", "G3_NOISE_REAL",
               "G3_NOISE_SYNTHETIC", "G4_PROTOTYPES", "G5_CONFIRMATORY", "G5_CONFIRMATORY_SMOKE")
FIRST_METRIC = {"CONFIG": "global_rules", "POLICIES": "selected_policy", "STRUCTURE": "rows"}
RATES = {"POLICIES": ("val_ba", "test_ba", "test_accuracy", "test_macro_f1"),
         "STRUCTURE": ("coverage", "no_hit_rate", "single_rate", "conflict_rate")}


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(D / name, keep_default_na=False, na_values=[""], low_memory=False)


def key_columns(df: pd.DataFrame, table: str) -> list[str]:
    cols = list(df.columns)
    keys = cols[: cols.index(FIRST_METRIC[table])]
    return keys + (["split"] if "split" in cols and "split" not in keys else []) + \
        [c for c in ("rule_variant", "method") if c in cols and c not in keys]


@pytest.mark.parametrize("exp", EXPERIMENTS)
@pytest.mark.parametrize("table", ("CONFIG", "POLICIES", "STRUCTURE"))
def test_raw_table_schema_keys_and_ranges(exp, table):
    path = D / f"REDESIGN_{exp}_{table}.csv"
    if not path.exists():
        assert table == "POLICIES" or table == "STRUCTURE", path
        pytest.skip(f"{path.name} not produced for this experiment")
    df = load(path.name)
    assert len(df) > 0
    keys = key_columns(df, table)
    assert {"dataset", "seed", "regime", "discretizer"} <= set(keys)
    dup = df.duplicated(keys).sum()
    assert dup == 0, f"{path.name}: {dup} duplicate rows on {keys}"
    assert df[keys].isna().sum().sum() == 0, f"{path.name}: missing key values"
    for col in RATES.get(table, ()):
        vals = df[col].dropna()
        assert vals.between(0, 1).all(), f"{path.name}:{col} out of [0,1]"
    if table == "POLICIES":
        assert df.test_ba.notna().all(), f"{path.name}: missing test_ba"


@pytest.mark.parametrize("exp", EXPERIMENTS)
def test_manifest_counts_match_config_and_failures(exp):
    manifest = json.loads((D / f"REDESIGN_{exp}_MANIFEST.json").read_text(encoding="utf-8"))
    config = load(f"REDESIGN_{exp}_CONFIG.csv")
    fail_path = D / f"REDESIGN_{exp}_FAILURES.csv"
    failures = load(fail_path.name) if fail_path.stat().st_size > 5 else pd.DataFrame()
    assert manifest["succeeded"] == len(config)
    assert manifest["failed"] == len(failures)
    assert manifest["tasks"] == len(config) + len(failures)


def test_g5_design_is_complete_and_balanced():
    p = load("REDESIGN_G5_CONFIRMATORY_POLICIES.csv")
    assert p.dataset.nunique() == 51 and sorted(p.seed.unique()) == list(range(1001, 1011))
    assert set(p.regime) == {"IID", "NONIID_05", "NONIID_01"}
    vb = p[p.method == "VALIDATION_BEST"]
    cells = vb.groupby(["discretizer", "rule_variant"]).size()
    # every preregistered rule-set arm is present for every (dataset, seed, regime)
    for disc, var in (("EQUAL_WIDTH_3", "A_ALL_RULES"), ("EQUAL_WIDTH_3", "B2_TRUE_AS_FALLBACK"),
                      ("FED_MD_HIST", "B2_TRUE_AS_FALLBACK"), ("RS_DISCERNIBILITY_CENTRAL", "B2_TRUE_AS_FALLBACK")):
        assert cells[(disc, var)] == 51 * 10 * 3, (disc, var)
    for cart in ("CART_CENTRAL", "CART_FED_VOTE"):
        assert (p.method == cart).sum() == 51 * 10 * 3, cart


def test_g1_failures_are_only_documented_control_c_infeasibility():
    f = load("REDESIGN_G1_DEGENERACY_FAILURES.csv")
    assert len(f) == 24
    assert set(f.partition_mode) == {"CONTROL_C"}


def test_experiment_runner_refuses_to_overwrite_published_evidence(monkeypatch):
    from experiments.redesign_20261116.common import ALLOW_OVERWRITE_ENV, OUT, guard_published
    monkeypatch.delenv(ALLOW_OVERWRITE_ENV, raising=False)
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        guard_published(OUT / "REDESIGN_G5_CONFIRMATORY_MANIFEST.json")
    guard_published(OUT / "NOT_YET_PUBLISHED_MANIFEST.json")  # new names are allowed
