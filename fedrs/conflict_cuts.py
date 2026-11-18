"""P4 prototypes: conflict-aware cut selection (RESEARCH PROTOTYPES, not validated).

Framework (candidate, not a settled definition):
    min_P  l1*L_decision(P) + l2*C_global(P) + l3*K_rules(P) + l4*T_compute(P)

Design 1 — FCP_HIST (Federated Conflict-Penalised cuts, one round, histograms):
    per feature f, greedy over a shared 32-cell grid,
    J_f(P) = H(D | I_P)/log2 K  +  l2 * Chat_f(P)  +  l3 * |P|
    Chat_f(P) = (1/N) sum_I sum_c n_c(I) * 1[c locally pure in I and another client is
                locally pure in I with a different class]
    -> a univariate proxy for "locally certain, globally contradictory" 1-condition rules.
    Needs PER-CLIENT class histograms (not only their sum): NOT compatible with plain
    secure aggregation; leaks per-client purity.  Cost O(F * G^2 * C * K) per greedy step.

Design 2 — LOCO_SELECT (leave-one-client-out rule feedback over candidate cut sets):
    for each candidate P in a federated-feasible pool, every client induces Classical
    reduct+LEM2 rules; client c then scores rules of all OTHER clients on its own
    development rows (base policy SIMPLE_VOTING, TRUE rules handled by ``variant``) and
    returns a K x K confusion matrix plus conflict / no-hit counts.
        J(P) = (1 - BA_LOCO) + l2 * Conflict_LOCO + l3 * log2(1+|R|)/log2(1+N)
    Uses NO validation or test data.  Communication per candidate: rules up/down
    (O(|R| * L)) + K^2 + 2 integers per client.

All lambdas are fixed a priori in this file; they were NOT tuned on any Test split.
"""
from __future__ import annotations

from time import perf_counter
from typing import Dict, Mapping, Sequence

import numpy as np
import pandas as pd

from . import discretize as dz
from .induce import induce_federation, union_rules
from .metrics import balanced_accuracy
from .predict import build_context, candidate_profile, match_matrix, resolve, variant_matrix

FCP_LAMBDA_CONFLICT = 1.0
FCP_LAMBDA_CUT = 0.01
LOCO_LAMBDA_CONFLICT = 0.25
LOCO_LAMBDA_RULES = 0.05
LOCO_POOL = ("EQUAL_WIDTH_3", "EQUAL_WIDTH_5", "EF_HIST_3", "EF_HIST_5", "MDLP_HIST", "FCP_HIST", "FED_MD_HIST")


# ------------------------------------------------------------ EF via histogram

def fit_ef_hist(clients, continuous, target, n_bins, grid=dz.HIST_GRID * 4):
    """Approximate equal-frequency cuts from SUMMED per-client histograms (federated-feasible)."""
    started = perf_counter()
    cuts, labels = {}, {}
    for f in continuous:
        lo, hi = dz._global_range(clients, f)
        if np.isclose(lo, hi):
            cuts[f], labels[f] = (), ("Constant",)
            continue
        edges = np.linspace(lo, hi, grid + 1)
        inner = edges[1:-1]
        total = np.zeros(grid)
        for df in clients.values():
            cell = np.searchsorted(inner, pd.to_numeric(df[f]).to_numpy(float), side="left")
            total += np.bincount(cell, minlength=grid)
        cdf = np.cumsum(total) / total.sum()
        c = [inner[min(int(np.searchsorted(cdf, q)), grid - 2)] for q in np.linspace(0, 1, n_bins + 1)[1:-1]]
        cuts[f] = dz._clean_cuts(c, lo, hi)
        labels[f] = dz._canonical_labels(len(cuts[f]) + 1, original_style=False)
    return dz.CutModel(f"EF_HIST_{n_bins}", cuts, labels, perf_counter() - started, uses_labels=False,
                       uses_pooled_raw_values=False, federated_note="summed per-client histograms (128 cells)",
                       communication_numbers_per_client=len(continuous) * (2 + grid))


# ------------------------------------------------------------------- FCP_HIST

