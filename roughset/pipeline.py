from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from .artifacts import RuleSystemArtifact
from .core import Rule, induce_lem2
from .evaluation import (
    audit_rule_conflicts,
    balanced_accuracy,
    evaluate_rule_model,
    fit_rule_support_sets,
    fit_rule_weights,
    macro_f1_score,
    majority_class,
    majority_class_from_clients,
    matching_rules,
    pairwise_rule_jaccard,
    target_coverage_by_class,
)
from .federated import (
    aggregate_rule_support_context,
    audit_order_distribution,
    union_rules_with_provenance,
)
from .reduct import (
    ReductSelectionResult,
    feature_selection_frequency,
    pairwise_reduct_jaccard,
    select_minimum_reduct,
)


def induce_lem2_on_reduct(
    df: pd.DataFrame,
    reduct: Sequence[str],
    target: str,
    source: str = "",
) -> list[Rule]:
    """LEM2 on the selected reduct, including the empty reduct.

    A non-empty reduct goes straight to the frozen V6.1 ``induce_lem2``.  That
    function needs at least one attribute, so R = () is handled here: IND(())
    has the single class U, the lower approximation of decision d is U when
    every object has decision d and empty otherwise, and the only complex is
    the empty conjunction with block U.  Hence TRUE -> d, or no certain rule.
    """
    if reduct:
        return induce_lem2(df, list(reduct), target, source=source, verbose=False)
    decisions = pd.unique(df[target])
    if len(df) and len(decisions) == 1:
        return [Rule(conditions=(), decision=decisions[0], source=source)]
    return []


def global_rule_support_context(
    clients: Mapping[str, pd.DataFrame],
    rules: Sequence[Rule],
    target: str,
) -> tuple[dict[Any, float], dict[Any, frozenset[Any]], dict[str, int]]:
    """Support of every global rule over ALL clients, not only its producers.

    Supp_c(r) = {z in U_c : z satisfies Ante(r) and D(z) = decision(r)}, keyed by
    (client, local row) so the union over disjoint clients is the pooled set.
    STANDARD_VOTING weight is Supp_G(r) = sum_c |Supp_c(r)|; GLOBAL_STRENGTH
    uses the sets themselves.  Provenance plays no part in the scope.
    """
    client_sets: dict[str, dict[Any, set[Any]]] = {}
    client_classes: dict[str, dict[Any, int]] = {}
    for client_id, client_df in clients.items():
        client_sets[client_id], client_classes[client_id] = fit_rule_support_sets(
            client_df, rules, target=target, row_prefix=client_id
        )
    support_sets, class_sizes = aggregate_rule_support_context(client_sets, client_classes)
    weights = {rule.key: float(len(support_sets.get(rule.key, ()))) for rule in rules}
    return (
        weights,
        {key: frozenset(value) for key, value in support_sets.items()},
        class_sizes,
    )


def _rule_condition_summary(rules: Sequence[Rule]) -> dict[str, Any]:
    counts = [len(rule.conditions) for rule in rules]
    if not counts:
        return {
            "rule_count": 0,
            "average_condition_count": float("nan"),
            "median_condition_count": float("nan"),
            "min_condition_count": float("nan"),
            "max_condition_count": float("nan"),
        }
    return {
        "rule_count": len(counts),
        "average_condition_count": float(np.mean(counts)),
        "median_condition_count": float(np.median(counts)),
        "min_condition_count": int(min(counts)),
        "max_condition_count": int(max(counts)),
    }


def _rule_metric_row(scope: str, rules: Sequence[Rule], client_id: str | None = None) -> dict[str, Any]:
    summary = _rule_condition_summary(rules)
    return {
        "scope": scope,
        "client_id": client_id,
        **summary,
    }


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    union = set(left) | set(right)
    return 1.0 if not union else len(set(left) & set(right)) / len(union)


