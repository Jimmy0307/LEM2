from __future__ import annotations

import math

import pytest

from roughset.conflict_concentration import (
    candidate_signature,
    summarize_candidate_signatures,
    summarize_configurations,
    summarize_decision_scores,
    summarize_factor_values,
    summarize_persistence,
    summarize_policy_accuracy,
    summarize_transition_status,
    summarize_true_classes,
)


POLICY_COLUMNS = {
    "FIRST_MATCH": "pred_first_match",
    "SIMPLE_VOTING": "pred_simple_voting",
    "STANDARD_VOTING": "pred_standard_voting",
    "GLOBAL_STRENGTH": "pred_global_strength",
    "POPULATION_STANDARD": "pred_population_standard",
    "POPULATION_GLOBAL": "pred_population_global",
}


def _rows():
    return [
        {
            "dataset": "Demo",
            "client_count": "2",
            "fold": "1",
            "row_id": "10",
            "true": "A",
            "matching_rules": "3",
            "candidate_decisions": '["B", "A", "A"]',
            "factor__x": "low",
            "factor__unused": "",
            "ps_status": "UNCHANGED",
            "pg_status": "CORRECTED",
            "pred_first_match": "A",
            "pred_simple_voting": "B",
            "pred_standard_voting": "A",
            "pred_global_strength": "B",
            "pred_population_standard": "A",
            "pred_population_global": "A",
        },
        {
            "dataset": "Demo",
            "client_count": "3",
            "fold": "1",
            "row_id": "10",
            "true": "A",
            "matching_rules": "4",
            "candidate_decisions": '["A", "B"]',
            "factor__x": "low",
            "factor__unused": "",
            "ps_status": "HARMED",
            "pg_status": "UNCHANGED",
            "pred_first_match": "B",
            "pred_simple_voting": "A",
            "pred_standard_voting": "A",
            "pred_global_strength": "A",
            "pred_population_standard": "B",
            "pred_population_global": "A",
        },
        {
            "dataset": "Demo",
            "client_count": "3",
            "fold": "1",
            "row_id": "11",
            "true": "B",
            "matching_rules": "2",
            "candidate_decisions": '["C", "A", "B"]',
            "factor__x": "high",
            "factor__unused": "",
            "ps_status": "UNCHANGED",
            "pg_status": "UNCHANGED",
            "pred_first_match": "C",
            "pred_simple_voting": "B",
            "pred_standard_voting": "C",
            "pred_global_strength": "B",
            "pred_population_standard": "C",
            "pred_population_global": "B",
        },
    ]


def test_candidate_signature_normalizes_json_list_to_sorted_distinct_labels():
    assert candidate_signature('["B", "A", "A"]') == "A|B"
    assert candidate_signature([3, 1, 3, 2]) == "1|2|3"


def test_configuration_true_class_candidate_and_persistence_summaries_reconcile():
    rows = _rows()
    metadata = [
        {"dataset": "Demo", "client_count": "2", "fold": "1", "test_rows": "10"},
        {"dataset": "Demo", "client_count": "3", "fold": "1", "test_rows": "20"},
    ]

    configs = summarize_configurations(rows, metadata)
    assert configs[0]["conflict_count"] == 1
    assert math.isclose(configs[0]["conflict_rate"], 0.1)
    assert math.isclose(configs[0]["share_of_all_conflicts"], 1 / 3)
    assert configs[1]["conflict_count"] == 2
    assert math.isclose(configs[1]["conflict_rate"], 0.1)
    assert configs[1]["true_candidate_missing_count"] == 0

    true_classes = summarize_true_classes(rows)
    demo_c3_a = next(r for r in true_classes if r["client_count"] == 3 and r["true_class"] == "A")
    assert demo_c3_a["conflict_count"] == 1
    assert math.isclose(demo_c3_a["share_within_configuration"], 0.5)

    candidates = summarize_candidate_signatures(rows)
    ab = [r for r in candidates if r["candidate_signature"] == "A|B"]
    assert len(ab) == 2
    assert {r["client_count"] for r in ab} == {2, 3}
    assert all(r["conflict_count"] == 1 for r in ab)
    assert any(r["candidate_signature"] == "A|B|C" and r["client_count"] == 3 and r["conflict_count"] == 1 for r in candidates)

    persistence = summarize_persistence(rows, expected_client_counts=(2, 3, 4, 5))
    row10 = next(r for r in persistence if r["row_id"] == "10")
    row11 = next(r for r in persistence if r["row_id"] == "11")
    assert row10["conflict_client_count"] == 2
    assert row10["persistence_label"] == "REPEATED"
    assert math.isclose(row10["persistence_rate"], 0.5)
    assert row11["conflict_client_count"] == 1
    assert row11["persistence_label"] == "SINGLE"
    assert sum(r["conflict_client_count"] for r in persistence) == len(rows)


def test_factor_policy_transition_and_decision_score_summaries_are_conflict_only():
    rows = _rows()

    factors = summarize_factor_values(rows)
    assert {r["factor"] for r in factors} == {"x"}
    low = next(r for r in factors if r["value"] == "low")
    assert low["conflict_count"] == 2
    assert math.isclose(low["share_within_dataset_conflicts"], 2 / 3)

    policy = summarize_policy_accuracy(rows, policy_columns=POLICY_COLUMNS)
    c2_first = next(r for r in policy if r["client_count"] == 2 and r["policy"] == "FIRST_MATCH")
    c2_simple = next(r for r in policy if r["client_count"] == 2 and r["policy"] == "SIMPLE_VOTING")
    assert c2_first["correct"] == 1 and c2_first["conflict_count"] == 1
    assert math.isclose(c2_first["conflict_accuracy"], 1.0)
    assert math.isclose(c2_simple["conflict_accuracy"], 0.0)

    transitions = summarize_transition_status(rows)
    pg_corrected = next(r for r in transitions if r["transition"] == "GS_TO_PG" and r["status"] == "CORRECTED")
    ps_harmed = next(r for r in transitions if r["transition"] == "STD_TO_PS" and r["status"] == "HARMED")
    assert pg_corrected["count"] == 1
    assert ps_harmed["count"] == 1

    score_rows = [
        {
            "dataset": "Demo",
            "client_count": "2",
            "fold": "1",
            "row_id": "10",
            "decision": "A",
            "is_true_decision": "True",
            "total_support_occurrences": "10",
            "unique_population": "7",
            "redundancy_ratio": "0.3",
        },
        {
            "dataset": "Demo",
            "client_count": "2",
            "fold": "1",
            "row_id": "10",
            "decision": "B",
            "is_true_decision": "False",
            "total_support_occurrences": "8",
            "unique_population": "8",
            "redundancy_ratio": "0.0",
        },
    ]
    score_summary = summarize_decision_scores(score_rows)
    true_row = next(r for r in score_summary if r["decision_role"] == "TRUE")
    competitor_row = next(r for r in score_summary if r["decision_role"] == "COMPETITOR")
    assert math.isclose(true_row["mean_redundancy_ratio"], 0.3)
    assert math.isclose(competitor_row["mean_redundancy_ratio"], 0.0)


def test_policy_accuracy_rejects_missing_prediction_schema_column():
    rows = _rows()
    del rows[0]["pred_population_global"]
    with pytest.raises(KeyError, match="pred_population_global"):
        summarize_policy_accuracy(rows, policy_columns=POLICY_COLUMNS)
