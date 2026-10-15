from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Mapping, Sequence, Tuple, List, Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ReductSelectionResult:
    """Original reduct quantities plus the canonical selection decision."""

    full_feature_count: int
    full_dependency: float
    minimum_reduct_size: int
    candidate_reducts: Tuple[Tuple[str, ...], ...]
    candidate_count: int
    selected_reduct: Tuple[str, ...]
    selected_dependency: float
    selection_policy: str = "lexicographic_first_among_minimum_cardinality"


def _positive_region_size(df: pd.DataFrame, attrs: Sequence[str], target: str) -> int:
    if not attrs:
        return len(df) if df[target].nunique(dropna=False) == 1 else 0

    grouped = df.groupby(list(attrs), dropna=False)[target].nunique(dropna=False)
    pure_keys = grouped[grouped == 1].index

    if len(pure_keys) == 0:
        return 0

    sizes = df.groupby(list(attrs), dropna=False).size()
    return int(sizes.loc[pure_keys].sum())


def dependency_degree(df: pd.DataFrame, attrs: Sequence[str], target: str) -> float:
    return _positive_region_size(df, attrs, target) / len(df) if len(df) else 0.0


def find_minimum_cardinality_reducts(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
) -> List[Tuple[str, ...]]:
    # V6.1 historical search, kept verbatim for the paper.py Wang replication
    # lane. Production selection uses find_exact_minimum_cardinality_reducts.
    features = list(features)
    full_gamma = dependency_degree(df, features, target)

    for size in range(1, len(features) + 1):
        found = []
        for combo in itertools.combinations(features, size):
            if np.isclose(dependency_degree(df, combo, target), full_gamma):
                found.append(tuple(combo))
        if found:
            return found

    return [tuple(features)]


def find_exact_minimum_cardinality_reducts(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
) -> List[Tuple[str, ...]]:
    """Minimum-cardinality R ⊆ C with |POS_R(D)| = |POS_C(D)|, searched from |R| = 0.

    Acceptance compares integer positive-region sizes, never dependency floats.
    R = () is a legal candidate: IND(()) has the single class U.
    """
    features = list(features)
    full_pos = _positive_region_size(df, features, target)

    for size in range(0, len(features) + 1):
        found = [
            tuple(combo)
            for combo in itertools.combinations(features, size)
            if _positive_region_size(df, combo, target) == full_pos
        ]
        if found:
            return found

    return [tuple(features)]


def select_minimum_reduct(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
    selection: str = "LEXICOGRAPHIC_FIRST",
) -> ReductSelectionResult:
    """Select one canonical minimum-cardinality reduct and retain every candidate."""
    policy = str(selection).strip().upper()
    if policy != "LEXICOGRAPHIC_FIRST":
        raise ValueError("selection must be LEXICOGRAPHIC_FIRST.")

    feature_list = list(features)
    raw_candidates = find_exact_minimum_cardinality_reducts(df, feature_list, target)
    candidates = tuple(sorted({tuple(sorted(candidate)) for candidate in raw_candidates}))
    if not candidates:
        raise RuntimeError("Minimum-cardinality reduct search returned no candidates.")

    selected = candidates[0]
    return ReductSelectionResult(
        full_feature_count=len(feature_list),
        full_dependency=dependency_degree(df, feature_list, target),
        minimum_reduct_size=len(selected),
        candidate_reducts=candidates,
        candidate_count=len(candidates),
        selected_reduct=selected,
        selected_dependency=dependency_degree(df, selected, target),
    )


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    # Identical empty sets have similarity 1 by set identity; this is an
    # explicit derived-metric convention, not a Rough Set quantity.
    return 1.0 if not union else len(left_set & right_set) / len(union)


def pairwise_reduct_jaccard(
    reducts: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Return pairwise selected-reduct similarity and its instability summary."""
    names = list(reducts)
    rows = []
    for i, client_i in enumerate(names):
        for client_j in names[i + 1 :]:
            reduct_i = tuple(sorted(set(reducts[client_i])))
            reduct_j = tuple(sorted(set(reducts[client_j])))
            intersection_size = len(set(reduct_i) & set(reduct_j))
            union_size = len(set(reduct_i) | set(reduct_j))
            rows.append(
                {
                    "client_i": client_i,
                    "client_j": client_j,
                    "reduct_i": reduct_i,
                    "reduct_j": reduct_j,
                    "intersection_size": intersection_size,
                    "union_size": union_size,
                    "jaccard": 1.0 if union_size == 0 else intersection_size / union_size,
                }
            )

    table = pd.DataFrame(
        rows,
        columns=[
            "client_i",
            "client_j",
            "reduct_i",
            "reduct_j",
            "intersection_size",
            "union_size",
            "jaccard",
        ],
    )
    if table.empty:
        mean_jaccard = float("nan")
        instability = float("nan")
    else:
        mean_jaccard = float(table["jaccard"].mean())
        instability = 1.0 - mean_jaccard
    return {
        "pairwise_table": table,
        "mean_reduct_jaccard": mean_jaccard,
        "reduct_instability": instability,
    }


def feature_selection_frequency(
    reducts: Mapping[str, Sequence[str]],
    features: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Calculate the derived fraction of clients selecting each feature."""
    names = list(reducts)
    feature_names = list(features) if features is not None else sorted(
        {feature for reduct in reducts.values() for feature in reduct}
    )
    total_clients = len(names)
    rows = []
    for feature in feature_names:
        count = sum(feature in set(reducts[name]) for name in names)
        rows.append(
            {
                "feature": feature,
                "selected_client_count": count,
                "total_clients": total_clients,
                "selection_frequency": count / total_clients if total_clients else float("nan"),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["feature", "selected_client_count", "total_clients", "selection_frequency"],
    )


# Backward-compatible name used by V6.1 and older notebooks.
find_minimal_reducts = find_minimum_cardinality_reducts
