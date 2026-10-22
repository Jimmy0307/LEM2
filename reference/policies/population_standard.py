"""POPULATION_STANDARD — project-defined experimental reference implementation.

This variant was specified in the 2026-10-22 research meeting. It is NOT
claimed as an established literature method.

For one candidate decision d and the matching same-decision rules M_d(x):

    T_d = sum_{r in M_d(x)} |S(r)|
    U_d = | union_{r in M_d(x)} S(r) |
    P_d = U_d / T_d

The original STANDARD_VOTING score is the raw support-occurrence sum T_d.
The population correction removes duplicate support inflation:

    Score_PS(d | x) = T_d * P_d = U_d

Example:
    S(r1) = {u1,u2,u3}
    S(r2) = {u2,u3,u4}
    T_A = 3 + 3 = 6
    U_A = 4
    P_A = 4/6 = 2/3
    Score_PS(A | x) = 6 * 2/3 = 4

Production semantics live in ``roughset.evaluation.predict_with_policy``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence, Set

import numpy as np
import pandas as pd

from roughset.core import Rule


def _matches(row: pd.Series, rule: Rule) -> bool:
    return all(str(row[attr]) == str(value) for attr, value in rule.conditions)


def _resolve_vote(votes: Mapping[Any, float], default_class: Any):
    if not votes:
        return default_class
    best = max(votes.values())
    winners = [decision for decision, score in votes.items() if np.isclose(score, best)]
    if default_class in winners:
        return default_class
    return sorted(winners, key=str)[0]


def predict_population_standard(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
    rule_support_sets: Mapping[Any, Set[Any]],
):
    """Predict by unique positive-support population per candidate decision."""
    matched_by_decision: dict[Any, list[Rule]] = defaultdict(list)
    for rule in rules:
        if _matches(row, rule):
            matched_by_decision[rule.decision].append(rule)

    if not matched_by_decision:
        return default_class

    scores: dict[Any, float] = {}
    for decision, decision_rules in matched_by_decision.items():
        unique_population: set[Any] = set()
        for rule in decision_rules:
            unique_population |= set(rule_support_sets.get(rule.key, set()))
        scores[decision] = float(len(unique_population))

    return _resolve_vote(scores, default_class)
