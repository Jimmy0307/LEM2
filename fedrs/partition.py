"""Client partitions: the original protocol and Control C (degeneracy-constrained).

Control C CHANGES THE DATA ALLOCATION.  Its results must never be read as the
effect of a rule-processing change; they answer "what if degenerate clients are
not created", and they also weaken the realised label skew (recorded).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional

import numpy as np
import pandas as pd

from roughset.federated import partition_clients

REGIMES = {
    "IID": ("STRATIFIED", 0.5),
    "NONIID_05": ("DIRICHLET_LABEL_SKEW", 0.5),
    "NONIID_01": ("DIRICHLET_LABEL_SKEW", 0.1),
}


@dataclass(frozen=True)
class ClientConstraint:
    min_rows: int = 20
    min_classes: int = 2
    min_rows_per_present_class: int = 3
    max_attempts: int = 500


def original_partition(dev: pd.DataFrame, target: str, n_clients: int, seed: int, regime: str):
    strategy, alpha = REGIMES[regime]
    return partition_clients(dev, target_col=target, n_clients=n_clients, seed=seed,
                             strategy=strategy, dirichlet_alpha=alpha, dirichlet_max_retries=100)


def satisfies(clients: Mapping[str, pd.DataFrame], target: str, c: ClientConstraint) -> bool:
    for df in clients.values():
        if len(df) < c.min_rows:
            return False
        counts = df[target].astype(str).value_counts()
        if len(counts) < c.min_classes:
            return False
        if int(counts.min()) < c.min_rows_per_present_class:
            return False
    return True


def constrained_partition(dev: pd.DataFrame, target: str, n_clients: int, seed: int, regime: str,
                          constraint: Optional[ClientConstraint] = None):
    """Deterministic rejection resampling of the SAME Dirichlet mechanism.

    Attempt k uses seed ``seed * 1000 + k`` (k=0 reproduces the original draw).
    Returns (clients or None, attempts, status)."""
    c = constraint or ClientConstraint()
    feasible_classes = dev[target].astype(str).value_counts()
    if (feasible_classes >= c.min_rows_per_present_class).sum() < c.min_classes:
        return None, 0, "INFEASIBLE_CLASS_COUNTS"
    for k in range(c.max_attempts):
        attempt_seed = seed if k == 0 else seed * 1000 + k
        try:
            clients = original_partition(dev, target, n_clients, attempt_seed, regime)
        except ValueError:
            continue
        if satisfies(clients, target, c):
            return clients, k + 1, "OK"
    return None, c.max_attempts, "MAX_ATTEMPTS_EXCEEDED"


def label_skew_index(clients: Mapping[str, pd.DataFrame], target: str) -> float:
    """Mean total-variation distance between client class mix and pooled class mix."""
    pooled = pd.concat(list(clients.values()))[target].astype(str).value_counts(normalize=True)
    tvs = []
    for df in clients.values():
        local = df[target].astype(str).value_counts(normalize=True).reindex(pooled.index, fill_value=0.0)
        tvs.append(0.5 * float(np.abs(local - pooled).sum()))
    return float(np.mean(tvs))
