from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from roughset.core import Rule
from roughset.established_metrics import (
    audit_order_variation_ratio,
    mean_variation_ratio,
    variation_ratio_by_case,
)


def test_variation_ratio_by_case_uses_modal_frequency():
    matrix = np.asarray(
        [
            ["A", "A", "A"],
            ["A", "B", "A"],
            ["A", "B", "C"],
            ["A", "B", "C"],
        ],
        dtype=object,
    )

    got = variation_ratio_by_case(matrix)

    assert np.allclose(got, np.asarray([0.0, 0.25, 0.5]))
    assert mean_variation_ratio(matrix) == pytest.approx(0.25)


def test_variation_ratio_empty_matrix_is_empty_and_nan_mean():
    matrix = np.empty((0, 0), dtype=object)

    assert variation_ratio_by_case(matrix).size == 0
    assert np.isnan(mean_variation_ratio(matrix))


def test_audit_order_variation_ratio_detects_two_order_first_match_disagreement():
    test = pd.DataFrame({"A": ["1"], "D": ["Y"]})
    local_rules = {
        "Client_1": [Rule((("A", "1"),), "Y", "Client_1")],
        "Client_2": [Rule((("A", "1"),), "N", "Client_2")],
    }

    out = audit_order_variation_ratio(
        test=test,
        local_rules=local_rules,
        default_class="Y",
        prediction_policy="FIRST_MATCH",
        conflict_case_flags=[True],
        max_permutations=120,
        seed=42,
    )

    assert out["orderings_checked"] == 2
    assert out["variation_ratio_by_case"] == pytest.approx((0.5,))
    assert out["mean_variation_ratio"] == pytest.approx(0.5)
    assert out["mean_variation_ratio_conflict"] == pytest.approx(0.5)


def test_audit_order_variation_ratio_is_zero_for_order_invariant_voting():
    test = pd.DataFrame({"A": ["1"], "D": ["Y"]})
    local_rules = {
        "Client_1": [Rule((("A", "1"),), "Y", "Client_1")],
        "Client_2": [Rule((("A", "1"),), "N", "Client_2")],
    }

    out = audit_order_variation_ratio(
        test=test,
        local_rules=local_rules,
        default_class="Y",
        prediction_policy="SIMPLE_VOTING",
        conflict_case_flags=[True],
        max_permutations=120,
        seed=42,
    )

    assert out["orderings_checked"] == 2
    assert out["variation_ratio_by_case"] == pytest.approx((0.0,))
    assert out["mean_variation_ratio"] == pytest.approx(0.0)
    assert out["mean_variation_ratio_conflict"] == pytest.approx(0.0)
