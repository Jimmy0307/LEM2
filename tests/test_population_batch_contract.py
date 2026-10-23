from __future__ import annotations

import json

import pandas as pd


def test_default_batch_policy_set_contains_four_baselines_plus_two_population_variants():
    from roughset.batch import _normalized_policies

    assert _normalized_policies({}, None) == [
        "FIRST_MATCH",
        "SIMPLE_VOTING",
        "STANDARD_VOTING",
        "GLOBAL_STRENGTH",
        "POPULATION_STANDARD",
        "POPULATION_GLOBAL",
    ]


def test_single_policy_config_accepts_population_variants():
    from roughset.app import validate_config

    for policy in ("POPULATION_STANDARD", "POPULATION_GLOBAL"):
        cfg = validate_config({"experiment": {"prediction_policy": policy}})
        assert cfg["experiment"]["prediction_policy"] == policy


def test_run_application_accepts_six_policy_list(monkeypatch):
    import roughset.app as app

    monkeypatch.setattr(app, "discover_datasets", lambda config, fetcher=None: [])
    result = app.run_application(
        {},
        prediction_policies=[
            "FIRST_MATCH",
            "SIMPLE_VOTING",
            "STANDARD_VOTING",
            "GLOBAL_STRENGTH",
            "POPULATION_STANDARD",
            "POPULATION_GLOBAL",
        ],
    )

    assert result["datasets"] == {}


def test_batch_summary_reports_dataset_shape_holdout_size_and_target_coverage(tmp_path):
    from roughset.batch import run_policy_matrix

    data_dir = tmp_path / "real_data" / "local"
    schema_dir = tmp_path / "real_data" / "schemas"
    data_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)

    frame = pd.DataFrame(
        {
            "A": [0, 0, 1, 1, 0, 1, 0, 1, 0, 1],
            "B": [0, 1, 0, 1, 0, 1, 1, 0, 0, 1],
            "class": ["N", "N", "Y", "Y", "N", "Y", "N", "Y", "N", "Y"],
        }
    )
    frame.to_csv(data_dir / "demo.csv", index=False)
    (schema_dir / "demo.schema.json").write_text(
        json.dumps({"target": "class", "categorical": ["A", "B"]}),
        encoding="utf-8",
    )

    config = {
        "input": {
            "mode": "LOCAL",
            "local_folder": str(data_dir),
            "schemas_folder": str(schema_dir),
            "run_local_files": True,
            "run_uci_sources": False,
        },
        "experiment": {
            "run_centralized": True,
            "run_federated": True,
            "prediction_policy": "FIRST_MATCH",
        },
        "evaluation": {"mode": "HOLDOUT", "test_ratio": 0.2, "seed": 42},
        "federated": {
            "n_clients": 2,
            "partition": "STRATIFIED",
            "run_client_sweep": False,
            "client_counts": [2],
            "order_sensitivity_max_permutations": 2,
        },
        "report": {
            "outputs_folder": str(tmp_path / "outputs"),
            "show_rules": False,
        },
    }

    result = run_policy_matrix(
        config,
        policies=["FIRST_MATCH"],
        run_id="POPULATION_METADATA_TEST",
    )
    summary = pd.read_csv(
        tmp_path
        / "outputs"
        / "batch_runs"
        / "POPULATION_METADATA_TEST"
        / "batch_summary.csv"
    )
    row = summary.iloc[0]

    assert int(row["dataset_rows"]) == 10
    assert int(row["dataset_columns"]) == 3
    assert int(row["condition_attribute_count"]) == 2
    assert row["target_column"] == "class"
    assert int(row["class_count"]) == 2
    assert int(row["train_rows"]) == 8
    assert int(row["test_rows"]) == 2
    assert 0.0 <= float(row["accuracy"]) <= 1.0
    assert 0.0 <= float(row["recall_macro"]) <= 1.0
    assert 0.0 <= float(row["macro_f1"]) <= 1.0
    assert 0.0 <= float(row["overall_coverage"]) <= 1.0
    assert 0.0 <= float(row["target_coverage_macro"]) <= 1.0
    decoded = json.loads(row["target_coverage_by_class"])
    assert set(decoded) == {"N", "Y"}
    assert result["policies"] == ["FIRST_MATCH"]