def _purity_conflict(per_client_intervals: Sequence[np.ndarray]) -> float:
    """per_client_intervals[c] : (n_intervals, K) counts. Returns disagreement mass."""
    stack = np.stack(per_client_intervals)            # (C, I, K)
    n = stack.sum(axis=2)                               # (C, I)
    present = (stack > 0).sum(axis=2)                   # (C, I)
    pure = (n > 0) & (present == 1)
    cls = stack.argmax(axis=2)
    mass = 0.0
    for i in range(stack.shape[1]):
        pc = np.flatnonzero(pure[:, i])
        if len(pc) < 2:
            continue
        labels = cls[pc, i]
        for c, lab in zip(pc, labels):
            if (labels != lab).any():
                mass += n[c, i]
    return float(mass)


def _intervals(mat: np.ndarray, cut_idx: Sequence[int]) -> np.ndarray:
    bounds = [0, *sorted(cut_idx), mat.shape[0]]
    return np.stack([mat[a:b].sum(axis=0) for a, b in zip(bounds[:-1], bounds[1:])])


def fcp_objective(per_client: Mapping[str, np.ndarray], cut_idx: Sequence[int], lam_conflict: float) -> float:
    total = sum(per_client.values())
    N = total.sum()
    K = max(int((total.sum(axis=0) > 0).sum()), 2)
    agg = _intervals(total, cut_idx)
    h = sum(row.sum() / N * dz._entropy(row) for row in agg) / np.log2(K)
    conflict = _purity_conflict([_intervals(m, cut_idx) for m in per_client.values()]) / N
    return h + lam_conflict * conflict


def fit_fcp_hist(clients, continuous, target, lam_conflict=FCP_LAMBDA_CONFLICT, lam_cut=FCP_LAMBDA_CUT,
                 max_cuts=dz.MAX_INTERVALS - 1):
    started = perf_counter()
    classes = sorted(set(dz._labels_pooled(clients, target).tolist()), key=str)
    cuts, labels, trace = {}, {}, {}
    for f in continuous:
        lo, hi, inner, per_client = dz.client_histograms(clients, f, target, classes)
        if inner is None:
            cuts[f], labels[f] = (), ("Constant",)
            continue
        chosen: list = []
        current = fcp_objective(per_client, chosen, lam_conflict)
        while len(chosen) < max_cuts:
            best = None
            for b in range(1, len(inner) + 1):
                if b in chosen:
                    continue
                val = fcp_objective(per_client, chosen + [b], lam_conflict)
                if best is None or val < best[0] - 1e-12:
                    best = (val, b)
            if best is None or current - best[0] <= lam_cut:
                break
            chosen.append(best[1])
            current = best[0]
        trace[f] = current
        cuts[f] = dz._clean_cuts([inner[b - 1] for b in chosen], lo, hi)
        labels[f] = dz._canonical_labels(len(cuts[f]) + 1, original_style=False)
    return dz.CutModel(f"FCP_HIST_L{lam_conflict:g}", cuts, labels, perf_counter() - started, uses_labels=True,
                       uses_pooled_raw_values=False,
                       federated_note="PER-CLIENT class histograms (32 cells); not secure-aggregation compatible",
                       communication_numbers_per_client=len(continuous) * (2 + dz.HIST_GRID * len(classes)),
                       extra={"objective": trace})


# ---------------------------------------------------------------- LOCO_SELECT

def candidate_cut_model(name, clients, continuous, target, categorical):
    if name.startswith("EF_HIST_"):
        return fit_ef_hist(clients, continuous, target, int(name.rsplit("_", 1)[1]))
    if name == "FCP_HIST":
        return fit_fcp_hist(clients, continuous, target)
    if name == "FED_MD_HIST":
        return fit_fed_md(clients, continuous, target, categorical, mu_within=1.0)
    return dz.fit_method(name, clients, continuous, target, categorical)


def loco_score(raw_clients: Mapping[str, pd.DataFrame], cut_model: dz.CutModel, features, continuous, categorical,
               target: str, variant: str = "B_DROP_TRUE", policy: str = "SIMPLE_VOTING") -> Dict[str, float]:
    cond = dz.condition_columns(features, continuous)
    clients = {k: dz.apply_cuts(v, cut_model, target, categorical) for k, v in raw_clients.items()}
    local = induce_federation(clients, cond, target)
    all_rules, _ = union_rules(local)
    y_all, p_all, conflict, nohit, n = [], [], 0, 0, 0
    for held in clients:
        others = {k: m for k, m in local.items() if k != held}
        rules, _ = union_rules(others)
        frame = clients[held]
        y = frame[target].astype(str).to_numpy()
        pooled = pd.concat([clients[k] for k in others], ignore_index=True)
        from roughset.evaluation import majority_class_from_clients
        ctx = build_context(rules, pooled, target, majority_class_from_clients({k: clients[k] for k in others}, target))
        M = variant_matrix(match_matrix(frame, rules), ctx, variant) if rules else np.zeros((len(frame), 0), bool)
        pred = resolve(M, ctx, policy)
        prof = candidate_profile(M, ctx, y)
        y_all.extend(y.tolist()); p_all.extend(pred.tolist())
        conflict += int(prof["multi"].sum()); nohit += int(prof["no_hit"].sum()); n += len(y)
    ba = balanced_accuracy(y_all, p_all)
    k_rules = np.log2(1 + len(all_rules)) / np.log2(1 + n)
    return {"loco_ba": ba, "loco_conflict": conflict / n, "loco_no_hit": nohit / n, "rules": len(all_rules),
            "k_rules": float(k_rules)}