def _pre_resolution_conflicts(
    test: pd.DataFrame,
    rules: Sequence[Rule],
    target: str,
    rule_conflicts: Mapping[str, Any],
) -> dict[str, Any]:
    flags: list[bool] = []
    rows: list[dict[str, Any]] = []
    matching_counts: list[int] = []
    for position, (_, row) in enumerate(test.iterrows()):
        matched = matching_rules(row, rules)
        decisions = sorted({str(rule.decision) for rule in matched})
        is_conflict = len(decisions) > 1
        flags.append(is_conflict)
        matching_counts.append(len(matched))
        if is_conflict:
            rows.append(
                {
                    "row_id": int(row["__row_id__"]) if "__row_id__" in row.index else position,
                    "true": str(row[target]),
                    "matching_rules": len(matched),
                    "decisions": decisions,
                }
            )

    conflict_counts = [row["matching_rules"] for row in rows]
    decision_counts = [len(row["decisions"]) for row in rows]
    total = len(test)
    conflict_count = len(rows)
    exact_count = int(rule_conflicts.get("conflict_group_count", 0))
    unique_antecedents = int(rule_conflicts.get("unique_antecedent_count", 0))
    return {
        "flags": tuple(flags),
        "case_ids": tuple(int(row["row_id"]) for row in rows),
        "table": pd.DataFrame(
            rows, columns=["row_id", "true", "matching_rules", "decisions"]
        ),
        "metrics": {
            "pre_resolution_conflict_case_rate": conflict_count / total if total else float("nan"),
            "conflict_case_rate": conflict_count / total if total else float("nan"),
            "conflict_cases_count": conflict_count,
            "non_conflict_cases_count": total - conflict_count,
            "conflict_case_count": conflict_count,
            "mean_matching_rules_per_test_case": float(np.mean(matching_counts)) if total else float("nan"),
            "mean_matching_rules_per_conflict_case": float(np.mean(conflict_counts)) if conflict_counts else float("nan"),
            "median_matching_rules_per_conflict_case": float(np.median(conflict_counts)) if conflict_counts else float("nan"),
            "max_matching_rules_per_conflict_case": int(max(conflict_counts)) if conflict_counts else float("nan"),
            "mean_distinct_decisions_per_conflict_case": float(np.mean(decision_counts)) if decision_counts else float("nan"),
            "exact_conflict_antecedent_count": exact_count,
            "exact_conflict_antecedent_rate": exact_count / unique_antecedents if unique_antecedents else 0.0,
        },
    }


def _serialize_rule_rows(
    rules: Sequence[Rule],
    *,
    client_id: str | None = None,
    selected_reduct: Sequence[str] | None = None,
    provenance: Mapping[Any, Sequence[str]] | None = None,
) -> list[dict[str, Any]]:
    rows = []
    for rule_no, rule in enumerate(rules, start=1):
        rows.append(
            {
                "rule_no": rule_no,
                "client_id": client_id,
                "selected_reduct": json.dumps(list(selected_reduct or ()), ensure_ascii=False),
                "reduct_size": len(selected_reduct) if selected_reduct is not None else None,
                "conditions": " AND ".join(f"{attr}={value}" for attr, value in rule.conditions),
                "decision": str(rule.decision),
                "rule_key": repr(rule.key),
                "condition_count": len(rule.conditions),
                "source": rule.source,
                "provenance": list((provenance or {}).get(rule.key, ())),
            }
        )
    return rows


