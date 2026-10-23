from __future__ import annotations

import ast
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from roughset.app import run_application
from roughset.evaluation import matching_rules, population_support_summary, predict_with_policy
from roughset.research_evidence import transition_redundancy_evidence


POLICIES = (
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
    "POPULATION_STANDARD",
    "POPULATION_GLOBAL",
)


def _rule_text(rule) -> str:
    if not rule.conditions:
        return "TRUE -> " + str(rule.decision)
    antecedent = " AND ".join(f"{attr}={value}" for attr, value in rule.conditions)
    return f"{antecedent} -> {rule.decision}"


def _scores_for_case(artifact, matched):
    by_decision = defaultdict(list)
    for rule in matched:
        by_decision[str(rule.decision)].append(rule)

    pop = population_support_summary(
        matched,
        artifact.global_rule_support_sets,
        class_sizes=artifact.global_class_sizes,
    )

    scores = {}
    for decision, rules in by_decision.items():
        summary = pop.get(decision) or pop.get(next((k for k in pop if str(k) == decision), decision), {})
        simple = float(len(rules))
        standard = float(sum(artifact.global_rule_weights.get(rule.key, 0.0) for rule in rules))
        unique_population = float(summary.get("unique_population", 0.0))
        global_strength = float(summary.get("global_strength", 0.0))
        nonredundancy = float(summary.get("population_nonredundancy_ratio", 0.0))
        scores[decision] = {
            "simple_score": simple,
            "standard_score": standard,
            "population_standard_score": unique_population,
            "global_strength_score": global_strength,
            "population_global_score": global_strength * nonredundancy,
            **{k: float(v) for k, v in summary.items()},
        }
    return scores


def _prediction_map(artifact, row):
    out = {}
    for policy in POLICIES:
        pred, matched = predict_with_policy(
            row,
            artifact.global_rules,
            artifact.default_class,
            policy=policy,
            rule_weights=artifact.global_rule_weights,
            rule_support_sets=artifact.global_rule_support_sets,
            class_sizes=artifact.global_class_sizes,
        )
        out[policy] = str(pred)
    return out


def _status(true_value: str, old: str, new: str) -> str:
    old_ok = old == true_value
    new_ok = new == true_value
    if not old_ok and new_ok:
        return "CORRECTED"
    if old_ok and not new_ok:
        return "HARMED"
    if old != new:
        return "CHANGED_SAME_CORRECTNESS"
    return "UNCHANGED"


def _case_impact(row: dict[str, Any]) -> tuple:
    category_priority = {
        "BOTH_CORRECTED": 90,
        "PS_CORRECTED": 80,
        "PG_CORRECTED": 80,
        "BOTH_HARMED": 75,
        "PS_HARMED": 70,
        "PG_HARMED": 70,
        "MIXED": 65,
        "CHANGED": 55,
        "HIGH_REDUNDANCY": 40,
        "UNCHANGED": 10,
    }
    return (
        category_priority.get(row["case_category"], 0),
        row["max_redundancy_ratio"],
        row["matching_rules"],
        -row["client_count"],
        -row["row_id"],
    )


def _categorize(ps_status: str, pg_status: str, changed: bool, max_redundancy_ratio: float) -> str:
    if ps_status == "CORRECTED" and pg_status == "CORRECTED":
        return "BOTH_CORRECTED"
    if ps_status == "CORRECTED":
        return "PS_CORRECTED"
    if pg_status == "CORRECTED":
        return "PG_CORRECTED"
    if ps_status == "HARMED" and pg_status == "HARMED":
        return "BOTH_HARMED"
    if ps_status == "HARMED":
        return "PS_HARMED"
    if pg_status == "HARMED":
        return "PG_HARMED"
    if (ps_status == "CORRECTED" and pg_status == "HARMED") or (ps_status == "HARMED" and pg_status == "CORRECTED"):
        return "MIXED"
    if changed:
        return "CHANGED"
    if max_redundancy_ratio >= 0.25:
        return "HIGH_REDUNDANCY"
    return "UNCHANGED"


