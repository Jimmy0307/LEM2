"""SIMPLE_VOTING — separated teaching/reference implementation.

Mathematical form
-----------------
For decision ``d`` and matching-rule subset ``M_d(x)``:

    S_SV(d | x) = |M_d(x)|

Each matching rule contributes exactly one vote.  The highest score wins.
Ties follow the frozen production rule: choose the default class when it is
among the tied winners; otherwise choose the string-smallest decision.

Literature anchor
-----------------
Lazo-Cortés et al. (2020), *Towards Selecting Reducts for Building Decision
Rules for Rule-Based Classifiers*, DOI 10.1007/978-3-030-49076-8_7.
The paper describes RSES voting where matching rules vote for their consequent
decisions; Simple Voting is the one-rule-one-vote case.

This file is reference-only.  Production semantics remain frozen in
``roughset.evaluation.predict_with_policy``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

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


def predict_simple_voting(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
):
    """Predict by counting matching rules for each decision."""
    votes: dict[Any, float] = defaultdict(float)
    for rule in rules:
        if _matches(row, rule):
            votes[rule.decision] += 1.0
    return _resolve_vote(votes, default_class)
