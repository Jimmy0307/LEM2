"""Gate 0/1 — TRUE -> d degeneracy: Baseline A / Control B (+B2) / Control C.

Rules are induced ONCE per (dataset, seed, regime, partition) on Equal-Width-3
(original baseline).  A / B / B2 are merge/prediction-layer variants of the SAME
rules (fedrs.predict.RULE_VARIANTS).  Control C re-draws the client partition
under degeneracy constraints and is reported separately (different data allocation).

Seeds 11/23 reproduce the historical protocol; 101..108 are additional
EXPLORATORY seeds on the same 20 already-explored UCI sources.
"""
from __future__ import annotations

import argparse

from .common import ALL_EXPLORATORY_SEEDS, UCI20, run_grid
from .workers import uci20_model


def tasks():
    out = []
    for d in UCI20:
        for s in ALL_EXPLORATORY_SEEDS:
            for r in ("IID", "NONIID_05", "NONIID_01"):
                for p in ("ORIGINAL", "CONTROL_C"):
                    out.append({"dataset": d, "seed": s, "regime": r, "partition_mode": p,
                                "discretizer": "EQUAL_WIDTH_3", "induction": "CLASSICAL", "beta": 1.0})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    t = tasks()
    if a.limit:
        t = t[: a.limit]
    run_grid("REDESIGN_G1_DEGENERACY", t, uci20_model, n_jobs=a.jobs,
             extra_manifest={"protocol": "nested 64/16/20; EW3; CLASSICAL reduct+LEM2; 3 clients",
                             "control_c_constraint": "min_rows=20, min_classes=2, min_rows_per_present_class=3, max_attempts=500",
                             "seed_status": "ALL EXPLORATORY (11/23 historically reused)"})


if __name__ == "__main__":
    main()
