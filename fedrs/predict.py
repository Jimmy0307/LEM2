"""Vectorised rule matching and the six original resolution policies.

Semantics are copied from ``roughset.evaluation.predict_with_policy`` and
``roughset.pipeline.global_rule_support_context``:

* rule order = UNION order (client order, then local LEM2 order, first copy kept);
* STANDARD_VOTING weight w(r) = |Supp_G(r)| over ALL clients (antecedent AND decision);
* GLOBAL_STRENGTH / POPULATION_* use the pooled support sets Supp_G(r);
* only decisions with >= 1 matching rule receive a vote;
* ties: ``np.isclose(score, best)``; the default class wins a tie it is part of,
  otherwise the smallest decision by ``str`` order.

Parity is enforced by tests/test_fedrs_parity.py on real data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence

import numpy as np
import pandas as pd

from roughset.core import Rule

POLICIES = (
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
    "POPULATION_STANDARD",
    "POPULATION_GLOBAL",
)


def match_matrix(frame: pd.DataFrame, rules: Sequence[Rule]) -> np.ndarray:
    """Boolean (n_rows, n_rules): row satisfies the rule antecedent (string equality)."""
    n = len(frame)
    out = np.ones((n, len(rules)), dtype=bool)
    cache: Dict[str, np.ndarray] = {}
    for j, rule in enumerate(rules):
        for attr, value in rule.conditions:
            if attr not in cache:
                cache[attr] = frame[attr].astype(str).to_numpy()
            out[:, j] &= cache[attr] == str(value)
    return out


@dataclass
class RuleContext:
    rules: tuple
    decisions: np.ndarray          # str decision per rule
    classes: tuple                 # sorted (by str) distinct decisions among rules
    rule_class: np.ndarray         # index into classes per rule
    support: np.ndarray            # (R, N_train) bool: antecedent & decision on pooled clients
    weights: np.ndarray            # |Supp_G(r)|
    class_sizes: Mapping[str, int] # pooled training class sizes
    default_class: str
    is_empty: np.ndarray           # antecedent == TRUE

    @property
    def n_rules(self) -> int:
        return len(self.rules)


def build_context(rules: Sequence[Rule], pooled_train: pd.DataFrame, target: str,
                  default_class: str) -> RuleContext:
    rules = tuple(rules)
    decisions = np.asarray([str(r.decision) for r in rules], dtype=object)
    classes = tuple(sorted(set(decisions.tolist()), key=str))
    lookup = {c: i for i, c in enumerate(classes)}
    rule_class = np.asarray([lookup[d] for d in decisions], dtype=int)
    y = pooled_train[target].astype(str).to_numpy()
    # Populate the final, contiguous (rule, row) support matrix directly.
    # Building and then transposing a full (row, rule) match matrix requires
    # multiple additional train-by-rule allocations for large datasets.
    support = np.empty((len(rules), len(y)), dtype=bool)
    cache: Dict[str, np.ndarray] = {}
    for j, rule in enumerate(rules):
        support[j] = y == decisions[j]
        for attr, value in rule.conditions:
            if attr not in cache:
                cache[attr] = pooled_train[attr].astype(str).to_numpy()
            support[j] &= cache[attr] == str(value)
    sizes = pooled_train[target].astype(str).value_counts().to_dict()
    return RuleContext(
        rules=rules, decisions=decisions, classes=classes, rule_class=rule_class,
        support=support, weights=support.sum(axis=1).astype(float),
        class_sizes={str(k): int(v) for k, v in sizes.items()},
        default_class=str(default_class),
        is_empty=np.asarray([len(r.conditions) == 0 for r in rules], dtype=bool),
    )


def _decision_masks(M: np.ndarray, ctx: RuleContext) -> np.ndarray:
    """(n, K) bool: some matching rule predicts class k."""
    out = np.zeros((M.shape[0], len(ctx.classes)), dtype=bool)
    for k in range(len(ctx.classes)):
        cols = ctx.rule_class == k
        if cols.any():
            out[:, k] = M[:, cols].any(axis=1)
    return out


def _scores(M: np.ndarray, ctx: RuleContext, policy: str) -> np.ndarray:
    n, K = M.shape[0], len(ctx.classes)
    scores = np.zeros((n, K), dtype=float)
    Mi = M.astype(np.int32)
    for k, cls in enumerate(ctx.classes):
        cols = np.flatnonzero(ctx.rule_class == k)
        if cols.size == 0:
            continue
        if policy == "SIMPLE_VOTING":
            scores[:, k] = Mi[:, cols].sum(axis=1)
        elif policy == "STANDARD_VOTING":
            scores[:, k] = M[:, cols].astype(float) @ ctx.weights[cols]
        else:
            S = ctx.support[cols].astype(np.int32)
            union = (Mi[:, cols] @ S) > 0
            U = union.sum(axis=1).astype(float)
            N = float(ctx.class_sizes.get(cls, 0))
            if policy == "GLOBAL_STRENGTH":
                scores[:, k] = U / N if N > 0 else 0.0
            elif policy == "POPULATION_STANDARD":
                scores[:, k] = U
            elif policy == "POPULATION_GLOBAL":
                T = M[:, cols].astype(float) @ ctx.weights[cols]
                gs = U / N if N > 0 else np.zeros(n)
                ratio = np.divide(U, T, out=np.zeros(n), where=T > 0)
                scores[:, k] = gs * ratio
            else:
                raise ValueError(policy)
    return scores


def resolve(M: np.ndarray, ctx: RuleContext, policy: str) -> np.ndarray:
    policy = str(policy).strip().upper()
    n = M.shape[0]
    pred = np.full(n, ctx.default_class, dtype=object)
    if ctx.n_rules == 0 or n == 0:
        return pred
    hit = M.any(axis=1)
    if policy == "FIRST_MATCH":
        first = M.argmax(axis=1)
        pred[hit] = ctx.decisions[first[hit]]
        return pred
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy}")
    present = _decision_masks(M, ctx)
    scores = _scores(M, ctx, policy)
    masked = np.where(present, scores, -np.inf)
    best = masked.max(axis=1)
    tol = 1e-8 + 1e-5 * np.abs(np.where(np.isfinite(best), best, 0.0))
    winners = present & (np.abs(scores - best[:, None]) <= tol[:, None])
    classes = np.asarray(ctx.classes, dtype=object)
    default_idx = ctx.classes.index(ctx.default_class) if ctx.default_class in ctx.classes else -1
    first_winner = winners.argmax(axis=1)  # classes sorted by str -> smallest str winner
    out = classes[first_winner]
    if default_idx >= 0:
        out = np.where(winners[:, default_idx], ctx.default_class, out)
    pred[hit] = out[hit]
    return pred


def _resolve_support_chunked(M: np.ndarray, ctx: RuleContext, policy: str) -> np.ndarray:
    """Original support-union scores, summed over bounded training-row blocks."""
    n = M.shape[0]
    pred = np.full(n, ctx.default_class, dtype=object)
    hit = M.any(axis=1)
    present = _decision_masks(M, ctx)
    scores = np.zeros((n, len(ctx.classes)), dtype=float)
    n_train = ctx.support.shape[1]
    for k, cls in enumerate(ctx.classes):
        cols = np.flatnonzero(ctx.rule_class == k)
        active = np.flatnonzero(present[:, k])
        if cols.size == 0 or active.size == 0:
            continue
        total = _union_sizes(M[np.ix_(active, cols)], ctx, k)
        U = total.astype(float)
        N = float(ctx.class_sizes.get(cls, 0))
        if policy == "GLOBAL_STRENGTH":
            scores[active, k] = U / N if N > 0 else 0.0
        elif policy == "POPULATION_STANDARD":
            scores[active, k] = U
        elif policy == "POPULATION_GLOBAL":
            T = M[np.ix_(active, cols)].astype(float) @ ctx.weights[cols]
            gs = U / N if N > 0 else np.zeros(len(active))
            ratio = np.divide(U, T, out=np.zeros(len(active)), where=T > 0)
            scores[active, k] = gs * ratio
        else:
            raise ValueError(policy)
    masked = np.where(present, scores, -np.inf)
    best = masked.max(axis=1)
    tol = 1e-8 + 1e-5 * np.abs(np.where(np.isfinite(best), best, 0.0))
    winners = present & (np.abs(scores - best[:, None]) <= tol[:, None])
    classes = np.asarray(ctx.classes, dtype=object)
    default_idx = ctx.classes.index(ctx.default_class) if ctx.default_class in ctx.classes else -1
    out = classes[winners.argmax(axis=1)]
    if default_idx >= 0:
        out = np.where(winners[:, default_idx], ctx.default_class, out)
    pred[hit] = out[hit]
    return pred


# --------------------------------------- exact bitset support unions ------
# |union of Supp_G(r) over the matched class-k rules| per match pattern.
# Equivalent to ((lhs @ support) > 0).sum(axis=1) but touches only matched rules.

def _class_bitsets(ctx: RuleContext, k: int):
    cache = ctx.__dict__.setdefault("_bitset_cache", {})
    if k not in cache:
        cols = np.flatnonzero(ctx.rule_class == k)
        rows = np.flatnonzero(ctx.support[cols].any(axis=0))  # class-k rows covered by some rule
        n_words = max(1, -(-len(rows) // 64))
        bits = np.zeros((len(cols), n_words * 8), dtype=np.uint8)
        for start in range(0, len(cols), 256):  # bound the dense temporary
            stop = min(start + 256, len(cols))
            packed = np.packbits(ctx.support[cols[start:stop]][:, rows], axis=1)
            bits[start:stop, :packed.shape[1]] = packed
        cache[k] = bits.view(np.uint64)
    return cache[k]


def _union_sizes(lhs: np.ndarray, ctx: RuleContext, k: int) -> np.ndarray:
    bits = _class_bitsets(ctx, k)
    memo = ctx.__dict__.setdefault("_union_memo", {})
    out = np.empty(lhs.shape[0], dtype=np.int64)
    keys = np.packbits(lhs, axis=1)
    for i in range(lhs.shape[0]):
        key = (k, keys[i].tobytes())
        value = memo.get(key)
        if value is None:
            sel = np.flatnonzero(lhs[i])
            acc = np.bitwise_or.reduce(bits[sel], axis=0) if sel.size else np.zeros(bits.shape[1], np.uint64)
            value = int(np.bitwise_count(acc).sum())
            memo[key] = value
        out[i] = value
    return out


def resolve_scalable(M: np.ndarray, ctx: RuleContext, policy: str) -> np.ndarray:
    """Resolve distinct Boolean match patterns using bounded support blocks."""
    if M.shape[0] == 0 or ctx.n_rules == 0:
        return resolve(M, ctx, policy)
    policy = str(policy).strip().upper()
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy}")
    # Bit packing is lossless for a Boolean match matrix and avoids several
    # dense row-by-rule copies during np.unique on high-rule-count models.
    packed = np.packbits(M, axis=1)
    unique, inverse = np.unique(packed, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    predictions = np.empty(len(unique), dtype=object)
    support_policies = {"GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL"}
    for start in range(0, len(unique), 1000):
        end = min(start + 1000, len(unique))
        block = np.unpackbits(unique[start:end], axis=1, count=M.shape[1]).astype(bool)
        predictions[start:end] = (_resolve_support_chunked(block, ctx, policy) if policy in support_policies
                                  else resolve(block, ctx, policy))
    return predictions[inverse]


# ------------------------------------------------ rule-set variants ------

RULE_VARIANTS = ("A_ALL_RULES", "B_DROP_TRUE", "B2_TRUE_AS_FALLBACK")


def variant_matrix(M: np.ndarray, ctx: RuleContext, variant: str) -> np.ndarray:
    """Apply a merge/prediction-layer rule variant WITHOUT re-inducing rules.

    A_ALL_RULES          original UNION.
    B_DROP_TRUE          empty-antecedent (TRUE -> d) rules removed.
    B2_TRUE_AS_FALLBACK  TRUE rules only fire for rows no non-empty rule matches.
    """
    if variant == "A_ALL_RULES" or not ctx.is_empty.any():
        return M
    out = M.copy()
    if variant == "B_DROP_TRUE":
        out[:, ctx.is_empty] = False
        return out
    if variant == "B2_TRUE_AS_FALLBACK":
        has_specific = M[:, ~ctx.is_empty].any(axis=1)
        out[np.ix_(has_specific, ctx.is_empty)] = False
        return out
    raise ValueError(variant)


# ------------------------------------------------ candidate profile ------

def candidate_profile(M: np.ndarray, ctx: RuleContext, y_true: Sequence[str]) -> Dict[str, np.ndarray]:
    y = np.asarray([str(v) for v in y_true], dtype=object)
    present = _decision_masks(M, ctx) if ctx.n_rules else np.zeros((len(y), 0), dtype=bool)
    n_dec = present.sum(axis=1)
    lookup = {c: i for i, c in enumerate(ctx.classes)}
    truth_idx = np.asarray([lookup.get(v, -1) for v in y], dtype=int)
    truth_in = np.zeros(len(y), dtype=bool)
    ok = truth_idx >= 0
    truth_in[ok] = present[np.flatnonzero(ok), truth_idx[ok]]
    return {
        "n_matched_rules": M.sum(axis=1),
        "n_candidate_decisions": n_dec,
        "no_hit": n_dec == 0,
        "single": n_dec == 1,
        "multi": n_dec >= 2,
        "truth_in_candidates": truth_in,
    }
