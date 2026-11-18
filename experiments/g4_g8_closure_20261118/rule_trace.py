"""Row-level, non-mutating diagnostics for federated LEM2 B2 and No-Match.

Only development-trained RuleContext / rules are required for online diagnostics.
Optional y_true is strictly for *offline* evaluation and never affects matching,
candidate sets, resolver selection or prediction.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from fedrs.predict import (
    RULE_VARIANTS,
    POLICIES,
    RuleContext,
    _decision_masks,
    match_matrix,
    resolve,
    variant_matrix,
)


def rule_trace(
    frame: pd.DataFrame,
    ctx: RuleContext,
    variant: str = "B2_TRUE_AS_FALLBACK",
    policy: str = "GLOBAL_STRENGTH",
    y_true: Sequence[object] | None = None,
) -> pd.DataFrame:
    """One trace row per input row, preserving original positions (not IDs).

    Raw match = original UNION, including empty antecedents.
    Nonempty match = at least one condition-carrying rule.
    Effective match = variant-selected rules. In B2 a TRUE rule can still be
    effective when there is no nonempty match. No match then invokes the
    default-class fallback: this is *not* abstention.
    """
    if variant not in RULE_VARIANTS:
        raise ValueError(f"Unknown variant {variant}")
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy}")
    n = len(frame)
    if y_true is not None and len(y_true) != n:
        raise ValueError("y_true must have exactly one label per row")

    raw = match_matrix(frame, ctx.rules)
    effective = variant_matrix(raw, ctx, variant)
    nonempty = raw[:, ~ctx.is_empty]
    true = raw[:, ctx.is_empty]
    raw_candidates = _decision_masks(raw, ctx)
    eff_candidates = _decision_masks(effective, ctx)
    raw_decs = raw_candidates.sum(axis=1)
    eff_decs = eff_candidates.sum(axis=1)
    specific_hit = nonempty.any(axis=1)
    true_hit = true.any(axis=1)
    raw_hit = raw.any(axis=1)
    effective_hit = effective.any(axis=1)
    pred = resolve(effective, ctx, policy)
    rows = {
        "row_position": np.arange(n, dtype=int),
        "raw_rule_match_count": raw.sum(axis=1),
        "nonempty_rule_match_count": nonempty.sum(axis=1),
        "true_rule_match_count": true.sum(axis=1),
        "effective_rule_match_count": effective.sum(axis=1),
        "raw_no_match": ~raw_hit,
        "nonempty_no_match": ~specific_hit,
        "true_only": (~specific_hit) & true_hit,
        "effective_no_match": ~effective_hit,
        "no_match_fallback_prediction": ~effective_hit,
        "abstained": np.zeros(n, dtype=bool),  # existing resolver never abstains
        "raw_conflict": raw_decs >= 2,
        "active_conflict": eff_decs >= 2,
        "raw_candidate_count": raw_decs,
        "effective_candidate_count": eff_decs,
        "raw_candidate_set": [
            tuple(ctx.classes[j] for j in np.flatnonzero(raw_candidates[i])) for i in range(n)
        ],
        "effective_candidate_set": [
            tuple(ctx.classes[j] for j in np.flatnonzero(eff_candidates[i])) for i in range(n)
        ],
        "prediction": pred,
        "variant": [variant] * n,
        "policy": [policy] * n,
    }
    if y_true is not None:
        truth = np.asarray([str(x) for x in y_true], dtype=object)
        truth_raw = np.asarray([
            truth[i] in rows["raw_candidate_set"][i] for i in range(n)
        ], dtype=bool)
        truth_eff = np.asarray([
            truth[i] in rows["effective_candidate_set"][i] for i in range(n)
        ], dtype=bool)
        correct = pred == truth
        # Mutually exclusive, collectively exhaustive labels; do NOT use for model selection.
        failure_mode = []
        for i in range(n):
            if not effective_hit[i]:
                failure_mode.append("NO_MATCH_FALLBACK_CORRECT" if correct[i] else "NO_MATCH_FALLBACK_WRONG")
            elif eff_decs[i] == 1:
                failure_mode.append("SINGLE_CORRECT" if correct[i] else "SINGLE_WRONG")
            elif not truth_eff[i]:
                failure_mode.append("MULTI_TRUTH_ABSENT")
            else:
                failure_mode.append("MULTI_CORRECT" if correct[i] else "MULTI_TRUTH_PRESENT_WRONG")
        rows.update({
            "true_decision": truth,
            "truth_in_raw_candidate": truth_raw,
            "truth_in_effective_candidate": truth_eff,
            "final_correct": correct,
            "failure_mode": failure_mode,
        })
    result = pd.DataFrame(rows)
    # Structural invariants and audit safety; this module has no file writes.
    assert len(result) == n
    assert not (result["true_only"] & ~result["nonempty_no_match"]).any()
    assert not (result["active_conflict"] & result["effective_no_match"]).any()
    assert not result["abstained"].any()
    if variant == "B2_TRUE_AS_FALLBACK":
        assert (result["raw_no_match"] == result["effective_no_match"]).all()
        assert (result["nonempty_rule_match_count"] > 0).equals(
            result["effective_rule_match_count"] > 0 if not true_hit.any()
            else (result["nonempty_rule_match_count"] > 0)
        )
    return result
