"""Validate separation of nonempty rule evidence, TRUE-only coverage and fallback."""
from __future__ import annotations

import pandas as pd
import pytest

from roughset.core import Rule
from fedrs.predict import build_context
from experiments.g4_g8_closure_20261118.rule_trace import rule_trace


def _context():
    rules = (
        Rule((("a", "x"),), "P", "C1"),
        Rule((), "N", "C2"),
        Rule((("a", "y"),), "N", "C1"),
    )
    train = pd.DataFrame({"a": ["x", "x", "y", "y"], "class": ["P", "P", "N", "N"]})
    return build_context(rules, train, "class", "P")


def test_B2_preserves_coverage_but_isolates_true_only_and_conflict():
    ctx = _context()
    x = pd.DataFrame({"a": ["x", "y", "z"]})
    result = rule_trace(x, ctx, y_true=["P", "N", "N"])
    assert result.raw_rule_match_count.tolist() == [2, 2, 1]
    assert result.nonempty_rule_match_count.tolist() == [1, 1, 0]
    assert result.true_only.tolist() == [False, False, True]
    assert result.raw_conflict.tolist() == [True, False, False]
    assert result.active_conflict.tolist() == [False, False, False]
    assert result.raw_no_match.tolist() == [False, False, False]
    assert result.effective_no_match.tolist() == [False, False, False]
    assert result.no_match_fallback_prediction.tolist() == [False, False, False]
    assert result.abstained.tolist() == [False, False, False]
    assert result.prediction.tolist() == ["P", "N", "N"]
    assert result.failure_mode.tolist() == ["SINGLE_CORRECT", "SINGLE_CORRECT", "SINGLE_CORRECT"]
    assert result.loc[0, "raw_candidate_set"] == ("N", "P")
    assert result.loc[0, "effective_candidate_set"] == ("P",)


def test_drop_true_changes_coverage_and_uses_default_instead_of_abstaining():
    ctx = _context()
    frame = pd.DataFrame({"a": ["x", "z"]})
    keep = rule_trace(frame, ctx, variant="B2_TRUE_AS_FALLBACK", y_true=["P", "N"])
    drop = rule_trace(frame, ctx, variant="B_DROP_TRUE", y_true=["P", "N"])
    assert keep.effective_no_match.tolist() == [False, False]
    assert drop.effective_no_match.tolist() == [False, True]
    assert drop.no_match_fallback_prediction.tolist() == [False, True]
    assert not drop.abstained.any()
    assert drop.prediction.tolist() == ["P", "P"]  # majority-class fallback, not reject
    assert drop.failure_mode.tolist() == ["SINGLE_CORRECT", "NO_MATCH_FALLBACK_WRONG"]


def test_no_test_labels_required_for_structural_trace_and_policy():
    frame = pd.DataFrame({"a": ["x", "z"]})
    no_labels = rule_trace(frame, _context())
    with_labels = rule_trace(frame, _context(), y_true=["N", "P"])
    assert "failure_mode" not in no_labels
    assert "final_correct" not in no_labels
    assert no_labels.prediction.tolist() == with_labels.prediction.tolist()
    assert no_labels.effective_candidate_set.tolist() == with_labels.effective_candidate_set.tolist()
    with pytest.raises(ValueError):
        rule_trace(frame, _context(), y_true=["P"])
    with pytest.raises(ValueError):
        rule_trace(frame, _context(), variant="BOGUS")