def _select_five(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Prefer distinct explanatory phenomena first, then highest-impact remaining cases.
    preferred = [
        "BOTH_CORRECTED",
        "PS_CORRECTED",
        "PG_CORRECTED",
        "BOTH_HARMED",
        "PS_HARMED",
        "PG_HARMED",
        "MIXED",
        "CHANGED",
        "HIGH_REDUNDANCY",
        "UNCHANGED",
    ]
    ranked = sorted(dataset_rows, key=_case_impact, reverse=True)
    selected = []
    used_keys = set()

    for category in preferred:
        candidate = next(
            (
                row
                for row in ranked
                if row["case_category"] == category
                and (row["client_count"], row["row_id"]) not in used_keys
            ),
            None,
        )
        if candidate is not None:
            selected.append(candidate)
            used_keys.add((candidate["client_count"], candidate["row_id"]))
        if len(selected) == 5:
            return selected

    for row in ranked:
        key = (row["client_count"], row["row_id"])
        if key in used_keys:
            continue
        selected.append(row)
        used_keys.add(key)
        if len(selected) == 5:
            break
    return selected


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    out_dir = root / "outputs" / "target_case_backtrace"
    out_dir.mkdir(parents=True, exist_ok=True)

    build = run_application(config, prediction_policies=list(POLICIES))

    all_case_rows: list[dict[str, Any]] = []
    all_decision_rows: list[dict[str, Any]] = []
    all_rule_rows: list[dict[str, Any]] = []
    standard_transition_rows: list[dict[str, Any]] = []
    global_transition_rows: list[dict[str, Any]] = []
    teacher_metric_rows: list[dict[str, Any]] = []
    teacher_coverage_rows: list[dict[str, Any]] = []
    teacher_metadata_rows: list[dict[str, Any]] = []

    # Teacher-facing experiment tables: one canonical source for dataset metadata,
    # six-policy HOLDOUT metrics, and both ordinary and true-candidate coverage.
    for dataset_key, dataset_result in build["datasets"].items():
        artifacts = list(dataset_result.get("structural_artifacts", []))
        policy_results = list(dataset_result.get("artifact_policy_results", []))
        for artifact, artifact_results in zip(artifacts, policy_results):
            teacher_metadata_rows.append(
                {
                    "dataset": artifact.dataset,
                    "dataset_rows": len(artifact.train) + len(artifact.test),
                    "dataset_columns": len(artifact.condition_columns) + 1,
                    "condition_attribute_count": len(artifact.condition_columns),
                    "target_column": artifact.target,
                    "class_count": len(
                        set(artifact.train[artifact.target].astype(str))
                        | set(artifact.test[artifact.target].astype(str))
                    ),
                    "train_rows": len(artifact.train),
                    "test_rows": len(artifact.test),
                    "client_count": artifact.client_count,
                    "fold": artifact.fold,
                }
            )
            for policy in POLICIES:
                fed = (artifact_results.get(policy, {}) or {}).get("federated") or {}
                if not fed:
                    continue
                teacher_metric_rows.append(
                    {
                        "dataset": artifact.dataset,
                        "client_count": artifact.client_count,
                        "fold": artifact.fold,
                        "policy": policy,
                        "accuracy": fed.get("accuracy"),
                        "recall_macro": fed.get("recall_macro"),
                        "balanced_accuracy": fed.get("balanced_accuracy"),
                        "macro_f1": fed.get("macro_f1"),
                        "overall_coverage": fed.get("overall_coverage"),
                        "target_coverage_macro": fed.get("target_coverage_macro"),
                        "target_candidate_coverage_macro": fed.get("target_candidate_coverage_macro"),
                        "conflict_balanced_accuracy": fed.get("conflict_balanced_accuracy"),
                        "conflict_macro_f1": fed.get("conflict_macro_f1"),
                    }
                )
                target_cov = fed.get("target_coverage_by_class", {}) or {}
                candidate_cov = fed.get("target_candidate_coverage_by_class", {}) or {}
                labels = sorted(set(map(str, target_cov)) | set(map(str, candidate_cov)), key=str)
                for label in labels:
                    teacher_coverage_rows.append(
                        {
                            "dataset": artifact.dataset,
                            "client_count": artifact.client_count,
                            "fold": artifact.fold,
                            "policy": policy,
                            "target_class": label,
                            "target_coverage": target_cov.get(label),
                            "target_candidate_coverage": candidate_cov.get(label),
                        }
                    )

    # First pass: collect every prediction-time conflict case with score decomposition.
    for dataset_key, dataset_result in build["datasets"].items():
        for artifact in dataset_result.get("structural_artifacts", []):
            if not artifact.global_rules:
                continue
            for _, row in artifact.test.iterrows():
                matched = matching_rules(row, artifact.global_rules)
                decisions = sorted({str(rule.decision) for rule in matched})
                if len(decisions) <= 1:
                    continue

                true_value = str(row[artifact.target])
                row_id = int(row["__row_id__"])
                predictions = _prediction_map(artifact, row)
                scores = _scores_for_case(artifact, matched)
                ps_evidence = transition_redundancy_evidence(
                    true_decision=true_value,
                    old_winner=predictions["STANDARD_VOTING"],
                    new_winner=predictions["POPULATION_STANDARD"],
                    decision_scores=scores,
                )
                pg_evidence = transition_redundancy_evidence(
                    true_decision=true_value,
                    old_winner=predictions["GLOBAL_STRENGTH"],
                    new_winner=predictions["POPULATION_GLOBAL"],
                    decision_scores=scores,
                )

                redundancies = []
                for decision, score in scores.items():
                    t = float(score.get("total_support_occurrences", 0.0))
                    u = float(score.get("unique_population", 0.0))
                    redundancies.append((t - u) / t if t > 0 else 0.0)
                max_redundancy_ratio = max(redundancies) if redundancies else 0.0

                ps_status = ps_evidence["status"]
                pg_status = pg_evidence["status"]
                changed = (
                    predictions["STANDARD_VOTING"] != predictions["POPULATION_STANDARD"]
                    or predictions["GLOBAL_STRENGTH"] != predictions["POPULATION_GLOBAL"]
                )
                case_category = _categorize(ps_status, pg_status, changed, max_redundancy_ratio)

                factors = {col: str(row[col]) for col in artifact.condition_columns}
                base = {
                    "dataset": artifact.dataset,
                    "client_count": artifact.client_count,
                    "fold": artifact.fold,
                    "row_id": row_id,
                    "true": true_value,
                    "matching_rules": len(matched),
                    "candidate_decisions": json.dumps(decisions, ensure_ascii=False),
                    "factors": json.dumps(factors, ensure_ascii=False, sort_keys=True),
                    "ps_status": ps_status,
                    "pg_status": pg_status,
                    "case_category": case_category,
                    "max_redundancy_ratio": max_redundancy_ratio,
                    "true_candidate_present": bool(ps_evidence["true_candidate_present"]),
                    "ps_error_type": ps_evidence["error_type"],
                    "pg_error_type": pg_evidence["error_type"],
                    "ps_redundancy_asymmetry": ps_evidence["redundancy_asymmetry"],
                    "pg_redundancy_asymmetry": pg_evidence["redundancy_asymmetry"],
                    "ps_winner_redundancy_drop": ps_evidence["winner_redundancy_drop"],
                    "pg_winner_redundancy_drop": pg_evidence["winner_redundancy_drop"],
                    **{f"pred_{policy.lower()}": predictions[policy] for policy in POLICIES},
                }
                for col, value in factors.items():
                    base[f"factor__{col}"] = value
                all_case_rows.append(base)

                def transition_row(kind: str, old_policy: str, new_policy: str, evidence: dict[str, Any]) -> dict[str, Any]:
                    old_decision = predictions[old_policy]
                    new_decision = predictions[new_policy]
                    old_score = scores.get(str(old_decision), {})
                    new_score = scores.get(str(new_decision), {})
                    true_score = scores.get(str(true_value), {})
                    return {
                        "dataset": artifact.dataset,
                        "client_count": artifact.client_count,
                        "fold": artifact.fold,
                        "row_id": row_id,
                        "true": true_value,
                        "transition": kind,
                        "old_policy": old_policy,
                        "new_policy": new_policy,
                        "old_winner": old_decision,
                        "new_winner": new_decision,
                        "status": evidence["status"],
                        "error_type": evidence["error_type"],
                        "true_candidate_present": evidence["true_candidate_present"],
                        "old_T": old_score.get("total_support_occurrences"),
                        "old_U": old_score.get("unique_population"),
                        "old_P": old_score.get("population_nonredundancy_ratio"),
                        "new_T": new_score.get("total_support_occurrences"),
                        "new_U": new_score.get("unique_population"),
                        "new_P": new_score.get("population_nonredundancy_ratio"),
                        "true_T": true_score.get("total_support_occurrences"),
                        "true_U": true_score.get("unique_population"),
                        "true_P": true_score.get("population_nonredundancy_ratio"),
                        "old_redundancy": evidence["old_redundancy"],
                        "new_redundancy": evidence["new_redundancy"],
                        "true_redundancy": evidence["true_redundancy"],
                        "winner_redundancy_drop": evidence["winner_redundancy_drop"],
                        "redundancy_asymmetry": evidence["redundancy_asymmetry"],
                    }

                standard_transition_rows.append(
                    transition_row(
                        "STANDARD_TO_POPULATION_STANDARD",
                        "STANDARD_VOTING",
                        "POPULATION_STANDARD",
                        ps_evidence,
                    )
                )
                global_transition_rows.append(
                    transition_row(
                        "GLOBAL_TO_POPULATION_GLOBAL",
                        "GLOBAL_STRENGTH",
                        "POPULATION_GLOBAL",
                        pg_evidence,
                    )
                )

                for decision, score in sorted(scores.items()):
                    decision_row = {
                        "dataset": artifact.dataset,
                        "client_count": artifact.client_count,
                        "fold": artifact.fold,
                        "row_id": row_id,
                        "true": true_value,
                        "decision": decision,
                        "is_true_decision": decision == true_value,
                        **score,
                    }
                    t = float(score.get("total_support_occurrences", 0.0))
                    u = float(score.get("unique_population", 0.0))
                    decision_row["redundancy_ratio"] = (t - u) / t if t > 0 else 0.0
                    all_decision_rows.append(decision_row)

                for rule_no, rule in enumerate(matched, start=1):
                    support_set = artifact.global_rule_support_sets.get(rule.key, frozenset())
                    all_rule_rows.append(
                        {
                            "dataset": artifact.dataset,
                            "client_count": artifact.client_count,
                            "fold": artifact.fold,
                            "row_id": row_id,
                            "true": true_value,
                            "match_no": rule_no,
                            "decision": str(rule.decision),
                            "rule": _rule_text(rule),
                            "conditions": json.dumps(list(rule.conditions), ensure_ascii=False),
                            "condition_count": len(rule.conditions),
                            "support_size": len(support_set),
                            "provenance": json.dumps(list(artifact.rule_provenance.get(rule.key, ())), ensure_ascii=False),
                            "support_object_ids": json.dumps(sorted(map(str, support_set)), ensure_ascii=False),
                        }
                    )

    all_cases_df = pd.DataFrame(all_case_rows)
    all_decisions_df = pd.DataFrame(all_decision_rows)
    all_rules_df = pd.DataFrame(all_rule_rows)
    all_cases_df.to_csv(out_dir / "ALL_CONFLICT_CASES.csv", index=False, encoding="utf-8-sig")
    all_decisions_df.to_csv(out_dir / "ALL_CONFLICT_DECISION_SCORES.csv", index=False, encoding="utf-8-sig")
    all_rules_df.to_csv(out_dir / "ALL_CONFLICT_MATCHED_RULES.csv", index=False, encoding="utf-8-sig")

    selected_rows: list[dict[str, Any]] = []
    for dataset in sorted(all_cases_df["dataset"].unique()):
        rows = all_cases_df[all_cases_df["dataset"] == dataset].to_dict(orient="records")
        for target_no, selected in enumerate(_select_five(rows), start=1):
            selected = dict(selected)
            selected["target_no"] = target_no
            selected_rows.append(selected)

    selected_df = pd.DataFrame(selected_rows)
    selected_df.to_csv(out_dir / "SELECTED_5_TARGET_CASES_PER_DATASET.csv", index=False, encoding="utf-8-sig")

    key_cols = ["dataset", "client_count", "fold", "row_id"]
    selected_keys = selected_df[key_cols].drop_duplicates()
    selected_decisions = all_decisions_df.merge(selected_keys, on=key_cols, how="inner")
    selected_rules = all_rules_df.merge(selected_keys, on=key_cols, how="inner")
    selected_decisions.to_csv(out_dir / "SELECTED_TARGET_DECISION_SCORES.csv", index=False, encoding="utf-8-sig")
    selected_rules.to_csv(out_dir / "SELECTED_TARGET_RULE_BACKTRACE.csv", index=False, encoding="utf-8-sig")

    # Canonical teacher-facing exports.  These are intentionally denormalized so
    # the presentation can answer the professor's questions without hand-copying
    # values from multiple internal files.
    metadata_df = pd.DataFrame(teacher_metadata_rows)
    if not metadata_df.empty:
        metadata_df = metadata_df.sort_values(["dataset", "client_count", "fold"])
        metadata_df.to_csv(out_dir / "TEACHER_DATASET_METADATA.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(teacher_metric_rows).to_csv(
        out_dir / "TEACHER_SIX_POLICY_METRICS.csv", index=False, encoding="utf-8-sig"
    )
    coverage_df = pd.DataFrame(teacher_coverage_rows)
    if not coverage_df.empty:
        coverage_df = coverage_df.drop_duplicates(
            ["dataset", "client_count", "fold", "target_class", "target_coverage", "target_candidate_coverage"]
        ).sort_values(["dataset", "client_count", "fold", "target_class"])
    coverage_df.to_csv(out_dir / "TEACHER_COVERAGE_BY_CLASS.csv", index=False, encoding="utf-8-sig")

    selected_key_map = {
        (str(row.dataset), int(row.client_count), int(row.fold), int(row.row_id)): int(row.target_no)
        for row in selected_df.itertuples()
    }
    for transition_rows in (standard_transition_rows, global_transition_rows):
        for transition in transition_rows:
            transition["selected_target_no"] = selected_key_map.get(
                (
                    str(transition["dataset"]),
                    int(transition["client_count"]),
                    int(transition["fold"]),
                    int(transition["row_id"]),
                )
            )

    standard_df = pd.DataFrame(standard_transition_rows)
    global_df = pd.DataFrame(global_transition_rows)
    standard_df.to_csv(out_dir / "TEACHER_STANDARD_TRANSITIONS.csv", index=False, encoding="utf-8-sig")
    global_df.to_csv(out_dir / "TEACHER_GLOBAL_TRANSITIONS.csv", index=False, encoding="utf-8-sig")
    selected_df.to_csv(out_dir / "TEACHER_TARGET_1_TO_5.csv", index=False, encoding="utf-8-sig")

    error_cols = [
        "dataset", "client_count", "fold", "row_id", "true", "candidate_decisions",
        "true_candidate_present", "ps_status", "pg_status", "ps_error_type", "pg_error_type",
    ]
    all_cases_df[error_cols].to_csv(
        out_dir / "TEACHER_ERROR_DECOMPOSITION.csv", index=False, encoding="utf-8-sig"
    )
    asymmetry_rows = []
    for method, frame in (("POPULATION_STANDARD", standard_df), ("POPULATION_GLOBAL", global_df)):
        for transition in frame.to_dict(orient="records"):
            asymmetry_rows.append(
                {
                    "dataset": transition["dataset"],
                    "client_count": transition["client_count"],
                    "fold": transition["fold"],
                    "row_id": transition["row_id"],
                    "selected_target_no": transition.get("selected_target_no"),
                    "method": method,
                    "true": transition["true"],
                    "old_winner": transition["old_winner"],
                    "new_winner": transition["new_winner"],
                    "status": transition["status"],
                    "error_type": transition["error_type"],
                    "true_candidate_present": transition["true_candidate_present"],
                    "true_redundancy": transition["true_redundancy"],
                    "competitor_redundancy": (
                        transition["old_redundancy"] if transition["status"] == "CORRECTED"
                        else transition["new_redundancy"] if transition["status"] == "HARMED"
                        else float("nan")
                    ),
                    "winner_redundancy_drop": transition["winner_redundancy_drop"],
                    "redundancy_asymmetry": transition["redundancy_asymmetry"],
                }
            )
    pd.DataFrame(asymmetry_rows).to_csv(
        out_dir / "TEACHER_REDUNDANCY_ASYMMETRY.csv", index=False, encoding="utf-8-sig"
    )

    # Human-readable explanation.
    md = [
        "# Five Target Cases per Dataset — Population Backtrace",
        "",
        "Interpretation: a target is one selected 20% holdout test object used for case-level backtrace.",
        "Each target shows its condition-factor values, six policy predictions, and per-decision support decomposition.",
        "",
        "Core quantities:",
        "- T_d = total support occurrences across matching rules for decision d",
        "- U_d = unique supporting training objects",
        "- P_d = U_d / T_d (population nonredundancy ratio)",
        "- STANDARD score = T_d",
        "- POPULATION_STANDARD score = U_d",
        "- GLOBAL score = U_d / N_d",
        "- POPULATION_GLOBAL score = (U_d / N_d) * P_d",
        "",
    ]

    selected_lookup = selected_df.set_index(key_cols + ["target_no"], drop=False)
    for dataset in sorted(selected_df["dataset"].unique()):
        md.extend([f"## {dataset}", ""])
        part = selected_df[selected_df["dataset"] == dataset].sort_values("target_no")
        for _, case in part.iterrows():
            md.append(
                f"### Target {int(case['target_no'])}: C={int(case['client_count'])}, row_id={int(case['row_id'])}, true={case['true']}"
            )
            md.append("")
            md.append(f"- Category: **{case['case_category']}**")
            md.append(f"- PS status: {case['ps_status']}; PG status: {case['pg_status']}")
            md.append(f"- Matching rules: {int(case['matching_rules'])}; max redundancy ratio: {case['max_redundancy_ratio']:.4f}")
            md.append(f"- Factors: `{case['factors']}`")
            md.append(
                "- Predictions: "
                + ", ".join(
                    f"{p}={case[f'pred_{p.lower()}']}" for p in POLICIES
                )
            )
            md.append("")
            drows = selected_decisions[
                (selected_decisions["dataset"] == case["dataset"])
                & (selected_decisions["client_count"] == case["client_count"])
                & (selected_decisions["fold"] == case["fold"])
                & (selected_decisions["row_id"] == case["row_id"])
            ].sort_values("decision")
            md.append("```text")
            md.append(
                drows[
                    [
                        "decision",
                        "is_true_decision",
                        "total_support_occurrences",
                        "unique_population",
                        "redundant_occurrences",
                        "population_nonredundancy_ratio",
                        "class_size",
                        "standard_score",
                        "population_standard_score",
                        "global_strength_score",
                        "population_global_score",
                    ]
                ].to_string(index=False)
            )
            md.append("```")
            md.append("")

    (out_dir / "TARGET_BACKTRACE_README.md").write_text("\n".join(md), encoding="utf-8")

    manifest = {
        "datasets": sorted(all_cases_df["dataset"].unique().tolist()),
        "selected_targets_per_dataset": 5,
        "total_selected_targets": int(len(selected_df)),
        "all_conflict_cases": int(len(all_cases_df)),
        "policies": list(POLICIES),
        "selection_is_descriptive_not_inferential": True,
        "target_definition": "selected holdout test object for case-level mechanism backtrace",
        "teacher_exports": [
            "TEACHER_DATASET_METADATA.csv",
            "TEACHER_SIX_POLICY_METRICS.csv",
            "TEACHER_COVERAGE_BY_CLASS.csv",
            "TEACHER_TARGET_1_TO_5.csv",
            "TEACHER_STANDARD_TRANSITIONS.csv",
            "TEACHER_GLOBAL_TRANSITIONS.csv",
            "TEACHER_ERROR_DECOMPOSITION.csv",
            "TEACHER_REDUNDANCY_ASYMMETRY.csv",
        ],
    }
    (out_dir / "TARGET_BACKTRACE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(selected_df[["dataset", "target_no", "client_count", "row_id", "true", "case_category", "ps_status", "pg_status", "max_redundancy_ratio"]].to_string(index=False))
    print(f"\nOutputs: {out_dir}")


if __name__ == "__main__":
    main()
