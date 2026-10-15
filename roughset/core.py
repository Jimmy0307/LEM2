from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence, Set, Tuple

import pandas as pd


@dataclass(frozen=True)
class Rule:
    conditions: Tuple[Tuple[str, Any], ...]
    decision: Any
    source: str = ""

    def __str__(self):
        lhs = " AND ".join(f"{a}={v}" for a, v in self.conditions)
        src = f" [source={self.source}]" if self.source else ""
        return f"IF {lhs} THEN decision={self.decision}{src}"

    @property
    def key(self):
        return (tuple(sorted(self.conditions)), self.decision)


def equivalence_classes(df: pd.DataFrame, condition_cols: Sequence[str]) -> List[Set[int]]:
    groups = df.groupby(list(condition_cols), sort=False, dropna=False).groups
    return [set(ids) for ids in groups.values()]


def lower_approximation(df, condition_cols, decision_col, decision_value) -> Set[int]:
    concept = set(df.index[df[decision_col] == decision_value])
    lower: Set[int] = set()

    for eq_class in equivalence_classes(df, condition_cols):
        if eq_class <= concept:
            lower |= eq_class

    return lower


def build_blocks(df, condition_cols):
    blocks = {}
    for attr in condition_cols:
        for value in pd.unique(df[attr]):
            blocks[(attr, value)] = set(df.index[df[attr] == value])
    return blocks


def complex_block(conditions, blocks, universe):
    if not conditions:
        return set(universe)

    result = set(universe)
    for pair in conditions:
        result &= blocks[pair]
    return result


def choose_best_pair(blocks, G, used_pairs):
    candidates = []

    for pair, block in blocks.items():
        if pair in used_pairs:
            continue

        overlap = len(block & G)
        if overlap:
            candidates.append((pair, overlap, len(block)))

    if not candidates:
        raise RuntimeError("No candidate pair can cover the remaining target objects.")

    candidates.sort(key=lambda x: (-x[1], x[2], str(x[0])))
    return candidates[0][0]


def minimize_complex(conditions, B, blocks, universe):
    conditions = list(conditions)
    changed = True

    while changed and len(conditions) > 1:
        changed = False
        for condition in list(conditions):
            trial = [x for x in conditions if x != condition]
            trial_block = complex_block(trial, blocks, universe)
            if trial_block and trial_block <= B:
                conditions = trial
                changed = True
                break

    return conditions


def build_one_complex(B, uncovered, blocks, universe, verbose=False):
    G = set(uncovered)
    T = []
    step = 0

    while True:
        current = complex_block(T, blocks, universe)
        if T and current and current <= B:
            break

        best_pair = choose_best_pair(blocks, G, T)

        if verbose:
            print(
                f"    Step {step+1}: choose {best_pair}, "
                f"|[t]∩G|={len(blocks[best_pair] & G)}, |[t]|={len(blocks[best_pair])}"
            )

        T.append(best_pair)
        G &= blocks[best_pair]
        step += 1

    T = minimize_complex(T, B, blocks, universe)
    return tuple(T), complex_block(T, blocks, universe)


def remove_redundant_complexes(complexes, B):
    complexes = list(complexes)
    changed = True

    while changed and len(complexes) > 1:
        changed = False
        for i in range(len(complexes)):
            covered_by_others: Set[int] = set()
            for j, (_, block) in enumerate(complexes):
                if i != j:
                    covered_by_others |= (block & B)
            if covered_by_others >= B:
                complexes.pop(i)
                changed = True
                break

    return complexes


def induce_lem2(
    df: pd.DataFrame,
    condition_cols: Sequence[str],
    decision_col: str,
    source: str = "",
    verbose: bool = False,
) -> List[Rule]:
    """Classical certain-rule LEM2 local-covering implementation."""
    data = df.reset_index(drop=True).copy()
    universe = set(data.index)
    blocks = build_blocks(data, condition_cols)
    rules: List[Rule] = []

    for decision_value in pd.unique(data[decision_col]):
        B = lower_approximation(data, condition_cols, decision_col, decision_value)

        if verbose:
            print("\n" + "=" * 72)
            print(f"Decision concept: {decision_col}={decision_value}")
            print(f"Lower approximation B = {sorted(B)}")

        if not B:
            continue

        complexes = []
        covered: Set[int] = set()

        while covered != B:
            uncovered = B - covered
            T, T_block = build_one_complex(B, uncovered, blocks, universe, verbose=verbose)
            complexes.append((T, T_block))
            covered |= (T_block & B)

            if verbose:
                readable = " AND ".join(f"{a}={v}" for a, v in T)
                print(f"  Minimal complex = {readable}")
                print(f"  [T] = {sorted(T_block)}")

        complexes = remove_redundant_complexes(complexes, B)

        for T, _ in complexes:
            rules.append(Rule(conditions=T, decision=decision_value, source=source))

    return rules
