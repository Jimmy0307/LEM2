"""Construct GitHub Actions matrices without shell interpolation of names."""
import argparse
import hashlib
import json
import os

from experiments.full_scale_20261118.registry import assign_shards, source_registry
from experiments.full_scale_20261118.registry import G5
import pandas as pd


def build_matrices(shard_count):
    if not 11 <= shard_count <= 256:
        raise ValueError("shard_count must be 11–256")
    registry = assign_shards(source_registry(), shard_count)
    chosen = registry[registry.status == "PENDING"].sort_values("dataset")
    include = [dict(dataset=r.dataset, shard=int(r.shard),
                    token=hashlib.sha256(r.dataset.encode("utf-8")).hexdigest()[:16]) for r in chosen.itertuples()]
    if len(include) > 256 or len({x["token"] for x in include}) != len(include):
        raise ValueError("GitHub matrix limit exceeded or artifact token collision")
    return {"include": include}, {"shard": list(range(shard_count))}


def build_retry_matrix(datasets_matrix, retry_jobs):
    """Restrict a rerun to specific (dataset, scenario) jobs of an earlier run."""
    from experiments.full_scale_20261118.model import SCENARIOS
    by_name = {x["dataset"]: x for x in datasets_matrix["include"]}
    include, seen = [], set()
    for dataset, scenario in retry_jobs:
        if dataset not in by_name:
            raise ValueError(f"Retry dataset is not a planned source: {dataset}")
        if scenario not in SCENARIOS:
            raise ValueError(f"Retry scenario is not valid: {scenario}")
        if (dataset, scenario) in seen:
            raise ValueError(f"Duplicate retry job: {dataset} {scenario}")
        seen.add((dataset, scenario))
        include.append(dict(by_name[dataset], scenario=scenario))
    if not include:
        raise ValueError("Retry mode needs at least one job")
    return {"include": include}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard-count", type=int, required=True)
    p.add_argument("--seeds", required=True)
    p.add_argument("--retry-jobs", default="", help='JSON list of [dataset, scenario] pairs')
    a = p.parse_args()
    seeds = [int(s.strip()) for s in a.seeds.split(",") if s.strip()]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be nonempty and distinct")
    datasets, shards = build_matrices(a.shard_count)
    retry = build_retry_matrix(datasets, json.loads(a.retry_jobs)) if a.retry_jobs.strip() else {"include": []}
    registry = pd.read_csv(G5)
    g5 = registry[(registry.status == "ELIGIBLE_PREPARED") & (registry.row_capped.astype(str) == "False")
                  & (registry.prepared_rows <= 1800)]
    g5_matrix = {"did": sorted(g5.did.astype(int).tolist())}
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write("datasets=" + json.dumps(datasets, separators=(",", ":")) + "\n")
        out.write("shards=" + json.dumps(shards, separators=(",", ":")) + "\n")
        out.write("g5=" + json.dumps(g5_matrix, separators=(",", ":")) + "\n")
        out.write("retry=" + json.dumps(retry, separators=(",", ":"), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
