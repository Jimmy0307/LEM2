from __future__ import annotations

import pandas as pd

from roughset.core import Rule
from roughset.evaluation import predict_with_policy
from reference.policies.first_match import predict_first_match
from reference.policies.global_strength import predict_global_strength
from reference.policies.simple_voting import predict_simple_voting
from reference.policies.standard_voting import predict_standard_voting


def _fixture():
    rules = [
        Rule((("A", "1"),), "Y", "c1"),
        Rule((("A", "1"),), "N", "c2"),
        Rule((("B", "1"),), "Y", "c3"),
    ]
    row = pd.Series({"A": "1", "B": "1"})
    weights = {
        rules[0].key: 2.0,
        rules[1].key: 5.0,
        rules[2].key: 3.0,
    }
    support_sets = {
        rules[0].key: {"y1", "y2"},
        rules[1].key: {"n1", "n2", "n3", "n4", "n5"},
        rules[2].key: {"y2", "y3", "y4"},
    }
    class_sizes = {"Y": 10, "N": 10}
    return row, rules, weights, support_sets, class_sizes


def test_separated_reference_policies_match_frozen_prediction_policy_semantics():
    row, rules, weights, support_sets, class_sizes = _fixture()
    default_class = "N"

    expected_first, _ = predict_with_policy(
        row, rules, default_class, policy="FIRST_MATCH"
    )
    expected_simple, _ = predict_with_policy(
        row, rules, default_class, policy="SIMPLE_VOTING"
    )
    expected_standard, _ = predict_with_policy(
        row,
        rules,
        default_class,
        policy="STANDARD_VOTING",
        rule_weights=weights,
    )
    expected_global, _ = predict_with_policy(
        row,
        rules,
        default_class,
        policy="GLOBAL_STRENGTH",
        rule_support_sets=support_sets,
        class_sizes=class_sizes,
    )

    assert predict_first_match(row, rules, default_class) == expected_first
    assert predict_simple_voting(row, rules, default_class) == expected_simple
    assert predict_standard_voting(row, rules, default_class, weights) == expected_standard
    assert (
        predict_global_strength(
            row,
            rules,
            default_class,
            support_sets,
            class_sizes,
        )
        == expected_global
    )
