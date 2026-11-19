import gzip
import hashlib
import io
import json
import time
from types import SimpleNamespace

import pandas as pd
import pytest
import ucimlrepo

from experiments.full_scale_20261118 import sources
from experiments.full_scale_20261118.dataset_worker import metadata
from experiments.full_scale_20261118 import dataset_worker


def test_pmlb_retries_rare_classes_without_sampling(monkeypatch):
    frame = pd.DataFrame({**{f"x{i}": range(29) for i in range(7)},
                          "target": ["a"] * 10 + ["b"] * 10 + ["rare"] * 9})
    blob = gzip.compress(frame.to_csv(index=False, sep="\t").encode(), mtime=0)
    monkeypatch.setattr(sources.pmlb, "specs", lambda: {"test": {"source_url": "https://example.test", "raw_url": "unused"}})
    monkeypatch.setattr(sources.pmlb, "download", lambda spec: (blob, 0.0))
    result = sources.load_pmlb("test")
    assert len(result.frame) == 20
    assert result.features == [f"f{i}" for i in range(6)]
    assert result.dropped_classes == {"rare": 9}
    assert result.raw_sha256 == hashlib.sha256(blob).hexdigest()


def test_pmlb_keeps_missing_numeric_categorical_values(monkeypatch):
    data = pd.DataFrame({"binary": [0, 1] * 12 + [float("nan")], "continuous": range(25),
                         "target": ["a"] * 12 + ["b"] * 13})
    blob = gzip.compress(data.to_csv(index=False, sep="\t").encode(), mtime=0)
    monkeypatch.setattr(sources.pmlb, "specs", lambda: {"test": {"source_url": "url", "raw_url": "unused"}})
    monkeypatch.setattr(sources.pmlb, "download", lambda spec: (blob, 0.0))
    result = sources.load_pmlb("test")
    assert len(result.frame) == 25
    assert result.frame["f0"].iloc[-1] == "__MISSING__"
    assert result.missing_treatments == {"f0": "KEEP_CATEGORY"}


def test_pmlb_excludes_explicit_identifiers_before_selecting_six(monkeypatch):
    data = pd.DataFrame({"patient_id": range(20), **{f"x{i}": range(20) for i in range(7)},
                         "target": ["a"] * 10 + ["b"] * 10})
    blob = gzip.compress(data.to_csv(index=False, sep="\t").encode(), mtime=0)
    monkeypatch.setattr(sources.pmlb, "specs", lambda: {"test": {"source_url": "url", "raw_url": "unused"}})
    monkeypatch.setattr(sources.pmlb, "download", lambda spec: (blob, 0.0))
    result = sources.load_pmlb("test")
    assert result.original_feature_names == [f"x{i}" for i in range(6)]
    assert result.original_features == 8
    assert result.excluded_features == ["patient_id"]


def test_rare_class_removal_requires_two_remaining_classes():
    frame = pd.DataFrame({"class": ["a"] * 10 + ["rare"] * 9})
    with pytest.raises(ValueError, match="EXCLUDED_TOO_FEW_CLASSES"):
        sources.drop_rare_classes(frame, "class")


def test_too_few_classes_preserves_metadata_for_registry(monkeypatch):
    data = pd.DataFrame({"x": range(19), "target": ["a"] * 10 + ["rare"] * 9})
    blob = gzip.compress(data.to_csv(index=False, sep="\t").encode(), mtime=0)
    monkeypatch.setattr(sources.pmlb, "specs", lambda: {"test": {"source_url": "url", "raw_url": "unused"}})
    monkeypatch.setattr(sources.pmlb, "download", lambda spec: (blob, 0.0))
    with pytest.raises(sources.TooFewClasses) as raised:
        sources.load_pmlb("test")
    details = raised.value.details
    assert details["status"] == "EXCLUDED_TOO_FEW_CLASSES"
    assert details["dropped_classes"] == '{"rare": 9}'
    assert details["raw_sha256"] == hashlib.sha256(blob).hexdigest()
    assert details["used_rows"] == 10 and details["n_classes"] == 1


def test_excluded_source_emits_registry_and_failure_events(monkeypatch, tmp_path):
    frame = pd.DataFrame({"f0": range(10), "class": ["a"] * 10})
    details = sources.exclusion_details(frame, ["f0"], "class", ["x"], "sha", 19, 1, {"rare": 9}, "url")
    def excluded(name):
        raise sources.TooFewClasses(frame, {"rare": 9}, details)
    monkeypatch.setattr(dataset_worker, "load_pmlb", excluded)
    events = tmp_path / "events.jsonl"
    args = SimpleNamespace(dataset="PMLB:allbp", events=str(events), cache=str(tmp_path),
                           seeds="1001", deadline=time.time()+10, isolated=False)
    assert dataset_worker.run(args) == 1
    records = [json.loads(line) for line in events.read_text().splitlines()]
    assert records[0]["record"]["status"] == "EXCLUDED_TOO_FEW_CLASSES"
    assert records[1]["status"] == "EXCLUDED_TOO_FEW_CLASSES"


