"""Prepare an earlier run's merged shard files for a partial rerun.

The earlier run's merged ``shard-<k>`` artifact holds every dataset/scenario of shard k.
For a rerun of selected (dataset, scenario) jobs, drop exactly those rows from the
earlier files; merge_shard then combines what is left with the rerun job artifacts and
reports anything still missing. Source metadata (registry_<k>.csv) is kept: the rerun
emits the same per-dataset metadata and merge_shard requires the two to agree.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

PRUNED = ("shard", "failures", "timings", "ladder")


def scenario_column(frame):
    if "scenario" in frame:
        return frame["scenario"].astype(str)
    from experiments.full_scale_20261118.analysis import scenario_of
    return pd.Series([scenario_of(r) for r in frame.itertuples()], index=frame.index, dtype=str)


def prune(folder, shard, retry_jobs):
    """Remove rows of the rerun (dataset, scenario) pairs; return removed counts per file."""
    folder = Path(folder)
    jobs = {(str(d), str(s)) for d, s in retry_jobs}
    removed = {}
    for prefix in PRUNED:
        path = folder / f"{prefix}_{shard}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Earlier merged shard file is missing: {path}")
        frame = pd.read_csv(path)
        if frame.empty or "dataset" not in frame:
            removed[path.name] = 0
            continue
        scen = scenario_column(frame)
        hit = pd.Series([(str(d), s) in jobs for d, s in zip(frame["dataset"], scen)], index=frame.index)
        removed[path.name] = int(hit.sum())
        frame[~hit].to_csv(path, index=False)
    return removed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--folder", required=True)
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--retry-jobs", required=True, help='JSON list of [dataset, scenario] pairs')
    a = p.parse_args()
    print(json.dumps(prune(a.folder, a.shard, json.loads(a.retry_jobs)), ensure_ascii=False))


if __name__ == "__main__":
    main()
