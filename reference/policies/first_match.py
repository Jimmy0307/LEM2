"""FIRST_MATCH — separated teaching/reference implementation.

Mathematical form
-----------------
For ordered global rules ``R_G = (r_1, ..., r_m)``:

    k*(x) = min { k : x satisfies Ante(r_k) }
    y_hat(x) = decision(r_k*)

If no rule matches, return the default class.

Literature anchor
-----------------
Woźniak, Sousa, & Śnieżyński (2026), *Rule-Based Federated Learning for
Healthcare*, DOI 10.1007/978-3-032-29921-5_38.  The source Federated LEM2
uses first-match inference and preserves rule-order semantics.

This file is reference-only.  Production semantics remain frozen in
``roughset.evaluation.predict_with_policy``.
"""

from __future__ import annotations

from typing import Any, Sequence

import pandas as pd

from roughset.core import Rule


def _matches(row: pd.Series, rule: Rule) -> bool:
    return all(str(row[attr]) == str(value) for attr, value in rule.conditions)


def predict_first_match(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
):
    """Return the decision of the earliest matching rule."""
    for rule in rules:
        if _matches(row, rule):
            return rule.decision
    return default_class
