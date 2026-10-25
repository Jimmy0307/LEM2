from pathlib import Path
import json
import pandas as pd


def test_policy_matrix_runs_each_policy_into_separate_output_folder(tmp_path):
    from roughset.batch import run_policy_matrix

    data_dir = tmp_path / "real_data" / "local"
    schema_dir = tmp_path / "real_data" / "schemas"
    data_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)

    frame = pd.DataFrame({
        "A": [0, 0, 1, 1, 0, 1, 0, 1, 0, 1],
        "B": [0, 1, 0, 1, 0, 1, 1, 0, 0, 1],
        "class": ["N", "N", "Y", "Y", "N", "Y", "N", "Y", "N", "Y"],
    })
    csv_path = data_dir / "demo.csv"
    frame.to_csv(csv_path, index=False)
    (schema_dir / "demo.schema.json").write_text(
        json.dumps({"target": "class", "categorical": ["A", "B"]}),
        encoding="utf-8",
    )

    config = {
        "input": {
            "mode": "LOCAL",
            "local_folder": str(data_dir),
            "schemas_folder": str(schema_dir),
            "uci_sources_file": str(tmp_path / "real_data" / "uci_sources.txt"),
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
        "report": {"outputs_folder": str(tmp_path / "outputs"), "show_rules": False},
    }

    result = run_policy_matrix(
        config,
        policies=["FIRST_MATCH", "SIMPLE_VOTING"],
        run_id="TEST_RUN",
    )

    root = tmp_path / "outputs" / "batch_runs" / "TEST_RUN"
    assert (root / "FIRST_MATCH" / "demo" / "summary.csv").exists()
    assert (root / "SIMPLE_VOTING" / "demo" / "summary.csv").exists()
    assert (root / "batch_summary.csv").exists()
    assert (root / "batch_manifest.json").exists()

    summary = pd.read_csv(root / "batch_summary.csv")
    assert set(summary["prediction_policy"]) == {"FIRST_MATCH", "SIMPLE_VOTING"}
    assert len(summary) == 2
    assert {"mean_variation_ratio", "mean_variation_ratio_conflict"} <= set(summary.columns)
    assert {
        "dataset_rows",
        "dataset_columns",
        "condition_attribute_count",
        "target_column",
        "class_count",
        "train_rows",
        "test_rows",
        "accuracy",
        "recall_macro",
        "balanced_accuracy",
        "macro_f1",
        "overall_coverage",
        "target_coverage_macro",
        "target_coverage_by_class",
        "target_candidate_coverage_macro",
        "target_candidate_coverage_by_class",
    } <= set(summary.columns)

    first_match = summary.loc[summary["prediction_policy"] == "FIRST_MATCH"].iloc[0]
    simple = summary.loc[summary["prediction_policy"] == "SIMPLE_VOTING"].iloc[0]
    assert 0.0 <= float(first_match["mean_variation_ratio"]) <= 1.0
    assert float(simple["mean_variation_ratio"]) == 0.0
    assert 0.0 <= float(first_match["target_candidate_coverage_macro"]) <= 1.0
    assert result["run_id"] == "TEST_RUN"
    assert Path(result["root_output"]) == root


def test_policy_matrix_does_not_mutate_callers_config(tmp_path):
    from roughset.batch import run_policy_matrix

    data_dir = tmp_path / "real_data" / "local"
    schema_dir = tmp_path / "real_data" / "schemas"
    data_dir.mkdir(parents=True)
    schema_dir.mkdir(parents=True)
    pd.DataFrame({"A": [0, 0, 1, 1, 0, 1], "class": ["N", "N", "Y", "Y", "N", "Y"]}).to_csv(data_dir / "demo.csv", index=False)
    (schema_dir / "demo.schema.json").write_text(json.dumps({"target": "class", "categorical": ["A"]}), encoding="utf-8")

    config = {
        "input": {"mode": "LOCAL", "local_folder": str(data_dir), "schemas_folder": str(schema_dir), "run_local_files": True, "run_uci_sources": False},
        "experiment": {"run_centralized": True, "run_federated": False, "prediction_policy": "FIRST_MATCH"},
        "evaluation": {"mode": "HOLDOUT", "test_ratio": 0.34, "seed": 42},
        "federated": {"run_client_sweep": False},
        "report": {"outputs_folder": str(tmp_path / "outputs"), "show_rules": False},
    }
    before = json.loads(json.dumps(config))
    run_policy_matrix(config, policies=["FIRST_MATCH"], run_id="MUTATION_TEST")
    assert config == before


def test_default_windows_launcher_runs_all_policies_and_single_launcher_is_kept():
    root = Path(__file__).resolve().parents[1]
    run_all = (root / "run.bat").read_text(encoding="utf-8")
    run_single = root / "run_single.bat"
    assert "--all-policies" in run_all
    assert run_single.exists()
    assert "--all-policies" not in run_single.read_text(encoding="utf-8")
