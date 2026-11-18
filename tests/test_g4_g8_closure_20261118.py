"""Executable G4-G8 closure diagnostics: no Internet, no private OpenML cache."""
from __future__ import annotations

import numpy as np
import pandas as pd

from roughset.core import Rule
from fedrs.closure_diagnostics import audit_fitted_model, error_modes, score_policies
from fedrs.predict import build_context, match_matrix, resolve, variant_matrix


def _rule_ctx():
    rules = (
        Rule((("a", "x"),), "P", "C1"),
        Rule((("a", "x"),), "N", "C2"),
        Rule((("a", "y"),), "P", "C1"),
        Rule((("a", "p"),), "P", "C2"),
        Rule((), "P", "C3"),
    )
    train = pd.DataFrame({"a": ["x", "x", "y", "p", "z"],
                          "class": ["P", "N", "P", "P", "P"]})
    return rules, build_context(rules, train, "class", "P")


def test_coverage_taxonomy_is_disjoint_and_true_only_not_no_match():
    rules, ctx = _rule_ctx()
    test = pd.DataFrame({"a": ["x", "y", "z", "p"],
                         "class": ["P", "N", "N", "P"]})
    M = match_matrix(test, rules)
    z = error_modes(M, ctx, test["class"])
    assert z["rows"] == 4
    assert z["count"] == {
        "NO_MATCH": 0,
        "TRUE_ONLY": 1,
        "CANDIDATE_MISS": 1,
        "CONFLICT_RESOLVABLE": 1,
        "SINGLE_CORRECT": 1,
    }
    assert z["strict_nonempty_coverage"] == 0.75
    assert z["effective_coverage_including_true"] == 1.0
    assert all(z["masks"][key].sum() == n for key, n in z["count"].items())
    all_buckets = np.stack(list(z["masks"].values()))
    assert all_buckets.sum(axis=0).tolist() == [1, 1, 1, 1]


def test_no_rule_can_exist_without_a_true_rule_and_explicit_abstention_is_not_implicit():
    rules = (Rule((("a", "x"),), "P", "C1"),)
    train = pd.DataFrame({"a": ["x", "y"], "class": ["P", "N"]})
    ctx = build_context(rules, train, "class", "N")
    test = pd.DataFrame({"a": ["y"], "class": ["N"]})
    M = match_matrix(test, rules)
    z = error_modes(M, ctx, test["class"])
    assert z["count"]["NO_MATCH"] == 1
    assert z["effective_coverage_including_true"] == 0.0
    # Existing core uses a majority fallback instead of abstaining.
    assert resolve(M, ctx, "SIMPLE_VOTING")[0] == "N"


def test_b2_is_not_unconditionally_better_than_union():
    rules = (Rule((), "P", "C1"), Rule((("a", "x"),), "N", "C2"))
    train = pd.DataFrame({"a": ["x", "y", "z"], "class": ["P", "P", "N"]})
    ctx = build_context(rules, train, "class", "P")
    test = pd.DataFrame({"a": ["x", "x"], "class": ["P", "N"]})
    M = match_matrix(test, rules)
    A = resolve(M, ctx, "SIMPLE_VOTING")
    B2 = resolve(variant_matrix(M, ctx, "B2_TRUE_AS_FALLBACK"), ctx, "SIMPLE_VOTING")
    assert A.tolist() == ["P", "P"]
    assert B2.tolist() == ["N", "N"]
    # Same antecedents, opposite true labels: both possible, no universal dominance.
    assert A[0] == test["class"][0] and B2[0] != test["class"][0]
    assert B2[1] == test["class"][1] and A[1] != test["class"][1]


def test_validation_selection_cannot_read_test_labels():
    rules, ctx = _rule_ctx()
    val = pd.DataFrame({"a": ["x", "x", "y", "p", "z", "z"],
                        "class": ["P", "N", "P", "P", "N", "P"]})
    test = pd.DataFrame({"a": ["x", "y", "z", "p"], "class": ["P", "N", "N", "P"]})
    Mv, Mt = match_matrix(val, rules), match_matrix(test, rules)
    a = score_policies(Mv, Mt, ctx, val["class"], test["class"])
    inverted = pd.Series(["N" if y == "P" else "P" for y in test["class"]])
    b = score_policies(Mv, Mt, ctx, val["class"], inverted)
    assert a["chosen_validation_policy"] == b["chosen_validation_policy"]
    assert a["validation_ba"] == b["validation_ba"]
    assert len(a["prediction_disagreement_fraction"]) == 15


def test_fit_and_audit_three_rule_variants_without_test_leakage():
    from fedrs.experiment import fit_model, nested_split
    from fedrs.noise import synthetic_table
    from fedrs.partition import original_partition
    df = synthetic_table(240, "balanced", 101)
    dev, val, test = nested_split(df, "class", 5)
    clients = original_partition(dev, "class", 3, 5, "NONIID_01")
    fm = fit_model(["x1", "x2", "x3", "c1", "c2"], ["x1", "x2", "x3"],
                   ["c1", "c2"], "class", clients, dev, val, test, "EQUAL_WIDTH_3")
    rows = audit_fitted_model(fm, "NONIID_01")
    assert len(rows) == 3
    assert [r["rule_variant"] for r in rows] == [
        "A_ALL_RULES", "B_DROP_TRUE", "B2_TRUE_AS_FALLBACK"
    ]
    assert len({r["n_test"] for r in rows}) == 1
    assert len({r["strict_nonempty_coverage"] for r in rows}) == 1
    for row in rows:
        assert sum(row[f"n_{name}"] for name in
                   ("no_match", "true_only", "candidate_miss",
                    "conflict_resolvable", "single_correct")) == len(test)
        assert 0.0 <= row["test_ba_validation_selected"] <= 1.0
        assert row["oracle_policy_range_exploratory"] >= 0.0
