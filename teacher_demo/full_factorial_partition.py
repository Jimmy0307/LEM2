from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from roughset.app import discover_datasets
from teacher_demo.full_factorial_matrix import (
    DEFAULT_CLIENT_COUNTS,
    POLICIES,
    _run_block,
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split-mode", choices=["FULL_DATA", "HOLDOUT_80_20"], required=True)
    parser.add_argument("--output", default="outputs/teacher_full_factorial_parts")
    args = parser.parse_args()

    base_config = json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    bundles = discover_datasets(base_config)
    selected = [bundle for bundle in bundles if bundle.name == args.dataset]
    if len(selected) != 1:
        raise AssertionError(f"Expected exactly one dataset named {args.dataset!r}; found {[b.name for b in bundles]}")
    bundle = selected[0]

    rows = []
    rows.extend(
        _run_block(
            bundle,
            base_config,
            split_mode=args.split_mode,
            system="CENTRALIZED",
            client_count=0,
        )
    )
    for client_count in DEFAULT_CLIENT_COUNTS:
        rows.extend(
            _run_block(
                bundle,
                base_config,
                split_mode=args.split_mode,
                system="FEDERATED",
                client_count=client_count,
            )
        )

    frame = pd.DataFrame(rows)
    if len(frame) != 35:
        raise AssertionError(f"Expected 35 rows for one dataset/split partition, got {len(frame)}")
    none = frame[frame["selection_policy"] == "NONE"]
    selected_rows = frame[frame["selection_policy"] != "NONE"]
    if len(none) != 5 or len(selected_rows) != 30:
        raise AssertionError(f"Expected 5 NONE + 30 policy rows, got {len(none)} + {len(selected_rows)}")
    if not none[["accuracy", "balanced_accuracy", "macro_f1"]].isna().all().all():
        raise AssertionError("NONE rows must not claim prediction metrics")
    if not selected_rows[["accuracy", "balanced_accuracy", "macro_f1"]].notna().all().all():
        raise AssertionError("Policy rows must contain prediction metrics")

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    name = f"PART_{_slug(bundle.name)}_{args.split_mode.lower()}.csv"
    frame.to_csv(out / name, index=False, encoding="utf-8-sig")
    print("PARTITION_VERDICT=PASS")
    print(f"DATASET={bundle.name}")
    print(f"SPLIT_MODE={args.split_mode}")
    print(f"ROWS={len(frame)}")
    print(f"OUTPUT={out / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
