"""Gate 3 (P2) — label-noise sensitivity of Classical vs VPRS-LEM2 under federation.

Noise is injected into DEVELOPMENT labels only (Validation/Test stay clean).
Real: 20 UCI sources x seeds {11,101} x 3 regimes x 6 noise x {EW3, EW5} x 3 inductions.
Synthetic: known-threshold mixed table, {balanced, skewed} x 5 generator/split seeds
x 3 regimes x 6 noise x {EW3, EW5, MDLP_HIST} x 3 inductions.
"""
from __future__ import annotations

import argparse

from .common import UCI20, run_grid
from .workers import synthetic_model, uci20_model

NOISE = (0.0, 0.01, 0.03, 0.05, 0.10, 0.15)
INDUCTIONS = (("CLASSICAL", 1.0), ("VPRS", 0.8), ("VPRS", 0.6))


def real_tasks():
    return [{"dataset": d, "seed": s, "regime": r, "partition_mode": "ORIGINAL", "discretizer": m,
             "induction": ind, "beta": b, "label_noise": nz}
            for d in UCI20 for s in (11, 101) for r in ("IID", "NONIID_05", "NONIID_01")
            for nz in NOISE for m in ("EQUAL_WIDTH_3", "EQUAL_WIDTH_5") for ind, b in INDUCTIONS]


def synthetic_tasks():
    return [{"dataset": f"synthetic_{imb}", "imbalance": imb, "generator_seed": 500 + s, "seed": 200 + s,
             "regime": r, "partition_mode": "ORIGINAL", "discretizer": m, "induction": ind, "beta": b,
             "label_noise": nz}
            for imb in ("balanced", "skewed") for s in range(5) for r in ("IID", "NONIID_05", "NONIID_01")
            for nz in NOISE for m in ("EQUAL_WIDTH_3", "EQUAL_WIDTH_5", "MDLP_HIST") for ind, b in INDUCTIONS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=28)
    ap.add_argument("--which", choices=("real", "synthetic"), required=True)
    a = ap.parse_args()
    if a.which == "real":
        run_grid("REDESIGN_G3_NOISE_REAL", real_tasks(), uci20_model, n_jobs=a.jobs,
                 tables=("config", "structure", "policies"),
                 extra_manifest={"noise_rates": NOISE, "noise_scope": "development labels only"})
    else:
        run_grid("REDESIGN_G3_NOISE_SYNTHETIC", synthetic_tasks(), synthetic_model, n_jobs=a.jobs,
                 tables=("config", "structure", "policies"),
                 extra_manifest={"noise_rates": NOISE, "generator": "fedrs.noise.synthetic_table"})


if __name__ == "__main__":
    main()
