from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def restore_evaluate_rule_model() -> None:
    rel = "roughset/evaluation.py"
    text = read(rel)
    start = text.index("def evaluate_rule_model(")
    end = text.index("\ndef run_centralized(", start)
    original = '''def evaluate_rule_model(
    test: pd.DataFrame,
    rules: Sequence[Rule],
    default_class: Any,
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    preds, matched = predict_table(
        test,
        rules,
        default_class,
        prediction_policy=prediction_policy,
        rule_weights=rule_weights,
        rule_support_sets=rule_support_sets,
        class_sizes=class_sizes,
    )

    return {
        "accuracy": classification_accuracy(test[target], preds),
        "balanced_accuracy": balanced_accuracy(test[target], preds),
        "macro_f1": macro_f1_score(test[target], preds),
        "coverage": float(np.mean([len(x) > 0 for x in matched])) if len(test) else 0.0,
        "predictions": preds,
        "matched_rules": matched,
        "prediction_policy": str(prediction_policy).strip().upper(),
    }

'''
    text = text[:start] + original + text[end + 1 :]
    write(rel, text)


def patch_pipeline() -> None:
    rel = "roughset/pipeline.py"
    text = read(rel)
    text = replace_once(
        text,
        "    pairwise_rule_jaccard,\n)",
        "    pairwise_rule_jaccard,\n    target_coverage_by_class,\n)",
        "pipeline import target coverage",
    )
    text = replace_once(
        text,
        '    if name not in {"FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"}:\n        raise ValueError(f"Unsupported prediction policy: {policy}")',
        '    if name not in {\n        "FIRST_MATCH",\n        "SIMPLE_VOTING",\n        "STANDARD_VOTING",\n        "GLOBAL_STRENGTH",\n        "POPULATION_STANDARD",\n        "POPULATION_GLOBAL",\n    }:\n        raise ValueError(f"Unsupported prediction policy: {policy}")',
        "pipeline six-policy whitelist",
    )
    anchor = '''    metrics = evaluate_rule_model(
        artifact.test,
        rules,
        default_class,
        artifact.target,
        prediction_policy=policy,
        rule_weights=weights,
        rule_support_sets=supports,
        class_sizes=class_sizes,
    )
    flags = np.asarray(artifact.pre_resolution_conflict_flags, dtype=bool)
'''
    replacement = '''    metrics = evaluate_rule_model(
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
'''
    text = replace_once(text, anchor, replacement, "pipeline holdout metrics")
    write(rel, text)


def patch_app() -> None:
    rel = "roughset/app.py"
    text = read(rel)
    text = replace_once(
        text,
        '    if policy not in {"FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"}:\n        raise ValueError("Unsupported prediction policy.")',
        '    if policy not in {\n        "FIRST_MATCH",\n        "SIMPLE_VOTING",\n        "STANDARD_VOTING",\n        "GLOBAL_STRENGTH",\n        "POPULATION_STANDARD",\n        "POPULATION_GLOBAL",\n    }:\n        raise ValueError("Unsupported prediction policy.")',
        "app six-policy whitelist",
    )
    write(rel, text)


def patch_batch() -> None:
    rel = "roughset/batch.py"
    text = read(rel)
    text = replace_once(
        text,
        '''SUPPORTED_POLICIES = (
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
)
''',
        '''SUPPORTED_POLICIES = (
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
    "POPULATION_STANDARD",
    "POPULATION_GLOBAL",
)
''',
        "batch supported policies",
    )
    old_row = '''                    {
                        "dataset": artifact.dataset,
                        "fold": artifact.fold,
                        "client_count": artifact.client_count,
                        "policy": policy,
                        "accuracy": fed.get("accuracy"),
                        "balanced_accuracy": fed.get("balanced_accuracy"),
                        "macro_f1": fed.get("macro_f1"),
                        "coverage": fed.get("coverage"),
'''
    new_row = '''                    {
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
'''
    text = replace_once(text, old_row, new_row, "batch resolver metadata")
    text = replace_once(
        text,
        '''                        "primary_evaluation_metrics": [
                            "balanced_accuracy",
                            "macro_f1",
                            "coverage",
                            "conflict_balanced_accuracy",
                            "conflict_macro_f1",
                            "mean_variation_ratio",
                        ],
''',
        '''                        "primary_evaluation_metrics": [
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
''',
        "resolver manifest metrics",
    )
    text = replace_once(
        text,
        '''        "primary_evaluation_metrics": [
            "balanced_accuracy",
            "macro_f1",
            "coverage",
            "ruleset_size",
''',
        '''        "primary_evaluation_metrics": [
            "accuracy",
            "recall_macro",
            "macro_f1",
            "balanced_accuracy",
            "overall_coverage",
            "target_coverage_macro",
            "ruleset_size",
''',
        "batch manifest metrics",
    )
    marker = '''        "legacy_project_metrics_are_supplementary": [
'''
    insert = '''        "experimental_population_policies": {
            "POPULATION_STANDARD": "deduplicated unique support population U_d = T_d * (U_d/T_d)",
            "POPULATION_GLOBAL": "GlobalStrength (U_d/N_d) multiplied by nonredundancy ratio (U_d/T_d)",
            "literature_status": "project-defined experimental variants; not attributed to prior literature",
        },
'''
    text = replace_once(text, marker, insert + marker, "batch population manifest")
    write(rel, text)


def patch_config() -> None:
    rel = "config.json"
    text = read(rel)
    text = replace_once(
        text,
        '''      "STANDARD_VOTING",
      "GLOBAL_STRENGTH"
''',
        '''      "STANDARD_VOTING",
      "GLOBAL_STRENGTH",
      "POPULATION_STANDARD",
      "POPULATION_GLOBAL"
''',
        "config six policies",
    )
    write(rel, text)


def main() -> None:
    restore_evaluate_rule_model()
    patch_pipeline()
    patch_app()
    patch_batch()
    patch_config()
    print("POPULATION_EXPERIMENT_PATCH=APPLIED")


if __name__ == "__main__":
    main()
