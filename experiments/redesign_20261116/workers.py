"""Picklable workers shared by the gate runners."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import List

from .common import bootstrap_path, flatten, split_id, uci20_bundle


@dataclass
class Source:
    name: str
    frame: object
    features: List[str]
    target: str
    continuous: List[str]
    categorical: List[str]
    sha256: str
    extra: dict = field(default_factory=dict)


def uci20_source(name: str) -> Source:
    bundle, sha = uci20_bundle(name)
    return Source(name, bundle.frame, list(bundle.features), bundle.target, list(bundle.schema.continuous),
                  list(bundle.schema.categorical), sha)


def synthetic_source(imbalance: str, seed: int, n: int = 1500) -> Source:
    bootstrap_path()
    from fedrs.noise import synthetic_table
    df = synthetic_table(n, imbalance, seed)
    sha = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
    return Source(f"synthetic_{imbalance}", df, ["x1", "x2", "x3", "c1", "c2"], "class",
                  ["x1", "x2", "x3"], ["c1", "c2"], sha, {"generator_seed": seed})


def run_source(task: dict, src: Source) -> dict:
    bootstrap_path()
    from fedrs.conflict_cuts import make_discretizer
    from fedrs.experiment import evaluate, fit_model, nested_split
    from fedrs.partition import constrained_partition, label_skew_index, original_partition

    dev, val, test = nested_split(src.frame, src.target, task["seed"])
    noise = float(task.get("label_noise", 0.0))
    if noise:
        from fedrs.noise import flip_labels
        dev = flip_labels(dev, src.target, noise, seed=task["seed"] * 7919 + 17)
    if task.get("partition_mode", "ORIGINAL") == "ORIGINAL":
        clients, attempts, status = original_partition(dev, src.target, 3, task["seed"], task["regime"]), 1, "OK"
    elif task["partition_mode"] == "CONTROL_C":
        clients, attempts, status = constrained_partition(dev, src.target, 3, task["seed"], task["regime"])
        if clients is None:
            raise RuntimeError(f"CONTROL_C_PARTITION_{status}")
    else:
        raise ValueError(task["partition_mode"])
    disc = make_discretizer(task.get("discretizer", "EQUAL_WIDTH_3"), src.features)
    fm = fit_model(src.features, src.continuous, src.categorical, src.target, clients, dev, val, test, disc,
                   task.get("induction", "CLASSICAL"), task.get("beta", 1.0),
                   measure_memory=task.get("measure_memory", False))
    res = evaluate(fm, task["regime"])
    res["config"].update({
        "source_sha256": src.sha256, "split_id": split_id(src.name, task["seed"]),
        "partition_attempts": attempts, "partition_status": status,
        "label_skew_tv": label_skew_index(clients, src.target),
        "continuous_features": len(src.continuous), "categorical_features": len(src.categorical),
        "feature_type": ("ALL_CONTINUOUS" if not src.categorical else
                         "ALL_CATEGORICAL" if not src.continuous else "MIXED"),
        "n_classes_total": int(src.frame[src.target].nunique()),
        "dev_rows": len(dev), "val_rows": len(val), "test_rows": len(test),
        "cut_method_resolved": fm.cut_model.method,
        "cut_model_extra_json": json.dumps(fm.cut_model.extra, default=str)[:4000],
        **{f"source_{k}": v for k, v in src.extra.items()},
    })
    return flatten(task, res)


def uci20_model(task: dict) -> dict:
    """task keys: dataset, seed, regime, partition_mode, discretizer, induction, beta, label_noise, measure_memory."""
    bootstrap_path()
    return run_source(task, uci20_source(task["dataset"]))


def synthetic_model(task: dict) -> dict:
    bootstrap_path()
    return run_source(task, synthetic_source(task["imbalance"], task["generator_seed"]))
