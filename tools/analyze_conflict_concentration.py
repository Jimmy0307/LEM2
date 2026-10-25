from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from roughset.conflict_concentration import (
    DEFAULT_POLICY_COLUMNS,
    summarize_candidate_signatures,
    summarize_configurations,
    summarize_decision_scores,
    summarize_factor_values,
    summarize_persistence,
    summarize_policy_accuracy,
    summarize_transition_status,
    summarize_true_classes,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_20261023 = ROOT / "docs/research/conflict_client_sweep_20261020/evidence/20261023"
DEFAULT_CASES = EVIDENCE_20261023 / "ALL_CONFLICT_CASES.csv"
DEFAULT_SCORES = EVIDENCE_20261023 / "ALL_CONFLICT_DECISION_SCORES.csv"
DEFAULT_METADATA = EVIDENCE_20261023 / "teacher/TEACHER_DATASET_METADATA.csv"
DEFAULT_OUTPUT = ROOT / "docs/research/conflict_client_sweep_20261020/evidence/20261025/conflict_concentration"

FROZEN_DATASET_TOTALS = {
    "Balance Scale": 266,
    "Car Evaluation": 598,
    "Hayes-Roth": 44,
}

OUTPUT_FILES = {
    "configuration": "CONFLICT_CONFIGURATION.csv",
    "true_class": "CONFLICT_TRUE_CLASS.csv",
    "candidate": "CONFLICT_CANDIDATE_SIGNATURE.csv",
    "persistence": "CONFLICT_PERSISTENCE.csv",
    "factor": "CONFLICT_FACTOR_VALUE.csv",
    "policy": "CONFLICT_POLICY_ACCURACY.csv",
    "transition": "CONFLICT_TRANSITION_STATUS.csv",
    "decision_score": "CONFLICT_DECISION_SCORE_SUMMARY.csv",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = [dict(row) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not materialized:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in materialized:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)


def _dataset_counts(configuration_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in configuration_rows:
        counts[str(row["dataset"])] += int(row["conflict_count"])
    return dict(sorted(counts.items()))


def _client_counts(configuration_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in configuration_rows:
        counts[str(row["client_count"])] += int(row["conflict_count"])
    return dict(sorted(counts.items(), key=lambda item: int(item[0])))


def _policy_overall(policy_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    aggregate: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in policy_rows:
        key = str(row["policy"])
        aggregate[key][0] += int(row["correct"])
        aggregate[key][1] += int(row["conflict_count"])
    return {
        policy: {
            "correct": correct,
            "conflict_count": total,
            "conflict_accuracy": correct / total if total else math.nan,
        }
        for policy, (correct, total) in sorted(aggregate.items())
    }


def _transition_totals(transition_rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    for row in transition_rows:
        totals[str(row["transition"])][str(row["status"])] += int(row["count"])
    return {
        transition: dict(sorted(statuses.items()))
        for transition, statuses in sorted(totals.items())
    }


def _persistence_distribution(persistence_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(int(row["conflict_client_count"]) for row in persistence_rows)
    return {str(key): counts[key] for key in sorted(counts)}


def _top_candidate_signatures(candidate_rows: list[dict[str, Any]], top_n: int = 5) -> dict[str, list[dict[str, Any]]]:
    aggregate: dict[tuple[str, str], int] = defaultdict(int)
    for row in candidate_rows:
        aggregate[(str(row["dataset"]), str(row["candidate_signature"]))] += int(row["conflict_count"])
    by_dataset: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (dataset, signature), count in aggregate.items():
        by_dataset[dataset].append((signature, count))
    return {
        dataset: [
            {"candidate_signature": signature, "conflict_count": count}
            for signature, count in sorted(values, key=lambda item: (-item[1], item[0]))[:top_n]
        ]
        for dataset, values in sorted(by_dataset.items())
    }


def _top_true_classes(true_class_rows: list[dict[str, Any]], top_n: int = 5) -> dict[str, list[dict[str, Any]]]:
    aggregate: dict[tuple[str, str], int] = defaultdict(int)
    for row in true_class_rows:
        aggregate[(str(row["dataset"]), str(row["true_class"]))] += int(row["conflict_count"])
    by_dataset: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (dataset, true_class), count in aggregate.items():
        by_dataset[dataset].append((true_class, count))
    return {
        dataset: [
            {"true_class": true_class, "conflict_count": count}
            for true_class, count in sorted(values, key=lambda item: (-item[1], item[0]))[:top_n]
        ]
        for dataset, values in sorted(by_dataset.items())
    }


def _top_factor_values(factor_rows: list[dict[str, Any]], top_n: int = 12) -> dict[str, list[dict[str, Any]]]:
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in factor_rows:
        by_dataset[str(row["dataset"])].append(row)
    return {
        dataset: [
            {
                "factor": str(row["factor"]),
                "value": str(row["value"]),
                "conflict_count": int(row["conflict_count"]),
                "share_within_dataset_conflicts": float(row["share_within_dataset_conflicts"]),
            }
            for row in sorted(
                rows,
                key=lambda item: (-int(item["conflict_count"]), str(item["factor"]), str(item["value"])),
            )[:top_n]
        ]
        for dataset, rows in sorted(by_dataset.items())
    }


def _fmt_pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _render_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Conflict Concentration / Anatomy",
        "",
        "This report analyzes the already-frozen prediction-time conflict evidence. It does **not** change LEM2, UNION, reducts, or any prediction-policy formula.",
        "",
        "## Headline reconciliation",
        "",
        f"- Conflict occurrences: **{summary['total_conflict_occurrences']}**",
        f"- Configuration-level test evaluations: **{summary['total_configuration_test_evaluations']}**",
        f"- Overall conflict workload: **{_fmt_pct(float(summary['overall_conflict_rate']))}**",
        f"- Unique test objects with at least one conflict: **{summary['unique_conflict_objects']}**",
        f"- True class absent from Candidate(x): **{summary['true_candidate_missing_count']}** occurrences",
        "",
        "## Where the 908 occurrences concentrate",
        "",
    ]
    for dataset, count in summary["dataset_conflicts"].items():
        share = count / summary["total_conflict_occurrences"]
        lines.append(f"- **{dataset}: {count}** ({_fmt_pct(share)} of all conflict occurrences)")
    lines.extend(["", "By client count:"])
    for client_count, count in summary["client_conflicts"].items():
        share = count / summary["total_conflict_occurrences"]
        lines.append(f"- **C={client_count}: {count}** ({_fmt_pct(share)})")

    lines.extend(["", "## Persistence across client counts", ""])
    lines.append("The same `(dataset, fold, row_id)` can be a conflict at multiple C values. Persistence therefore separates isolated partition-sensitive conflicts from repeatedly recurring objects.")
    for count, objects in summary["persistence_distribution"].items():
        label = "client count" if count == "1" else "client counts"
        lines.append(f"- Conflict at **{count} {label}**: {objects} unique objects")

    lines.extend(["", "## Candidate decision concentration", ""])
    for dataset, rows in summary["top_candidate_signatures"].items():
        lines.append(f"### {dataset}")
        for row in rows:
            lines.append(f"- `{row['candidate_signature']}`: {row['conflict_count']} occurrences")
        lines.append("")

    lines.extend(["## Conflict-only resolver accuracy", ""])
    for policy, row in summary["policy_overall"].items():
        lines.append(f"- **{policy}**: {row['correct']}/{row['conflict_count']} = {_fmt_pct(float(row['conflict_accuracy']))}")

    lines.extend(["", "## Population transition outcomes", ""])
    for transition, statuses in summary["transition_totals"].items():
        rendered = ", ".join(f"{status}={count}" for status, count in statuses.items())
        lines.append(f"- **{transition}**: {rendered}")

    lines.extend(
        [
            "",
            "## Factor/value interpretation boundary",
            "",
            "`CONFLICT_FACTOR_VALUE.csv` reports **within-conflict concentration only**. It tells us what values are common among conflict occurrences, but it does not estimate relative risk or causal effect because non-conflict rows are not used as denominators in this layer.",
            "",
            "## Interpretation",
            "",
            "The 908 conflicts should not be treated as one homogeneous block. They can now be decomposed into configuration concentration, recurring objects, candidate-decision combinations, evidence structure, and resolver outcomes. This supports the next research question: which data/rule structures repeatedly create cross-decision overlap, and which resolver biases matter for those structures?",
            "",
        ]
    )
    return "\n".join(lines)


def generate_outputs(
    *,
    conflict_cases_path: Path,
    decision_scores_path: Path,
    metadata_path: Path,
    output_dir: Path,
    expected_total: int | None = 908,
    expected_dataset_totals: Mapping[str, int] | None = FROZEN_DATASET_TOTALS,
    expected_true_candidate_missing: int | None = 45,
) -> dict[str, Any]:
    conflict_cases = _read_csv(conflict_cases_path)
    decision_scores = _read_csv(decision_scores_path)
    metadata = _read_csv(metadata_path)

    configurations = summarize_configurations(conflict_cases, metadata)
    true_classes = summarize_true_classes(conflict_cases)
    candidates = summarize_candidate_signatures(conflict_cases)
    persistence = summarize_persistence(conflict_cases)
    factors = summarize_factor_values(conflict_cases)
    policies = summarize_policy_accuracy(conflict_cases, policy_columns=DEFAULT_POLICY_COLUMNS)
    transitions = summarize_transition_status(conflict_cases)
    decision_score_summary = summarize_decision_scores(decision_scores)

    outputs = {
        "configuration": configurations,
        "true_class": true_classes,
        "candidate": candidates,
        "persistence": persistence,
        "factor": factors,
        "policy": policies,
        "transition": transitions,
        "decision_score": decision_score_summary,
    }
    for key, rows in outputs.items():
        _write_csv(output_dir / OUTPUT_FILES[key], rows)

    total_conflicts = sum(int(row["conflict_count"]) for row in configurations)
    total_test_evaluations = sum(int(row["test_rows"]) for row in configurations)
    dataset_conflicts = _dataset_counts(configurations)
    client_conflicts = _client_counts(configurations)
    true_candidate_missing = sum(int(row["true_candidate_missing_count"]) for row in configurations)
    persistence_weighted = sum(int(row["conflict_client_count"]) for row in persistence)
    policy_overall = _policy_overall(policies)
    transition_totals = _transition_totals(transitions)

    if expected_total is not None and total_conflicts != expected_total:
        raise AssertionError(f"Conflict total mismatch: expected {expected_total}, got {total_conflicts}")
    if expected_dataset_totals is not None and dataset_conflicts != dict(expected_dataset_totals):
        raise AssertionError(f"Dataset conflict totals mismatch: expected {dict(expected_dataset_totals)}, got {dataset_conflicts}")
    if expected_true_candidate_missing is not None and true_candidate_missing != expected_true_candidate_missing:
        raise AssertionError(
            f"True-candidate-missing mismatch: expected {expected_true_candidate_missing}, got {true_candidate_missing}"
        )
    if persistence_weighted != total_conflicts:
        raise AssertionError(
            f"Persistence reconciliation failed: weighted occurrences={persistence_weighted}, conflicts={total_conflicts}"
        )
    for policy, row in policy_overall.items():
        if int(row["conflict_count"]) != total_conflicts:
            raise AssertionError(
                f"Policy denominator mismatch for {policy}: {row['conflict_count']} != {total_conflicts}"
            )

    summary: dict[str, Any] = {
        "total_conflict_occurrences": total_conflicts,
        "total_configuration_test_evaluations": total_test_evaluations,
        "overall_conflict_rate": total_conflicts / total_test_evaluations if total_test_evaluations else math.nan,
        "dataset_conflicts": dataset_conflicts,
        "client_conflicts": client_conflicts,
        "true_candidate_missing_count": true_candidate_missing,
        "unique_conflict_objects": len(persistence),
        "persistence_weighted_occurrences": persistence_weighted,
        "persistence_distribution": _persistence_distribution(persistence),
        "top_candidate_signatures": _top_candidate_signatures(candidates),
        "top_true_classes": _top_true_classes(true_classes),
        "top_factor_values_within_conflicts": _top_factor_values(factors),
        "policy_overall": policy_overall,
        "transition_totals": transition_totals,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "CONFLICT_PPT_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "CONFLICT_CONCENTRATION_REPORT.md").write_text(_render_report(summary), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze concentration and anatomy of frozen Federated LEM2 conflict cases")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-frozen-assertions", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frozen = not args.no_frozen_assertions
    summary = generate_outputs(
        conflict_cases_path=args.cases,
        decision_scores_path=args.scores,
        metadata_path=args.metadata,
        output_dir=args.output,
        expected_total=908 if frozen else None,
        expected_dataset_totals=FROZEN_DATASET_TOTALS if frozen else None,
        expected_true_candidate_missing=45 if frozen else None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
