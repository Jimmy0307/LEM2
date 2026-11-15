"""Gate 2 — supervised vs unsupervised discretization under ONE fixed rule protocol.

Fixed: same 17 UCI sources with continuous features, same seeds/splits/partitions,
Classical reduct + LEM2, UNION; rule variants A/B/B2 evaluated on identical rules.
Count-matched controls (EW/EF with MDLP_HIST's per-feature interval count) separate
cut POSITION from interval COUNT.  P4 prototypes run on the identical grid (--p4).
A separate --memory pass (seed 11 only) records tracemalloc peaks; timing columns
from the main pass are not distorted by tracing.
"""
from __future__ import annotations

import argparse

from .common import ALL_EXPLORATORY_SEEDS, UCI20, run_grid
from .workers import uci20_model

CONTINUOUS_SOURCES = tuple(d for d in UCI20 if d not in ("letter", "mushroom", "phishing"))
GATE2_METHODS = ("EQUAL_WIDTH_3", "EQUAL_WIDTH_5", "EQUAL_FREQUENCY_3", "EQUAL_FREQUENCY_5", "ROBUST_WIDTH_3",
                 "MDLP_CENTRAL", "MDLP_HIST", "CHIMERGE_CENTRAL", "RS_DISCERNIBILITY_CENTRAL",
                 "EW_COUNT_MATCHED_MDLP_HIST", "EF_COUNT_MATCHED_MDLP_HIST")
P4_METHODS = ("EF_HIST_3", "EF_HIST_5", "FCP_HIST", "FCP_HIST_NOCONFLICT", "FED_MD_HIST", "FED_MD_XC",
              "LOCO_SELECT", "LOCO_SELECT_NOCONFLICT", "LOCO_SELECT_NORULES", "LOCO_SELECT_KEEP_TRUE")


def tasks(methods, seeds, memory=False):
    return [{"dataset": d, "seed": s, "regime": r, "partition_mode": "ORIGINAL", "discretizer": m,
             "induction": "CLASSICAL", "beta": 1.0, "measure_memory": memory}
            for d in CONTINUOUS_SOURCES for s in seeds for r in ("IID", "NONIID_05", "NONIID_01") for m in methods]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=28)
    ap.add_argument("--p4", action="store_true")
    ap.add_argument("--memory", action="store_true")
    a = ap.parse_args()
    methods = P4_METHODS if a.p4 else GATE2_METHODS
    seeds = (11,) if a.memory else ALL_EXPLORATORY_SEEDS
    name = ("REDESIGN_G4_PROTOTYPES" if a.p4 else "REDESIGN_G2_DISCRETIZATION") + ("_MEMORY" if a.memory else "")
    run_grid(name, tasks(methods, seeds, a.memory), uci20_model, n_jobs=a.jobs,
             tables=("config", "structure", "policies") if not a.memory else ("config",),
             extra_manifest={"methods": list(methods), "sources": list(CONTINUOUS_SOURCES),
                             "seed_status": "ALL EXPLORATORY", "test_labels_used_for_cuts": False})


if __name__ == "__main__":
    main()
