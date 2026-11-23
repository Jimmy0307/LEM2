"""Pilot CLI; does not mutate the frozen 188x42 checkpoint/result directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .protocol import SCENARIOS, VARIANTS, run_one


def main():
    cli = argparse.ArgumentParser(description="Validation-before-Test LEM2 pilot, source-safe")
    cli.add_argument("--csv", type=Path, required=True, help="CSV with discrete target and no missing values")
    cli.add_argument("--target", required=True)
    cli.add_argument("--features", nargs="+", help="candidate features; defaults to first <=6 non-target columns")
    cli.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    cli.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=["CENTRALIZED", "FED_IID"])
    cli.add_argument("--variants", nargs="+", choices=VARIANTS, default=["B2_TRUE_AS_FALLBACK"])
    cli.add_argument("--metric", choices=["accuracy", "ba"], default="ba")
    cli.add_argument("--include-legacy", action="store_true",
                     help="Also fit fresh 64/16/20 validation selection; this is not the original frozen Test-selected result")
    cli.add_argument("--out", type=Path, default=Path("validation_first_results"))
    args = cli.parse_args()
    df = pd.read_csv(args.csv)
    if args.target not in df:
        cli.error("target column not in csv")
    features = args.features or [c for c in df.columns if c != args.target][:6]
    if len(features) > 6:
        cli.error(">6 features must be a distinct preregistered ablation")
    if any(f not in df for f in features):
        cli.error("unknown feature")
    args.out.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    receipt = {
        "protocol": "validation_first_20261123_v1",
        "source_file_sha256": source_sha, "source_filename": args.csv.name,
        "source_n_rows": len(df), "features": list(features), "target": args.target,
        "seeds": list(args.seeds), "scenarios": args.scenarios,
        "variants": args.variants, "selection_metric": args.metric,
        "include_legacy": args.include_legacy,
        "candidate_policy_selection_uses": "Validation only; never Test",
        "test_policy_evaluation": "frozen policy and fixed STV, paired same 20% Test",
        "privacy_note": "horizontal FL simulation, not cryptographically secure federation",
        "missing_data_note": "missing-value procedure blocked until exact professor specification",
    }
    (args.out / "manifest.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for seed in args.seeds:
        for scenario in args.scenarios:
            for variant in args.variants:
                print(f"RUN {args.csv.name} seed={seed} scenario={scenario} variant={variant}", flush=True)
                attempt = run_one(df, args.target, features, args.csv.stem, seed, scenario,
                                  variant, args.metric, args.include_legacy)
                rows.extend(attempt)
                # Incremental *atomic* checkpoint after each complete configuration.
                tmp = args.out / "results.csv.part"
                pd.DataFrame(rows).to_csv(tmp, index=False)
                tmp.replace(args.out / "results.csv")
    print(f"SUCCESS {len(rows)} arms; rows={len(df)}; {args.out/'results.csv'}", flush=True)


if __name__ == "__main__":
    main()
