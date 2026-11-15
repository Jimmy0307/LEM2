"""Local (per-client) induction with full degeneracy diagnostics.

CLASSICAL mode delegates to the frozen originals:
    roughset.reduct.select_minimum_reduct  (exact minimum-cardinality POS reduct)
    roughset.pipeline.induce_lem2_on_reduct (LEM2; empty reduct -> TRUE -> d)

VPRS mode (P2 noise study, NOT called "improved LEM2"):
    beta-positive region (Ziarko 1993) for the reduct criterion and LEM2 run on
    beta-lower approximations (probabilistic-approximation LEM2 in the spirit of
    Grzymala-Busse).  With beta = 1 it coincides with CLASSICAL (tested).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from time import perf_counter
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from roughset.core import Rule, build_blocks, build_one_complex, remove_redundant_complexes
from roughset.pipeline import induce_lem2_on_reduct
from roughset.reduct import select_minimum_reduct

TINY_CLIENT_ROWS = 20


@dataclass
class LocalModel:
    client: str
    rows: int
    class_counts: Dict[str, int]
    reduct: Tuple[str, ...]
    reduct_candidates: int
    rules: Tuple[Rule, ...]
    reduct_seconds: float
    lem2_seconds: float
    pos_fraction_full: float
    pos_fraction_reduct: float
    extra: Dict[str, object] = field(default_factory=dict)

    @property
    def n_classes(self) -> int:
        return sum(1 for v in self.class_counts.values() if v > 0)

    @property
    def empty_rules(self) -> int:
        return sum(1 for r in self.rules if not r.conditions)


# --------------------------------------------------------- positive regions --

def _group_codes(df: pd.DataFrame, attrs: Sequence[str]) -> np.ndarray:
    if not attrs:
        return np.zeros(len(df), dtype=np.int64)
    return df.groupby(list(attrs), sort=False, dropna=False).ngroup().to_numpy()


def beta_positive_mask(df: pd.DataFrame, attrs: Sequence[str], target: str, beta: float) -> np.ndarray:
    """Objects whose elementary set E has max_k P(k | E) >= beta (beta=1: classical POS)."""
    g = _group_codes(df, attrs)
    y = pd.factorize(df[target].astype(str))[0]
    counts = np.zeros((g.max() + 1 if len(g) else 0, y.max() + 1 if len(y) else 0), dtype=float)
    np.add.at(counts, (g, y), 1.0)
    share = counts.max(axis=1) / np.maximum(counts.sum(axis=1), 1.0)
    ok = share >= beta - 1e-12
    return ok[g]


def beta_lower_masks(df: pd.DataFrame, attrs: Sequence[str], target: str, beta: float) -> Dict[str, np.ndarray]:
    """beta-lower approximation of every decision concept (beta > 0.5 -> disjoint)."""
    g = _group_codes(df, attrs)
    labels = df[target].astype(str).to_numpy()
    out = {}
    for d in pd.unique(labels):
        hit = labels == d
        num = np.bincount(g, weights=hit.astype(float))
        den = np.bincount(g).astype(float)
        out[str(d)] = (num / np.maximum(den, 1.0) >= beta - 1e-12)[g]
    return out


def beta_reduct(df: pd.DataFrame, features: Sequence[str], target: str, beta: float) -> Tuple[Tuple[str, ...], int]:
    full = int(beta_positive_mask(df, features, target, beta).sum())
    for size in range(0, len(features) + 1):
        found = sorted(tuple(sorted(c)) for c in itertools.combinations(features, size)
                       if int(beta_positive_mask(df, c, target, beta).sum()) == full)
        if found:
            return found[0], len(found)
    return tuple(features), 1


def induce_lem2_beta(df: pd.DataFrame, attrs: Sequence[str], target: str, beta: float, source: str) -> List[Rule]:
    data = df.reset_index(drop=True)
    if not attrs:
        lower = beta_lower_masks(data, (), target, beta)
        return [Rule(conditions=(), decision=d, source=source) for d, m in lower.items() if m.all() and len(data)]
    universe = set(data.index)
    blocks = build_blocks(data, list(attrs))
    rules: List[Rule] = []
    for decision, mask in beta_lower_masks(data, attrs, target, beta).items():
        B = set(np.flatnonzero(mask).tolist())
        if not B:
            continue
        complexes, covered = [], set()
        while covered != B:
            T, T_block = build_one_complex(B, B - covered, blocks, universe)
            complexes.append((T, T_block))
            covered |= T_block & B
        for T, _ in remove_redundant_complexes(complexes, B):
            rules.append(Rule(conditions=T, decision=decision, source=source))
    return rules


# ------------------------------------------------------------- per client --

def induce_client(name: str, df: pd.DataFrame, cond_cols: Sequence[str], target: str,
                  mode: str = "CLASSICAL", beta: float = 1.0) -> LocalModel:
    counts = {str(k): int(v) for k, v in df[target].astype(str).value_counts().items()}
    started = perf_counter()
    if mode == "CLASSICAL":
        sel = select_minimum_reduct(df, list(cond_cols), target)
        reduct, n_cand = tuple(sel.selected_reduct), sel.candidate_count
    elif mode == "VPRS":
        reduct, n_cand = beta_reduct(df, list(cond_cols), target, beta)
    else:
        raise ValueError(mode)
    t_reduct = perf_counter() - started
    started = perf_counter()
    if mode == "CLASSICAL":
        rules = tuple(induce_lem2_on_reduct(df, list(reduct), target, source=name))
    else:
        rules = tuple(induce_lem2_beta(df, list(reduct), target, beta, source=name))
    t_lem2 = perf_counter() - started
    pos_full = float(beta_positive_mask(df, cond_cols, target, 1.0).mean()) if len(df) else float("nan")
    pos_red = float(beta_positive_mask(df, reduct, target, 1.0).mean()) if len(df) else float("nan")
    return LocalModel(name, len(df), counts, reduct, n_cand, rules, t_reduct, t_lem2, pos_full, pos_red,
                      extra={"mode": mode, "beta": beta})


def induce_federation(clients: Mapping[str, pd.DataFrame], cond_cols: Sequence[str], target: str,
                      mode: str = "CLASSICAL", beta: float = 1.0) -> Dict[str, LocalModel]:
    return {name: induce_client(name, df, cond_cols, target, mode, beta) for name, df in clients.items()}


def union_rules(models: Mapping[str, LocalModel]) -> Tuple[Tuple[Rule, ...], Dict[object, Tuple[str, ...]]]:
    """UNION in client order keeping first copy; provenance keeps every producer."""
    merged, seen, sources = [], set(), {}
    for name, model in models.items():
        for rule in model.rules:
            sources.setdefault(rule.key, set()).add(name)
            if rule.key not in seen:
                seen.add(rule.key)
                merged.append(rule)
    return tuple(merged), {k: tuple(sorted(v)) for k, v in sources.items()}


def client_overlap(models: Mapping[str, LocalModel]) -> Dict[str, float]:
    """Mean pairwise Jaccard of antecedents and of full rules between clients."""
    names = list(models)
    ants, fulls = [], []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A = {tuple(sorted(r.conditions)) for r in models[a].rules}
            B = {tuple(sorted(r.conditions)) for r in models[b].rules}
            FA = {r.key for r in models[a].rules}
            FB = {r.key for r in models[b].rules}
            if A | B:
                ants.append(len(A & B) / len(A | B))
            if FA | FB:
                fulls.append(len(FA & FB) / len(FA | FB))
    return {
        "pairwise_antecedent_jaccard": float(np.mean(ants)) if ants else float("nan"),
        "pairwise_full_rule_jaccard": float(np.mean(fulls)) if fulls else float("nan"),
    }
