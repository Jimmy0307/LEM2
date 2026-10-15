from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


POLICIES = [
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
]


def _heterogeneous_frame() -> pd.DataFrame:
    rows = []
    for site in (0, 1):
        for decision in (0, 1):
            for rep in range(8):
                rows.append(
                    {
                        "A": decision if site == 0 else 0,
                        "B": 0 if site == 0 else decision,
                        "C": (rep + decision + site) % 3,
                        "site": site,
                        "class": "Y" if decision else "N",
                    }
                )
    return pd.DataFrame(rows)


def _project(tmp_path: Path, *, mode: str = "HOLDOUT", run_federated: bool = True):
    local = tmp_path / "real_data" / "local"
    schemas = tmp_path / "real_data" / "schemas"
    outputs = tmp_path / "outputs"
    local.mkdir(parents=True)
    schemas.mkdir(parents=True)
    _heterogeneous_frame().to_csv(local / "toy.csv", index=False)
    (schemas / "toy.schema.json").write_text(
        json.dumps(
            {
                "target": "class",
                "categorical": ["A", "B", "C"],
                "ignore": ["site"],
            }
        ),
        encoding="utf-8",
    )
    return {
        "input": {
            "mode": "LOCAL",
            "local_folder": str(local),
            "schemas_folder": str(schemas),
            "uci_sources_file": str(tmp_path / "real_data" / "uci_sources.txt"),
            "run_local_files": True,
            "run_uci_sources": False,
        },
        "experiment": {
            "run_centralized": True,
            "run_federated": run_federated,
            "prediction_policy": "FIRST_MATCH",
        },
        "evaluation": {
            "mode": mode,
            "test_ratio": 0.25,
            "cv_folds": 4,
            "seed": 42,
        },
        "preprocessing": {
            "auto_discretize": True,
            "unique_numeric_threshold": 10,
            "n_bins": 3,
        },
        "federated": {
            "n_clients": 2,
            "partition": "STRATIFIED",
            "dirichlet_alpha": 0.5,
            "dirichlet_max_retries": 100,
            "run_client_sweep": False,
            "client_counts": [2],
            "order_sensitivity_max_permutations": 2,
        },
        "reduct": {
            "enabled": True,
            "method": "MINIMUM_CARDINALITY",
            "selection": "LEXICOGRAPHIC_FIRST",
            "record_all_candidates": True,
        },
        "report": {"outputs_folder": str(outputs), "show_rules": False},
        "batch": {"prediction_policies": POLICIES},
    }


def _condition_attributes(rules):
    return {attribute for rule in rules for attribute, _ in rule.conditions}


def test_centralized_selected_reduct_controls_lem2_features(tmp_path, monkeypatch):
    from roughset import pipeline
    from roughset.app import run_application

    condition_columns_seen = []
    original = pipeline.induce_lem2

    def record_conditions(df, condition_cols, decision_col, **kwargs):
        condition_columns_seen.append(tuple(condition_cols))
        return original(df, condition_cols, decision_col, **kwargs)

    monkeypatch.setattr(pipeline, "induce_lem2", record_conditions)
    result = run_application(_project(tmp_path, run_federated=False))
    dataset = result["datasets"]["toy"]
    central_reduct = dataset["central_reduct_result"]
    selected = set(central_reduct.selected_reduct)

    assert condition_columns_seen == [tuple(central_reduct.selected_reduct)]
    assert _condition_attributes(dataset["centralized"]["rules"]) <= selected


