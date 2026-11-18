import pandas as pd
from fedrs.predict import POLICIES
from experiments.full_scale_20261118.analysis import dataset_best, summary
from experiments.full_scale_20261118.aggregate import aggregate, check_19
import pytest


def test_seed_averages_ties_fractional_wins_and_average_rank():
    rows = []
    for seed in (1001, 1002):
        for i, policy in enumerate(POLICIES):
            rows.append(dict(dataset="A", seed=seed, system="CENTRALIZED", distribution="IID",
                             dirichlet_alpha=None, selection_policy=policy,
                             accuracy_pct=(80 if i == 0 else 80-5e-7) if i < 2 else 70-i,
                             balanced_accuracy_pct=60 if i < 2 else 50-i))
    registry = pd.DataFrame([dict(dataset="A", feature_type="連續", size_class="小")])
    best = dataset_best(pd.DataFrame(rows), registry, [1001, 1002]).iloc[0]
    assert best[f"{POLICIES[0]}_wins"] == .5
    assert best[f"{POLICIES[1]}_wins"] == .5
    assert best[f"{POLICIES[0]}_rank"] == 1.5
    assert best["accuracy_lead_pp"] == 0
    assert best["metric_winners_agree"]
    assert len(summary(pd.DataFrame([best]))) == 18


def test_incomplete_seeds_are_not_silently_averaged():
    rows = [dict(dataset="A", seed=1001, system="CENTRALIZED", distribution="IID", dirichlet_alpha=None,
                 selection_policy=p, accuracy_pct=50, balanced_accuracy_pct=50) for p in POLICIES]
    registry = pd.DataFrame([dict(dataset="A", feature_type="混合", size_class="小")])
    assert dataset_best(pd.DataFrame(rows), registry, [1001, 1002]).empty


def test_seed_variable_feature_type_is_unclassified_not_mixed():
    rows = [dict(dataset="A", seed=1001, system="CENTRALIZED", distribution="IID", dirichlet_alpha=None,
                 selection_policy=p, accuracy_pct=50, balanced_accuracy_pct=50) for p in POLICIES]
    registry = pd.DataFrame([dict(dataset="A", feature_type=None, size_class="小")])
    best = dataset_best(pd.DataFrame(rows), registry, [1001])
    summary_data = summary(best)
    feature = summary_data[summary_data.stratum == "feature_type"]
    assert set(feature.stratum_value) == {"未分類（跨種子變動）"}


def test_19_column_validation_rejects_bad_counts_and_conflict_bound():
    rows = [dict(dataset="A", seed=1001, system="CENTRALIZED", distribution="IID", dirichlet_alpha=None,
                 selection_policy=p, test_rows=10, covered_count=8, no_match_count=2, true_in_candidate_count=7,
                 test_coverage_pct=80, candidate_coverage_pct=70, accuracy_pct=60,
                 balanced_accuracy_pct=50, conflict_rate_pct=0) for p in POLICIES]
    check_19(pd.DataFrame(rows))
    corrupt = pd.DataFrame(rows)
    corrupt.loc[0, "covered_count"] = 9
    with pytest.raises(ValueError, match="covered"):
        check_19(corrupt)
    corrupt = pd.DataFrame(rows)
    corrupt.loc[0, "accuracy_pct"] = 61
    with pytest.raises(ValueError, match="CONFLICT_BOUND"):
        check_19(corrupt)
    corrupt = pd.DataFrame(rows)
    corrupt["dirichlet_alpha"] = 0.5
    with pytest.raises(ValueError, match="IID.*alpha"):
        check_19(corrupt)
    corrupt = pd.DataFrame(rows)
    corrupt["test_coverage_pct"] = 75
    with pytest.raises(ValueError, match="coverage percentage"):
        check_19(corrupt)


def test_aggregation_preserves_excluded_source_status(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    pd.DataFrame([dict(dataset="UCI20:iris", status="EXCLUDED_TOO_FEW_CLASSES", raw_sha256="abc",
                       dropped_classes='{"rare": 9}', n_classes=1)]).to_csv(artifacts / "registry_0.csv", index=False)
    aggregate(artifacts, tmp_path / "report", [1001], smoke=True)
    registry = pd.read_csv(tmp_path / "report" / "REGISTRY.csv").set_index("dataset")
    assert registry.loc["UCI20:iris", "status"] == "EXCLUDED_TOO_FEW_CLASSES"
    assert registry.loc["UCI20:iris", "dropped_classes"] == '{"rare": 9}'


def test_aggregation_preserves_prior_dispatch_failure(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    report = tmp_path / "report"
    previous = report / "dispatch_attempt_1"
    previous.mkdir(parents=True)
    pd.DataFrame([dict(phase="DISPATCH", status="HTTP_404", error="workflow unavailable")]).to_csv(previous / "FAILURES.csv", index=False)
    aggregate(artifacts, report, [1001], smoke=True)
    failures = pd.read_csv(report / "FAILURES.csv")
    assert ((failures.phase == "PRELIMINARY_DISPATCH") & (failures.status == "HTTP_404")).any()
