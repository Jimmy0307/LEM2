"""POPULATION_GLOBAL — project-defined experimental reference implementation.

This variant was specified from the 2026-10-22 research meeting discussion.
It is NOT attributed to Bazan et al. or other prior literature.  The established
GLOBAL_STRENGTH baseline remains unchanged and is compared separately.

For candidate decision d:

    T_d = sum_{r in M_d(x)} |S(r)|
    U_d = | union_{r in M_d(x)} S(r) |
    P_d = U_d / T_d
    GS_d = U_d / N_d

The same nonredundancy correction is then applied to GlobalStrength:

    Score_PG(d | x) = GS_d * P_d
                      = U_d^2 / (N_d * T_d)

This preserves class-size normalization while penalizing support occurrences
that are duplicated across multiple matching rules.

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


def predict_population_global(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
    rule_support_sets: Mapping[Any, Set[Any]],
    class_sizes: Mapping[Any, int],
):
    """Predict with class-normalized unique population plus redundancy penalty."""
    matched_by_decision: dict[Any, list[Rule]] = defaultdict(list)
    for rule in rules:
        if _matches(row, rule):
            matched_by_decision[rule.decision].append(rule)

    if not matched_by_decision:
        return default_class

    scores: dict[Any, float] = {}
    for decision, decision_rules in matched_by_decision.items():
        total_occurrences = 0
        unique_population: set[Any] = set()
        for rule in decision_rules:
            support = set(rule_support_sets.get(rule.key, set()))
            total_occurrences += len(support)
            unique_population |= support

        unique_count = len(unique_population)
        class_size = int(class_sizes.get(decision, class_sizes.get(str(decision), 0)))
        nonredundancy = unique_count / total_occurrences if total_occurrences > 0 else 0.0
        global_strength = unique_count / class_size if class_size > 0 else 0.0
        scores[decision] = global_strength * nonredundancy

    return _resolve_vote(scores, default_class)