def _reduct_tables(
    metadata: Mapping[str, Any],
    condition_columns: Sequence[str],
    train: pd.DataFrame,
    central_reduct: ReductSelectionResult | None,
    local_reducts: Mapping[str, ReductSelectionResult | None],
    central_reduct_seconds: float | None,
    local_reduct_seconds: Mapping[str, float | None],
) -> dict[str, pd.DataFrame]:
    central_rows: list[dict[str, Any]] = []
    local_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    def add_candidates(scope: str, result: ReductSelectionResult, client_id: str = ""):
        for candidate_id, candidate in enumerate(result.candidate_reducts, start=1):
            from .reduct import dependency_degree

            candidate_rows.append(
                {
                    "dataset": metadata.get("dataset"),
                    "fold": metadata.get("fold", 1),
                    "client_count": metadata.get("client_count", 0),
                    "scope": scope,
                    "client_id": client_id,
                    "candidate_id": candidate_id,
                    "reduct_size": len(candidate),
                    "features": json.dumps(list(candidate), ensure_ascii=False),
                    "dependency": dependency_degree(train if scope == "CENTRAL" else metadata["clients"][client_id], candidate, metadata["target"]),
                }
            )

    if central_reduct is not None:
        central_rows.append(
            {
                "dataset": metadata.get("dataset"),
                "evaluation_mode": metadata.get("evaluation_mode"),
                "fold": metadata.get("fold", 1),
                "seed": metadata.get("seed", 42),
                "train_rows": len(train),
                "full_feature_count": central_reduct.full_feature_count,
                "full_dependency": central_reduct.full_dependency,
                "minimum_reduct_size": central_reduct.minimum_reduct_size,
                "candidate_reduct_count": central_reduct.candidate_count,
                "selected_reduct": json.dumps(list(central_reduct.selected_reduct), ensure_ascii=False),
                "selected_reduct_dependency": central_reduct.selected_dependency,
                "all_candidate_reducts": json.dumps([list(x) for x in central_reduct.candidate_reducts], ensure_ascii=False),
                "reduct_selection_policy": central_reduct.selection_policy,
                "reduct_seconds": central_reduct_seconds,
            }
        )
        add_candidates("CENTRAL", central_reduct)

    for client_id, result in local_reducts.items():
        if result is None:
            continue
        client_df = metadata["clients"][client_id]
        selected = result.selected_reduct
        central_selected = central_reduct.selected_reduct if central_reduct else ()
        local_rows.append(
            {
                "dataset": metadata.get("dataset"),
                "fold": metadata.get("fold", 1),
                "client_count": metadata.get("client_count", len(local_reducts)),
                "client_id": client_id,
                "client_rows": len(client_df),
                "full_feature_count": result.full_feature_count,
                "full_dependency": result.full_dependency,
                "minimum_reduct_size": result.minimum_reduct_size,
                "candidate_reduct_count": result.candidate_count,
                "selected_reduct": json.dumps(list(selected), ensure_ascii=False),
                "selected_reduct_dependency": result.selected_dependency,
                "all_candidate_reducts": json.dumps([list(x) for x in result.candidate_reducts], ensure_ascii=False),
                "central_reduct": json.dumps(list(central_selected), ensure_ascii=False),
                "jaccard_with_central_reduct": _jaccard(selected, central_selected) if central_reduct else float("nan"),
                "reduct_selection_policy": result.selection_policy,
                "reduct_seconds": local_reduct_seconds.get(client_id),
            }
        )
        add_candidates("LOCAL", result, client_id)

    pairwise = pairwise_reduct_jaccard(
        {name: result.selected_reduct for name, result in local_reducts.items() if result is not None}
    )["pairwise_table"].copy()
    frequency = feature_selection_frequency(
        {name: result.selected_reduct for name, result in local_reducts.items() if result is not None},
        condition_columns,
    )
    for table in (pairwise, frequency):
        table.insert(0, "client_count", metadata.get("client_count", len(local_reducts)))
        table.insert(0, "fold", metadata.get("fold", 1))
        table.insert(0, "dataset", metadata.get("dataset"))
    return {
        "central_reduct": pd.DataFrame(
            central_rows,
            columns=["dataset", "evaluation_mode", "fold", "seed", "train_rows", "full_feature_count", "full_dependency", "minimum_reduct_size", "candidate_reduct_count", "selected_reduct", "selected_reduct_dependency", "all_candidate_reducts", "reduct_selection_policy", "reduct_seconds"],
        ),
        "local_reducts": pd.DataFrame(
            local_rows,
            columns=["dataset", "fold", "client_count", "client_id", "client_rows", "full_feature_count", "full_dependency", "minimum_reduct_size", "candidate_reduct_count", "selected_reduct", "selected_reduct_dependency", "all_candidate_reducts", "central_reduct", "jaccard_with_central_reduct", "reduct_selection_policy", "reduct_seconds"],
        ),
        "reduct_candidates": pd.DataFrame(
            candidate_rows,
            columns=["dataset", "fold", "client_count", "scope", "client_id", "candidate_id", "reduct_size", "features", "dependency"],
        ),
        "pairwise_reduct_jaccard": pairwise,
        "feature_selection_frequency": frequency,
    }


