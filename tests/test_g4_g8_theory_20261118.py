"""G7 formal-bound sanity checks; not a formal verifier."""
from __future__ import annotations

import math
import pytest

from fedrs.theory_bounds import (
    any_pure_client_label_probability,
    global_confidence_bounds,
)


def test_pure_probability_two_classes_equal_parameter_one():
    # Uniform p ~ Beta(1,1); P(all n in one class) = 2/(n+1).
    for n in (1, 2, 3, 10, 100):
        assert any_pure_client_label_probability(n, (1, 1)) == pytest.approx(2 / (n+1))


def test_pure_probability_bounded_and_decreases_with_more_local_samples():
    for alpha in (.1, .5, 1.0, 5.0):
        vals = [any_pure_client_label_probability(n, [alpha] * 3) for n in (1, 2, 3, 10, 100)]
        assert vals[0] == pytest.approx(1.0)
        assert 0 <= min(vals) <= max(vals) <= 1.0
        assert all(a >= b for a, b in zip(vals, vals[1:]))


def test_pure_formula_is_not_directly_the_actual_classwise_partition_distribution():
    # The function documents a different generative mechanism. CI only checks
    # this exact identity, NOT equality to empirical partition_clients results.
    assert any_pure_client_label_probability(2, (1, 1)) == pytest.approx(2/3)


def test_global_bounds_attained_with_extreme_remote_assignments():
    assert global_confidence_bounds(8, 8, 12) == pytest.approx((0.4, 1.0))
    lo, hi = global_confidence_bounds(6, 10, 10)
    assert lo == pytest.approx(0.3) and hi == pytest.approx(0.8)
    assert lo < 6 / 10 < hi


def test_global_bounds_have_no_universal_positive_threshold_without_remote_cap():
    assert global_confidence_bounds(10, 10, 10**9)[0] < 1e-7


@pytest.mark.parametrize("args", [
    (0,0,0), (5,4,0), (-1,2,0), (2,2,-1),
    (1.5,3,0), (1,1.5,0),
])
def test_reject_invalid_confidence_bound_inputs(args):
    with pytest.raises(ValueError):
        global_confidence_bounds(*args)


@pytest.mark.parametrize("n,alphas", [
    (0,[1,1]), (3,[0,1]), (2,[1]), (3,[1,-1]), (1,[math.nan,1]),
])
def test_reject_invalid_dirichlet_pure_prob(n, alphas):
    with pytest.raises(ValueError):
        any_pure_client_label_probability(n, alphas)
