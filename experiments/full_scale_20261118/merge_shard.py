"""Combine dataset/scenario jobs into the three requested shard artifacts."""
import argparse
from pathlib import Path

import pandas as pd
from experiments.full_scale_20261118.analysis import scenario_of
from experiments.full_scale_20261118.model import SCENARIOS
from experiments.full_scale_20261118.registry import assign_shards, source_registry
from experiments.full_scale_20261118.shard import FULL19, _write


def coalesce_metadata(meta):
    if meta.empty:
        return meta
    check = [c for c in meta.columns if c != "dataset"]
    for dataset, group in meta.groupby("dataset", sort=True):
        normalized = group[check].fillna("<missing>").astype(str)
        if (normalized.nunique(dropna=False) > 1).any():
            cols = normalized.columns[normalized.nunique(dropna=False) > 1].tolist()
            raise ValueError(f"SOURCE_METADATA_MISMATCH {dataset}: {cols}")
    return meta.drop_duplicates(subset=["dataset"]).reset_index(drop=True)


def _read(directory, prefix, shard):
    files = sorted(Path(directory).rglob(f"{prefix}_{shard}.csv"))
    return pd.concat([pd.read_csv(p) for p in files], ignore_index=True) if files else pd.DataFrame()


def merge(directory, output, shard, shard_count, seeds):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    registry = assign_shards(source_registry(), shard_count)
    planned = registry[(registry.status == "PENDING") & (registry.shard == shard)]
    datasets = set(planned.dataset)
    rows = _read(directory, "shard", shard)
    timings = _read(directory, "timings", shard)
    ladder = _read(directory, "ladder", shard)
    failures = _read(directory, "failures", shard)
    try:
        metadata = coalesce_metadata(_read(directory, "registry", shard))
    except ValueError as exc:
        failures = pd.concat([failures, pd.DataFrame([dict(phase="SOURCE", status="SOURCE_METADATA_MISMATCH", error=str(exc))])], ignore_index=True)
        _write(output / f"failures_{shard}.csv", failures.to_dict("records"), ["dataset", "seed", "scenario", "phase", "status", "error"])
        raise
    expected = {(d, int(seed), scenario) for d in datasets for seed in seeds for scenario in SCENARIOS}
    if not rows.empty and not set(rows.dataset).issubset(datasets):
        raise ValueError("Unexpected dataset in shard artifact")
    primary = rows[rows.rule_variant == "A_ALL_RULES"] if not rows.empty else rows
    found = {(r.dataset, int(r.seed), scenario_of(r)) for r in primary.itertuples()}
    if failures.empty:
        failures = pd.DataFrame(columns=["dataset", "seed", "scenario", "phase", "status", "error"])
    else:
        registry_failures = failures[failures.phase == "REGISTRY"].drop_duplicates(subset=["dataset", "phase", "status", "error"])
        failures = pd.concat([failures[failures.phase != "REGISTRY"], registry_failures], ignore_index=True)
    known = {(r.dataset, int(r.seed), r.scenario) for r in failures.itertuples()
             if pd.notna(getattr(r, "dataset", None)) and pd.notna(getattr(r, "seed", None))
             and getattr(r, "scenario", None) in SCENARIOS and getattr(r, "phase", None) in ("MODEL", "SOURCE", "SHARD")}
    missing = expected - found - known
    if missing:
        add = [dict(dataset=d, seed=s, scenario=sc, phase="SHARD", status="MISSING_DATASET_JOB_ARTIFACT",
                    error="Dataset/scenario job did not upload a result or failure artifact") for d, s, sc in sorted(missing)]
        failures = pd.concat([failures, pd.DataFrame(add)], ignore_index=True)
    # The ladder always uses seed 1001, even with custom primary seeds.
    actual_ladder = {(r.dataset, r.scenario, str(r.scale)) for r in ladder.itertuples()} if not ladder.empty else set()
    failed_ladder = {(r.dataset, r.scenario, str(r.scale)) for r in failures.itertuples()
                     if getattr(r, "phase", None) == "SCALE_LADDER" and pd.notna(getattr(r, "scale", None))}
    large = planned[planned.original_rows >= 20_000]
    for dataset in large.dataset:
        for scenario in ("FED_IID", "FED_A01"):
            for scale in ("1800", "10000", "FULL"):
                if (dataset, scenario, scale) not in actual_ladder | failed_ladder:
                    failures = pd.concat([failures, pd.DataFrame([dict(dataset=dataset, seed=1001, scenario=scenario,
                                           phase="SCALE_LADDER", scale=scale, status="MISSING_DATASET_JOB_ARTIFACT",
                                           error="No ladder result or failure artifact")])], ignore_index=True)
    _write(output / f"shard_{shard}.csv", rows.to_dict("records"), FULL19 + ["rule_variant"])
    _write(output / f"failures_{shard}.csv", failures.to_dict("records"), ["dataset", "seed", "scenario", "phase", "status", "error"])
    _write(output / f"timings_{shard}.csv", timings.to_dict("records"), ["dataset", "seed", "scenario", "partition_status", "partition_attempts"])
    _write(output / f"registry_{shard}.csv", metadata.to_dict("records"), ["cohort", "dataset", "status"])
    _write(output / f"ladder_{shard}.csv", ladder.to_dict("records"), FULL19 + ["rule_variant", "scenario", "scale", "scale_rows", "dropped_classes"])
    return 3 if "status" in failures and (failures.status == "ConflictBoundViolation").any() else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shard-count", type=int, required=True)
    p.add_argument("--seeds", required=True)
    a = p.parse_args()
    return merge(a.artifacts, a.output, a.shard, a.shard_count, [int(s.strip()) for s in a.seeds.split(",") if s.strip()])


if __name__ == "__main__":
    raise SystemExit(main())
