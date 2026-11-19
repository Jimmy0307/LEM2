"""Full-row adapters around the existing public source loaders."""
from dataclasses import dataclass, field
import hashlib
import io
import json
import re
import shutil
import sys
import time
from pathlib import Path
from copy import deepcopy
from urllib.request import urlopen
from unittest.mock import patch

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from experiments.redesign_20261116 import confirmatory_registry as openml
from roughset.schema import clean_column_name
from teacher_demo import extreme_dataset_runner as uci
from teacher_demo import pmlb_117_runner as pmlb


@dataclass
class Source:
    frame: pd.DataFrame
    features: list
    target: str
    continuous: list
    categorical: list
    raw_sha256: str
    prepared_sha256: str
    original_rows: int
    original_features: int
    original_feature_names: list
    dropped_classes: dict
    source_url: str
    dynamic_types: bool = False
    missing_treatments: dict = field(default_factory=dict)
    excluded_features: list = field(default_factory=list)


class TooFewClasses(ValueError):
    def __init__(self, frame, dropped, details=None):
        super().__init__(f"EXCLUDED_TOO_FEW_CLASSES; dropped={dropped!r}")
        self.frame = frame
        self.dropped = dropped
        self.details = details or {}


def exclusion_details(frame, features, target, original_names, raw_sha, original_rows, original_features, dropped, url):
    counts = frame[target].astype(str).value_counts()
    return dict(source_url=url, raw_sha256=raw_sha,
                prepared_sha256=hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(),
                original_rows=original_rows, used_rows=len(frame), original_features=original_features,
                used_features=len(features), used_feature_names=json.dumps(original_names, ensure_ascii=False),
                n_classes=len(counts), dropped_classes=json.dumps(dropped, ensure_ascii=False),
                minority_share=float(counts.min()/counts.sum()) if len(counts) else None,
                continuous_fraction=None, feature_type=None, status="EXCLUDED_TOO_FEW_CLASSES")


def drop_rare_classes(frame, target):
    counts = frame[target].astype(str).value_counts()
    dropped = {str(label): int(count) for label, count in counts.items() if count < 10}
    result = frame.loc[~frame[target].astype(str).isin(dropped)].copy().reset_index(drop=True)
    if result[target].nunique() < 2:
        raise TooFewClasses(result, dropped)
    return result, dropped


def load_pmlb(name):
    """Use PMLB's pinned registry and downloader with its first-six selection.

    The original loader capped rows and rejected rare classes before they could
    be removed; both operations are replaced by the preregistered full-row
    rule. Numeric missing values are dropped and categorical missing retained.
    """
    spec = pmlb.specs()[name]
    previous_limit = pmlb.MAX_COMPRESSED_BYTES
    try:
        # The feasibility pilot's compressed-size limit must not become an
        # undisclosed substitute for the removed row cap.
        pmlb.MAX_COMPRESSED_BYTES = float("inf")
        blob, _ = pmlb.download(spec)
    finally:
        pmlb.MAX_COMPRESSED_BYTES = previous_limit
    columns = pd.read_csv(io.BytesIO(blob), sep="\t", compression="gzip", nrows=0).columns.tolist()
    if "target" not in columns:
        raise ValueError("MISSING_TARGET_COLUMN")
    original_predictors = [c for c in columns if c != "target"]
    def is_identifier(column):
        text = str(column).lower()
        normalized = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
        return (text.startswith(("unnamed:", "__row_id__")) or normalized in {"id", "index", "identifier", "row_number", "record_number"}
                or normalized.endswith(("_id", "_identifier")))
    excluded = [c for c in original_predictors if is_identifier(c)]
    predictors = [c for c in original_predictors if c not in excluded]
    chosen = predictors[:6]
    if not chosen:
        raise ValueError("NO_PREDICTORS")
    frame = pd.read_csv(io.BytesIO(blob), sep="\t", compression="gzip", usecols=[*chosen, "target"])
    frame = frame[[*chosen, "target"]]
    n_raw = len(frame)
    frame = frame.dropna(subset=["target"])
    # Use observed predictor values, never labels, to distinguish continuous
    # columns from numeric-coded categorical columns before handling missingness.
    continuous = []
    for c in chosen:
        present = frame[c].dropna()
        numeric_like = len(present) > 0 and pd.to_numeric(present, errors="coerce").notna().all()
        if numeric_like and present.nunique() > 10:
            continuous.append(c)
    missing_treatments = {f"f{i}": ("DROP_NUMERIC" if c in continuous else "KEEP_CATEGORY")
                          for i, c in enumerate(chosen) if frame[c].isna().any()}
    frame = frame.dropna(subset=continuous)
    for c in chosen:
        if c not in continuous and frame[c].isna().any():
            frame[c] = frame[c].astype("string").fillna("__MISSING__").astype(str)
    frame["target"] = frame["target"].astype(str)
    names = {c: f"f{i}" for i, c in enumerate(chosen)}
    frame = frame.rename(columns={**names, "target": "class"})
    features = list(names.values())
    try:
        frame, dropped = drop_rare_classes(frame, "class")
    except TooFewClasses as exc:
        exc.frame = exc.frame[features + ["class"]]
        exc.details = exclusion_details(exc.frame, features, "class", chosen, hashlib.sha256(blob).hexdigest(),
                                        n_raw, len(original_predictors), exc.dropped, spec["source_url"])
        exc.details["excluded_features"] = json.dumps(excluded, ensure_ascii=False)
        raise
    frame = frame[features + ["class"]]
    return Source(frame, features, "class", [], [], hashlib.sha256(blob).hexdigest(),
                  hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(),
                  n_raw, len(original_predictors), chosen, dropped, spec["source_url"], True, missing_treatments, excluded)