def build_rule_system(
    train: pd.DataFrame,
    test: pd.DataFrame,
    condition_columns: Sequence[str],
    target: str,
    *,
    clients: Mapping[str, pd.DataFrame] | None = None,
    reduct_enabled: bool = True,
    reduct_selection: str = "LEXICOGRAPHIC_FIRST",
    run_central: bool = True,
    run_federated: bool = True,
    metadata: Mapping[str, Any] | None = None,
    order_sensitivity_max_permutations: int = 120,
) -> RuleSystemArtifact:
    """Build the policy-independent rules and diagnostics for one split/config."""
    structural_build_started = perf_counter()
    meta = dict(metadata or {})
    feature_cols = tuple(condition_columns)
    client_tables = dict(clients or {}) if run_federated else {}
    meta["clients"] = client_tables
    meta["target"] = target
    central_reduct_seconds = None
    if reduct_enabled:
        central_reduct_started = perf_counter()
        central_reduct = select_minimum_reduct(train, feature_cols, target, reduct_selection)
        central_reduct_seconds = perf_counter() - central_reduct_started
    else:
        central_reduct = None
    central_cols = central_reduct.selected_reduct if central_reduct else feature_cols

    # Same steps as run_centralized(run_evaluation=False), with induction routed
    # through induce_lem2_on_reduct so an empty central reduct is supported.
    central_rules: tuple[Rule, ...] = ()
    central_weights: Mapping[Any, float] = {}
    central_support: Mapping[Any, Any] = {}
    central_classes: Mapping[Any, int] = {}
    central_default = None
    if run_central:
        central_rules = tuple(
            induce_lem2_on_reduct(train, central_cols, target, source="Centralized")
        )
        central_default = majority_class(train, target)
        central_weights = fit_rule_weights(train, central_rules)
        central_support, central_classes = fit_rule_support_sets(
            train, central_rules, target=target
        )

    local_reducts: dict[str, ReductSelectionResult | None] = {}
    local_reduct_seconds: dict[str, float | None] = {}
    local_rules: dict[str, tuple[Rule, ...]] = {}
    local_weights: dict[str, dict[Any, float]] = {}
    local_support: dict[str, dict[Any, frozenset[Any]]] = {}
    local_classes: dict[str, dict[str, int]] = {}
    for client_id, client_df in client_tables.items():
        if reduct_enabled:
            local_reduct_started = perf_counter()
            local_reduct = select_minimum_reduct(client_df, feature_cols, target, reduct_selection)
            local_reduct_seconds[client_id] = perf_counter() - local_reduct_started
        else:
            local_reduct = None
            local_reduct_seconds[client_id] = None
        local_reducts[client_id] = local_reduct
        client_cols = local_reduct.selected_reduct if local_reduct else feature_cols
        rules = tuple(induce_lem2_on_reduct(client_df, client_cols, target, source=client_id))
        weights = fit_rule_weights(client_df, rules)
        supports, class_sizes = fit_rule_support_sets(
            client_df, rules, target=target, row_prefix=client_id
        )
        local_rules[client_id] = rules
        local_weights[client_id] = weights
        local_support[client_id] = {key: frozenset(value) for key, value in supports.items()}
        local_classes[client_id] = {str(key): int(value) for key, value in class_sizes.items()}

    global_rules: tuple[Rule, ...] = ()
    provenance: Mapping[Any, tuple[str, ...]] = {}
    global_weights: Mapping[Any, float] = {}
    global_support: Mapping[Any, frozenset[Any]] = {}
    global_classes: Mapping[str, int] = {}
    global_default = None
    local_pairwise = pairwise_rule_jaccard(local_rules) if local_rules else {
        "pairwise_table": pd.DataFrame(),
        "pairwise_jaccard_antecedent": float("nan"),
        "pairwise_jaccard_full_rule": float("nan"),
    }
    rule_conflicts: Mapping[str, Any] = {
        "conflict_groups_table": pd.DataFrame(),
        "unique_antecedent_count": 0,
        "conflict_group_count": 0,
        "conflict_antecedent_rate": 0.0,
    }
    if client_tables:
        merged, sources = union_rules_with_provenance(local_rules)
        global_rules = tuple(merged)
        provenance = {key: tuple(value) for key, value in sources.items()}
        global_weights, global_support, global_classes = global_rule_support_context(
            client_tables, global_rules, target
        )
        global_default = majority_class_from_clients(client_tables, target)
        rule_conflicts = audit_rule_conflicts(global_rules, rule_sources=provenance)

    conflict_rules = global_rules if client_tables else central_rules
    conflict_audit = audit_rule_conflicts(
        conflict_rules,
        rule_sources=provenance if client_tables else None,
    )
    conflicts = _pre_resolution_conflicts(test, conflict_rules, target, conflict_audit)
    local_reduct_values = {
        name: result.selected_reduct
        for name, result in local_reducts.items()
        if result is not None
    }
    reduct_pairwise = pairwise_reduct_jaccard(local_reduct_values)
    frequency = feature_selection_frequency(local_reduct_values, feature_cols)
    frequency_values = pd.to_numeric(frequency["selection_frequency"], errors="coerce")
    central_local = [
        _jaccard(result.selected_reduct, central_reduct.selected_reduct)
        for result in local_reducts.values()
        if result is not None and central_reduct is not None
    ]
    local_sizes = [len(value) for value in local_reduct_values.values()]
    local_candidate_counts = [value.candidate_count for value in local_reducts.values() if value is not None]
    local_rule_counts = [len(rules) for rules in local_rules.values()]
    local_rule_condition_counts = [
        len(rule.conditions) for rules in local_rules.values() for rule in rules
    ]
    local_condition_means = [
        _rule_condition_summary(rules)["average_condition_count"] for rules in local_rules.values()
    ]
    global_rule_stats = _rule_condition_summary(global_rules)
    central_rule_stats = _rule_condition_summary(central_rules)
    matching_per_test = [len(matching_rules(row, conflict_rules)) for _, row in test.iterrows()]
    exact_count = int(conflict_audit.get("conflict_group_count", 0))
    exact_total = int(conflict_audit.get("unique_antecedent_count", 0))
    metrics = {
        "central_reduct_size": central_reduct.minimum_reduct_size if central_reduct else None,
        "central_reduct": list(central_reduct.selected_reduct) if central_reduct else list(feature_cols),
        "central_reduct_candidate_count": central_reduct.candidate_count if central_reduct else None,
        "central_dependency": central_reduct.full_dependency if central_reduct else None,
        "mean_local_reduct_size": float(np.mean(local_sizes)) if local_sizes else float("nan"),
        "std_local_reduct_size": float(np.std(local_sizes, ddof=0)) if local_sizes else float("nan"),
        "mean_local_reduct_candidate_count": float(np.mean(local_candidate_counts)) if local_candidate_counts else float("nan"),
        "mean_minimum_reduct_candidate_count": float(np.mean(local_candidate_counts)) if local_candidate_counts else float("nan"),
        "mean_reduct_jaccard": reduct_pairwise["mean_reduct_jaccard"],
        "reduct_instability": reduct_pairwise["reduct_instability"],
        "mean_local_central_reduct_jaccard": float(np.mean(central_local)) if central_local else float("nan"),
        "std_local_central_reduct_jaccard": float(np.std(central_local, ddof=0)) if central_local else float("nan"),
        "min_local_central_reduct_jaccard": float(np.min(central_local)) if central_local else float("nan"),
        "max_local_central_reduct_jaccard": float(np.max(central_local)) if central_local else float("nan"),
        "features_selected_by_all_clients": int(sum(value == 1.0 for value in frequency_values.dropna())) if local_sizes else 0,
        "features_selected_by_no_clients": int(sum(value == 0.0 for value in frequency_values.dropna())) if local_sizes else len(feature_cols),
        "mean_feature_selection_frequency": float(frequency_values.mean()) if frequency_values.notna().any() else float("nan"),
        "feature_selection_frequency_std": float(frequency_values.std(ddof=0)) if frequency_values.notna().any() else float("nan"),
        "mean_local_rule_count": float(np.mean(local_rule_counts)) if local_rule_counts else float("nan"),
        "global_rule_count": len(global_rules),
        "central_rule_average_condition_count": central_rule_stats["average_condition_count"],
        "central_rule_median_condition_count": central_rule_stats["median_condition_count"],
        "central_rule_min_condition_count": central_rule_stats["min_condition_count"],
        "central_rule_max_condition_count": central_rule_stats["max_condition_count"],
        "local_rule_total_count": len(local_rule_condition_counts),
        "local_rule_average_condition_count": float(np.mean(local_rule_condition_counts)) if local_rule_condition_counts else float("nan"),
        "local_rule_median_condition_count": float(np.median(local_rule_condition_counts)) if local_rule_condition_counts else float("nan"),
        "local_rule_min_condition_count": int(min(local_rule_condition_counts)) if local_rule_condition_counts else float("nan"),
        "local_rule_max_condition_count": int(max(local_rule_condition_counts)) if local_rule_condition_counts else float("nan"),
        "global_rule_average_condition_count": global_rule_stats["average_condition_count"],
        "global_rule_median_condition_count": global_rule_stats["median_condition_count"],
        "global_rule_min_condition_count": global_rule_stats["min_condition_count"],
        "global_rule_max_condition_count": global_rule_stats["max_condition_count"],
        "mean_local_rule_condition_count": float(np.nanmean(local_condition_means)) if local_condition_means and np.isfinite(local_condition_means).any() else float("nan"),
        "global_rule_condition_count": global_rule_stats["average_condition_count"],
        "central_rule_count": central_rule_stats["rule_count"],
        "pairwise_jaccard_antecedent": local_pairwise["pairwise_jaccard_antecedent"],
        "pairwise_jaccard_full_rule": local_pairwise["pairwise_jaccard_full_rule"],
        "rule_heterogeneity": 1.0 - local_pairwise["pairwise_jaccard_full_rule"] if np.isfinite(local_pairwise["pairwise_jaccard_full_rule"]) else float("nan"),
        "coverage": float(np.mean([count > 0 for count in matching_per_test])) if matching_per_test else float("nan"),
        **conflicts["metrics"],
    }
    tables = _reduct_tables(
        {**meta, "clients": client_tables, "target": target, "client_count": len(client_tables)},
        feature_cols,
        train,
        central_reduct,
        local_reducts,
        central_reduct_seconds,
        local_reduct_seconds,
    )
    local_rule_rows = []
    for client_id, rules in local_rules.items():
        reduct = local_reducts[client_id].selected_reduct if local_reducts[client_id] else feature_cols
        local_rule_rows.extend(
            _serialize_rule_rows(rules, client_id=client_id, selected_reduct=reduct)
        )
    tables.update(
        {
            "centralized_rules": pd.DataFrame(_serialize_rule_rows(central_rules, selected_reduct=central_cols), columns=["rule_no", "client_id", "selected_reduct", "reduct_size", "conditions", "decision", "rule_key", "condition_count", "source", "provenance"]),
            "local_rules": pd.DataFrame(local_rule_rows, columns=["rule_no", "client_id", "selected_reduct", "reduct_size", "conditions", "decision", "rule_key", "condition_count", "source", "provenance"]),
            "federated_rules": pd.DataFrame(_serialize_rule_rows(global_rules, provenance=provenance), columns=["rule_no", "client_id", "selected_reduct", "reduct_size", "conditions", "decision", "rule_key", "condition_count", "source", "provenance"]),
            "pairwise_rule_jaccard": local_pairwise["pairwise_table"] if not local_pairwise["pairwise_table"].empty else pd.DataFrame(columns=["client_i", "client_j", "jaccard_antecedent", "jaccard_full_rule"]),
            "conflict_groups": rule_conflicts.get("conflict_groups_table", pd.DataFrame(columns=["antecedent", "decisions", "rule_count", "sources"])),
            "conflict_cases": conflicts["table"],
            "rule_metrics": pd.DataFrame(
                [
                    _rule_metric_row("CENTRAL", central_rules),
                    *[
                        _rule_metric_row("LOCAL", rules, client_id)
                        for client_id, rules in local_rules.items()
                    ],
                    _rule_metric_row("FEDERATED", global_rules),
                ],
                columns=["scope", "client_id", "rule_count", "average_condition_count", "median_condition_count", "min_condition_count", "max_condition_count"],
            ),
        }
    )
    structural_build_seconds = perf_counter() - structural_build_started
    measured_local_reduct_seconds = [
        seconds for seconds in local_reduct_seconds.values() if seconds is not None
    ]
    metrics.update(
        {
            "central_reduct_seconds": central_reduct_seconds,
            "mean_local_reduct_seconds": (
                float(np.mean(measured_local_reduct_seconds))
                if measured_local_reduct_seconds
                else float("nan")
            ),
            "structural_build_seconds": structural_build_seconds,
        }
    )
    return RuleSystemArtifact(
        dataset=str(meta.get("dataset", "")),
        source=str(meta.get("source", "")),
        evaluation_mode=str(meta.get("evaluation_mode", "HOLDOUT")),
        fold=int(meta.get("fold", 1)),
        client_count=len(client_tables),
        seed=int(meta.get("seed", 42)),
        target=target,
        condition_columns=feature_cols,
        train_row_ids=tuple(int(x) for x in train["__row_id__"]) if "__row_id__" in train else (),
        test_row_ids=tuple(int(x) for x in test["__row_id__"]) if "__row_id__" in test else (),
        train=train.copy(deep=True),
        test=test.copy(deep=True),
        central_reduct_result=central_reduct,
        local_reduct_results=local_reducts,
        central_reduct_seconds=central_reduct_seconds,
        local_reduct_seconds=local_reduct_seconds,
        structural_build_seconds=structural_build_seconds,
        central_rules=central_rules,
        local_rules=local_rules,
        global_rules=global_rules,
        rule_provenance=provenance,
        central_default_class=central_default,
        default_class=global_default,
        central_rule_weights=central_weights,
        central_rule_support_sets={key: frozenset(value) for key, value in central_support.items()},
        central_class_sizes={str(key): int(value) for key, value in central_classes.items()},
        local_rule_weights=local_weights,
        local_rule_support_sets=local_support,
        local_class_sizes=local_classes,
        global_rule_weights=global_weights,
        global_rule_support_sets=global_support,
        global_class_sizes=global_classes,
        pre_resolution_conflict_flags=conflicts["flags"],
        pre_resolution_conflict_case_ids=conflicts["case_ids"],
        pre_resolution_conflicts={"table": conflicts["table"], "metrics": conflicts["metrics"]},
        structural_metrics=metrics,
        tables=tables,
        order_sensitivity_max_permutations=int(order_sensitivity_max_permutations),
    )


