# Resume tooling for `experiments/expanded_42seeds_20261120` (2026-11-22)

These scripts resumed the 188 × 42-seed run from the 3566580 checkpoint on a local
Windows 11 + WSL2 (Ubuntu, Python 3.12.3, numpy 2.3.5, pandas 2.2.3) machine.
**None of them modify the scientific code.** Every model is still computed by the
unmodified `python -m experiments.expanded_42seeds_20261120.run` at 56e293c
(tree 3dc3d175, identical to 3566580), whose own run-contract check runs for every job.

## Verification before resuming
| Script | Purpose | Result |
|---|---|---|
| `01_extract_and_freeze.sh` | extract checkpoint zip; freeze byte copies of original manifest + SOURCE.json (read-only, sha256 list) | 19 files frozen |
| `02_verify_sources.py` | re-download the 12 started sources via run.py's loader; write `source.pkl` only if SHA and full metadata equal the original `SOURCE.json` (never rewrites SOURCE.json) | 12/12 identical |
| `03_fidelity_gate.py` | recompute all 1,559 completed checkpoints in isolated dirs; compare rows, source SHA, partition, feature typing | 1,559/1,559 identical (also under single-thread BLAS) |
| `04_migrate_manifest_revision.py`, `04_run_migration.sh` | gated `git_revision` migration 3566580 → 56e293c: clean tree, tree SHA, frozen-copy byte equality, all other contract fields equal, gates above passed; writes `REVISION_COMPATIBILITY.json`, `MANIFEST_HISTORY.jsonl` | migrated; negative test confirms run.py still rejects the old manifest |

## Execution
| Script | Purpose |
|---|---|
| `orchestrate.py` | memory-aware scheduler: one job = (dataset, seed chunk) running the unmodified run.py in its own dir seeded with the main manifest and verified source; validates (`run.validate_record`) and merges results into the main dir, **never overwriting**; single writer; heaviest-first; live limits via `ORCHESTRATOR_CONTROL.json` |
| `08_prefetch_sources.py`, `12_retry_source.sh` | download every source ahead via `run.run_dataset(item, staging, seeds=[])` (run.py's own code path, no model); `--warm-openml` fetches the OpenML parquet into run.py's cache path without the 300 s source deadline (needed for openml_40996 on a slow link) |
| `10_detached_pipeline.sh` | WMI-launched, session-independent full run (waits for single-writer prerequisites, checks tree identity) |
| `15_host_memory_watchdog.ps1` | throttles new-job admission when Windows memory is tight; never kills processes |
| `publish.py`, `11_publisher_detached.cmd` | commit + push each dataset once all 168 models are decided; `[skip ci]`; fetch+rebase on conflict, never force |
| `16_interim_package.sh`, `interim_findings.py` | interim package + analysis (read-only copy of live checkpoints) |
| `test_orchestrate.py` | unit tests for merge / scheduling / snapshot rules (13 tests) |

Helper/diagnostic: `build_profile.py`, `timing_probe.py`, `resource_probe.sh`, `inspect_driver.sh`,
`check_sources.sh`, `compare_conflicts.py`, `poll_events.sh`, `13_stop_full_run.sh`,
`14_install_control.sh`, `kill_waiting_launcher.sh`, `06_launch.sh` (now a no-op guard),
`07_full_run_after_speedtest.sh`, `09_prefetch_then_full_run.sh` (superseded launchers).

## Deviations from run.py's own scheduler (scheduling only)
- run.py parallelises only across datasets and runs > 500k-row sources serially at the end
  (~16 days critical path here). The orchestrator instead parallelises by seed chunk under a
  memory budget. Model computation, per-model 2,700 s deadline, seeds, scenarios, policies,
  variants, split and sources are unchanged.
- WSL memory capped at 10 GB (`.wslconfig`) because host commit charge reached 54.7/55 GB.

## Known issues found and fixed during the run
1. Snapshot crashed the scheduler (copied read-only `ORIGINAL_3566580/` could not be removed) → `force_rmtree`; bookkeeping errors no longer stop scheduling. (fixed, active since 18:19)
2. After a scheduler restart, a half-finished seed was recomputed because job dirs did not
   carry already-decided models; recomputed results were identical except timing, main copy
   kept, 1 benign "conflict" logged → job dirs now carry decided models; equal results with
   different timing count as identical. **This fix is in the file but only takes effect at the
   next scheduler restart** (the running process predates it).
3. Earlier monitor processes held a lock on `host_watchdog.log` (17:47–18:20); one throttle
   event was applied but not logged there (it is visible in the run log `control` events).
