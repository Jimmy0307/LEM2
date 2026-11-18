"""Cut-point discretizers fitted on DEVELOPMENT client data only.

Every discretizer returns a :class:`CutModel` whose cuts are interior cut
points.  A value ``v`` falls into interval ``i`` = number of cuts strictly
smaller than ``v`` (right-closed intervals), which reproduces
``pandas.cut(..., right=True, include_lowest=True)`` used by the original
``roughset.preprocessing`` equal-width binning exactly.

Federated feasibility is recorded per method and must not be over-read:

* ``uses_pooled_raw_values=True``  -> CENTRAL REFERENCE ONLY (needs raw values
  or an un-modelled private quantile protocol).
* histogram methods only need per-client per-class histogram counts on a shared
  grid.  Plain histogram summation is *not* secure aggregation or differential
  privacy; no such guarantee is claimed.

No Validation or Test value or label is ever passed to a fit function.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Dict, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import chi2

HIST_GRID = 32          # shared equal-width grid for histogram methods
MAX_INTERVALS = 6       # cap for supervised methods (keeps exact reduct tractable)
CHIMERGE_SIGNIFICANCE = 0.95
RS_MD_CANDIDATES = 64


@dataclass(frozen=True)
class CutModel:
    method: str
    cuts: Mapping[str, Tuple[float, ...]]
    labels: Mapping[str, Tuple[str, ...]]
    fit_seconds: float
    uses_labels: bool
    uses_pooled_raw_values: bool
    federated_note: str
    communication_numbers_per_client: int
    extra: Mapping[str, object] = field(default_factory=dict)

    def effective_intervals(self) -> Dict[str, int]:
        return {f: len(lbl) for f, lbl in self.labels.items()}


# ---------------------------------------------------------------- helpers ---

def _values(clients: Mapping[str, pd.DataFrame], feature: str) -> np.ndarray:
    arrays = [pd.to_numeric(df[feature], errors="raise").to_numpy(dtype=float) for df in clients.values()]
    out = np.concatenate(arrays) if arrays else np.array([], dtype=float)
    if out.size == 0 or not np.isfinite(out).all():
        raise ValueError(f"Missing or non-finite numeric values in feature {feature!r}")
    return out


def _labels_pooled(clients: Mapping[str, pd.DataFrame], target: str) -> np.ndarray:
    return np.concatenate([df[target].astype(str).to_numpy() for df in clients.values()])


def _global_range(clients: Mapping[str, pd.DataFrame], feature: str) -> Tuple[float, float]:
    lo = min(float(pd.to_numeric(df[feature]).min()) for df in clients.values())
    hi = max(float(pd.to_numeric(df[feature]).max()) for df in clients.values())
    return lo, hi


def _canonical_labels(n_intervals: int, original_style: bool) -> Tuple[str, ...]:
    if n_intervals <= 1:
        return ("Constant",)
    if original_style:
        if n_intervals == 3:
            return ("Low", "Medium", "High")
        return tuple(f"Bin_{i}" for i in range(1, n_intervals + 1))
    return tuple(f"B{i}" for i in range(1, n_intervals + 1))


def _clean_cuts(cuts: Sequence[float], lo: float, hi: float) -> Tuple[float, ...]:
    arr = np.unique(np.asarray([c for c in cuts if lo < c < hi], dtype=float))
    return tuple(float(x) for x in arr)


def apply_cuts(df: pd.DataFrame, model: CutModel, target: str, categorical: Sequence[str]) -> pd.DataFrame:
    """Return a discretized copy: continuous ``f`` -> ``f_bin``; categorical -> stripped str."""
    out = df.copy()
    for feature in categorical:
        out[feature] = out[feature].astype(str).str.strip()
    for feature, cuts in model.cuts.items():
        values = pd.to_numeric(out[feature], errors="raise").to_numpy(dtype=float)
        labels = np.asarray(model.labels[feature], dtype=object)
        if len(cuts) == 0:
            out[f"{feature}_bin"] = labels[0]
        else:
            idx = np.searchsorted(np.asarray(cuts, dtype=float), values, side="left")
            out[f"{feature}_bin"] = labels[idx]
    out[target] = out[target].astype(str).str.strip()
    return out


def condition_columns(features: Sequence[str], continuous: Sequence[str]) -> list:
    cont = set(continuous)
    return [f"{f}_bin" if f in cont else f for f in features]


# ------------------------------------------------------- unsupervised -----

def fit_equal_width(clients, continuous, target, n_bins):
    started = perf_counter()
    cuts, labels = {}, {}
    for f in continuous:
        lo, hi = _global_range(clients, f)
        if np.isclose(lo, hi):
            cuts[f], labels[f] = (), ("Constant",)
            continue
        edges = np.linspace(lo, hi, n_bins + 1)
        cuts[f] = tuple(float(x) for x in edges[1:-1])
        labels[f] = _canonical_labels(n_bins, original_style=True)
    return CutModel(f"EQUAL_WIDTH_{n_bins}", cuts, labels, perf_counter() - started,
                    uses_labels=False, uses_pooled_raw_values=False,
                    federated_note="per-client min/max only",
                    communication_numbers_per_client=2 * len(continuous))


def fit_equal_frequency(clients, continuous, target, n_bins):
    started = perf_counter()
    cuts, labels = {}, {}
    for f in continuous:
        values = _values(clients, f)
        lo, hi = float(values.min()), float(values.max())
        if np.isclose(lo, hi):
            cuts[f], labels[f] = (), ("Constant",)
            continue
        q = np.quantile(values, np.linspace(0, 1, n_bins + 1))[1:-1]
        cuts[f] = _clean_cuts(q, lo, hi)
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False)
    return CutModel(f"EQUAL_FREQUENCY_{n_bins}", cuts, labels, perf_counter() - started,
                    uses_labels=False, uses_pooled_raw_values=True,
                    federated_note="CENTRAL REFERENCE: pooled quantiles",
                    communication_numbers_per_client=0)


def fit_robust_width(clients, continuous, target, n_bins=3):
    started = perf_counter()
    cuts, labels = {}, {}
    for f in continuous:
        values = _values(clients, f)
        lo, hi = float(values.min()), float(values.max())
        if np.isclose(lo, hi):
            cuts[f], labels[f] = (), ("Constant",)
            continue
        qlo, qhi = np.quantile(values, [0.01, 0.99])
        if np.isclose(qlo, qhi):
            qlo, qhi = lo, hi
        edges = np.linspace(float(qlo), float(qhi), n_bins + 1)
        cuts[f] = _clean_cuts(edges[1:-1], lo, hi)
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False)
    return CutModel(f"ROBUST_WIDTH_{n_bins}", cuts, labels, perf_counter() - started,
                    uses_labels=False, uses_pooled_raw_values=True,
                    federated_note="CENTRAL REFERENCE: pooled 1st/99th percentiles",
                    communication_numbers_per_client=0)


# ------------------------------------------------------------- MDLP -------

def _entropy(counts: np.ndarray) -> float:
    total = counts.sum()
    if total <= 0:
        return 0.0
    p = counts[counts > 0] / total
    return float(-(p * np.log2(p)).sum())


def mdlp_cut_indices(count_matrix: np.ndarray, max_cuts: int = MAX_INTERVALS - 1) -> list:
    """Fayyad & Irani (1993) recursive MDLP on ordered points with class counts.

    ``count_matrix[j, k]`` = #objects of class k at ordered position j.
    Returns sorted split indices s meaning "cut between position s-1 and s".
    """
    accepted: list = []

    def recurse(a: int, b: int, depth: int) -> None:
        if b - a < 2 or depth > 12:
            return
        block = count_matrix[a:b]
        total = block.sum(axis=0)
        n = float(total.sum())
        if n < 2 or (total > 0).sum() < 2:
            return
        ent = _entropy(total)
        left = np.cumsum(block, axis=0)[:-1]
        right = total - left
        nl, nr = left.sum(axis=1), right.sum(axis=1)
        valid = (nl > 0) & (nr > 0)
        if not valid.any():
            return
        best, best_s, best_e1, best_e2 = None, None, 0.0, 0.0
        for j in np.flatnonzero(valid):
            e1, e2 = _entropy(left[j]), _entropy(right[j])
            w = (nl[j] * e1 + nr[j] * e2) / n
            if best is None or w < best - 1e-12:
                best, best_s, best_e1, best_e2 = w, j + 1, e1, e2
        gain = ent - best
        k = int((total > 0).sum())
        k1 = int((left[best_s - 1] > 0).sum())
        k2 = int((right[best_s - 1] > 0).sum())
        delta = np.log2(3 ** k - 2) - (k * ent - k1 * best_e1 - k2 * best_e2)
        threshold = (np.log2(n - 1) + delta) / n
        if gain > threshold:
            accepted.append(a + best_s)
            recurse(a, a + best_s, depth + 1)
            recurse(a + best_s, b, depth + 1)

    recurse(0, count_matrix.shape[0], 0)
    accepted = sorted(set(accepted))
    if len(accepted) > max_cuts:
        # keep the earliest-accepted (largest information) cuts deterministically:
        # re-rank by entropy reduction of single cut
        scores = []
        total = count_matrix.sum(axis=0)
        n = total.sum()
        for s in accepted:
            left = count_matrix[:s].sum(axis=0)
            right = total - left
            scores.append((_entropy(total) - (left.sum() * _entropy(left) + right.sum() * _entropy(right)) / n, -s, s))
        accepted = sorted(s for *_, s in sorted(scores, reverse=True)[:max_cuts])
    return accepted


def _class_index(labels: np.ndarray) -> Tuple[np.ndarray, list]:
    classes = sorted(set(labels.tolist()), key=str)
    lookup = {c: i for i, c in enumerate(classes)}
    return np.asarray([lookup[x] for x in labels], dtype=int), classes


def _point_counts(values: np.ndarray, y_idx: np.ndarray, n_classes: int):
    uniq, inv = np.unique(values, return_inverse=True)
    mat = np.zeros((len(uniq), n_classes), dtype=float)
    np.add.at(mat, (inv, y_idx), 1.0)
    return uniq, mat


def fit_mdlp_central(clients, continuous, target):
    started = perf_counter()
    y, classes = _class_index(_labels_pooled(clients, target))
    cuts, labels = {}, {}
    for f in continuous:
        values = _values(clients, f)
        uniq, mat = _point_counts(values, y, len(classes))
        idx = mdlp_cut_indices(mat)
        c = [(uniq[s - 1] + uniq[s]) / 2.0 for s in idx]
        cuts[f] = _clean_cuts(c, float(uniq[0]), float(uniq[-1]))
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False)
    return CutModel("MDLP_CENTRAL", cuts, labels, perf_counter() - started,
                    uses_labels=True, uses_pooled_raw_values=True,
                    federated_note="CENTRAL REFERENCE: pooled raw values and labels",
                    communication_numbers_per_client=0)


def client_histograms(clients, feature, target, classes, grid=HIST_GRID):
    """Per-client per-class counts on a shared equal-width grid (needs global min/max)."""
    lo, hi = _global_range(clients, feature)
    if np.isclose(lo, hi):
        return lo, hi, None, {}
    edges = np.linspace(lo, hi, grid + 1)
    inner = edges[1:-1]
    lookup = {c: i for i, c in enumerate(classes)}
    per_client = {}
    for name, df in clients.items():
        v = pd.to_numeric(df[feature]).to_numpy(dtype=float)
        cell = np.searchsorted(inner, v, side="left")
        yy = np.asarray([lookup[x] for x in df[target].astype(str)], dtype=int)
        mat = np.zeros((grid, len(classes)), dtype=float)
        np.add.at(mat, (cell, yy), 1.0)
        per_client[name] = mat
    return lo, hi, inner, per_client


def fit_mdlp_histogram(clients, continuous, target, grid=HIST_GRID):
    started = perf_counter()
    classes = sorted(set(_labels_pooled(clients, target).tolist()), key=str)
    cuts, labels = {}, {}
    for f in continuous:
        lo, hi, inner, per_client = client_histograms(clients, f, target, classes, grid)
        if inner is None:
            cuts[f], labels[f] = (), ("Constant",)
            continue
        total = sum(per_client.values())
        idx = mdlp_cut_indices(total)
        cuts[f] = _clean_cuts([inner[s - 1] for s in idx], lo, hi)
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False)
    return CutModel("MDLP_HIST", cuts, labels, perf_counter() - started,
                    uses_labels=True, uses_pooled_raw_values=False,
                    federated_note="summed per-client class histograms on shared 32-cell grid; no secure aggregation/DP claimed",
                    communication_numbers_per_client=len(continuous) * (2 + grid * len(classes)))


# ---------------------------------------------------------- ChiMerge ------

def chimerge_boundaries(mat: np.ndarray, significance: float = CHIMERGE_SIGNIFICANCE,
                        max_intervals: int = MAX_INTERVALS) -> list:
    """Kerber (1992) ChiMerge on ordered initial intervals; returns kept boundary indices."""
    rows = [r.copy() for r in mat if r.sum() > 0]
    starts = [i for i, r in enumerate(mat) if r.sum() > 0]
    if len(rows) <= 1:
        return []
    k = mat.shape[1]
    threshold = chi2.ppf(significance, df=max(k - 1, 1))

    def pair_chi(a, b):
        table = np.vstack([a, b])
        col = table.sum(axis=0)
        keep = col > 0
        table, col = table[:, keep], col[keep]
        rsum = table.sum(axis=1, keepdims=True)
        exp = rsum * col / table.sum()
        exp = np.where(exp == 0, 0.1, exp)
        return float(((table - exp) ** 2 / exp).sum())

    chis = [pair_chi(rows[i], rows[i + 1]) for i in range(len(rows) - 1)]
    while len(rows) > 1:
        j = int(np.argmin(chis))
        if chis[j] >= threshold and len(rows) <= max_intervals:
            break
        rows[j] = rows[j] + rows[j + 1]
        del rows[j + 1], starts[j + 1], chis[j]
        if j < len(chis):
            chis[j] = pair_chi(rows[j], rows[j + 1])
        if j - 1 >= 0:
            chis[j - 1] = pair_chi(rows[j - 1], rows[j])
    return starts[1:]


def fit_chimerge_central(clients, continuous, target):
    started = perf_counter()
    y, classes = _class_index(_labels_pooled(clients, target))
    cuts, labels = {}, {}
    for f in continuous:
        uniq, mat = _point_counts(_values(clients, f), y, len(classes))
        starts = chimerge_boundaries(mat)
        cuts[f] = _clean_cuts([(uniq[s - 1] + uniq[s]) / 2.0 for s in starts], float(uniq[0]), float(uniq[-1]))
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False)
    return CutModel("CHIMERGE_CENTRAL", cuts, labels, perf_counter() - started,
                    uses_labels=True, uses_pooled_raw_values=True,
                    federated_note="CENTRAL REFERENCE: pooled raw values and labels",
                    communication_numbers_per_client=0)


# ------------------------------------------- Rough-set MD heuristic -------

def _conflict_pairs(cell: np.ndarray, y: np.ndarray, k: int) -> float:
    _, inv = np.unique(cell, return_inverse=True)
    counts = np.zeros((inv.max() + 1, k), dtype=float)
    np.add.at(counts, (inv, y), 1.0)
    n = counts.sum(axis=1)
    return float(((n ** 2 - (counts ** 2).sum(axis=1)) / 2.0).sum())


def fit_rs_discernibility(clients, continuous, target, categorical=(), max_intervals=MAX_INTERVALS):
    """Nguyen & Skowron (1995) MD-heuristic: greedily choose the cut that discerns the
    most still-indiscernible object pairs with different decisions (central reference)."""
    started = perf_counter()
    pooled = pd.concat(list(clients.values()), ignore_index=True)
    y, classes = _class_index(pooled[target].astype(str).to_numpy())
    k = len(classes)
    cell = np.zeros(len(pooled), dtype=np.int64)
    for c in categorical:
        codes = pd.factorize(pooled[c].astype(str))[0]
        # re-factorise after each attribute: product codes cannot overflow int64
        cell = pd.factorize(cell * (codes.max() + 1) + codes)[0].astype(np.int64)
    X = {f: pd.to_numeric(pooled[f]).to_numpy(dtype=float) for f in continuous}
    cand = {}
    for f in continuous:
        u = np.unique(X[f])
        mids = (u[:-1] + u[1:]) / 2.0
        if len(mids) > RS_MD_CANDIDATES:
            mids = np.unique(np.quantile(mids, np.linspace(0, 1, RS_MD_CANDIDATES)))
        cand[f] = list(mids)
    chosen = {f: [] for f in continuous}
    current = _conflict_pairs(cell, y, k)
    while current > 0:
        best = None
        for fi, f in enumerate(continuous):
            if len(chosen[f]) >= max_intervals - 1:
                continue
            for c in cand[f]:
                trial = cell * 2 + (X[f] > c)
                val = _conflict_pairs(trial, y, k)
                key = (val, fi, c)
                if best is None or key < best[0]:
                    best = (key, f, c, trial)
        if best is None or best[0][0] >= current:
            break
        (_, f, c, trial) = best
        chosen[f].append(c)
        cand[f].remove(c)
        cell = pd.factorize(trial)[0].astype(np.int64)
        current = best[0][0]
    cuts, labels = {}, {}
    for f in continuous:
        lo, hi = float(X[f].min()), float(X[f].max())
        cuts[f] = _clean_cuts(chosen[f], lo, hi)
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False) if hi > lo else ("Constant",)
    return CutModel("RS_DISCERNIBILITY_CENTRAL", cuts, labels, perf_counter() - started,
                    uses_labels=True, uses_pooled_raw_values=True,
                    federated_note="CENTRAL REFERENCE: pooled pairwise discernibility",
                    communication_numbers_per_client=0,
                    extra={"remaining_conflicting_pairs": current})


# ------------------------------------------ count-matched controls -------

def fit_count_matched(clients, continuous, target, reference: CutModel, kind: str):
    """Same per-feature interval COUNT as ``reference`` but unsupervised positions.

    Separates "where the cuts are" from "how many intervals there are"."""
    started = perf_counter()
    cuts, labels = {}, {}
    for f in continuous:
        n = len(reference.labels[f])
        if n <= 1:
            cuts[f], labels[f] = (), ("Constant",)
            continue
        if kind == "EW":
            lo, hi = _global_range(clients, f)
            c = np.linspace(lo, hi, n + 1)[1:-1]
        else:
            values = _values(clients, f)
            lo, hi = float(values.min()), float(values.max())
            c = np.quantile(values, np.linspace(0, 1, n + 1))[1:-1]
        cuts[f] = _clean_cuts(c, lo, hi)
        labels[f] = _canonical_labels(len(cuts[f]) + 1, original_style=False)
    return CutModel(f"{kind}_COUNT_MATCHED_{reference.method}", cuts, labels, perf_counter() - started,
                    uses_labels=False, uses_pooled_raw_values=(kind != "EW"),
                    federated_note="count copied from supervised reference; positions unsupervised",
                    communication_numbers_per_client=reference.communication_numbers_per_client)


# --------------------------------------------------------- registry -------

FitFn = Callable[..., CutModel]

BASE_METHODS: Dict[str, Callable] = {
    "EQUAL_WIDTH_3": lambda cl, cont, t, cat: fit_equal_width(cl, cont, t, 3),
    "EQUAL_WIDTH_5": lambda cl, cont, t, cat: fit_equal_width(cl, cont, t, 5),
    "EQUAL_FREQUENCY_3": lambda cl, cont, t, cat: fit_equal_frequency(cl, cont, t, 3),
    "EQUAL_FREQUENCY_5": lambda cl, cont, t, cat: fit_equal_frequency(cl, cont, t, 5),
    "ROBUST_WIDTH_3": lambda cl, cont, t, cat: fit_robust_width(cl, cont, t, 3),
    "MDLP_CENTRAL": lambda cl, cont, t, cat: fit_mdlp_central(cl, cont, t),
    "MDLP_HIST": lambda cl, cont, t, cat: fit_mdlp_histogram(cl, cont, t),
    "CHIMERGE_CENTRAL": lambda cl, cont, t, cat: fit_chimerge_central(cl, cont, t),
    "RS_DISCERNIBILITY_CENTRAL": lambda cl, cont, t, cat: fit_rs_discernibility(cl, cont, t, cat),
}


def fit_method(name: str, clients, continuous, target, categorical=()) -> CutModel:
    if name in BASE_METHODS:
        return BASE_METHODS[name](clients, list(continuous), target, list(categorical))
    if name in ("EW_COUNT_MATCHED_MDLP_HIST", "EF_COUNT_MATCHED_MDLP_HIST"):
        ref = fit_mdlp_histogram(clients, list(continuous), target)
        return fit_count_matched(clients, list(continuous), target, ref, name[:2])
    raise ValueError(f"Unknown discretizer {name!r}")
