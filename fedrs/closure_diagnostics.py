"""G4-G8 exploratory closure: disjoint coverage/decision failure taxonomy.

Separate:
- strict LEM2 non-empty rule hit from TRUE->d-only coverage;
- candidate-generation errors from decision resolver errors;
- rule NoMatch from explicit abstention (this module does not abstain);
- development fitting from validation-only selector choice and untouched test.

These diagnostic analyses are POST-HOC with respect to Gate 5 and are NOT
new independent confirmatory tests.
"""
from __future__ import annotations

import json
from itertools import combinations
from typing import Mapping, Sequence

import numpy as np

from .metrics import scores
from .predict import (
    POLICIES, RuleContext, candidate_profile, match_matrix, resolve, variant_matrix,
)


def error_modes(M: np.ndarray, ctx: RuleContext, y_true: Sequence[str]) -> dict:
    """Partition all rows into five mutually exclusive failure/opportunity buckets.

    Classification uses TRUE labels only to evaluate outcomes. Do not use this
    function to select model thresholds or to fit supplementary rules.
    """
    y = np.asarray([str(v) for v in y_true], dtype=object)
    if M.ndim != 2 or M.shape != (len(y), ctx.n_rules):
        raise ValueError("match matrix must be (#rows, #rules)")
    nonempty = M[:, ~ctx.is_empty]
    specific = nonempty.any(axis=1)
    has_true_rule = M[:, ctx.is_empty].any(axis=1)
    M_specific = M.copy()
    M_specific[:, ctx.is_empty] = False
    p = candidate_profile(M_specific, ctx, y)
    masks = {
        "NO_MATCH": ~specific & ~has_true_rule,
        "TRUE_ONLY": ~specific & has_true_rule,
        "CANDIDATE_MISS": specific & ~p["truth_in_candidates"],
        "CONFLICT_RESOLVABLE": specific & p["truth_in_candidates"] & p["multi"],
        "SINGLE_CORRECT": specific & p["truth_in_candidates"] & p["single"],
    }
    count = {k: int(v.sum()) for k, v in masks.items()}
    if sum(count.values()) != len(y):
        raise AssertionError("coverage decomposition must be disjoint and exhaustive")
    return {
        "rows": len(y), "count": count,
        "rates": {k: (v / len(y) if len(y) else float("nan")) for k, v in count.items()},
        "strict_nonempty_coverage": float(specific.mean()) if len(y) else float("nan"),
        "effective_coverage_including_true": float((specific | has_true_rule).mean()) if len(y) else float("nan"),
        "masks": masks,
    }


def score_policies(M_val: np.ndarray, M_test: np.ndarray, ctx: RuleContext,
                   y_val: Sequence[str], y_test: Sequence[str],
                   fixed_policy: str = "SIMPLE_VOTING") -> dict:
    """Select validation winner without using test truth; report test regret.

    A positive test delta does not establish causal/inferential benefit. For
    statistical inference, aggregate at independent dataset/source-family level.
    """
    yv = np.asarray([str(v) for v in y_val], dtype=object)
    yt = np.asarray([str(v) for v in y_test], dtype=object)
    if fixed_policy not in POLICIES:
        raise ValueError("fixed_policy not in historical six")
    from .experiment import POLICY_ORDER
    validation = {p: scores(yv, resolve(M_val, ctx, p))["ba"] for p in POLICIES}
    chosen = max(POLICY_ORDER, key=lambda p: (validation[p], -POLICY_ORDER.index(p)))
    pred = {p: resolve(M_test, ctx, p) for p in POLICIES}
    metrics = {p: scores(yt, v) for p, v in pred.items()}
    test_winner_delta = metrics[chosen]["ba"] - metrics[fixed_policy]["ba"]
    return {
        "chosen_validation_policy": chosen,
        "validation_ba": validation,
        "test_ba": {p: m["ba"] for p, m in metrics.items()},
        "fixed_policy": fixed_policy,
        "test_ba_delta_from_fixed": float(test_winner_delta),
        "test_policy_range_oracle_only": float(max(m["ba"] for m in metrics.values()) -
                                                min(m["ba"] for m in metrics.values())),
        "prediction_disagreement_fraction": {
            f"{a}__{b}": float(np.mean(pred[a] != pred[b])) if len(yt) else float("nan")
            for a, b in combinations(POLICIES, 2)
        },
    }


def audit_fitted_model(fm, regime: str) -> list[dict]:
    """Collect A/B/B2 comparisons from identical splits, training rules and clients."""
    from .experiment import DEFAULT_BASE
    val, test = fm.frames["val"], fm.frames["test"]
    yv = val[fm.target].astype(str).to_numpy()
    yt = test[fm.target].astype(str).to_numpy()
    Mv = match_matrix(val, fm.rules)
    Mt = match_matrix(test, fm.rules)
    modes = error_modes(Mt, fm.ctx, yt)
    results = []
    for variant in ("A_ALL_RULES", "B_DROP_TRUE", "B2_TRUE_AS_FALLBACK"):
        av, at = variant_matrix(Mv, fm.ctx, variant), variant_matrix(Mt, fm.ctx, variant)
        selection = score_policies(av, at, fm.ctx, yv, yt, DEFAULT_BASE[regime])
        pt = resolve(at, fm.ctx, selection["chosen_validation_policy"])
        total = len(yt)
        row = {
            "rule_variant": variant,
            "regime": regime,
            "n_test": total,
            **{f"n_{k.lower()}": n for k, n in modes["count"].items()},
            "strict_nonempty_coverage": modes["strict_nonempty_coverage"],
            "effective_coverage_including_true": modes["effective_coverage_including_true"],
            "selected_policy_on_validation": selection["chosen_validation_policy"],
            "test_ba_validation_selected": selection["test_ba"][selection["chosen_validation_policy"]],
            "test_ba_fixed": selection["test_ba"][selection["fixed_policy"]],
            "delta_selected_minus_fixed": selection["test_ba_delta_from_fixed"],
            "oracle_policy_range_exploratory": selection["test_policy_range_oracle_only"],
        }
        for name, mask in modes["masks"].items():
            n = int(mask.sum())
            row[f"{name.lower()}_correct_of_n"] = (
                int(np.sum(pt[mask] == yt[mask])) if n else 0
            )
        # Explicitly expose true-only prediction vs majority fallback outcomes.
        for p in POLICIES:
            row[f"test_ba__{p}"] = selection["test_ba"][p]
        if sum(row[f"n_{k.lower()}"] for k in modes["count"]) != total:
            raise AssertionError("error taxonomy non-exhaustive")
        results.append(row)
    return results