def _conflict_class_metrics(y_true: Sequence[Any], y_pred: Sequence[Any]) -> pd.DataFrame:
    if len(y_true) == 0:
        return pd.DataFrame(columns=["class", "support", "precision", "recall", "f1"])
    true = np.asarray(y_true, dtype=object)
    pred = np.asarray(y_pred, dtype=object)
    rows = []
    for label in sorted(set(true.tolist()), key=str):
        tp = int(np.sum((true == label) & (pred == label)))
        fp = int(np.sum((true != label) & (pred == label)))
        fn = int(np.sum((true == label) & (pred != label)))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "class": str(label),
                "support": int(np.sum(true == label)),
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return pd.DataFrame(rows)


def _evaluate_system(
    artifact: RuleSystemArtifact,
    *,
    system: str,
    rules: Sequence[Rule],
    default_class: Any,
    weights: Mapping[Any, float],
    supports: Mapping[Any, set[Any] | frozenset[Any]],
    class_sizes: Mapping[str, int],
    policy: str,
) -> dict[str, Any]:
    metrics = evaluate_rule_model(
        artifact.test,
        rules,
        default_class,
        artifact.target,
        prediction_policy=policy,
        rule_weights=weights,
        rule_support_sets=supports,
        class_sizes=class_sizes,
    )
    # Meeting-required HOLDOUT reporting is added outside evaluate_rule_model so
    # the frozen V6.1 evaluation primitive remains AST-identical to the audited
    # baseline.  These fields are descriptive outputs over the untouched test set.
    metrics["recall_macro"] = metrics["balanced_accuracy"]
    metrics["overall_coverage"] = metrics["coverage"]
    target_coverage = target_coverage_by_class(
        artifact.test[artifact.target], metrics["matched_rules"]
    )
    metrics["target_coverage_by_class"] = target_coverage
    finite_target_coverage = [
        value for value in target_coverage.values() if np.isfinite(value)
    ]
    metrics["target_coverage_macro"] = (
        float(np.mean(finite_target_coverage))
        if finite_target_coverage
        else float("nan")
    )
    flags = np.asarray(artifact.pre_resolution_conflict_flags, dtype=bool)
    if len(flags) != len(artifact.test):
        # Centralized evaluation uses its own rule workload; derive its flags when
        # it differs from the federated workload.
        flags = np.asarray(
            [len({str(r.decision) for r in matching_rules(row, rules)}) > 1 for _, row in artifact.test.iterrows()],
            dtype=bool,
        )
    if system == "CENTRALIZED":
        flags = np.asarray(
            [len({str(r.decision) for r in matching_rules(row, rules)}) > 1 for _, row in artifact.test.iterrows()],
            dtype=bool,
        )
    y_true = artifact.test[artifact.target].astype(str).to_numpy()[flags]
    y_pred = np.asarray(metrics["predictions"], dtype=object)[flags]
    if len(y_true):
        conflict_accuracy = float(np.mean(y_true == y_pred))
        conflict_ba = balanced_accuracy(y_true, y_pred)
        conflict_f1 = macro_f1_score(y_true, y_pred)
    else:
        conflict_accuracy = conflict_ba = conflict_f1 = float("nan")
    class_metrics = _conflict_class_metrics(y_true, y_pred)
    result = {
        **metrics,
        "system": system,
        "conflict_resolution_accuracy": conflict_accuracy,
        "conflict_balanced_accuracy": conflict_ba,
        "conflict_macro_f1": conflict_f1,
        "conflict_class_metrics": class_metrics,
        "conflict_case_count": int(flags.sum()),
        "conflict_cases_count": int(flags.sum()),
        "non_conflict_cases_count": int(len(flags) - flags.sum()),
    }
    return result


