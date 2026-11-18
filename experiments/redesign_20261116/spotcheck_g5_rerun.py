"""Deterministic re-execution spot check of published Gate 5 confirmatory tasks.

Re-runs a fixed, pre-declared sample of confirmatory tasks into a scratch folder (never
the published folder) and compares every non-timing column with the published rows.
It does NOT replace or extend the confirmatory sample; it only tests the reproduction chain
(cached OpenML source -> prepared SHA -> split -> partition -> discretize -> reduct -> LEM2
-> predict -> metrics).

Sample (fixed before running): 3 sources drawn with numpy seed 20261116 from the 51
preregistered sources, seeds {1005, 1010}, all 3 regimes, all 7 discretizers = 126 tasks.

Requires data_cache/openml (git-ignored; rebuild with confirmatory_registry if absent).
Usage: python -m experiments.redesign_20261116.spotcheck_g5_rerun --scratch <dir> [--jobs 8]
Writes data/G5_RERUN_SPOTCHECK_20261116.csv (comparison summary only).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import OUT

SAMPLE_SEED = 20261116
SEEDS = (1005, 1010)
TIMING = ("seconds",)
REPORT = OUT / "G5_RERUN_SPOTCHECK_20261116.csv"


def sample_dids() -> list[int]:
    reg = pd.read_csv(OUT / "CONFIRMATORY_SOURCE_REGISTRY.csv")
    dids = sorted(reg[reg.status == "ELIGIBLE_PREPARED"].did.astype(int))
    return sorted(int(x) for x in np.random.default_rng(SAMPLE_SEED).choice(dids, size=3, replace=False))


def compare(table: str, scratch: Path, keys: list[str]) -> dict:
    pub = pd.read_csv(OUT / f"REDESIGN_G5_CONFIRMATORY_{table}.csv", keep_default_na=False, na_values=[""], low_memory=False)
    new = pd.read_csv(scratch / f"REDESIGN_G5_SPOTCHECK_{table}.csv", keep_default_na=False, na_values=[""], low_memory=False)
    cols = [c for c in new.columns if c in pub.columns and not any(t in c for t in TIMING)]
    k = [c for c in keys if c in cols]
    merged = new[cols].merge(pub[cols], on=k, how="left", suffixes=("_new", "_pub"), indicator=True)
    missing = int((merged["_merge"] != "both").sum())
    diffs = {}
    for c in cols:
        if c in k:
            continue
        a, b = merged[f"{c}_new"], merged[f"{c}_pub"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            bad = ~(np.isclose(a, b, rtol=0, atol=1e-12, equal_nan=True))
        else:
            both_null = a.isna() & b.isna()
            bad = ~both_null & (a.astype(str) != b.astype(str))
        if int(bad.sum()):
            diffs[c] = int(bad.sum())
    return {"table": table, "rows_rerun": len(new), "rows_unmatched": missing, "columns_compared": len(cols) - len(k),
            "columns_with_differences": ";".join(f"{c}:{n}" for c, n in diffs.items()),
            "identical": missing == 0 and not diffs}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gate 5 re-execution spot check")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    scratch = Path(a.scratch).resolve()
    if scratch == OUT.resolve():
        raise SystemExit("scratch folder must not be the published evidence folder")
    os.environ["LEM2_REDESIGN_RUN_OUT"] = str(scratch)
    from . import common
    common.RUN_OUT = scratch
    from .gate5_confirmatory import SEEDS as PREREG_SEEDS, confirmatory_model, tasks
    from .common import run_grid
    assert set(SEEDS) <= set(PREREG_SEEDS)
    dids = sample_dids()
    t = [x for x in tasks(dids) if x["seed"] in SEEDS]
    run_grid("REDESIGN_G5_SPOTCHECK", t, confirmatory_model, n_jobs=a.jobs, tables=("config", "structure", "policies"))
    base = ["dataset", "did", "seed", "regime", "partition_mode", "discretizer", "induction", "beta"]
    rows = [compare("POLICIES", scratch, base + ["rule_variant", "method"]),
            compare("STRUCTURE", scratch, base + ["split", "rule_variant"]),
            compare("CONFIG", scratch, base)]
    out = pd.DataFrame(rows).assign(sample_dids=";".join(map(str, dids)), seeds=";".join(map(str, SEEDS)), tasks=len(t))
    out.to_csv(REPORT, index=False)
    print(out.to_string(index=False))
    return 0 if out.identical.all() else 1


if __name__ == "__main__":
    sys.exit(main())