def fit_loco_select(clients, continuous, target, categorical, features, lam_conflict=LOCO_LAMBDA_CONFLICT,
                    lam_rules=LOCO_LAMBDA_RULES, pool=LOCO_POOL, variant="B_DROP_TRUE"):
    started = perf_counter()
    table = []
    models = {}
    for name in pool:
        cm = candidate_cut_model(name, clients, list(continuous), target, list(categorical))
        sc = loco_score(clients, cm, features, continuous, categorical, target, variant)
        J = (1 - sc["loco_ba"]) + lam_conflict * sc["loco_conflict"] + lam_rules * sc["k_rules"]
        total_cuts = sum(len(c) for c in cm.cuts.values())
        table.append({"candidate": name, "J": J, "total_cuts": total_cuts, **sc})
        models[name] = cm
    best = min(table, key=lambda r: (round(r["J"], 10), r["total_cuts"], pool.index(r["candidate"])))
    chosen = models[best["candidate"]]
    return dz.CutModel(f"LOCO_SELECT_L{lam_conflict:g}_R{lam_rules:g}", chosen.cuts, chosen.labels,
                       perf_counter() - started, uses_labels=True,
                       uses_pooled_raw_values=False,
                       federated_note="per-candidate rule exchange + LOCO confusion counts; candidates histogram/min-max only",
                       communication_numbers_per_client=sum(models[n].communication_numbers_per_client for n in pool),
                       extra={"chosen": best["candidate"], "table": table})


# ------------------------------------------------- Design 3: FED_MD (federated MD)

def _pairs_by_cell(cell: np.ndarray, y: np.ndarray, k: int) -> float:
    if cell.size == 0:
        return 0.0
    _, inv = np.unique(cell, return_inverse=True)
    counts = np.zeros((inv.max() + 1, k), dtype=float)
    np.add.at(counts, (inv, y), 1.0)
    n = counts.sum(axis=1)
    return float(((n ** 2 - (counts ** 2).sum(axis=1)) / 2.0).sum())


