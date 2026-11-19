"""Verify full-scale model outputs against all uncapped G5 IID references."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError

import pandas as pd

from experiments.full_scale_20261118 import sources
from experiments.full_scale_20261118.model import ConflictBoundViolation, run_model
from experiments.full_scale_20261118.registry import G5, ROOT
from experiments.full_scale_20261118.runner import invoke_with_deadline
from fedrs.predict import POLICIES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--prefer-cached-metadata", action="store_true")
    ap.add_argument("--failures", required=True)
    ap.add_argument("--did", type=int)
    args = ap.parse_args()
    cache = Path(args.cache)
    if args.prefer_cached_metadata:
        original = sources.openml._download
        def cached(did):
            folder = cache / str(did)
            desc, feats, data = folder / "description.json", folder / "features.json", folder / f"dataset_{did}.pq"
            if desc.is_file() and feats.is_file() and data.is_file():
                return json.loads(desc.read_text()), json.loads(feats.read_text()), data
            return original(did)
        sources.openml._download = cached
    registry = pd.read_csv(G5)
    registry = registry[(registry.status == "ELIGIBLE_PREPARED") & (registry.row_capped.astype(str) == "False")
                        & (registry.prepared_rows <= 1800)]
    if args.did is not None:
        registry = registry[registry.did == args.did]
        if len(registry) != 1:
            raise ValueError(f"Not an eligible uncapped G5 source: {args.did}")
    reference = pd.read_csv(ROOT / "docs/research/redesign_20261116/data/REDESIGN_G5_CONFIRMATORY_POLICIES.csv")
    failure_path = Path(args.failures)
    errors = 0
    def record(did, phase, exc, seed=None, status="FAILED"):
        new = not failure_path.exists()
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        with failure_path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["dataset", "seed", "system", "distribution", "phase", "status", "error"])
            if new:
                writer.writeheader()
            writer.writerow(dict(dataset=f"OML51:openml_{did}", seed=seed, system="FEDERATED" if seed else "",
                                 distribution="IID" if seed else "", phase=phase, status=status,
                                 error=f"{type(exc).__name__}: {exc}"))
    for r in registry.itertuples():
        did = int(r.did)
        current_seed = None
        try:
            for attempt in range(1, 4):
                try:
                    src = sources.load_openml(did, cache)
                    break
                except (HTTPError, URLError, ConnectionError, TimeoutError) as exc:
                    retryable = not isinstance(exc, HTTPError) or exc.code == 429 or exc.code >= 500
                    if not retryable or attempt == 3:
                        raise
                    record(did, "G5_SOURCE_RETRY", exc)
                    time.sleep(2 ** (attempt - 1))
            for seed in range(1001, 1006):
                current_seed = seed
                run = invoke_with_deadline(run_model, (src, f"OML51:openml_{did}", seed, "FED_IID"), 2700)
                if run["status"] != "OK":
                    exc = RuntimeError(run["error"])
                    record(did, "G5_MODEL", exc, seed=seed, status=run["status"])
                    if run["status"] == "ConflictBoundViolation":
                        return 1
                    errors += 1
                    break
                current = run["value"]["rows"]
                expected = reference[(reference.did == did) & (reference.seed == seed) & (reference.regime == "IID")
                                     & (reference.discretizer == "EQUAL_WIDTH_3") & (reference.rule_variant == "A_ALL_RULES")]
                for policy in POLICIES:
                    old = expected[expected.method == policy]
                    actual = [x for x in current if x["rule_variant"] == "A_ALL_RULES" and x["selection_policy"] == policy]
                    if len(old) != 1 or len(actual) != 1:
                        raise RuntimeError(f"G5_REFERENCE_ROW_COUNT did={did} seed={seed} policy={policy}")
                    prior = float(old.iloc[0].test_accuracy)
                    now = actual[0]["accuracy_pct"] / 100.0
                    if abs(now - prior) > 1e-12:
                        raise ArithmeticError(f"G5_MISMATCH did={did} seed={seed} policy={policy} old={prior!r} new={now!r}")
                print("PASS", did, seed, flush=True)
        except Exception as exc:
            errors += 1
            record(did, "G5_VALIDATION", exc, seed=current_seed,
                   status="G5_MISMATCH" if isinstance(exc, ArithmeticError) else "FAILED")
            print("FAILED", did, exc, flush=True)
            if isinstance(exc, (ArithmeticError, ConflictBoundViolation)):
                return 1  # A numerical mismatch must stop the experiment.
    print(f"G5 validation: {len(registry)} sources, {errors} failures", flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
