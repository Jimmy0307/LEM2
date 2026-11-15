"""Classification metrics (same definitions as roughset.evaluation)."""
from __future__ import annotations

from typing import Dict, Sequence

import numpy as np


def balanced_accuracy(y_true: Sequence, y_pred: Sequence) -> float:
    y, p = np.asarray(y_true, dtype=object), np.asarray(y_pred, dtype=object)
    recalls = [float((p[y == c] == c).mean()) for c in dict.fromkeys(y.tolist())]
    return float(np.mean(recalls)) if recalls else 0.0


def macro_f1(y_true: Sequence, y_pred: Sequence) -> float:
    y, p = np.asarray(y_true, dtype=object), np.asarray(y_pred, dtype=object)
    classes = sorted(set(y.tolist()) | set(p.tolist()), key=str)
    scores = []
    for c in classes:
        tp = int(((y == c) & (p == c)).sum())
        fp = int(((y != c) & (p == c)).sum())
        fn = int(((y == c) & (p != c)).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return float(np.mean(scores)) if scores else 0.0


def scores(y_true: Sequence, y_pred: Sequence) -> Dict[str, float]:
    y, p = np.asarray(y_true, dtype=object), np.asarray(y_pred, dtype=object)
    return {
        "ba": balanced_accuracy(y, p),
        "accuracy": float((y == p).mean()) if len(y) else 0.0,
        "macro_f1": macro_f1(y, p),
    }
