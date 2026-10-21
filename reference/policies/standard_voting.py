"""STANDARD_VOTING — separated teaching/reference implementation.

Mathematical form
-----------------
For decision ``d`` and matching-rule subset ``M_d(x)``:

    S_STD(d | x) = sum_{r in M_d(x)} w(r)

In the frozen Federated LEM2 implementation, ``w(r)`` is the pooled,
decision-consistent positive support of global rule ``r`` across all clients:

    Supp_c(r) = { z in U_c : z satisfies Ante(r) and D(z) = decision(r) }
    w_F(r) = sum_c |Supp_c(r)|

This federated support scope is an adaptation of the support-weighted voting
principle; it is not claimed to be the original RSES weight definition.

Literature anchor
-----------------
Lazo-Cortés et al. (2020), *Towards Selecting Reducts for Building Decision
Rules for Rule-Based Classifiers*, DOI 10.1007/978-3-030-49076-8_7.

Ties follow the frozen production rule: choose the default class when it is
among tied winners; otherwise choose the string-smallest decision.

This file is reference-only.  Production semantics remain frozen in
``roughset.evaluation.predict_with_policy`` and the federated support context
is built by ``roughset.pipeline.global_rule_support_context``.
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


def predict_standard_voting(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
    rule_weights: Mapping[Any, float],
):
    """Predict by summing support weights of matching rules by decision."""
    votes: dict[Any, float] = defaultdict(float)
    for rule in rules:
        if _matches(row, rule):
            votes[rule.decision] += float(rule_weights.get(rule.key, 0.0))
    return _resolve_vote(votes, default_class)
