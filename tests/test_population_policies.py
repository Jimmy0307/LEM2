from __future__ import annotations

import math

import pandas as pd

from roughset.core import Rule
from roughset.evaluation import (
    evaluate_rule_model,
    population_support_summary,
    predict_with_policy,
    target_coverage_by_class,
)


def _conflict_example():
    rules = [
        Rule((("X", "1"),), "A"),
        Rule((("Y", "1"),), "A"),
        Rule((("Z", "1"),), "B"),
    ]
    row = pd.Series({"X": "1", "Y": "1", "Z": "1"})
    supports = {
        rules[0].key: {"u1", "u2", "u3"},
        rules[1].key: {"u2", "u3", "u4"},
        rules[2].key: {"v1", "v2", "v3", "v4", "v5"},
    }
    weights = {key: float(len(values)) for key, values in supports.items()}
    class_sizes = {"A": 4, "B": 6}
    return row, rules, weights, supports, class_sizes


def test_population_ratio_matches_meeting_example_four_unique_over_six_occurrences():
    row, rules, _weights, supports, class_sizes = _conflict_example()
    matching_a_rules = rules[:2]
    summary = population_support_summary(
        matching_a_rules,
        supports,
        class_sizes=class_sizes,
    )["A"]

    assert summary["total_support_occurrences"] == 6.0
    assert summary["unique_population"] == 4.0
    assert summary["redundant_occurrences"] == 2.0
    assert math.isclose(summary["population_nonredundancy_ratio"], 2.0 / 3.0)


def test_population_standard_deduplicates_repeated_support_population():
    row, rules, weights, supports, class_sizes = _conflict_example()

    raw_standard = predict_with_policy(
        row,
        rules,
        "A",
        "STANDARD_VOTING",
        rule_weights=weights,
    )[0]
    population_standard = predict_with_policy(
        row,
        rules,
        "A",
        "POPULATION_STANDARD",
        rule_weights=weights,
        rule_support_sets=supports,
        class_sizes=class_sizes,
    )[0]

    # A has raw support 3+3=6 but only four unique support objects.
    # B has five unique objects.  The population correction must remove
    # duplicate support inflation, so the winner flips from A to B.
    assert raw_standard == "A"
    assert population_standard == "B"


def test_population_global_applies_same_redundancy_correction_to_global_strength():
    row, rules, weights, supports, class_sizes = _conflict_example()

    raw_global = predict_with_policy(
        row,
        rules,
        "A",
        "GLOBAL_STRENGTH",
        rule_support_sets=supports,
        class_sizes=class_sizes,
    )[0]
    population_global = predict_with_policy(
        row,
        rules,
        "A",
        "POPULATION_GLOBAL",
        rule_weights=weights,
        rule_support_sets=supports,
        class_sizes=class_sizes,
    )[0]

    # A: U/T = 4/6 = 2/3 and raw GlobalStrength = 4/4 = 1,
    # corrected score = 2/3.
    # B: U/T = 5/5 = 1 and raw GlobalStrength = 5/6,
    # corrected score = 5/6, so B must win.
    assert raw_global == "A"
    assert population_global == "B"


def test_holdout_coverage_helpers_report_overall_and_per_target_coverage():
    test = pd.DataFrame(
        {
            "A": ["1", "0", "1", "0"],
            "B": ["0", "0", "0", "1"],
            "D": ["Y", "Y", "N", "N"],
        }
    )
    rules = [
        Rule((("A", "1"),), "Y"),
        Rule((("B", "1"),), "N"),
    ]

    metrics = evaluate_rule_model(
        test,
        rules,
        default_class="N",
        target="D",
        prediction_policy="FIRST_MATCH",
    )
    target_coverage = target_coverage_by_class(test["D"], metrics["matched_rules"])

    # Keep evaluate_rule_model itself frozen; the new reporting layer aliases
    # its existing coverage as overall_coverage and adds per-target coverage.
    assert math.isclose(metrics["coverage"], 0.75)
    assert target_coverage == {"N": 1.0, "Y": 0.5}
    assert math.isclose(sum(target_coverage.values()) / len(target_coverage), 0.75)
    assert math.isclose(metrics["balanced_accuracy"], 0.5)