def test_source_hashes_survive_seed_type_metadata_failure(monkeypatch, tmp_path):
    frame = pd.DataFrame({"x": range(20), "class": ["a"] * 10 + ["b"] * 10})
    src = sources.Source(frame, ["x"], "class", ["x"], [], "rawsha", "prepsha", 20, 1, ["x"], {}, "url")
    monkeypatch.setattr(dataset_worker, "load_uci", lambda name: src)
    def bad_metadata(*args):
        raise ValueError("split failed")
    monkeypatch.setattr(dataset_worker, "metadata", bad_metadata)
    monkeypatch.setattr(dataset_worker, "invoke_with_deadline", lambda *args: {"status": "SPLIT_FAILED", "error": "split failed"})
    events = tmp_path / "events.jsonl"
    args = SimpleNamespace(dataset="UCI20:iris", events=str(events), cache=str(tmp_path),
                           seeds="1001", deadline=time.time()+10, isolated=False, scenarios="CENTRALIZED")
    dataset_worker.run(args)
    records = [json.loads(line) for line in events.read_text().splitlines()]
    assert records[0]["record"]["raw_sha256"] == "rawsha"
    assert records[0]["record"]["prepared_sha256"] == "prepsha"
    assert records[1]["status"] == "FEATURE_TYPE_METADATA_ERROR"


def test_openml_adapter_removes_cap_and_preserves_rare_counts(monkeypatch, tmp_path):
    raw = pd.DataFrame({"x": range(29), "label": ["a"] * 10 + ["b"] * 10 + ["rare"] * 9})
    path = tmp_path / "37" / "dataset_37.pq"
    path.parent.mkdir()
    raw.to_parquet(path)
    meta = {"features": ["x"], "target": "label", "continuous": ["x"], "categorical": [],
            "raw_sha256": "raw", "prepared_sha256": "prepared", "parquet_url": "url", "dropped_small_classes": ["rare"]}
    def prepare(did, *, allow_fewer_classes=False):
        assert sources.openml.MAX_ROWS > len(raw)
        assert allow_fewer_classes
        return raw.iloc[:20].rename(columns={"label": "class"}), meta
    monkeypatch.setattr(sources.openml, "prepare", prepare)
    old = sources.openml.MAX_ROWS
    result = sources.load_openml(37, tmp_path)
    assert result.dropped_classes == {"rare": 9}
    assert result.original_rows == 29
    assert sources.openml.MAX_ROWS == old


def test_openml_exclusion_keeps_raw_hash_and_dropped_counts(monkeypatch, tmp_path):
    raw = pd.DataFrame({"x": range(19), "label": ["a"] * 10 + ["rare"] * 9})
    path = tmp_path / "37" / "dataset_37.pq"
    path.parent.mkdir()
    raw.to_parquet(path)
    meta = {"features": ["x"], "target": "label", "continuous": ["x"], "categorical": [],
            "raw_sha256": "raw", "prepared_sha256": "prepared", "parquet_url": "url", "dropped_small_classes": ["rare"]}
    monkeypatch.setattr(sources.openml, "prepare", lambda did, **kwargs: (raw.iloc[:10].rename(columns={"label": "class"}), meta))
    with pytest.raises(sources.TooFewClasses) as raised:
        sources.load_openml(37, tmp_path)
    assert raised.value.details["raw_sha256"] == "raw"
    assert raised.value.dropped == {"rare": 9}
    assert raised.value.details["status"] == "EXCLUDED_TOO_FEW_CLASSES"


def test_original_openml_loader_keeps_default_exclusion_behavior(monkeypatch, tmp_path):
    raw = pd.DataFrame({"x": [i % 5 for i in range(19)], "label": ["a"] * 10 + ["rare"] * 9})
    path = tmp_path / "raw.pq"
    raw.to_parquet(path)
    desc = {"default_target_attribute": "label", "parquet_url": "url"}
    feats = [{"name": "x", "index": "0", "data_type": "numeric"},
             {"name": "label", "index": "1", "data_type": "nominal"}]
    monkeypatch.setattr(sources.openml, "_download", lambda did: (desc, feats, path))
    with pytest.raises(RuntimeError, match="FEWER_THAN_2_CLASSES"):
        sources.openml.prepare(37)
    frame, meta = sources.openml.prepare(37, allow_fewer_classes=True)
    assert len(frame) == 10 and frame["class"].nunique() == 1
    assert meta["dropped_small_classes"] == ["rare"]


def test_openml_loader_records_when_all_classes_are_rare(monkeypatch, tmp_path):
    raw = pd.DataFrame({"x": [i % 5 for i in range(18)], "label": ["a"] * 9 + ["b"] * 9})
    folder = tmp_path / "37"
    folder.mkdir()
    path = folder / "dataset_37.pq"
    raw.to_parquet(path)
    desc = {"default_target_attribute": "label", "parquet_url": "url"}
    feats = [{"name": "x", "index": "0", "data_type": "numeric"},
             {"name": "label", "index": "1", "data_type": "nominal"}]
    monkeypatch.setattr(sources.openml, "_download", lambda did: (desc, feats, path))
    with pytest.raises(sources.TooFewClasses) as raised:
        sources.load_openml(37, tmp_path)
    assert raised.value.details["n_classes"] == 0
    assert raised.value.dropped == {"a": 9, "b": 9}


