"""Exploratory Train-only supplemental rule extension for federated LEM2.

Derived from historical teacher_demo supplementary pilot; its relaxed rules are
NOT original LEM2 exact rules. Only development/client labels are accessed for
candidate purity. Validation/Test labels NEVER enter candidate fitting.

The server observes aggregated counts, without secure aggregation or DP.
This is NOT privacy-preserving federated deployment; the goal is controlled
causal isolation of rule-coverage intervention vs B2 resolver intervention.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from .metrics import scores
from .predict import candidate_profile, match_matrix, resolve, variant_matrix


@dataclass(frozen=True)
class Supplement:
    conditions: tuple
    decision: str
    matching_dev: int
    correct_dev: int
    purity: float


def build_supplements(fm, *, min_support: int = 5, min_purity: float = .90,
                      cap: int = 200) -> list[Supplement]:
    """Only fixed DEVELOPMENT client tables determine relaxed rule candidates."""
    if min_support < 1 or not 0 < min_purity <= 1 or cap < 1:
        raise ValueError("Invalid train-only supplement thresholds")
    originals = {(tuple(sorted(r.conditions)), str(r.decision)) for r in fm.rules}
    proposals = set()
    for r in fm.rules:
        if len(r.conditions) < 2:
            continue
        for j in range(len(r.conditions)):
            sub = tuple(sorted(r.conditions[:j] + r.conditions[j+1:]))
            if sub and (sub, str(r.decision)) not in originals:
                proposals.add((sub, str(r.decision)))
    scored = []
    for cond, decision in sorted(proposals, key=str):
        total, correct = 0, 0
        for dev_client in fm.clients.values():
            matches = np.ones(len(dev_client), dtype=bool)
            for feature, value in cond:
                matches &= dev_client[feature].astype(str).to_numpy() == str(value)
            total += int(matches.sum())
            correct += int((dev_client.loc[matches, fm.target].astype(str) == decision).sum())
        if total >= min_support and correct/total >= min_purity:
            scored.append(Supplement(cond, decision, total, correct, correct/total))
    scored.sort(key=lambda x:(-x.purity,-x.correct_dev,-len(x.conditions),x.decision,str(x.conditions)))
    return scored[:cap]


def supplement_test(fm, *, min_support: int = 5, min_purity: float = .90,
                    base_policy: str = "SIMPLE_VOTING") -> dict:
    """Augment ONLY rows with no nonempty LEM2 antecedent matches.

    Baseline is B2(TRUE as fallback), not DROP_TRUE. This never changes
    original LEM2 rule predictions where some nonempty rule matches.
    """
    if base_policy not in ("FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING",
                           "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL"):
        raise ValueError("Not one of historical fixed policies")
    train_supp = build_supplements(fm, min_support=min_support, min_purity=min_purity)
    test = fm.frames["test"]
    y = test[fm.target].astype(str).to_numpy()
    M = match_matrix(test, fm.rules)
    base_M = variant_matrix(M, fm.ctx, "B2_TRUE_AS_FALLBACK")
    base_pred = resolve(base_M, fm.ctx, base_policy)
    base_profile = candidate_profile(base_M, fm.ctx, y)
    exact_nonempty = M[:, ~fm.ctx.is_empty].any(axis=1)
    rescued = np.zeros(len(test), dtype=bool)
    changed_pred = base_pred.copy()
    rescue_candidates = np.zeros(len(test),dtype=bool)
    if len(test):
        cache = {f: test[f].astype(str).to_numpy() for s in train_supp for f,_ in s.conditions}
        winners = {}
        for supp in train_supp:
            matches = ~exact_nonempty
            for f,val in supp.conditions:
                matches = matches & (cache[f] == str(val))
            for i in np.flatnonzero(matches):
                prev = winners.get(int(i), [])
                prev.append(supp)
                winners[int(i)] = prev
        for i, ls in winners.items():
            rescued[i] = True
            decisions = sorted({s.decision for s in ls})
            rescue_candidates[i] = str(y[i]) in decisions
            top = max((s.purity,s.correct_dev) for s in ls)
            dec = sorted({s.decision for s in ls if (s.purity,s.correct_dev) == top})
            default = fm.ctx.default_class
            changed_pred[i] = default if default in dec else dec[0]
    accepted = exact_nonempty | rescued
    if not (accepted | ~accepted).all():
        raise AssertionError("Non exhaustive accepted partition")
    changed_on_exact = np.any(changed_pred[exact_nonempty] != base_pred[exact_nonempty])
    if changed_on_exact:
        raise AssertionError("Supplement changed original nonempty LEM2 predictions")
    b = scores(y, base_pred)
    after = scores(y, changed_pred)
    true_candidates_after = base_profile["truth_in_candidates"].copy()
    true_candidates_after[rescued] |= rescue_candidates[rescued]
    return {
        "n": len(test), "n_supplements": len(train_supp), "min_purity": min_purity,
        "min_support": min_support, "policy": base_policy,
        "strict_nonempty_coverage": float(exact_nonempty.mean()) if len(test) else float("nan"),
        "augmented_strict_coverage": float(accepted.mean()) if len(test) else float("nan"),
        "supplement_rescued": int(rescued.sum()),
        "supplement_correct": int((changed_pred[rescued] == y[rescued]).sum()),
        "baseline_correct_on_rescued": int((base_pred[rescued] == y[rescued]).sum()),
        "baseline_true_in_candidates": float(base_profile["truth_in_candidates"].mean()) if len(y) else float("nan"),
        "augmented_truth_in_candidates": float(true_candidates_after.mean()) if len(y) else float("nan"),
        "explicit_abstain_if_not_accepted": float((~accepted).mean()) if len(test) else float("nan"),
        "accepted_only_accuracy": float((changed_pred[accepted] == y[accepted]).mean()) if accepted.any() else float("nan"),
        "baseline_test_ba": b["ba"], "supplement_test_ba": after["ba"],
        "test_ba_gain_pp": 100*(after["ba"] - b["ba"]),
        "test_accuracy_gain_pp": 100*(after["accuracy"] - b["accuracy"]),
        "test_macro_f1_gain_pp": 100*(after["macro_f1"] - b["macro_f1"]),
    }
