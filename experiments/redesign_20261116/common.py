"""Shared grid runner: deterministic tasks, multiprocessing, failure ledger, manifest.

Every task row carries dataset / source SHA-256 / seed / split id / regime /
partition mode / discretizer / induction so any CSV row can be re-run alone.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter
from typing import Callable, Dict, Iterable, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "research" / "redesign_20261116" / "data"

UCI20 = ("adult_income", "bank_marketing", "banknote", "breast_diagnostic", "covertype", "dry_bean",
         "eeg_eye_state", "german_credit", "grid_stability", "haberman", "htru2", "iris", "letter",
         "magic_gamma", "mushroom", "phishing", "rice", "sonar", "spambase", "wine")
REPRO_SEEDS = (11, 23)                       # historically reused -> EXPLORATORY
EXPLORATORY_SEEDS = (101, 102, 103, 104, 105, 106, 107, 108)
ALL_EXPLORATORY_SEEDS = REPRO_SEEDS + EXPLORATORY_SEEDS


def bootstrap_path() -> None:
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


_BUNDLES: Dict[str, tuple] = {}


def uci20_bundle(name: str):
    bootstrap_path()
    if name not in _BUNDLES:
        from teacher_demo.conflict_aware_coverage_pilot import load_bundle
        _BUNDLES[name] = load_bundle(name)
    return _BUNDLES[name]


def split_id(dataset: str, seed: int) -> str:
    return f"{dataset}|outer80_20_seed{seed}|inner80_20_seed{1000 + seed}"


def _safe(worker: Callable, task: dict):
    started = perf_counter()
    try:
        out = worker(task)
        return {"task": task, "ok": True, "result": out, "seconds": perf_counter() - started}
    except Exception as exc:
        return {"task": task, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc()[-1500:], "seconds": perf_counter() - started}


def run_grid(name: str, tasks: List[dict], worker: Callable, n_jobs: int = 24,
             tables: Iterable[str] = ("config", "clients", "structure", "policies"),
             extra_manifest: dict | None = None) -> Dict[str, pd.DataFrame]:
    bootstrap_path()
    from fedrs.provenance import write_manifest
    OUT.mkdir(parents=True, exist_ok=True)
    collected: Dict[str, List[dict]] = {t: [] for t in tables}
    failures: List[dict] = []
    started = perf_counter()
    done = 0
    with ProcessPoolExecutor(max_workers=n_jobs) as pool:
        futures = [pool.submit(_safe, worker, t) for t in tasks]
        for fut in as_completed(futures):
            res = fut.result()
            done += 1
            if res["ok"]:
                for table in tables:
                    for row in res["result"].get(table, []):
                        collected[table].append({**res["task"], **row})
            else:
                failures.append({**res["task"], "error": res["error"], "trace": res["trace"]})
            if done % 50 == 0 or done == len(tasks):
                print(f"[{name}] {done}/{len(tasks)} done, failures={len(failures)}, "
                      f"{perf_counter() - started:.0f}s", flush=True)
    frames = {}
    for table, rows in collected.items():
        df = pd.DataFrame(rows)
        sort_cols = [c for c in ("dataset", "seed", "regime", "partition_mode", "discretizer", "induction") if c in df]
        if len(df) and sort_cols:
            df = df.sort_values(sort_cols, kind="stable").reset_index(drop=True)
        df.to_csv(OUT / f"{name}_{table.upper()}.csv", index=False)
        frames[table] = df
    pd.DataFrame(failures).to_csv(OUT / f"{name}_FAILURES.csv", index=False)
    write_manifest(OUT / f"{name}_MANIFEST.json", {
        "experiment": name, "tasks": len(tasks), "succeeded": len(tasks) - len(failures),
        "failed": len(failures), "wall_seconds": perf_counter() - started,
        "outputs": [f"{name}_{t.upper()}.csv" for t in tables] + [f"{name}_FAILURES.csv"],
        **(extra_manifest or {}),
    })
    return frames


def flatten(task: dict, res: dict) -> dict:
    """Turn fedrs.experiment.evaluate output into run_grid table rows."""
    return {
        "config": [res["config"]],
        "clients": res["clients"],
        "structure": res["structure"],
        "policies": res["policies"],
    }