def test_federated_clients_use_own_local_reducts(tmp_path, monkeypatch):
    from roughset import app
    from roughset.app import run_application

    def partition_by_site(train_df, **_kwargs):
        site_ids = (train_df["__row_id__"] >= 16).astype(int)
        return {
            f"Client_{site + 1}": group.copy().reset_index(drop=True)
            for site, group in train_df.groupby(site_ids, sort=True)
        }

    monkeypatch.setattr(app, "partition_clients", partition_by_site)
    result = run_application(_project(tmp_path))
    federated = result["datasets"]["toy"]["federated"]
    local_reducts = federated["local_reduct_results"]

    assert tuple(local_reducts["Client_1"].selected_reduct) == ("a",)
    assert tuple(local_reducts["Client_2"].selected_reduct) == ("b",)
    assert tuple(local_reducts["Client_1"].selected_reduct) != tuple(
        local_reducts["Client_2"].selected_reduct
    )
    recorded = pd.read_csv(tmp_path / "outputs" / "toy" / "local_reducts.csv")
    recorded_selected = set(recorded["selected_reduct"])
    assert '["a"]' in recorded_selected
    assert '["b"]' in recorded_selected
    for client_id, rules in federated["local_rules"].items():
        selected = set(local_reducts[client_id].selected_reduct)
        assert _condition_attributes(rules) <= selected


@pytest.mark.parametrize("mode", ["HOLDOUT", "K_FOLD_CV"])
def test_reduct_is_train_only_for_holdout_and_each_fold(tmp_path, monkeypatch, mode):
    from roughset import reduct
    from roughset.app import run_application

    seen_row_ids = []
    original = reduct.find_exact_minimum_cardinality_reducts

    def record_reduct_input(df, features, target):
        seen_row_ids.append(set(df["__row_id__"].astype(int)))
        return original(df, features, target)

    monkeypatch.setattr(reduct, "find_exact_minimum_cardinality_reducts", record_reduct_input)
    result = run_application(_project(tmp_path, mode=mode))
    dataset = result["datasets"]["toy"]
    if mode == "HOLDOUT":
        folds = [dataset]
    else:
        folds = dataset["fold_results"]
    expected_train_ids = [
        set(fold["train"]["__row_id__"].astype(int)) for fold in folds
    ]

    assert seen_row_ids
    assert all(any(row_ids <= train_ids for train_ids in expected_train_ids) for row_ids in seen_row_ids)
    assert all(train_ids in seen_row_ids for train_ids in expected_train_ids)


def test_policy_does_not_change_structural_artifact(tmp_path, monkeypatch):
    from roughset import reduct
    from roughset.batch import run_policy_matrix

    reduct_calls = []
    original = reduct.find_exact_minimum_cardinality_reducts

    def count_reduct_builds(df, features, target):
        reduct_calls.append(tuple(sorted(set(df["__row_id__"].astype(int)))))
        return original(df, features, target)

    monkeypatch.setattr(reduct, "find_exact_minimum_cardinality_reducts", count_reduct_builds)
    result = run_policy_matrix(
        _project(tmp_path), policies=POLICIES, run_id="SHARED_STRUCTURE"
    )
    artifacts = [
        result["results"][policy]["datasets"]["toy"]["structural_artifact"]
        for policy in POLICIES
    ]

    assert all(artifact is artifacts[0] for artifact in artifacts)
    assert len(reduct_calls) == 3  # one central selection plus two client selections
    assert artifacts[0].central_reduct_result is not None
    assert set(artifacts[0].local_reduct_results) == {"Client_1", "Client_2"}
    assert len({artifact.pre_resolution_conflict_case_ids for artifact in artifacts}) == 1
    assert len({tuple(rule.key for rule in artifact.central_rules) for artifact in artifacts}) == 1
    assert len({tuple(rule.key for rule in artifact.global_rules) for artifact in artifacts}) == 1
    root = Path(result["root_output"])
    assert (root / "structural_summary.csv").exists()
    assert (root / "resolver_summary.csv").exists()
    assert (root / "research_chain_summary.csv").exists()
    for filename in (
        "central_reduct.csv",
        "local_reducts.csv",
        "reduct_candidates.csv",
        "pairwise_reduct_jaccard.csv",
        "feature_selection_frequency.csv",
        "local_rules.csv",
        "rule_metrics.csv",
    ):
        assert (root / "structural" / "toy" / filename).exists()
    for policy in POLICIES:
        assert (root / "resolver" / policy / "toy" / "resolver_summary.csv").exists()
    assert (root / "structural_summary_aggregate.csv").exists()
    assert (root / "resolver_summary_aggregate.csv").exists()
    structural = pd.read_csv(root / "structural_summary.csv")
    resolver = pd.read_csv(root / "resolver_summary.csv")
    assert len(structural) == 1
    assert len(resolver) == len(POLICIES)
    assert {
        "disagreement_vs_first_match",
        "conflict_disagreement_vs_first_match",
    } <= set(resolver.columns)