DOWNLOAD_ATTEMPTS = 3


def _transient_download_error(exc):
    """Network failures worth retrying; data or protocol errors are not."""
    import http.client
    import urllib.error
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500
    return isinstance(exc, (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError))


def _prepare_openml_with_retry(did, attempts=DOWNLOAD_ATTEMPTS, wait=time.sleep):
    """Run the G5 preparation, retrying truncated or failed downloads.

    The data is unchanged by a retry: the same URL is fetched again and its raw SHA-256
    is recorded downstream. The partial cache folder is removed before each retry.
    """
    for attempt in range(1, attempts + 1):
        try:
            return openml.prepare(int(did), allow_fewer_classes=True)
        except Exception as exc:  # noqa: BLE001 - re-raised unless transient
            if attempt == attempts or not _transient_download_error(exc):
                raise
            shutil.rmtree(Path(openml.CACHE) / str(did), ignore_errors=True)
            print(f"OPENML_DOWNLOAD_RETRY did={did} attempt={attempt} error={exc!r}", file=sys.stderr, flush=True)
            wait(20 * attempt)


def load_openml(did, cache_dir):
    """Reuse G5 preparation with its row cap disabled and record drop counts."""
    old_cache, old_limit = openml.CACHE, openml.MAX_ROWS
    try:
        openml.CACHE = Path(cache_dir)
        openml.MAX_ROWS = 2**63 - 1
        frame, meta = _prepare_openml_with_retry(did)
        path = openml.CACHE / str(did) / f"dataset_{int(did)}.pq"
    finally:
        openml.CACHE, openml.MAX_ROWS = old_cache, old_limit
    parquet = pq.ParquetFile(path)
    target = meta["target"]
    columns = list(dict.fromkeys([target] + list(meta["continuous"])))
    before = pd.read_parquet(path, columns=columns)
    before = before[before[target].notna()]
    if meta["continuous"]:
        before = before[~before[meta["continuous"]].isna().any(axis=1)]
    counts = before[target].astype(str).str.strip().value_counts()
    dropped = {str(label): int(counts[label]) for label in meta["dropped_small_classes"]}
    if frame["class"].nunique() < 2:
        details = exclusion_details(frame, list(meta["features"]), "class", list(meta["features"]),
                                    meta["raw_sha256"], parquet.metadata.num_rows,
                                    len(parquet.schema_arrow.names) - 1, dropped, meta["parquet_url"])
        raise TooFewClasses(frame, dropped, details)
    return Source(frame, list(meta["features"]), "class", list(meta["continuous"]),
                  list(meta["categorical"]), meta["raw_sha256"], meta["prepared_sha256"],
                  parquet.metadata.num_rows, len(parquet.schema_arrow.names) - 1,
                  list(meta["features"]), dropped, meta["parquet_url"])


def fetch_uci_with_raw(did):
    from ucimlrepo import fetch_ucirepo
    original_read = pd.read_csv
    captured = []
    def read_and_capture(path, *args, **kwargs):
        if isinstance(path, str) and path.startswith(("https://", "http://")):
            with urlopen(path, timeout=180) as response:
                raw = response.read()
            captured.append((path, raw))
            return original_read(io.BytesIO(raw), *args, **kwargs)
        return original_read(path, *args, **kwargs)
    # The existing ucimlrepo reader parses the captured bytes, so the raw digest
    # identifies the exact data used even if the upstream file changes later.
    with patch.object(pd, "read_csv", read_and_capture):
        dataset = fetch_ucirepo(id=int(did))
    if len(captured) != 1 or captured[0][0] != dataset.metadata.data_url:
        raise ValueError("UCI_RAW_BYTES_NOT_CAPTURED")
    return dataset, captured[0][1]


