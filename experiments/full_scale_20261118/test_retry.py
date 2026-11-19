import http.client
import urllib.error

import pandas as pd
import pytest

from experiments.full_scale_20261118.retry_merge import prune


def _row(dataset, system, distribution, alpha, policy="FIRST_MATCH"):
    return dict(dataset=dataset, seed=1001, distribution=distribution, dirichlet_alpha=alpha,
                system=system, client_count=0 if system == "CENTRALIZED" else 3,
                selection_policy=policy, rule_variant="A_ALL_RULES")


def test_prune_removes_only_the_rerun_dataset_scenario_rows(tmp_path):
    pd.DataFrame([_row("A", "CENTRALIZED", "IID", None), _row("A", "FEDERATED", "IID", None),
                  _row("A", "FEDERATED", "DIRICHLET_NONIID", 0.5), _row("B", "CENTRALIZED", "IID", None)]
                 ).to_csv(tmp_path / "shard_3.csv", index=False)
    pd.DataFrame([dict(dataset="A", seed=1001, scenario="CENTRALIZED", phase="SOURCE", status="IncompleteRead", error="x"),
                  dict(dataset="A", seed=1001, scenario="FED_IID", phase="MODEL", status="TIMEOUT", error="y"),
                  dict(dataset="", seed=None, scenario="", phase="REGISTRY", status="NOTE", error="z")]
                 ).to_csv(tmp_path / "failures_3.csv", index=False)
    pd.DataFrame([dict(dataset="A", seed=1001, scenario="CENTRALIZED", wall_seconds=1.0),
                  dict(dataset="B", seed=1001, scenario="CENTRALIZED", wall_seconds=2.0)]
                 ).to_csv(tmp_path / "timings_3.csv", index=False)
    pd.DataFrame(columns=["dataset", "scenario", "scale"]).to_csv(tmp_path / "ladder_3.csv", index=False)
    removed = prune(tmp_path, 3, [["A", "CENTRALIZED"]])
    assert removed == {"shard_3.csv": 1, "failures_3.csv": 1, "timings_3.csv": 1, "ladder_3.csv": 0}
    shard = pd.read_csv(tmp_path / "shard_3.csv")
    assert len(shard) == 3 and not ((shard.dataset == "A") & (shard.system == "CENTRALIZED")).any()
    failures = pd.read_csv(tmp_path / "failures_3.csv")
    assert set(failures.status) == {"TIMEOUT", "NOTE"}


def test_prune_refuses_a_missing_earlier_shard_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        prune(tmp_path, 0, [["A", "CENTRALIZED"]])


def test_download_retry_only_retries_transient_errors(monkeypatch, tmp_path):
    from experiments.full_scale_20261118 import sources
    calls = []

    def flaky(did, allow_fewer_classes=False):
        calls.append(did)
        if len(calls) < 3:
            raise http.client.IncompleteRead(b"x" * 10, 5)
        return "frame", {"ok": True}

    monkeypatch.setattr(sources.openml, "prepare", flaky)
    monkeypatch.setattr(sources.openml, "CACHE", tmp_path)
    assert sources._prepare_openml_with_retry(7, wait=lambda s: None) == ("frame", {"ok": True})
    assert len(calls) == 3

    def always_cut(did, allow_fewer_classes=False):
        raise http.client.IncompleteRead(b"x", 5)

    monkeypatch.setattr(sources.openml, "prepare", always_cut)
    with pytest.raises(http.client.IncompleteRead):
        sources._prepare_openml_with_retry(7, wait=lambda s: None)

    def bad_data(did, allow_fewer_classes=False):
        raise RuntimeError("EXCLUDED_E6")

    calls.clear()
    monkeypatch.setattr(sources.openml, "prepare", lambda did, allow_fewer_classes=False: calls.append(did) or bad_data(did))
    with pytest.raises(RuntimeError):
        sources._prepare_openml_with_retry(7, wait=lambda s: None)
    assert len(calls) == 1
    assert not sources._transient_download_error(urllib.error.HTTPError("u", 404, "nf", None, None))
    assert sources._transient_download_error(urllib.error.HTTPError("u", 503, "busy", None, None))
