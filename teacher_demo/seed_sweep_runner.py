"""Run the original LEM2 full-factorial contract for exactly one seed (1..42)."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
import pandas as pd
from roughset.app import discover_datasets
from teacher_demo.full_factorial_matrix import run_full_factorial, _validate_runtime_output

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--output", default="outputs/seed_sweep_1_42")
    args = ap.parse_args()
    if not 1 <= args.seed <= 42:
        raise ValueError("seed must be in 1..42")
    cfg = deepcopy(json.loads(Path("config.json").read_text(encoding="utf-8-sig")))
    cfg["evaluation"]["seed"] = args.seed
    bundles = discover_datasets(cfg)
    df = run_full_factorial(cfg, bundles)
    _validate_runtime_output(df)
    if len(df) != 210 or not (pd.to_numeric(df["seed"]) == args.seed).all():
        raise AssertionError("Seed sweep result contract mismatch")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    fname = out / f"ff_seed{args.seed:02d}.csv"
    df.to_csv(fname, index=False, encoding="utf-8-sig")
    print(f"SEED_SWEEP_PASS seed={args.seed} rows={len(df)} file={fname}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