def evaluate_resolver(artifact: RuleSystemArtifact, policy: str) -> dict[str, Any]:
    """Evaluate one resolver without rebuilding reducts, rules, or conflicts."""
    name = str(policy).strip().upper()
    if name not in {
        "FIRST_MATCH",
        "SIMPLE_VOTING",
        "STANDARD_VOTING",
        "GLOBAL_STRENGTH",
        "POPULATION_STANDARD",
        "POPULATION_GLOBAL",
    }:
        raise ValueError(f"Unsupported prediction policy: {policy}")
    results: dict[str, Any] = {"policy": name}
    if artifact.central_rules:
        results["centralized"] = _evaluate_system(
            artifact,
            system="CENTRALIZED",
            rules=artifact.central_rules,
            default_class=artifact.central_default_class,
            weights=artifact.central_rule_weights,
            supports=artifact.central_rule_support_sets,
            class_sizes=artifact.central_class_sizes,
            policy=name,
        )
        results["centralized"].update(
            {
                "rules": artifact.central_rules,
                "rule_weights": artifact.central_rule_weights,
                "rule_support_sets": artifact.central_rule_support_sets,
                "class_sizes": artifact.central_class_sizes,
                "default_class": artifact.central_default_class,
            }
        )
    else:
        results["centralized"] = None
    if artifact.local_rules:
        results["federated"] = _evaluate_system(
            artifact,
            system="FEDERATED",
            rules=artifact.global_rules,
            default_class=artifact.default_class,
            weights=artifact.global_rule_weights,
            supports=artifact.global_rule_support_sets,
            class_sizes=artifact.global_class_sizes,
            policy=name,
        )
        fed = results["federated"]
        fed.update(artifact.structural_metrics)
        fed.update(
            {
                "clients": artifact.local_rules,
                "client_count": artifact.client_count,
                "local_rules": artifact.local_rules,
                "global_rules": artifact.global_rules,
                "global_rule_sources": artifact.rule_provenance,
                "local_reduct_results": artifact.local_reduct_results,
                "pre_resolution_conflict_case_ids": artifact.pre_resolution_conflict_case_ids,
                "pre_resolution_conflict_case_rate": artifact.structural_metrics["pre_resolution_conflict_case_rate"],
                "conflict_case_rate": artifact.structural_metrics["pre_resolution_conflict_case_rate"],
            }
        )
        class_metrics = fed["conflict_class_metrics"].copy()
        if not class_metrics.empty:
            class_metrics.insert(0, "client_count", artifact.client_count)
            class_metrics.insert(0, "fold", artifact.fold)
            class_metrics.insert(0, "dataset", artifact.dataset)
            class_metrics.insert(0, "policy", name)
        fed["conflict_class_metrics"] = class_metrics
    else:
        results["federated"] = None

    order_invariant = name != "FIRST_MATCH"
    fed = results["federated"]
    if fed is not None:
        if order_invariant:
            fed.update(
                {
                    "order_invariant_by_design": True,
                    "order_sensitivity_status": "ORDER_INVARIANT_BY_DESIGN",
                    "order_sensitivity_rate": 0.0,
                    "order_sensitivity_conflict_rate": 0.0,
                    "order_balanced_accuracy_mean": fed["balanced_accuracy"],
                    "order_balanced_accuracy_std": 0.0,
                    "order_balanced_accuracy_min": fed["balanced_accuracy"],
                    "order_balanced_accuracy_max": fed["balanced_accuracy"],
                    "order_distribution_table": pd.DataFrame(),
                }
            )
        else:
            order = audit_order_distribution(
                test=artifact.test,
                local_rules=artifact.local_rules,
                default_class=artifact.default_class,
                target=artifact.target,
                prediction_policy=name,
                rule_weights=artifact.global_rule_weights,
                rule_support_sets=artifact.global_rule_support_sets,
                class_sizes=artifact.global_class_sizes,
                max_permutations=artifact.order_sensitivity_max_permutations,
                seed=artifact.seed,
            )
            fed.update(order)
            fed["order_invariant_by_design"] = False
            fed["order_sensitivity_status"] = "MEASURED"
        conflict_rows = artifact.pre_resolution_conflicts["table"].copy()
        if not conflict_rows.empty:
            prediction_by_id = {
                int(row_id): pred
                for row_id, pred in zip(artifact.test_row_ids, fed["predictions"])
            }
            conflict_rows["predicted"] = conflict_rows["row_id"].map(prediction_by_id)
            conflict_rows["correct"] = conflict_rows["predicted"].astype(str) == conflict_rows["true"].astype(str)
        fed["conflict_cases_table"] = conflict_rows
    if results["centralized"] is not None:
        results["centralized"]["order_invariant_by_design"] = order_invariant
    return results


