"""Mathematical regression checks for frozen-rule resolver opportunity bounds."""
from __future__ import annotations

import pytest

from experiments.g4_g8_closure_20261118.bounds import resolver_change_bounds


def test_minority_conflict_can_have_large_ba_effect_relative_to_global_rate():
    # Minority is only one of ten rows. A single conflict can change
    # balanced accuracy by 0.5 even though total conflict rate is 0.1.
    y = ["A"] * 9 + ["B"]
    a = ["A"] * 10
    b = ["A"] * 9 + ["B"]
    z = [False] * 9 + [True]
    q = resolver_change_bounds(y, a, b, z)
    assert q["n"] == 10
    assert q["n_conflict"] == 1
    assert q["accuracy_absolute_upper_bound"] == pytest.approx(0.1)
    assert q["accuracy_gap_b_minus_a"] == pytest.approx(0.1)
    assert q["balanced_accuracy_absolute_upper_bound"] == pytest.approx(0.5)
    assert q["balanced_accuracy_gap_b_minus_a"] == pytest.approx(0.5)


def test_multiple_conflicts_do_not_guarantee_actual_accuracy_gain():
    y = ["A", "B", "A", "B"]
    a = ["A", "B", "B", "B"]
    b = ["B", "B", "A", "B"]
    z = [True, False, True, False]
    q = resolver_change_bounds(y, a, b, z)
    assert q["accuracy_gap_b_minus_a"] == pytest.approx(0)
    assert q["balanced_accuracy_gap_b_minus_a"] == pytest.approx(0)
    assert q["accuracy_absolute_upper_bound"] == pytest.approx(0.5)


def test_changed_non_conflict_row_is_contract_violation():
    with pytest.raises(ValueError, match="outside frozen-rule conflict"):
        resolver_change_bounds(["A", "B"], ["A", "B"], ["B", "B"], [False, False])


def test_reject_missing_and_misaligned_inputs():
    for args in [([], [], [], []), (["A"], [], ["A"], [True])]:
        with pytest.raises(ValueError):
            resolver_change_bounds(*args)