def load_uci(name):
    """Reuse the UCI reader and remove its pilot cap before execution."""
    from teacher_demo.public_next12_registry import REGISTRY as next12
    import ucimlrepo
    if name in uci.REGISTRY:
        cfg = deepcopy(uci.REGISTRY[name])
    elif name in next12:
        cfg = deepcopy(next12[name])
    else:
        base = {"balance_scale": 12, "car_evaluation": 19, "hayes_roth": 44}
        did = base[name]
        cfg = {"id": did, "name": name, "cap_rows": None, "max_features": 6,
               "feature_mode": "ALL_CATEGORICAL", "url": f"https://archive.ics.uci.edu/dataset/{did}"}
    dataset, raw = fetch_uci_with_raw(cfg["id"])
    dataset = deepcopy(dataset)
    x = dataset.data.features.copy().reset_index(drop=True)
    y = dataset.data.targets.copy().reset_index(drop=True)
    if isinstance(y, pd.Series):
        y = y.to_frame("class")
    original_features, original_rows = len(x.columns), len(x)
    cleaned_x = [clean_column_name(c) for c in x.columns]
    if len(set(cleaned_x)) != len(cleaned_x):
        raise ValueError("Column collision after normalization")
    selected = list(cfg.get("feature_columns") or cleaned_x[:cfg["max_features"]])[:6]
    cfg["cap_rows"], cfg["max_features"] = None, min(6, cfg["max_features"])
    if cfg.get("feature_columns"):
        cfg["feature_columns"] = selected
    if cfg.get("continuous_columns") is not None:
        cfg["continuous_columns"] = [c for c in cfg["continuous_columns"] if c in selected]
    mode = cfg["feature_mode"]
    continuous = (selected if mode == "ALL_CONTINUOUS" else cfg.get("continuous_columns", []) if mode == "EXPLICIT_MIXED"
                  else [c for c in selected if c in ("wife_age", "num_children")] if mode == "CMC_MIXED" else [])
    wanted = cfg.get("target_column")
    target_names = [clean_column_name(c) for c in y.columns]
    if wanted:
        idx = target_names.index(wanted)
    elif len(target_names) == 1:
        idx = 0
    else:
        raise ValueError(f"{name}: expected one target, found {target_names}")
    labels = y.iloc[:, idx].astype("string")
    transformation = cfg.get("label_transform")
    if transformation == "adult_income_strip_period":
        labels = labels.str.strip().str.removesuffix(".")
    elif transformation == "wine_quality_binary_ge6":
        numeric_labels = pd.to_numeric(labels, errors="raise").astype(float).fillna(float("-inf"))
        labels = pd.Series(np.where(numeric_labels >= 6, "HIGH_QUALITY_GE6", "LOW_QUALITY_LT6"), dtype="string")
    elif transformation == "heart_disease_binary_gt0":
        numeric_labels = pd.to_numeric(labels, errors="raise").astype(float).fillna(float("-inf"))
        labels = pd.Series(np.where(numeric_labels > 0, "PRESENT_GT0", "ABSENT_0"), dtype="string")
    elif transformation == "student_final_grade_ge10":
        numeric_labels = pd.to_numeric(labels, errors="raise").astype(float).fillna(float("-inf"))
        labels = pd.Series(np.where(numeric_labels >= 10, "PASS_GE10", "FAIL_LT10"), dtype="string")
    x_normal = x.copy()
    x_normal.columns = cleaned_x
    keep = y.iloc[:, idx].notna()
    if continuous:
        keep &= x_normal[continuous].notna().all(axis=1)
    if cfg.get("drop_incomplete_source_rows"):
        keep &= x_normal[selected].notna().all(axis=1)
    counts = labels[keep].astype(str).value_counts()
    dropped = {str(k): int(v) for k, v in counts.items() if v < 10}
    keep &= ~labels.astype(str).isin(dropped)
    if labels[keep].nunique() < 2:
        partial = x_normal.loc[keep, selected].copy().reset_index(drop=True)
        for col in selected:
            if col in continuous:
                partial[col] = pd.to_numeric(partial[col], errors="raise")
            else:
                partial[col] = partial[col].astype("string").fillna("__MISSING_FEATURE__").astype(str)
        partial["class"] = labels[keep].astype(str).reset_index(drop=True)
        details = exclusion_details(partial, selected, "class", selected, hashlib.sha256(raw).hexdigest(),
                                    original_rows, original_features, dropped, cfg["url"])
        raise TooFewClasses(partial, dropped, details)
    dataset.data.features = x.loc[keep].reset_index(drop=True)
    dataset.data.targets = y.loc[keep].reset_index(drop=True)
    original_fetch = ucimlrepo.fetch_ucirepo
    previous = uci.REGISTRY.get(name)
    try:
        ucimlrepo.fetch_ucirepo = lambda **kwargs: dataset
        uci.REGISTRY[name] = cfg
        bundle, _ = uci.read_external(name)
    finally:
        ucimlrepo.fetch_ucirepo = original_fetch
        if previous is None:
            del uci.REGISTRY[name]
        else:
            uci.REGISTRY[name] = previous
    frame = bundle.frame.reset_index(drop=True)
    return Source(frame, list(bundle.features), bundle.target, list(bundle.schema.continuous),
                  list(bundle.schema.categorical), hashlib.sha256(raw).hexdigest(),
                  hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest(), original_rows,
                  original_features, selected, dropped, cfg["url"])