def evaluate_resolvers(
    artifact: RuleSystemArtifact,
    policies: Sequence[str],
) -> dict[str, dict[str, Any]]:
    """Evaluate a policy set on one identical structural artifact."""
    selected = list(dict.fromkeys(str(policy).strip().upper() for policy in policies))
    if "FIRST_MATCH" not in selected:
        selected = ["FIRST_MATCH", *selected]
    outputs = {policy: evaluate_resolver(artifact, policy) for policy in selected}
    baseline = outputs["FIRST_MATCH"]
    baseline_ids = artifact.pre_resolution_conflict_case_ids
    conflict_mask = np.asarray(artifact.pre_resolution_conflict_flags, dtype=bool)
    for policy, output in outputs.items():
        for system in ("centralized", "federated"):
            current = output.get(system)
            first = baseline.get(system)
            if current is None or first is None:
                continue
            current_predictions = np.asarray(current["predictions"], dtype=object)
            first_predictions = np.asarray(first["predictions"], dtype=object)
            disagreement = current_predictions.astype(str) != first_predictions.astype(str)
            current["all_case_disagreement_rate_vs_first_match"] = float(np.mean(disagreement)) if len(disagreement) else float("nan")
            mask = conflict_mask if system == "federated" else np.asarray(
                [len({str(rule.decision) for rule in matching_rules(row, artifact.central_rules)}) > 1 for _, row in artifact.test.iterrows()],
                dtype=bool,
            )
            current["conflict_case_disagreement_rate_vs_first_match"] = (
                float(np.mean(disagreement[mask])) if mask.any() else float("nan")
            )
            current["disagreement_vs_first_match"] = current["all_case_disagreement_rate_vs_first_match"]
            current["conflict_disagreement_vs_first_match"] = current["conflict_case_disagreement_rate_vs_first_match"]
            current["pre_resolution_conflict_case_ids"] = baseline_ids if system == "FEDERATED" else tuple(
                int(row["__row_id__"]) if "__row_id__" in row.index else pos
                for pos, (_, row) in enumerate(artifact.test.iterrows())
                if mask[pos]
            )
            current["order_invariant_by_design"] = policy != "FIRST_MATCH"
    return {policy: outputs[policy] for policy in selected if policy in set(str(x).strip().upper() for x in policies)}