def fit_fed_md(clients, continuous, target, categorical=(), mu_within=1.0, grid=dz.HIST_GRID,
               max_intervals=dz.MAX_INTERVALS):
    """Federated Nguyen-Skowron MD heuristic on a shared grid, cross-client aware.

    For a cut set P, let W(P) be the number of object pairs with different decisions
    that P (together with the categorical attributes) cannot discern, over the POOLED
    development data.  W = W_within + W_cross, where W_within = sum_c W_c is the local
    count of client c.  Both terms need only SUM-aggregatable quantities: per-cell class
    counts summed over clients (-> W) and one scalar per client (-> W_within).
    Greedy step: add the grid cut minimising  W_cross + mu * W_within.
    mu = 1 reproduces the pooled MD heuristic restricted to grid candidates;
    mu < 1 prioritises CROSS-client indiscernible conflicts, i.e. exactly the pairs that
    make locally certain rules globally contradictory.
    """
    started = perf_counter()
    names = list(clients)
    pooled = pd.concat([clients[n] for n in names], ignore_index=True)
    owner = np.concatenate([np.full(len(clients[n]), i) for i, n in enumerate(names)])
    y, classes = dz._class_index(pooled[target].astype(str).to_numpy())
    k = len(classes)
    cell = np.zeros(len(pooled), dtype=np.int64)
    for c in categorical:
        codes = pd.factorize(pooled[c].astype(str))[0]
        # re-factorise after each attribute: product codes cannot overflow int64
        cell = pd.factorize(cell * (codes.max() + 1) + codes)[0].astype(np.int64)
    X, inner, ranges = {}, {}, {}
    for f in continuous:
        lo, hi = dz._global_range(clients, f)
        ranges[f] = (lo, hi)
        X[f] = pd.to_numeric(pooled[f]).to_numpy(dtype=float)
        inner[f] = list(np.linspace(lo, hi, grid + 1)[1:-1]) if hi > lo else []

    def score(cells):
        total = _pairs_by_cell(cells, y, k)
        within = sum(_pairs_by_cell(cells[owner == i], y[owner == i], k) for i in range(len(names)))
        return (total - within) + mu_within * within, total, within

    chosen = {f: [] for f in continuous}
    current, total, within = score(cell)
    rounds, evaluated = 0, 0
    while current > 0:
        best = None
        for fi, f in enumerate(continuous):
            if len(chosen[f]) >= max_intervals - 1:
                continue
            for c in inner[f]:
                if c in chosen[f]:
                    continue
                trial = cell * 2 + (X[f] > c)
                val = score(trial)
                evaluated += 1
                key = (val[0], fi, c)
                if best is None or key < best[0]:
                    best = (key, f, c, trial, val)
        if best is None or best[0][0] >= current - 1e-9:
            break
        _, f, c, trial, val = best
        chosen[f].append(c)
        cell = pd.factorize(trial)[0].astype(np.int64)
        current, total, within = val
        rounds += 1
    cuts, labels = {}, {}
    for f in continuous:
        lo, hi = ranges[f]
        cuts[f] = dz._clean_cuts(chosen[f], lo, hi)
        labels[f] = dz._canonical_labels(len(cuts[f]) + 1, original_style=False) if hi > lo else ("Constant",)
    n_cells = int(len(np.unique(cell)))
    return dz.CutModel(f"FED_MD_MU{mu_within:g}", cuts, labels, perf_counter() - started, uses_labels=True,
                       uses_pooled_raw_values=False,
                       federated_note="summed per-cell class counts + per-client scalar within-pair counts on shared grid; "
                                      "cell-level contingency counts are revealed to the aggregator (no secure aggregation/DP claimed)",
                       communication_numbers_per_client=int(evaluated * max(n_cells, 1) * 2 * k),
                       extra={"rounds": rounds, "candidates_evaluated": evaluated, "final_cells": n_cells,
                              "remaining_cross_pairs": total - within, "remaining_within_pairs": within})


# ------------------------------------------------------------------ registry

P4_METHODS = ("EF_HIST_3", "EF_HIST_5", "FCP_HIST", "FCP_HIST_NOCONFLICT", "FED_MD_HIST", "FED_MD_XC",
              "LOCO_SELECT", "LOCO_SELECT_NOCONFLICT", "LOCO_SELECT_NORULES", "LOCO_SELECT_KEEP_TRUE")


def make_discretizer(name: str, features: Sequence[str]):
    """Return a fit callable (clients, continuous, target, categorical) -> CutModel, or the name itself."""
    feats = list(features)
    if name.startswith("EF_HIST_"):
        k = int(name.rsplit("_", 1)[1])
        return lambda cl, cont, t, cat: fit_ef_hist(cl, cont, t, k)
    if name == "FCP_HIST":
        return lambda cl, cont, t, cat: fit_fcp_hist(cl, cont, t)
    if name == "FCP_HIST_NOCONFLICT":
        return lambda cl, cont, t, cat: fit_fcp_hist(cl, cont, t, lam_conflict=0.0)
    if name == "FED_MD_HIST":
        return lambda cl, cont, t, cat: fit_fed_md(cl, cont, t, cat, mu_within=1.0)
    if name == "FED_MD_XC":
        return lambda cl, cont, t, cat: fit_fed_md(cl, cont, t, cat, mu_within=0.25)
    if name == "LOCO_SELECT":
        return lambda cl, cont, t, cat: fit_loco_select(cl, cont, t, cat, feats)
    if name == "LOCO_SELECT_NOCONFLICT":
        return lambda cl, cont, t, cat: fit_loco_select(cl, cont, t, cat, feats, lam_conflict=0.0)
    if name == "LOCO_SELECT_NORULES":
        return lambda cl, cont, t, cat: fit_loco_select(cl, cont, t, cat, feats, lam_rules=0.0)
    if name == "LOCO_SELECT_KEEP_TRUE":
        return lambda cl, cont, t, cat: fit_loco_select(cl, cont, t, cat, feats, variant="A_ALL_RULES")
    return name
