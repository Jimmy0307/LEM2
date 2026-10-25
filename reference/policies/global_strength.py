"""GLOBAL_STRENGTH — separated teaching/reference implementation.

Mathematical form
-----------------
For decision ``d`` and matching rules ``M_d(x)``:

    S_d(x) = union_{r in M_d(x)} S_G(r)
    GS(d | x) = |S_d(x)| / N_d

where ``S_G(r)`` is the positive support-object set of global rule ``r`` and
``N_d`` is the training-set size of decision class ``d``.  The set union means
the same training object is counted once even if several same-decision rules
cover it.

Literature anchor
-----------------
Bazan, Nguyen, Nguyen, Synak, & Wróblewski (2000), *Rough Set Algorithms in
Classification Problem*, GlobalStrength Eq. (23),
DOI 10.1007/978-3-7908-1840-6_3.

The federated implementation preserves this formula structure while the support
sets are aggregated across clients.

Ties follow the frozen production rule: choose the default class when it is
among tied winners; otherwise choose the string-smallest decision.

This file is reference-only.  Production semantics remain frozen in
``roughset.evaluation.predict_with_policy``.
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


def predict_global_strength(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
    rule_support_sets: Mapping[Any, Set[Any]],
    class_sizes: Mapping[Any, int],
):
    """Predict by unique support-object coverage normalized by class size."""
    matched_by_decision: dict[Any, list[Rule]] = defaultdict(list)
    for rule in rules:
        if _matches(row, rule):
            matched_by_decision[rule.decision].append(rule)

    if not matched_by_decision:
        return default_class

    scores: dict[Any, float] = {}
    for decision, decision_rules in matched_by_decision.items():
        supported_objects: set[Any] = set()
        for rule in decision_rules:
            supported_objects |= set(rule_support_sets.get(rule.key, set()))

        denominator = int(class_sizes.get(decision, 0))
        scores[decision] = (
            len(supported_objects) / denominator
            if denominator > 0
            else 0.0
        )

    return _resolve_vote(scores, default_class)
