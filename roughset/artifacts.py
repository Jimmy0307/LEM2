from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pandas as pd

from .core import Rule
from .reduct import ReductSelectionResult


@dataclass(frozen=True)
class RuleSystemArtifact:
    """Frozen input to resolver evaluation for one dataset/split/client count."""

    dataset: str
    source: str
    evaluation_mode: str
    fold: int
    client_count: int
    seed: int
    target: str
    condition_columns: tuple[str, ...]
    train_row_ids: tuple[int, ...]
    test_row_ids: tuple[int, ...]
    train: pd.DataFrame = field(repr=False, compare=False)
    test: pd.DataFrame = field(repr=False, compare=False)
    central_reduct_result: ReductSelectionResult | None
    local_reduct_results: Mapping[str, ReductSelectionResult | None]
    central_reduct_seconds: float | None
    local_reduct_seconds: Mapping[str, float | None]
    structural_build_seconds: float
    central_rules: tuple[Rule, ...]
    local_rules: Mapping[str, tuple[Rule, ...]]
    global_rules: tuple[Rule, ...]
    rule_provenance: Mapping[Any, tuple[str, ...]]
    central_default_class: Any
    default_class: Any
    central_rule_weights: Mapping[Any, float]
    central_rule_support_sets: Mapping[Any, frozenset[Any]]
    central_class_sizes: Mapping[str, int]
    local_rule_weights: Mapping[str, Mapping[Any, float]]
    local_rule_support_sets: Mapping[str, Mapping[Any, frozenset[Any]]]
    local_class_sizes: Mapping[str, Mapping[str, int]]
    global_rule_weights: Mapping[Any, float]
    global_rule_support_sets: Mapping[Any, frozenset[Any]]
    global_class_sizes: Mapping[str, int]
    pre_resolution_conflict_flags: tuple[bool, ...]
    pre_resolution_conflict_case_ids: tuple[int, ...]
    pre_resolution_conflicts: Mapping[str, Any]
    structural_metrics: Mapping[str, Any]
    tables: Mapping[str, pd.DataFrame] = field(repr=False, compare=False)
    order_sensitivity_max_permutations: int = 120
