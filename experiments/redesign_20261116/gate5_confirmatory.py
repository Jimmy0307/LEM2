"""Gate 5 — confirmatory run under PREREGISTRATION_CONFIRMATORY_20261116.md (frozen)."""
from __future__ import annotations

import argparse
import hashlib
import json

import pandas as pd

from .common import OUT, ROOT, bootstrap_path, flatten, run_grid
from .workers import Source, run_source

SEEDS = tuple(range(1001, 1011))
REGIMES = ("IID", "NONIID_05", "NONIID_01")
DISCRETIZERS = ("EQUAL_WIDTH_3", "EQUAL_WIDTH_5", "MDLP_HIST", "FED_MD_HIST", "FED_MD_XC",
                "RS_DISCERNIBILITY_CENTRAL", "CART")
CACHE = ROOT / "data_cache" / "openml"


def openml_source(did: int) -> Source:
    folder = CACHE / str(did)
    meta = json.loads((folder / "prepared_meta.json").read_text(encoding="utf-8"))
    df = pd.read_csv(folder / "prepared.csv", dtype={c: str for c in meta["categorical"] + ["class"]},
                     float_precision="round_trip", keep_default_na=False, na_values=[""])
    for c in meta["categorical"]:
        df[c] = df[c].fillna("__MISSING__").astype(str)
    sha = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
    assert sha == meta["prepared_sha256"], f"prepared SHA mismatch for {did}"
    return Source(f"openml_{did}", df, list(meta["features"]), "class", list(meta["continuous"]),
                  list(meta["categorical"]), sha, {"did": did, "raw_sha256": meta["raw_sha256"]})


def confirmatory_model(task: dict) -> dict:
    bootstrap_path()
    src = openml_source(task["did"])
    if task["discretizer"] != "CART":
        return run_source(task, src)
    from fedrs.baselines import cart_rows
    from fedrs.experiment import nested_split
    from fedrs.partition import original_partition
    dev, val, test = nested_split(src.frame, src.target, task["seed"])
    clients = original_partition(dev, src.target, 3, task["seed"], task["regime"])
    rows = cart_rows(clients, dev, val, test, src.continuous, src.categorical, src.target)
    return {"config": [{"source_sha256": src.sha256}], "policies": [{**r, "rule_variant": "NA"} for r in rows],
            "clients": [], "structure": []}


def tasks(dids):
    return [{"dataset": f"openml_{d}", "did": int(d), "seed": s, "regime": r, "partition_mode": "ORIGINAL",
             "discretizer": m, "induction": "CLASSICAL", "beta": 1.0}
            for d in dids for s in SEEDS for r in REGIMES for m in DISCRETIZERS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=28)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    reg = pd.read_csv(OUT / "CONFIRMATORY_SOURCE_REGISTRY.csv")
    dids = reg[reg.status == "ELIGIBLE_PREPARED"].did.astype(int).tolist()
    t = tasks(dids)
    if a.limit:
        t = t[: a.limit]
    run_grid("REDESIGN_G5_CONFIRMATORY" + ("_SMOKE" if a.limit else ""), t, confirmatory_model, n_jobs=a.jobs,
             tables=("config", "structure", "policies"),
             extra_manifest={"preregistration": "docs/research/redesign_20261116/PREREGISTRATION_CONFIRMATORY_20261116.md",
                             "sources": len(dids), "seeds": list(SEEDS), "regimes": list(REGIMES)})


if __name__ == "__main__":
    main()
