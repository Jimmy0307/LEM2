"""Dataset-as-unit paired statistics (Demšar 2006; Benavoli et al. 2016).

Seeds are averaged WITHIN a dataset first; the dataset is the statistical unit.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd
from scipy import stats

BOOT = 10000
BOOT_SEED = 20261116


def holm(pvalues: Sequence[float]) -> List[float]:
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(np.where(np.isnan(p), np.inf, p))
    m = int(np.isfinite(p).sum())
    adj = np.full(len(p), np.nan)
    running = 0.0
    for rank, idx in enumerate(order):
        if not np.isfinite(p[idx]):
            continue
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adj[idx] = running
    return adj.tolist()


def rank_biserial(diff: np.ndarray) -> float:
    d = diff[diff != 0]
    if d.size == 0:
        return 0.0
    r = stats.rankdata(np.abs(d))
    return float((r[d > 0].sum() - r[d < 0].sum()) / r.sum())


def bootstrap_ci(diff: np.ndarray, seed: int = BOOT_SEED) -> tuple:
    if diff.size == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = diff[rng.integers(0, diff.size, size=(BOOT, diff.size))].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def paired_compare(df: pd.DataFrame, unit: str, treatment_col: str, a: str, b: str, metric: str,
                   strata: Sequence[str] = ()) -> pd.DataFrame:
    """b minus a, per stratum, with dataset-level aggregation."""
    rows = []
    groups = df.groupby(list(strata)) if strata else [((), df)]
    for key, g in groups:
        key = key if isinstance(key, tuple) else (key,)
        # Pair on the finest replicate keys first (dataset, seed) so both arms average over
        # exactly the same seeds; only then aggregate to the statistical unit.
        pair_keys = [k for k in ("dataset", "seed") if k in g.columns and k != unit]
        cell = g[g[treatment_col].isin([a, b])].groupby([unit, *pair_keys, treatment_col])[metric].mean().unstack()
        if a not in cell or b not in cell:
            continue
        cell = cell[[a, b]].dropna()
        n_pairs = cell.groupby(level=0).size()
        per = cell.groupby(level=0).mean()
        diff = (per[b] - per[a]).to_numpy(dtype=float)
        if diff.size == 0:
            continue
        try:
            p = float(stats.wilcoxon(diff).pvalue) if np.any(diff != 0) else 1.0
        except ValueError:
            p = np.nan
        lo, hi = bootstrap_ci(diff)
        rows.append({**dict(zip(strata, key)), "metric": metric, "baseline": a, "treatment": b,
                     "n_datasets": int(diff.size), "n_paired_replicates": int(n_pairs.sum()),
                     "min_replicates_per_unit": int(n_pairs.min()), "mean_baseline": float(per[a].mean()),
                     "mean_treatment": float(per[b].mean()), "mean_diff": float(diff.mean()),
                     "median_diff": float(np.median(diff)), "ci95_low": lo, "ci95_high": hi,
                     "wins": int((diff > 1e-12).sum()), "ties": int((np.abs(diff) <= 1e-12).sum()),
                     "losses": int((diff < -1e-12).sum()), "wilcoxon_p": p,
                     "rank_biserial": rank_biserial(diff)})
    out = pd.DataFrame(rows)
    if len(out):
        out["holm_p_within_table"] = holm(out["wilcoxon_p"].tolist())
    return out


def friedman(df: pd.DataFrame, unit: str, method_col: str, metric: str, methods: Iterable[str]) -> Dict[str, object]:
    methods = list(methods)
    per = df[df[method_col].isin(methods)].groupby([unit, method_col])[metric].mean().unstack()[methods].dropna()
    if per.shape[0] < 3:
        return {"n_datasets": per.shape[0], "friedman_p": np.nan}
    res = stats.friedmanchisquare(*[per[m].to_numpy() for m in methods])
    ranks = per.rank(axis=1, ascending=False).mean()
    return {"n_datasets": int(per.shape[0]), "friedman_chi2": float(res.statistic), "friedman_p": float(res.pvalue),
            "mean_rank": {m: float(ranks[m]) for m in methods}}