def test_kfold_aggregate_retains_mean_std_min_max():
    from roughset.app import _aggregate_cv

    aggregate = _aggregate_cv(
        [
            {"federated": {"accuracy": 0.5, "balanced_accuracy": 0.4, "macro_f1": 0.3, "coverage": 0.8, "conflict_balanced_accuracy": 0.2, "rules": []}},
            {"federated": {"accuracy": 0.9, "balanced_accuracy": 0.8, "macro_f1": 0.7, "coverage": 1.0, "conflict_balanced_accuracy": 0.6, "rules": []}},
        ],
        "federated",
    )

    assert aggregate["accuracy"] == pytest.approx(0.7)
    assert aggregate["accuracy_std"] == pytest.approx(0.2)
    assert aggregate["accuracy_min"] == pytest.approx(0.5)
    assert aggregate["accuracy_max"] == pytest.approx(0.9)
    assert aggregate["conflict_balanced_accuracy_min"] == pytest.approx(0.2)
    assert aggregate["conflict_balanced_accuracy_max"] == pytest.approx(0.6)


def test_pairwise_reduct_metrics_match_hand_calculation():
    from roughset.reduct import pairwise_reduct_jaccard

    result = pairwise_reduct_jaccard(
        {"Client_1": ("A", "B", "C"), "Client_2": ("A", "D")}
    )
    row = result["pairwise_table"].iloc[0]

    assert row["intersection_size"] == 1
    assert row["union_size"] == 4
    assert row["jaccard"] == pytest.approx(0.25)
    assert result["mean_reduct_jaccard"] == pytest.approx(0.25)
    assert result["reduct_instability"] == pytest.approx(0.75)


def test_deterministic_multiple_minimum_reduct_selection_records_all_candidates():
    from roughset.reduct import select_minimum_reduct

    rows = [
        {"A": 0, "B": 0, "C": 0, "D": "N"},
        {"A": 0, "B": 1, "C": 1, "D": "Y"},
        {"A": 1, "B": 0, "C": 0, "D": "Y"},
        {"A": 1, "B": 1, "C": 1, "D": "N"},
    ]
    result = select_minimum_reduct(pd.DataFrame(rows), ["B", "A", "C"], "D")

    assert result.candidate_reducts == (("A", "B"), ("A", "C"))
    assert result.selected_reduct == ("A", "B")
    assert result.candidate_count == 2
    assert result.minimum_reduct_size == 2


def test_reduct_disabled_keeps_all_feature_lem2_baseline(tmp_path, monkeypatch):
    from roughset import pipeline
    from roughset.app import run_application

    config = _project(tmp_path, run_federated=False)
    config["reduct"]["enabled"] = False
    observed = []
    original = pipeline.induce_lem2

    def record_conditions(df, condition_cols, decision_col, **kwargs):
        observed.append(tuple(condition_cols))
        return original(df, condition_cols, decision_col, **kwargs)

    monkeypatch.setattr(pipeline, "induce_lem2", record_conditions)
    result = run_application(config)
    dataset = result["datasets"]["toy"]

    assert observed == [("a", "b", "c")]
    assert dataset["central_reduct_result"] is None
    assert set(_condition_attributes(dataset["centralized"]["rules"])) <= set(observed[0])


def test_empty_reduct_jaccard_convention_and_single_client_instability():
    from roughset.reduct import pairwise_reduct_jaccard

    identical_empty = pairwise_reduct_jaccard({"Client_1": (), "Client_2": ()})
    single_client = pairwise_reduct_jaccard({"Client_1": ("A",)})

    assert identical_empty["pairwise_table"].iloc[0]["jaccard"] == 1.0
    assert identical_empty["reduct_instability"] == 0.0
    assert pd.isna(single_client["mean_reduct_jaccard"])
    assert pd.isna(single_client["reduct_instability"])


