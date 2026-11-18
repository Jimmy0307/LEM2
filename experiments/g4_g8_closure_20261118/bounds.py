"""Exact finite-sample resolver opportunity bounds for frozen-rule comparisons.

Proof and interpretation:
docs/research/g4_g8_closure_20261118/STRUCTURAL_BOUNDS_AND_COUNTEREXAMPLES.md
"""
from __future__ import annotations

from collections import Counter
from typing import Sequence


def resolver_change_bounds(
    y_true: Sequence[object],
    predictions_a: Sequence[object],
    predictions_b: Sequence[object],
    active_conflict: Sequence[bool],
) -> dict:
    """Compute accuracy/BA difference and class-aware maxima for fixed rules.

    A different prediction on a non-conflict row is a hard violation of the
    frozen-rule, same-fallback resolver comparison contract.
    """
    y = list(map(str, y_true))
    a = list(map(str, predictions_a))
    b = list(map(str, predictions_b))
    z = list(map(bool, active_conflict))
    n = len(y)
    if not n or len(a) != n or len(b) != n or len(z) != n:
        raise ValueError("Equal nonempty lengths are required")
    bad = [i for i in range(n) if a[i] != b[i] and not z[i]]
    if bad:
        raise ValueError(f"Resolvers differ outside frozen-rule conflict region at positions {bad[:10]}")

    sizes = Counter(y)
    cls = sorted(sizes)
    a_acc = sum(y[i] == a[i] for i in range(n)) / n
    b_acc = sum(y[i] == b[i] for i in range(n)) / n
    a_ba = sum(sum(y[i] == a[i] for i in range(n) if y[i] == c) / sizes[c] for c in cls) / len(cls)
    b_ba = sum(sum(y[i] == b[i] for i in range(n) if y[i] == c) / sizes[c] for c in cls) / len(cls)

    accuracy_bound = sum(z) / n
    class_conflict = {
        c: sum(z[i] for i in range(n) if y[i] == c) / sizes[c] for c in cls
    }
    ba_bound = sum(class_conflict.values()) / len(cls)
    if abs(b_acc - a_acc) > accuracy_bound + 1e-12:
        raise AssertionError("Accuracy gap violates frozen-rule conflict upper bound")
    if abs(b_ba - a_ba) > ba_bound + 1e-12:
        raise AssertionError("Balanced Accuracy gap violates class-conditional conflict upper bound")

    return {
        "n": n,
        "n_classes": len(cls),
        "n_conflict": sum(z),
        "accuracy_gap_b_minus_a": b_acc - a_acc,
        "accuracy_absolute_upper_bound": accuracy_bound,
        "balanced_accuracy_gap_b_minus_a": b_ba - a_ba,
        "balanced_accuracy_absolute_upper_bound": ba_bound,
        "class_conditional_conflict_rate": class_conflict,
        "note": "Only applies to identical effective rules, same fallback, and resolvers restricted to matched candidate classes",
    }
