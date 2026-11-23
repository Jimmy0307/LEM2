"""Contract / leakage / baseline tests for NEW, separate research protocol."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fedrs.experiment import nested_split
from fedrs.predict import POLICIES
from experiments.validation_first_20261123.protocol import (
    choose_by_validation, make_splits, run_one,
)


def sample(n=120):
    # Separable but not trivial, two informative condition attributes.
    rng = np.random.default_rng(124)
    x = rng.integers(0, 4, size=n)
    z = rng.integers(0, 3, size=n)
    labels = np.where(x >= 2, "A", "B")
    # non-determinism in labels ensures conflict/coverage checks run.
    labels = np.where(np.arange(n) % 17 == 0, np.where(labels == "A", "B", "A"), labels)
    return pd.DataFrame({"f1": x.astype(str), "f2": z.astype(str), "class": labels})


@pytest.mark.parametrize("seed", [1, 7, 19])
def test_same_outer_holdout_as_frozen_nested_split(seed):
    df = sample()
    new = make_splits(df, "class", seed)
    old_dev, old_val, old_test = nested_split(df, "class", seed)
    assert set(new.test20.__row_id__) == set(old_test.__row_id__)
    assert set(new.dev64.__row_id__) == set(old_dev.__row_id__)
    assert set(new.val16.__row_id__) == set(old_val.__row_id__)
    assert set(new.dev60.__row_id__).isdisjoint(set(new.val20.__row_id__))
    assert set(new.outer_train.__row_id__).isdisjoint(set(new.test20.__row_id__))
    assert len(new.outer_train) + len(new.test20) == len(df)
    assert len(new.dev60) + len(new.val20) == len(new.outer_train)
    assert len(new.dev64) + len(new.val16) == len(new.outer_train)
    # Due to stratified integer rounding, use tolerances, not exact 60/20/20.
    assert abs(len(new.dev60) / len(df) - .6) < .03


def test_validation_selection_uses_only_validation_truth():
    y = ["A", "B", "A", "B", "A", "B"]
    predictions = {p: ["A"] * len(y) for p in POLICIES}
    predictions["SIMPLE_VOTING"] = y.copy()
    winner, d = choose_by_validation(y, predictions, "accuracy")
    assert winner == "SIMPLE_VOTING"
    assert d[winner] == 1.0
    tied = {p: y.copy() for p in POLICIES}
    win, _ = choose_by_validation(y, tied, "ba")
    assert win == "STANDARD_VOTING", "Tie break must be frozen before test"
    with pytest.raises(ValueError):
        choose_by_validation(y, {"FIRST_MATCH": y}, "accuracy")
    with pytest.raises(ValueError):
        choose_by_validation(y, predictions, "unknown")


@pytest.mark.parametrize("scenario", ["CENTRALIZED", "FED_IID"])
def test_refit_vs_fixed_same_80_percent_model_and_test(scenario):
    df = sample()
    rows = run_one(df, "class", ["f1", "f2"], "toy", 3, scenario)
    assert {r["arm"] for r in rows} == {
        "STAGED60_VAL_SELECTED", "REFIT80_VAL_SELECTED", "FIXED80_STV"}
    stages = {r["arm"]: r for r in rows}
    a = stages["REFIT80_VAL_SELECTED"]
    b = stages["FIXED80_STV"]
    assert a["train_rows"] == b["train_rows"]
    assert a["test_rows"] == b["test_rows"] == stages["STAGED60_VAL_SELECTED"]["test_rows"]
    assert a["rule_count"] == b["rule_count"]
    assert a["test_conflict"] == b["test_conflict"]
    assert a["test_coverage"] == b["test_coverage"]
    assert a["selected_policy_on_val"] == b["selected_policy_on_val"]
    assert a["policy_used_on_test"] == a["selected_policy_on_val"]
    assert b["policy_used_on_test"] == "STANDARD_VOTING"
    for row in rows:
        assert 0 <= row["test_accuracy"] <= 1
        assert 0 <= row["test_ba"] <= 1
        assert 0 <= row["test_conflict"] <= 1
        assert 0 <= row["majority_only_test_accuracy"] <= 1
    assert a["selected_validation_mean"] >= a["val_stv"] - 1e-12


def test_legacy_fresh_selection_disclosed_separately():
    rows = run_one(sample(), "class", ["f1", "f2"], "toy", 7,
                   "CENTRALIZED", include_legacy=True)
    assert len(rows) == 5
    legacy = [r for r in rows if r["split_contract"] == "64_16_20"]
    assert len(legacy) == 2
    assert legacy[0]["train_rows"] == legacy[1]["train_rows"]
    assert legacy[0]["validation_rows"] == legacy[1]["validation_rows"]


def test_fail_closed_on_missing_values_or_target_as_feature():
    df = sample()
    df.loc[0, "f1"] = None
    with pytest.raises(ValueError, match="Missing-value algorithm"):
        run_one(df, "class", ["f1", "f2"], "toy", 1, "CENTRALIZED")
    df = sample()
    with pytest.raises(ValueError, match="Target leakage"):
        run_one(df, "class", ["f1", "class"], "toy", 1, "CENTRALIZED")
