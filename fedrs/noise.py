"""Label-noise injection (DEVELOPMENT rows only) and a controlled synthetic generator."""
from __future__ import annotations

import numpy as np
import pandas as pd


def flip_labels(df: pd.DataFrame, target: str, rate: float, seed: int) -> pd.DataFrame:
    """Flip round(rate*n) uniformly chosen labels to a different class (uniform)."""
    if rate <= 0:
        return df
    out = df.copy()
    rng = np.random.default_rng(seed)
    labels = out[target].astype(str).to_numpy().copy()
    classes = np.asarray(sorted(set(labels.tolist())), dtype=object)
    if len(classes) < 2:
        return out
    n_flip = int(round(rate * len(out)))
    idx = rng.choice(len(out), size=n_flip, replace=False)
    for i in idx:
        others = classes[classes != labels[i]]
        labels[i] = others[rng.integers(len(others))]
    out[target] = labels
    out["__label_flipped__"] = False
    out.iloc[idx, out.columns.get_loc("__label_flipped__")] = True
    return out


def synthetic_table(n: int, imbalance: str, seed: int) -> pd.DataFrame:
    """Mixed continuous/categorical table with a known threshold concept.

    class A : x1 < 0.35
    class B : x1 >= 0.35 and x2 < 0.60 and c1 != 'c'
    class C : otherwise
    x3 (continuous) and c2 (categorical) are irrelevant.  ``imbalance``:
    'balanced' -> rejection-sample to ~1:1:1, 'skewed' -> ~70:20:10.
    """
    rng = np.random.default_rng(seed)
    target_mix = {"balanced": (1 / 3, 1 / 3, 1 / 3), "skewed": (0.70, 0.20, 0.10)}[imbalance]
    rows = []
    want = {k: int(round(n * p)) for k, p in zip("ABC", target_mix)}
    got = {k: 0 for k in "ABC"}
    while sum(got.values()) < sum(want.values()):
        x1, x2, x3 = rng.random(3)
        c1 = "abc"[rng.integers(3)]
        c2 = "uvw"[rng.integers(3)]
        y = "A" if x1 < 0.35 else ("B" if (x2 < 0.60 and c1 != "c") else "C")
        if got[y] < want[y]:
            got[y] += 1
            rows.append((round(x1, 4), round(x2, 4), round(x3, 4), c1, c2, y))
    return pd.DataFrame(rows, columns=["x1", "x2", "x3", "c1", "c2", "class"])