def test_uci_adapter_clears_cap_and_trims_selected_features(monkeypatch):
    data = pd.DataFrame({**{f"x{i}": range(25) for i in range(9)}, "target": ["a"] * 12 + ["b"] * 12 + ["z"]})
    dataset = SimpleNamespace(data=SimpleNamespace(features=data.drop(columns="target"), targets=data[["target"]]))
    monkeypatch.setattr(sources, "fetch_uci_with_raw", lambda did: (dataset, b"raw bytes"))
    cfg = {"id": 1, "name": "example", "cap_rows": 20, "max_features": 9,
           "feature_mode": "ALL_CONTINUOUS", "url": "https://example.test"}
    monkeypatch.setitem(sources.uci.REGISTRY, "test_fullscale", cfg)
    result = sources.load_uci("test_fullscale")
    assert len(result.frame) == 24
    assert result.features == [f"x{i}" for i in range(6)]
    assert result.dropped_classes == {"z": 1}
    assert result.raw_sha256 == hashlib.sha256(b"raw bytes").hexdigest()
    assert sources.uci.REGISTRY["test_fullscale"]["cap_rows"] == 20


def test_uci_raw_hash_uses_exact_bytes_read_by_loader(monkeypatch):
    raw = b"x,target\n1,a\n2,b\n"
    url = "https://archive.ics.uci.edu/static/test.csv"
    original_read = pd.read_csv
    reads = []
    def fake_read(path, *args, **kwargs):
        reads.append(path)
        return original_read(io.BytesIO(raw) if path == url else path, *args, **kwargs)
    def fake_fetch(id):
        frame = pd.read_csv(url)
        return SimpleNamespace(data=SimpleNamespace(original=frame), metadata=SimpleNamespace(data_url=url))
    monkeypatch.setattr(pd, "read_csv", fake_read)
    monkeypatch.setattr(ucimlrepo, "fetch_ucirepo", fake_fetch)
    monkeypatch.setattr(sources, "urlopen", lambda url, timeout: io.BytesIO(raw))
    dataset, actual = sources.fetch_uci_with_raw(1)
    assert actual == raw
    assert len(reads) == 1 and isinstance(reads[0], io.BytesIO)
    assert len(dataset.data.original) == 2


def test_uci_too_few_classes_keeps_exclusion_details(monkeypatch):
    data = pd.DataFrame({"x": range(19), "target": ["a"] * 10 + ["rare"] * 9})
    dataset = SimpleNamespace(data=SimpleNamespace(features=data[["x"]], targets=data[["target"]]))
    monkeypatch.setattr(sources, "fetch_uci_with_raw", lambda did: (dataset, b"raw bytes"))
    monkeypatch.setitem(sources.uci.REGISTRY, "test_excluded", {"id": 1, "name": "test", "cap_rows": None,
                                                                "max_features": 1, "feature_mode": "ALL_CONTINUOUS",
                                                                "url": "url"})
    with pytest.raises(sources.TooFewClasses) as raised:
        sources.load_uci("test_excluded")
    assert raised.value.details["status"] == "EXCLUDED_TOO_FEW_CLASSES"
    assert raised.value.details["used_rows"] == 10
    assert raised.value.dropped == {"rare": 9}


@pytest.mark.parametrize("transformation", ["heart_disease_binary_gt0", "wine_quality_binary_ge6", "student_final_grade_ge10"])
def test_uci_binary_transforms_remove_missing_nullable_targets(monkeypatch, transformation):
    y = pd.Series([0] * 10 + [10] * 10 + [None], dtype="Int64", name="target")
    dataset = SimpleNamespace(data=SimpleNamespace(features=pd.DataFrame({"x": range(21)}), targets=y.to_frame()))
    monkeypatch.setattr(sources, "fetch_uci_with_raw", lambda did: (dataset, b"raw bytes"))
    monkeypatch.setitem(sources.uci.REGISTRY, "test_nullable", {"id": 1, "name": "test", "cap_rows": None,
                                                                "max_features": 1, "feature_mode": "ALL_CONTINUOUS",
                                                                "label_transform": transformation, "url": "url"})
    result = sources.load_uci("test_nullable")
    assert len(result.frame) == 20 and result.frame["class"].nunique() == 2


def test_seed_dependent_feature_types_are_reported_without_exclusion():
    frame = pd.DataFrame({"f0": list(range(10)) * 12 + [10], "class": ["a", "b"] * 60 + ["a"]})
    source = sources.Source(frame, ["f0"], "class", [], [], "raw", "prepared", 121, 1, ["x"], {}, "url", True)
    item = SimpleNamespace(cohort="PMLB", dataset="PMLB:test", upstream_commit="commit", same_source_as="", related_source="")
    result = metadata(source, item, [1001, 1002, 1003, 1004, 1005])
    assert result["feature_type"] is None
    assert result["continuous_fraction"] is None
    assert result["feature_type_varies"]
    assert '"1002": ["f0"]' in result["continuous_by_seed"]
    assert result["status"] == "PREPARED"