def test_structural_artifact_records_reduct_and_build_runtimes():
    artifact = _conflict_artifact(conflict=True)

    assert artifact.central_reduct_seconds is not None
    assert artifact.central_reduct_seconds >= 0
    assert set(artifact.local_reduct_seconds) == {"Client_1", "Client_2"}
    assert all(seconds >= 0 for seconds in artifact.local_reduct_seconds.values())
    assert artifact.structural_build_seconds >= 0


def test_feature_selection_frequency_matches_hand_calculation():
    from roughset.reduct import feature_selection_frequency

    table = feature_selection_frequency(
        {"Client_1": ("A", "B"), "Client_2": ("A", "C"), "Client_3": ("A", "B")},
        ["A", "B", "C", "D"],
    ).set_index("feature")

    assert table.loc["A", "selection_frequency"] == 1.0
    assert table.loc["B", "selection_frequency"] == pytest.approx(2 / 3)
    assert table.loc["C", "selection_frequency"] == pytest.approx(1 / 3)
    assert table.loc["D", "selected_client_count"] == 0


def _conflict_artifact(*, conflict: bool):
    from roughset.pipeline import build_rule_system

    client_1 = pd.DataFrame(
        {
            "A": [0, 0, 1, 1],
            "B": [0, 1, 0, 1],
            "D": ["N", "Y", "N", "Y"],
            "__row_id__": [0, 1, 2, 3],
        }
    )
    client_2 = pd.DataFrame(
        {
            "A": [0, 0, 1, 1],
            "B": [0, 1, 0, 1],
            "D": (["Y", "N", "N", "Y"] if conflict else ["N", "Y", "N", "Y"]),
            "__row_id__": [4, 5, 6, 7],
        }
    )
    train = pd.concat([client_1, client_2], ignore_index=True)
    test = pd.DataFrame(
        {
            "A": [0, 1],
            "B": [0, 1],
            "D": ["Y", "Y"],
            "__row_id__": [8, 9],
        }
    )
    return build_rule_system(
        train,
        test,
        ["A", "B"],
        "D",
        clients={"Client_1": client_1, "Client_2": client_2},
        metadata={"dataset": "conflict_demo", "seed": 42},
    )


def test_conflict_only_metrics_and_case_identity_are_policy_invariant():
    from roughset.pipeline import evaluate_resolvers

    artifact = _conflict_artifact(conflict=True)
    results = evaluate_resolvers(artifact, POLICIES)

    assert artifact.pre_resolution_conflict_case_ids == (8,)
    for policy in POLICIES:
        fed = results[policy]["federated"]
        assert fed["pre_resolution_conflict_case_ids"] == (8,)
        assert fed["pre_resolution_conflict_case_rate"] == 0.5
        assert fed["conflict_case_count"] == 1
        assert fed["conflict_cases_table"]["row_id"].tolist() == [8]
        assert fed["conflict_class_metrics"]["support"].sum() == 1


def test_no_conflict_metrics_are_nan_and_order_invariance_is_explicit():
    from roughset.pipeline import evaluate_resolvers

    artifact = _conflict_artifact(conflict=False)
    results = evaluate_resolvers(artifact, POLICIES)

    for policy in POLICIES:
        fed = results[policy]["federated"]
        assert fed["conflict_case_count"] == 0
        assert pd.isna(fed["conflict_resolution_accuracy"])
        assert pd.isna(fed["conflict_balanced_accuracy"])
        assert pd.isna(fed["conflict_macro_f1"])
        assert fed["order_invariant_by_design"] is (policy != "FIRST_MATCH")
        if policy == "FIRST_MATCH":
            assert fed["order_sensitivity_status"] == "MEASURED"
        else:
            assert fed["order_sensitivity_status"] == "ORDER_INVARIANT_BY_DESIGN"
