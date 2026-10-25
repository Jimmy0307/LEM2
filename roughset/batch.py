from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
import json

import pandas as pd
import numpy as np

from .app import run_application, _write_dataset_output, _summary, _aggregate_cv
from .environment import environment_manifest
from .established_metrics import audit_order_variation_ratio


SUPPORTED_POLICIES = (
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
    "POPULATION_STANDARD",
    "POPULATION_GLOBAL",
)


def _normalized_policies(config: Mapping[str, Any], policies: Sequence[str] | None) -> list[str]:
    raw = policies
    if raw is None:
        raw = config.get("batch", {}).get("prediction_policies", SUPPORTED_POLICIES)
    normalized: list[str] = []
    seen: set[str] = set()
    for policy in raw:
        name = str(policy).upper().strip()
        if name not in SUPPORTED_POLICIES:
            raise ValueError(f"Unsupported batch prediction policy: {policy}")
        if name not in seen:
            normalized.append(name)
            seen.add(name)
    if not normalized:
        raise ValueError("At least one batch prediction policy is required.")
    return normalized


def run_policy_matrix(
    config: Mapping[str, Any],
    policies: Sequence[str] | None = None,
    run_id: str | None = None,
    fetcher=None,
) -> dict[str, Any]:
    """Build structural artifacts once, then evaluate each prediction policy."""
    base_config = deepcopy(dict(config))
    selected = _normalized_policies(base_config, policies)
    actual_run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

    configured_output = Path(base_config.get("report", {}).get("outputs_folder", "./outputs"))
    root_output = configured_output / "batch_runs" / actual_run_id
    root_output.mkdir(parents=True, exist_ok=True)

    build_config = deepcopy(base_config)
    build_config.setdefault("report", {})["outputs_folder"] = str(root_output / "structural")
    build = run_application(build_config, fetcher=fetcher, prediction_policies=selected)

    structural_rows: list[dict[str, Any]] = []
    resolver_rows: list[dict[str, Any]] = []
    disagreement_rows: list[dict[str, Any]] = []
    conflict_class_tables: list[pd.DataFrame] = []
    chain_rows_by_artifact: dict[tuple[str, int, int], dict[str, Any]] = {}
    results: dict[str, Any] = {policy: {"datasets": {}, "config": build["config"]} for policy in selected}
    artifacts_by_dataset: dict[str, list[Any]] = {}

    def put_table(folder: Path, name: str, frames: list[pd.DataFrame]):
        available = [frame for frame in frames if isinstance(frame, pd.DataFrame)]
        if available:
            pd.concat(available, ignore_index=True).to_csv(
                folder / name, index=False, encoding="utf-8-sig"
            )

    for dataset_key, dataset_result in build["datasets"].items():
        artifacts = list(dataset_result.get("structural_artifacts", []))
        artifact_policy_results = list(dataset_result.get("artifact_policy_results", []))
        artifacts_by_dataset[dataset_key] = artifacts
        structural_folder = root_output / "structural" / dataset_key
        structural_folder.mkdir(parents=True, exist_ok=True)
        table_frames: dict[str, list[pd.DataFrame]] = {}
        for artifact in artifacts:
            metrics = dict(artifact.structural_metrics)
            structural_rows.append(
                {
                    "dataset": artifact.dataset,
                    "fold": artifact.fold,
                    "client_count": artifact.client_count,
                    "central_reduct_size": metrics.get("central_reduct_size"),
                    "central_reduct": json.dumps(metrics.get("central_reduct", []), ensure_ascii=False),
                    "central_reduct_candidate_count": metrics.get("central_reduct_candidate_count"),
                    "central_dependency": metrics.get("central_dependency"),
                    "mean_local_reduct_size": metrics.get("mean_local_reduct_size"),
                    "std_local_reduct_size": metrics.get("std_local_reduct_size"),
                    "mean_local_reduct_candidate_count": metrics.get("mean_local_reduct_candidate_count"),
                    "mean_minimum_reduct_candidate_count": metrics.get("mean_minimum_reduct_candidate_count"),
                    "features_selected_by_all_clients": metrics.get("features_selected_by_all_clients"),
                    "features_selected_by_no_clients": metrics.get("features_selected_by_no_clients"),
                    "mean_feature_selection_frequency": metrics.get("mean_feature_selection_frequency"),
                    "feature_selection_frequency_std": metrics.get("feature_selection_frequency_std"),
                    "mean_reduct_jaccard": metrics.get("mean_reduct_jaccard"),
                    "reduct_instability": metrics.get("reduct_instability"),
                    "mean_local_central_reduct_jaccard": metrics.get("mean_local_central_reduct_jaccard"),
                    "std_local_central_reduct_jaccard": metrics.get("std_local_central_reduct_jaccard"),
                    "min_local_central_reduct_jaccard": metrics.get("min_local_central_reduct_jaccard"),
                    "max_local_central_reduct_jaccard": metrics.get("max_local_central_reduct_jaccard"),
                    "mean_local_rule_count": metrics.get("mean_local_rule_count"),
                    "global_rule_count": metrics.get("global_rule_count"),
                    "central_rule_count": metrics.get("central_rule_count"),
                    "mean_local_rule_condition_count": metrics.get("mean_local_rule_condition_count"),
                    "global_rule_condition_count": metrics.get("global_rule_condition_count"),
                    "central_rule_average_condition_count": metrics.get("central_rule_average_condition_count"),
                    "central_rule_median_condition_count": metrics.get("central_rule_median_condition_count"),
                    "central_rule_min_condition_count": metrics.get("central_rule_min_condition_count"),
                    "central_rule_max_condition_count": metrics.get("central_rule_max_condition_count"),
                    "local_rule_total_count": metrics.get("local_rule_total_count"),
                    "local_rule_average_condition_count": metrics.get("local_rule_average_condition_count"),
                    "local_rule_median_condition_count": metrics.get("local_rule_median_condition_count"),
                    "local_rule_min_condition_count": metrics.get("local_rule_min_condition_count"),
                    "local_rule_max_condition_count": metrics.get("local_rule_max_condition_count"),
                    "global_rule_average_condition_count": metrics.get("global_rule_average_condition_count"),
                    "global_rule_median_condition_count": metrics.get("global_rule_median_condition_count"),
                    "global_rule_min_condition_count": metrics.get("global_rule_min_condition_count"),
                    "global_rule_max_condition_count": metrics.get("global_rule_max_condition_count"),
                    "rule_jaccard_antecedent": metrics.get("pairwise_jaccard_antecedent"),
                    "rule_jaccard_full": metrics.get("pairwise_jaccard_full_rule"),
                    "rule_heterogeneity": metrics.get("rule_heterogeneity"),
                    "coverage": metrics.get("coverage"),
                    "pre_resolution_conflict_case_rate": metrics.get("pre_resolution_conflict_case_rate"),
                    "exact_conflict_antecedent_rate": metrics.get("exact_conflict_antecedent_rate"),
                    "mean_matching_rules_per_conflict_case": metrics.get("mean_matching_rules_per_conflict_case"),
                    "mean_distinct_decisions_per_conflict_case": metrics.get("mean_distinct_decisions_per_conflict_case"),
                    "conflict_cases_count": metrics.get("conflict_cases_count"),
                    "non_conflict_cases_count": metrics.get("non_conflict_cases_count"),
                    "mean_matching_rules_per_test_case": metrics.get("mean_matching_rules_per_test_case"),
                    "median_matching_rules_per_conflict_case": metrics.get("median_matching_rules_per_conflict_case"),
                    "max_matching_rules_per_conflict_case": metrics.get("max_matching_rules_per_conflict_case"),
                    "exact_conflict_antecedent_count": metrics.get("exact_conflict_antecedent_count"),
                    "central_reduct_seconds": metrics.get("central_reduct_seconds"),
                    "mean_local_reduct_seconds": metrics.get("mean_local_reduct_seconds"),
                    "structural_build_seconds": metrics.get("structural_build_seconds"),
                    "rule_system_build_seconds": metrics.get("rule_system_build_seconds"),
                }
            )
            for key, table in artifact.tables.items():
                enriched = table.copy()
                for column, value in (
                    ("dataset", artifact.dataset),
                    ("fold", artifact.fold),
                    ("client_count", artifact.client_count),
                ):
                    if column not in enriched.columns:
                        enriched.insert(0, column, value)
                table_frames.setdefault(key, []).append(enriched)

        structural_files = {
            "central_reduct": "central_reduct.csv",
            "local_reducts": "local_reducts.csv",
            "reduct_candidates": "reduct_candidates.csv",
            "pairwise_reduct_jaccard": "pairwise_reduct_jaccard.csv",
            "feature_selection_frequency": "feature_selection_frequency.csv",
            "centralized_rules": "centralized_rules.csv",
            "local_rules": "local_rules.csv",
            "federated_rules": "federated_rules.csv",
            "pairwise_rule_jaccard": "pairwise_rule_jaccard.csv",
            "conflict_groups": "conflict_groups.csv",
            "conflict_cases": "conflict_cases.csv",
            "rule_metrics": "rule_metrics.csv",
        }
        for key, filename in structural_files.items():
            put_table(structural_folder, filename, table_frames.get(key, []))
        (structural_folder / "structural_manifest.json").write_text(
            json.dumps(
                {
                    "dataset": dataset_result.get("name"),
                    "source": dataset_result.get("source"),
                    "evaluation_mode": dataset_result.get("evaluation_mode"),
                    "reduct_enabled": bool(build["config"]["reduct"]["enabled"]),
                    "reduct_method": build["config"]["reduct"]["method"],
                    "record_all_candidates": bool(build["config"]["reduct"]["record_all_candidates"]),
                    "reduct_selection_policy": "lexicographic_first_among_minimum_cardinality",
                    "structural_configurations": [
                        {"fold": artifact.fold, "client_count": artifact.client_count, "seed": artifact.seed}
                        for artifact in artifacts
                    ],
                    "conflict_rate_definition": "pre-resolution; all matching rules with more than one distinct decision",
                    "derived_metrics_are_not_original_rough_set_quantities": True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        for policy in selected:
            results[policy]["datasets"][dataset_key] = {
                **dataset_result,
                "centralized": (dataset_result.get("policy_results", {}).get(policy) or {}).get("centralized"),
                "federated": (dataset_result.get("policy_results", {}).get(policy) or {}).get("federated"),
            }
            policy_structural_rows = []
            policy_fed_rows = []
            policy_conflict_case_tables: list[pd.DataFrame] = []
            for artifact, policy_result in zip(artifacts, artifact_policy_results):
                evaluated = policy_result.get(policy, {})
                central = evaluated.get("centralized") or {}
                fed = evaluated.get("federated") or {}

                if fed and artifact.local_rules:
                    if policy == "FIRST_MATCH":
                        variation = audit_order_variation_ratio(
                            test=artifact.test,
                            local_rules=artifact.local_rules,
                            default_class=artifact.default_class,
                            prediction_policy=policy,
                            rule_weights=artifact.global_rule_weights,
                            rule_support_sets=artifact.global_rule_support_sets,
                            class_sizes=artifact.global_class_sizes,
                            conflict_case_flags=artifact.pre_resolution_conflict_flags,
                            max_permutations=artifact.order_sensitivity_max_permutations,
                            seed=artifact.seed,
                        )
                        fed.update(variation)
                    else:
                        fed.update(
                            {
                                "variation_ratio_by_case": tuple(),
                                "mean_variation_ratio": 0.0,
                                "mean_variation_ratio_conflict": 0.0,
                                "variation_ratio_orderings_checked": 0,
                            }
                        )

                policy_fed_rows.append(fed)
                case_table=fed.get("conflict_cases_table")
                if isinstance(case_table,pd.DataFrame):
                    case_copy=case_table.copy()
                    for column,value in (("dataset",artifact.dataset),("fold",artifact.fold),("client_count",artifact.client_count),("policy",policy)):
                        if column not in case_copy.columns: case_copy.insert(0,column,value)
                    policy_conflict_case_tables.append(case_copy)
                resolver_rows.append(
                    {
                        "dataset": artifact.dataset,
                        "dataset_rows": len(artifact.train) + len(artifact.test),
                        "dataset_columns": len(artifact.condition_columns) + 1,
                        "condition_attribute_count": len(artifact.condition_columns),
                        "target_column": artifact.target,
                        "class_count": len(
                            set(artifact.train[artifact.target].astype(str).tolist())
                            | set(artifact.test[artifact.target].astype(str).tolist())
                        ),
                        "train_rows": len(artifact.train),
                        "test_rows": len(artifact.test),
                        "fold": artifact.fold,
                        "client_count": artifact.client_count,
                        "policy": policy,
                        "accuracy": fed.get("accuracy"),
                        "recall_macro": fed.get("recall_macro"),
                        "balanced_accuracy": fed.get("balanced_accuracy"),
                        "macro_f1": fed.get("macro_f1"),
                        "coverage": fed.get("coverage"),
                        "overall_coverage": fed.get("overall_coverage"),
                        "target_coverage_macro": fed.get("target_coverage_macro"),
                        "target_coverage_by_class": json.dumps(
                            fed.get("target_coverage_by_class", {}),
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        "target_candidate_coverage_macro": fed.get("target_candidate_coverage_macro"),
                        "target_candidate_coverage_by_class": json.dumps(
                            fed.get("target_candidate_coverage_by_class", {}),
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        "conflict_resolution_accuracy": fed.get("conflict_resolution_accuracy"),
                        "conflict_balanced_accuracy": fed.get("conflict_balanced_accuracy"),
                        "conflict_macro_f1": fed.get("conflict_macro_f1"),
                        "disagreement_vs_first_match": fed.get("disagreement_vs_first_match"),
                        "conflict_disagreement_vs_first_match": fed.get("conflict_disagreement_vs_first_match"),
                        "all_case_disagreement_rate_vs_first_match": fed.get("all_case_disagreement_rate_vs_first_match"),
                        "conflict_case_disagreement_rate_vs_first_match": fed.get("conflict_case_disagreement_rate_vs_first_match"),
                        "order_invariant_by_design": fed.get("order_invariant_by_design"),
                        "order_sensitivity_status": fed.get("order_sensitivity_status"),
                        "order_sensitivity_rate": fed.get("order_sensitivity_rate"),
                        "mean_variation_ratio": fed.get("mean_variation_ratio"),
                        "mean_variation_ratio_conflict": fed.get("mean_variation_ratio_conflict"),
                        "order_balanced_accuracy_mean": fed.get("order_balanced_accuracy_mean"),
                        "order_balanced_accuracy_std": fed.get("order_balanced_accuracy_std"),
                        "order_balanced_accuracy_min": fed.get("order_balanced_accuracy_min"),
                        "order_balanced_accuracy_max": fed.get("order_balanced_accuracy_max"),
                        "central_accuracy": central.get("accuracy"),
                        "central_balanced_accuracy": central.get("balanced_accuracy"),
                        "central_macro_f1": central.get("macro_f1"),
                        "central_coverage": central.get("coverage"),
                    }
                )
                disagreement_rows.extend(
                    {
                        "dataset": artifact.dataset,
                        "fold": artifact.fold,
                        "client_count": artifact.client_count,
                        "policy": policy,
                        "system": system,
                        "all_case_disagreement_rate_vs_first_match": output.get("all_case_disagreement_rate_vs_first_match"),
                        "conflict_case_disagreement_rate_vs_first_match": output.get("conflict_case_disagreement_rate_vs_first_match"),
                    }
                    for system, output in (("CENTRALIZED", central), ("FEDERATED", fed))
                    if output
                )
                for system, output in (("CENTRALIZED", central), ("FEDERATED", fed)):
                    class_table = output.get("conflict_class_metrics")
                    if isinstance(class_table, pd.DataFrame) and not class_table.empty:
                        class_copy = class_table.copy()
                        class_copy.insert(0, "system", system)
                        conflict_class_tables.append(class_copy)

                metric = artifact.structural_metrics
                chain_key=(artifact.dataset,artifact.fold,artifact.client_count)
                chain=chain_rows_by_artifact.setdefault(
                    chain_key,
                    {
                        "dataset": artifact.dataset,
                        "fold": artifact.fold,
                        "client_count": artifact.client_count,
                        "central_reduct_size": metric.get("central_reduct_size"),
                        "mean_local_reduct_size": metric.get("mean_local_reduct_size"),
                        "reduct_instability": metric.get("reduct_instability"),
                        "mean_local_central_reduct_jaccard": metric.get("mean_local_central_reduct_jaccard"),
                        "rule_heterogeneity": metric.get("rule_heterogeneity"),
                        "pre_resolution_conflict_case_rate": metric.get("pre_resolution_conflict_case_rate"),
                    },
                )
                chain[f"{policy}_conflict_balanced_accuracy"] = fed.get("conflict_balanced_accuracy")
                chain[f"{policy}_balanced_accuracy"] = fed.get("balanced_accuracy")
                policy_structural_rows.append(chain)

            resolver_folder = root_output / "resolver" / policy / dataset_key
            resolver_folder.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                [row for row in resolver_rows if row["dataset"] == dataset_result.get("name") and row["policy"] == policy]
            ).to_csv(resolver_folder / "resolver_summary.csv", index=False, encoding="utf-8-sig")
            policy_class_tables = [
                table for table in conflict_class_tables
                if "policy" in table.columns and (table["policy"] == policy).all()
            ]
            put_table(
                resolver_folder,
                "conflict_class_metrics.csv",
                policy_class_tables or [pd.DataFrame(columns=["dataset", "fold", "client_count", "policy", "system", "class", "support", "precision", "recall", "f1"])],
            )
            put_table(resolver_folder,"conflict_cases.csv",policy_conflict_case_tables or [pd.DataFrame(columns=["dataset","fold","client_count","policy","row_id","true","matching_rules","decisions","predicted","correct"])])
            put_table(
                resolver_folder,
                "policy_disagreement.csv",
                [pd.DataFrame([row for row in disagreement_rows if row["dataset"] == dataset_result.get("name") and row["policy"] == policy])],
            )
            (resolver_folder / "resolver_manifest.json").write_text(
                json.dumps(
                    {
                        "dataset": dataset_result.get("name"),
                        "policy": policy,
                        "order_invariant_by_design": policy != "FIRST_MATCH",
                        "coverage_is_structural_and_shared": True,
                        "primary_evaluation_metrics": [
                            "accuracy",
                            "recall_macro",
                            "macro_f1",
                            "balanced_accuracy",
                            "overall_coverage",
                            "target_coverage_macro",
                            "conflict_balanced_accuracy",
                            "conflict_macro_f1",
                            "mean_variation_ratio",
                        ],
                        "experimental_population_policies": [
                            "POPULATION_STANDARD",
                            "POPULATION_GLOBAL",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            # Preserve the previous per-policy result tree for existing scripts.
            legacy_folder = root_output / policy / dataset_key
            legacy_folder.mkdir(parents=True, exist_ok=True)
            policy_dataset = results[policy]["datasets"][dataset_key]
            if dataset_result.get("evaluation_mode") == "K_FOLD_CV":
                policy_dataset["centralized"] = _aggregate_cv(
                    [{"centralized": (fold.get("policy_results", {}).get(policy) or {}).get("centralized")} for fold in dataset_result["fold_results"]],
                    "centralized",
                )
                policy_dataset["federated"] = _aggregate_cv(
                    [{"federated": (fold.get("policy_results", {}).get(policy) or {}).get("federated")} for fold in dataset_result["fold_results"]],
                    "federated",
                )
            _write_dataset_output(policy_dataset, legacy_folder)

    structural_summary = pd.DataFrame(structural_rows)
    resolver_summary = pd.DataFrame(resolver_rows)

    def aggregate_folds(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
        rows = []
        if frame.empty:
            return pd.DataFrame()
        for group_key, group in frame.groupby(group_columns, dropna=False, sort=True):
            if not isinstance(group_key, tuple):
                group_key = (group_key,)
            row = dict(zip(group_columns, group_key))
            row["fold_count"] = int(group["fold"].nunique()) if "fold" in group else len(group)
            for column in frame.columns:
                if column in group_columns or column == "fold":
                    continue
                if column == "order_invariant_by_design":
                    if group[column].notna().any():
                        row[column] = bool(group[column].iloc[0])
                    continue
                numeric = pd.to_numeric(group[column], errors="coerce")
                if not numeric.notna().any():
                    if pd.api.types.is_numeric_dtype(frame[column]) or group[column].isna().all():
                        row[f"{column}_mean"] = float("nan")
                        row[f"{column}_std"] = float("nan")
                        row[f"{column}_min"] = float("nan")
                        row[f"{column}_max"] = float("nan")
                    continue
                values = numeric.to_numpy(dtype=float)
                values = values[np.isfinite(values)]
                if not len(values):
                    continue
                row[f"{column}_mean"] = float(values.mean())
                row[f"{column}_std"] = float(values.std(ddof=0))
                row[f"{column}_min"] = float(values.min())
                row[f"{column}_max"] = float(values.max())
            rows.append(row)
        return pd.DataFrame(rows)

    structural_aggregate = aggregate_folds(structural_summary, ["dataset", "client_count"])
    resolver_aggregate = aggregate_folds(
        resolver_summary, ["dataset", "client_count", "policy"]
    )
    for policy in selected:
        summaries=[]
        for dataset_result in results[policy]["datasets"].values():
            summary=_summary(dataset_result)
            summary["prediction_policy"]=policy
            summaries.append(summary)
        results[policy]["summary"]=pd.DataFrame(summaries)
        results[policy]["root_output"]=str(root_output / policy)
    structural_summary.to_csv(root_output / "structural_summary.csv", index=False, encoding="utf-8-sig")
    resolver_summary.to_csv(root_output / "resolver_summary.csv", index=False, encoding="utf-8-sig")
    structural_aggregate.to_csv(root_output / "structural_summary_aggregate.csv", index=False, encoding="utf-8-sig")
    resolver_aggregate.to_csv(root_output / "resolver_summary_aggregate.csv", index=False, encoding="utf-8-sig")
    put_table(root_output, "policy_disagreement.csv", [pd.DataFrame(disagreement_rows)])
    put_table(root_output, "conflict_class_metrics.csv", conflict_class_tables or [pd.DataFrame(columns=["dataset", "fold", "client_count", "policy", "system", "class", "support", "precision", "recall", "f1"])])
    pd.DataFrame(chain_rows_by_artifact.values()).to_csv(root_output / "research_chain_summary.csv", index=False, encoding="utf-8-sig")
    batch_summary = resolver_summary.copy()
    if "policy" in batch_summary.columns and "prediction_policy" not in batch_summary.columns:
        batch_summary.insert(0, "prediction_policy", batch_summary["policy"])
    batch_summary.to_csv(root_output / "batch_summary.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "run_id": actual_run_id,
        "prediction_policies": selected,
        "evaluation_mode": str(base_config.get("evaluation", {}).get("mode", "HOLDOUT")).upper(),
        "base_outputs_folder": str(configured_output),
        "root_output": str(root_output),
        "environment": environment_manifest(),
        "base_config": base_config,
        "reduct_selection_policy": "lexicographic_first_among_minimum_cardinality",
        "record_all_candidates": bool(base_config.get("reduct", {}).get("record_all_candidates", True)),
        "structural_artifacts_built_once_and_reused": True,
        "primary_evaluation_metrics": [
            "accuracy",
            "recall_macro",
            "macro_f1",
            "balanced_accuracy",
            "overall_coverage",
            "target_coverage_macro",
            "ruleset_size",
            "mean_conditions_per_rule",
            "pairwise_antecedent_jaccard",
            "conflict_set_count_and_proportion",
            "conflict_balanced_accuracy",
            "conflict_macro_f1",
            "mean_variation_ratio",
        ],
        "experimental_population_policies": {
            "POPULATION_STANDARD": "deduplicated unique support population U_d = T_d * (U_d/T_d)",
            "POPULATION_GLOBAL": "GlobalStrength (U_d/N_d) multiplied by nonredundancy ratio (U_d/T_d)",
            "literature_status": "project-defined experimental variants; not attributed to prior literature",
        },
        "legacy_project_metrics_are_supplementary": [
            "conflict_resolution_accuracy",
            "order_sensitivity_rate",
            "rule_heterogeneity",
        ],
    }
    (root_output / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    configured_output.mkdir(parents=True, exist_ok=True)
    (configured_output / "latest_batch.txt").write_text(str(root_output), encoding="utf-8")

    return {
        "run_id": actual_run_id,
        "root_output": str(root_output),
        "summary": batch_summary,
        "results": results,
        "policies": selected,
        "structural_summary": structural_summary,
        "resolver_summary": resolver_summary,
        "structural_artifacts": artifacts_by_dataset,
    }
