"""Run a shard under a bounded wall clock and checkpoint every model."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import pandas as pd
from experiments.full_scale_20261118.registry import assign_shards, source_registry
from experiments.full_scale_20261118.runner import collect_events
from experiments.full_scale_20261118.model import SCENARIOS

FULL19 = ["dataset", "seed", "distribution", "dirichlet_alpha", "split_mode", "system", "client_count",
          "selection_policy", "train_rows", "test_rows", "rule_count", "no_match_count", "covered_count",
          "test_coverage_pct", "true_in_candidate_count", "candidate_coverage_pct", "accuracy_pct",
          "balanced_accuracy_pct", "conflict_rate_pct"]
SMOKE = ("UCI20:iris", "UCI20:wine", "UCI20:haberman", "UCI20:sonar", "O3:Hayes-Roth")


def _write(path, rows, columns):
    frame = pd.DataFrame(rows)
    for col in columns:
        if col not in frame:
            frame[col] = pd.Series(dtype=object)
    remaining = [c for c in frame.columns if c not in columns]
    frame[columns + remaining].to_csv(path, index=False)


def read_events(path, dataset):
    events = []
    if not path.exists():
        return events
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            events.append({"kind": "checkpoint_failure", "dataset": dataset,
                           "status": "CORRUPT_CHECKPOINT", "error": f"line {i+1}: {exc}"})
            break
    return events


def run_shard(shard_id, shard_count, seeds, smoke, output, budget_seconds=325*60, dataset=None, scenarios=None):
    registry = source_registry()
    scenarios = tuple(scenarios) if scenarios is not None else SCENARIOS
    if not scenarios or not set(scenarios).issubset(SCENARIOS):
        raise ValueError("Invalid scenarios")
    if smoke:
        if shard_id != 0:
            raise ValueError("Smoke has only shard 0")
        chosen = registry[registry.dataset.isin(SMOKE)].copy()
        if len(chosen) != 5:
            raise ValueError("Smoke sources missing from registry")
        seeds = seeds[:1]
    else:
        assigned = assign_shards(registry, shard_count)
        chosen = assigned[(assigned.status == "PENDING") & (assigned.shard == shard_id)]
        isolated = len(chosen) == 1
        if dataset:
            chosen = chosen[chosen.dataset == dataset]
            if len(chosen) != 1:
                raise ValueError("Dataset is not in the specified shard")
    if smoke:
        isolated = False
    datasets = chosen.dataset.tolist()
    deadline = time.time() + budget_seconds
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    events = []
    with tempfile.TemporaryDirectory(prefix="full-scale-") as tmp:
        scratch = Path(tmp)
        for i, item in enumerate(chosen.itertuples()):
            if time.time() >= deadline:
                break
            event_file = scratch / f"events_{i}.jsonl"
            command = [sys.executable, "-m", "experiments.full_scale_20261118.dataset_worker", "--dataset", item.dataset,
                       "--events", str(event_file), "--cache", str(scratch / "openml"),
                       "--seeds", ",".join(map(str, seeds)), "--scenarios", ",".join(scenarios), "--deadline", str(deadline)]
            if isolated:
                command.append("--isolated")
            with (scratch / f"worker_{i}.log").open("w", encoding="utf-8") as log:
                proc = subprocess.Popen(command, start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
                try:
                    code = proc.wait(timeout=max(0.01, deadline-time.time()))
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    code = -signal.SIGKILL
            new_events = read_events(event_file, item.dataset)
            if not new_events and code:
                message = (scratch / f"worker_{i}.log").read_text(encoding="utf-8")[-4000:]
                new_events.append({"kind": "source_failure", "dataset": item.dataset,
                                   "status": "PROCESS_KILLED_OR_OOM", "error": f"exit={code}; {message}"})
            elif code and code not in (2, 3) and not any(e["kind"] == "source_failure" for e in new_events):
                message = (scratch / f"worker_{i}.log").read_text(encoding="utf-8")[-4000:]
                new_events.append({"kind": "checkpoint_failure", "dataset": item.dataset,
                                   "status": "PROCESS_KILLED_OR_OOM" if code < 0 else "WORKER_ERROR",
                                   "error": f"exit={code}; {message}"})
            events.extend(new_events)
            print("DATASET", item.dataset, "exit", code, "events", len(new_events), flush=True)
            shutil.rmtree(scratch / "openml", ignore_errors=True)
            if code == 3:
                break  # A conflict-bound violation requires the shard to stop.
    rows, timings, metadata, ladder, failures = collect_events(datasets, seeds, events, scenarios)
    if not smoke:
        completed_ladders = {(e["dataset"], e["scenario"], e["scale"]) for e in events
                             if e["kind"] in ("ladder", "ladder_failure")}
        for meta in metadata:
            if meta["original_rows"] >= 20_000:
                for scenario in (s for s in ("FED_IID", "FED_A01") if s in scenarios):
                    for scale in ("1800", "10000", "FULL"):
                        key = (meta["dataset"], scenario, scale)
                        if key not in completed_ladders:
                            failures.append(dict(dataset=key[0], seed=1001, scenario=scenario,
                                                 phase="SCALE_LADDER", scale=scale,
                                                 status="NOT_RUN_SHARD_TERMINATED", error="No ladder event before shard stopped"))
    _write(output / f"shard_{shard_id}.csv", rows, FULL19 + ["rule_variant"])
    _write(output / f"failures_{shard_id}.csv", failures, ["dataset", "seed", "scenario", "phase", "status", "error"])
    _write(output / f"timings_{shard_id}.csv", timings, ["dataset", "seed", "scenario", "partition_status", "partition_attempts"])
    _write(output / f"registry_{shard_id}.csv", metadata, ["cohort", "dataset", "status"])
    _write(output / f"ladder_{shard_id}.csv", ladder, FULL19 + ["rule_variant", "scenario", "scale", "scale_rows", "dropped_classes"])
    return 3 if any(f.get("status") == "ConflictBoundViolation" for f in failures) else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--shard-count", type=int, default=24)
    p.add_argument("--seeds", default="1001,1002,1003,1004,1005")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--output", required=True)
    p.add_argument("--budget-seconds", type=float, default=325*60)
    p.add_argument("--dataset")
    p.add_argument("--scenarios", default=",".join(SCENARIOS))
    a = p.parse_args()
    seeds = [int(x.strip()) for x in a.seeds.split(",") if x.strip()]
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be a nonempty list of distinct integers")
    return run_shard(a.shard, a.shard_count, seeds, a.smoke, a.output, a.budget_seconds, a.dataset,
                     [s.strip() for s in a.scenarios.split(",") if s.strip()])


if __name__ == "__main__":
    raise SystemExit(main())
