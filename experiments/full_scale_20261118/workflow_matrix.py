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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard-count", type=int, required=True)
    p.add_argument("--seeds", required=True)
    a = p.parse_args()
    seeds = [int(s.strip()) for s in a.seeds.split(",") if s.strip()]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be nonempty and distinct")
    datasets, shards = build_matrices(a.shard_count)
    registry = pd.read_csv(G5)
    g5 = registry[(registry.status == "ELIGIBLE_PREPARED") & (registry.row_capped.astype(str) == "False")
                  & (registry.prepared_rows <= 1800)]
    g5_matrix = {"did": sorted(g5.did.astype(int).tolist())}
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write("datasets=" + json.dumps(datasets, separators=(",", ":")) + "\n")
        out.write("shards=" + json.dumps(shards, separators=(",", ":")) + "\n")
        out.write("g5=" + json.dumps(g5_matrix, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
