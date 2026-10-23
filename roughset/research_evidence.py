from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .core import Rule


def target_candidate_coverage_by_class(
    y_true: Sequence[Any],
    matched_rule_lists: Sequence[Sequence[Rule]],
) -> dict[str, float]:
    """Coverage of the *true decision candidate* inside each true class.

    Ordinary target coverage asks whether any rule matches a test object.
    This stricter research diagnostic asks whether at least one matching rule
    proposes the object's true decision.  It therefore separates candidate
    generation / rule-coverage failure from later candidate-ranking failure.
    """
    labels = [str(value) for value in y_true]
    result: dict[str, float] = {}
    for label in sorted(set(labels), key=str):
        indices = [idx for idx, value in enumerate(labels) if value == label]
        if not indices:
            result[label] = float("nan")
            continue
        represented = 0
        for idx in indices:
            decisions = {str(rule.decision) for rule in matched_rule_lists[idx]}
            represented += int(label in decisions)
        result[label] = represented / len(indices)
    return result


def _status(true_decision: str, old_winner: str, new_winner: str) -> str:
    old_ok = old_winner == true_decision
    new_ok = new_winner == true_decision
    if not old_ok and new_ok:
        return "CORRECTED"
    if old_ok and not new_ok:
        return "HARMED"
    if old_winner != new_winner:
        return "CHANGED_SAME_CORRECTNESS"
    return "UNCHANGED"


def _redundancy_for(
    decision: str,
    decision_scores: Mapping[str, Mapping[str, Any]],
) -> float:
    row = decision_scores.get(str(decision))
    if row is None:
        return float("nan")
    p = row.get("population_nonredundancy_ratio")
    if p is None:
        return float("nan")
    try:
        value = float(p)
    except (TypeError, ValueError):
        return float("nan")
    return 1.0 - value


def transition_redundancy_evidence(
    *,
    true_decision: Any,
    old_winner: Any,
    new_winner: Any,
    decision_scores: Mapping[Any, Mapping[str, Any]],
) -> dict[str, Any]:
    """Describe one baseline→population winner transition.

    Redundancy is R_d = 1 - P_d, where P_d = U_d / T_d.

    For corrected/harmed transitions, ``redundancy_asymmetry`` is defined as

        R_competitor - R_true

    so a positive value means the competing decision is more redundant than
    the true decision, while a negative value means the true decision carries
    more repeated support and is therefore at risk of over-correction.

    The quantity is project-defined mechanism evidence, not a literature metric.
    """
    true_value = str(true_decision)
    old_value = str(old_winner)
    new_value = str(new_winner)
    normalized_scores = {str(key): value for key, value in decision_scores.items()}

    true_present = true_value in normalized_scores
    old_redundancy = _redundancy_for(old_value, normalized_scores)
    new_redundancy = _redundancy_for(new_value, normalized_scores)
    true_redundancy = _redundancy_for(true_value, normalized_scores)
    status = _status(true_value, old_value, new_value)

    competitor = None
    if status == "CORRECTED":
        competitor = old_value
    elif status == "HARMED":
        competitor = new_value

    competitor_redundancy = (
        _redundancy_for(competitor, normalized_scores)
        if competitor is not None
        else float("nan")
    )
    if competitor is not None and true_present and math.isfinite(true_redundancy) and math.isfinite(competitor_redundancy):
        asymmetry = competitor_redundancy - true_redundancy
    else:
        asymmetry = float("nan")

    if math.isfinite(old_redundancy) and math.isfinite(new_redundancy):
        winner_redundancy_drop = old_redundancy - new_redundancy
    else:
        winner_redundancy_drop = float("nan")

    if not true_present:
        error_type = "COVERAGE_INDUCTION_FAILURE"
    elif status == "CORRECTED":
        error_type = "CORRECTED_CONFLICT"
    elif status == "HARMED":
        error_type = "HARMED_OVER_CORRECTION"
    elif status == "CHANGED_SAME_CORRECTNESS":
        error_type = "RANKING_CHANGED_SAME_CORRECTNESS"
    else:
        error_type = "RANKING_UNCHANGED"

    return {
        "true_decision": true_value,
        "old_winner": old_value,
        "new_winner": new_value,
        "status": status,
        "error_type": error_type,
        "true_candidate_present": true_present,
        "true_redundancy": true_redundancy,
        "old_redundancy": old_redundancy,
        "new_redundancy": new_redundancy,
        "competitor": competitor,
        "competitor_redundancy": competitor_redundancy,
        "winner_redundancy_drop": winner_redundancy_drop,
        "redundancy_asymmetry": asymmetry,
    }
