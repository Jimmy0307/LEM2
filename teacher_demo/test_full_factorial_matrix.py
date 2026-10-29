from __future__ import annotations

import math

from teacher_demo.full_factorial_matrix import (
    POLICIES,
    build_factorial_design,
    no_selection_metric_contract,
)


DATASETS = ["Hayes-Roth", "Car Evaluation", "Balance Scale"]


def test_full_factorial_design_has_exact_requested_210_rows():
    rows = build_factorial_design(DATASETS, client_counts=(2, 3, 4, 5))

    assert len(rows) == 210
    assert set(POLICIES) == {
        "FIRST_MATCH",
        "SIMPLE_VOTING",
        "STANDARD_VOTING",
        "GLOBAL_STRENGTH",
        "POPULATION_STANDARD",
        "POPULATION_GLOBAL",
    }

    for dataset in DATASETS:
        dataset_rows = [row for row in rows if row["dataset"] == dataset]
        assert len(dataset_rows) == 70

        for split_mode in ("FULL_DATA", "HOLDOUT_80_20"):
            split_rows = [row for row in dataset_rows if row["split_mode"] == split_mode]
            assert len(split_rows) == 35

            central = [row for row in split_rows if row["system"] == "CENTRALIZED"]
            federated = [row for row in split_rows if row["system"] == "FEDERATED"]
            assert len(central) == 7
            assert len(federated) == 28

            assert {row["selection_policy"] for row in central} == {"NONE", *POLICIES}
            for client_count in (2, 3, 4, 5):
                block = [row for row in federated if row["client_count"] == client_count]
                assert len(block) == 7
                assert {row["selection_policy"] for row in block} == {"NONE", *POLICIES}


def test_none_rows_are_structural_baselines_not_fake_predictions():
    contract = no_selection_metric_contract()
    assert math.isnan(contract["accuracy"])
    assert math.isnan(contract["balanced_accuracy"])
    assert math.isnan(contract["macro_f1"])
    assert contract["prediction_defined"] is False
    assert contract["selection_layer"] == "NONE"
