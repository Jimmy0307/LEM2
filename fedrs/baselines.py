"""Non-rough-set interpretable comparators (CART), same splits and partitions.

CART_CENTRAL     : one sklearn DecisionTreeClassifier on pooled development rows
                   (a CENTRALISED reference, not a federated method).
CART_FED_VOTE    : one tree per client, server averages class probabilities
                   (federated-feasible: only trees are shared).
max_depth is chosen on Inner Validation BA from a fixed grid; Test is read once.
"""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from .metrics import scores

DEPTHS = (1, 2, 3, 4, 5, 6, 8, 10, None)


class _Encoder:
    def __init__(self, dev: pd.DataFrame, continuous: Sequence[str], categorical: Sequence[str]):
        self.cont = list(continuous)
        self.cats = {c: sorted(dev[c].astype(str).unique().tolist()) for c in categorical}

    def __call__(self, df: pd.DataFrame) -> np.ndarray:
        parts = [df[self.cont].to_numpy(dtype=float)] if self.cont else []
        for c, levels in self.cats.items():
            v = df[c].astype(str).to_numpy()
            parts.append(np.stack([(v == lv).astype(float) for lv in levels], axis=1))
        return np.hstack(parts) if parts else np.zeros((len(df), 0))


def _proba(tree: DecisionTreeClassifier, X: np.ndarray, classes: Sequence[str]) -> np.ndarray:
    out = np.zeros((len(X), len(classes)))
    p = tree.predict_proba(X)
    idx = {c: i for i, c in enumerate(classes)}
    for j, c in enumerate(tree.classes_):
        out[:, idx[str(c)]] = p[:, j]
    return out


def cart_rows(clients: Mapping[str, pd.DataFrame], dev, val, test, continuous, categorical, target) -> list:
    enc = _Encoder(dev, continuous, categorical)
    classes = sorted(dev[target].astype(str).unique().tolist())
    yv, yt = val[target].astype(str).to_numpy(), test[target].astype(str).to_numpy()
    Xd, Xv, Xt = enc(dev), enc(val), enc(test)
    rows = []
    best = None
    for d in DEPTHS:
        tree = DecisionTreeClassifier(max_depth=d, random_state=0).fit(Xd, dev[target].astype(str))
        s = scores(yv, tree.predict(Xv))["ba"]
        if best is None or s > best[0] + 1e-12:
            best = (s, d, tree)
    st = scores(yt, best[2].predict(Xt))
    rows.append({"method": "CART_CENTRAL", "selected_depth": str(best[1]), "val_ba": best[0], "test_ba": st["ba"],
                 "test_accuracy": st["accuracy"], "test_macro_f1": st["macro_f1"],
                 "n_leaves": int(best[2].get_n_leaves())})
    best = None
    for d in DEPTHS:
        trees = [DecisionTreeClassifier(max_depth=d, random_state=0).fit(enc(df), df[target].astype(str))
                 for df in clients.values()]
        pv = sum(_proba(t, Xv, classes) for t in trees)
        s = scores(yv, np.asarray(classes, dtype=object)[pv.argmax(axis=1)])["ba"]
        if best is None or s > best[0] + 1e-12:
            best = (s, d, trees)
    pt = sum(_proba(t, Xt, classes) for t in best[2])
    st = scores(yt, np.asarray(classes, dtype=object)[pt.argmax(axis=1)])
    rows.append({"method": "CART_FED_VOTE", "selected_depth": str(best[1]), "val_ba": best[0], "test_ba": st["ba"],
                 "test_accuracy": st["accuracy"], "test_macro_f1": st["macro_f1"],
                 "n_leaves": int(sum(t.get_n_leaves() for t in best[2]))})
    return rows
