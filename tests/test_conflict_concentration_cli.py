from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.analyze_conflict_concentration import generate_outputs


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_generate_outputs_writes_reconciled_evidence_bundle(tmp_path: Path):
    cases = [
        {
            "dataset": "Demo",
            "client_count": "2",
            "fold": "1",
            "row_id": "1",
            "true": "A",
            "matching_rules": "2",
            "candidate_decisions": '["A", "B"]',
            "factors": '{"x":"low"}',
            "ps_status": "UNCHANGED",
            "pg_status": "CORRECTED",
            "case_category": "UNCHANGED",
            "max_redundancy_ratio": "0.2",
            "pred_first_match": "A",
            "pred_simple_voting": "B",
            "pred_standard_voting": "A",
            "pred_global_strength": "B",
            "pred_population_standard": "A",
            "pred_population_global": "A",
            "factor__x": "low",
        },
        {
            "dataset": "Demo",
            "client_count": "3",
            "fold": "1",
            "row_id": "1",
            "true": "A",
            "matching_rules": "3",
            "candidate_decisions": '["A", "B"]',
            "factors": '{"x":"low"}',
            "ps_status": "HARMED",
            "pg_status": "UNCHANGED",
            "case_category": "PS_HARMED",
            "max_redundancy_ratio": "0.3",
            "pred_first_match": "B",
            "pred_simple_voting": "A",
            "pred_standard_voting": "A",
            "pred_global_strength": "A",
            "pred_population_standard": "B",
            "pred_population_global": "A",
            "factor__x": "low",
        },
        {
            "dataset": "Demo",
            "client_count": "3",
            "fold": "1",
            "row_id": "2",
            "true": "B",
            "matching_rules": "2",
            "candidate_decisions": '["A", "B", "C"]',
            "factors": '{"x":"high"}',
            "ps_status": "UNCHANGED",
            "pg_status": "UNCHANGED",
            "case_category": "UNCHANGED",
            "max_redundancy_ratio": "0.0",
            "pred_first_match": "C",
            "pred_simple_voting": "B",
            "pred_standard_voting": "C",
            "pred_global_strength": "B",
            "pred_population_standard": "C",
            "pred_population_global": "B",
            "factor__x": "high",
        },
    ]
    scores = [
        {
            "dataset": "Demo",
            "client_count": "2",
            "fold": "1",
            "row_id": "1",
            "true": "A",
            "decision": "A",
            "is_true_decision": "True",
            "simple_score": "1",
            "standard_score": "10",
            "population_standard_score": "7",
            "global_strength_score": "0.7",
            "population_global_score": "0.49",
            "total_support_occurrences": "10",
            "unique_population": "7",
            "redundant_occurrences": "3",
            "population_nonredundancy_ratio": "0.7",
            "class_size": "10",
            "global_strength": "0.7",
            "redundancy_ratio": "0.3",
        },
        {
            "dataset": "Demo",
            "client_count": "2",
            "fold": "1",
            "row_id": "1",
            "true": "A",
            "decision": "B",
            "is_true_decision": "False",
            "simple_score": "1",
            "standard_score": "8",
            "population_standard_score": "8",
            "global_strength_score": "0.8",
            "population_global_score": "0.8",
            "total_support_occurrences": "8",
            "unique_population": "8",
            "redundant_occurrences": "0",
            "population_nonredundancy_ratio": "1",
            "class_size": "10",
            "global_strength": "0.8",
            "redundancy_ratio": "0",
        },
    ]
    metadata = [
        {"dataset": "Demo", "dataset_rows": "30", "dataset_columns": "3", "condition_attribute_count": "2", "target_column": "class", "class_count": "3", "train_rows": "20", "test_rows": "10", "client_count": "2", "fold": "1"},
        {"dataset": "Demo", "dataset_rows": "30", "dataset_columns": "3", "condition_attribute_count": "2", "target_column": "class", "class_count": "3", "train_rows": "20", "test_rows": "10", "client_count": "3", "fold": "1"},
    ]

    cases_path = tmp_path / "cases.csv"
    scores_path = tmp_path / "scores.csv"
    metadata_path = tmp_path / "metadata.csv"
    output_dir = tmp_path / "out"
    _write_csv(cases_path, cases)
    _write_csv(scores_path, scores)
    _write_csv(metadata_path, metadata)

    summary = generate_outputs(
        conflict_cases_path=cases_path,
        decision_scores_path=scores_path,
        metadata_path=metadata_path,
        output_dir=output_dir,
        expected_total=None,
        expected_dataset_totals=None,
        expected_true_candidate_missing=None,
    )

    assert summary["total_conflict_occurrences"] == 3
    assert summary["total_configuration_test_evaluations"] == 20
    assert summary["persistence_weighted_occurrences"] == 3
    assert summary["dataset_conflicts"] == {"Demo": 3}
    assert (output_dir / "CONFLICT_CONFIGURATION.csv").exists()
    assert (output_dir / "CONFLICT_PERSISTENCE.csv").exists()
    assert (output_dir / "CONFLICT_POLICY_ACCURACY.csv").exists()
    assert (output_dir / "CONFLICT_PPT_SUMMARY.json").exists()
    report = (output_dir / "CONFLICT_CONCENTRATION_REPORT.md").read_text(encoding="utf-8")
    assert "Conflict Concentration / Anatomy" in report
    ppt_summary = json.loads((output_dir / "CONFLICT_PPT_SUMMARY.json").read_text(encoding="utf-8"))
    assert ppt_summary["total_conflict_occurrences"] == 3
