# Interim package — 188 datasets × 42 seeds (INCOMPLETE)

**This is a progress snapshot, not a final result.** Final conclusions require
`STATUS.json` = `COMPLETE` (31,584 models). Snapshot time: see `SNAPSHOT_STAMP`
(YYYYMMDDTHHMMSS, UTC+8).

## Start here
- `INTERIM_FINDINGS.md` — interim conclusions (Chinese), with completeness, sample-bias
  table, fed-minus-central comparisons, structure (coverage/conflict/rules), policy ranks,
  B2 vs A, failures and limitations.

## Files
| File | Content |
|---|---|
| `STATUS.json`, `COMPLETENESS.csv` | authoritative completion gates (per dataset 168 models) |
| `MISSING.csv` | every model without a successful result, with status (`NOT_RUN`, `TIMEOUT`, …) |
| `FAILURES.csv` | recorded model failures (all TIMEOUT at the 2,700 s per-model deadline so far) |
| `RESULTS.csv.gz` | every completed metric row (12 rows per model) |
| `PAIRED_COMPARISONS.csv.gz` | federated vs centralized pairs: same dataset, seed, variant, policy, source SHA |
| `PAIRED_SUMMARY.csv` | per dataset × scenario × variant × policy seed statistics (counts may be < 42) |
| `TIMINGS.csv.gz` | per-model timing / RSS / partition status / feature typing |
| `checkpoints_all_completed_models.zip` | per-model JSON checkpoints for every completed model (incl. partial datasets) |
| `interim_*.csv` | tables behind `INTERIM_FINDINGS.md` (dataset-level aggregation) |
| `SOURCE_REGISTRY.csv` | frozen registry (sha256 fffa2519…) |

Raw third-party data is never included.

## How these were produced
1. Copy of the live checkpoints (read only; raw data excluded).
2. `python -m experiments.expanded_42seeds_20261120.run --audit --output <copy>` (unmodified code, 56e293c).
3. `tools/expanded_resume_20261122/interim_findings.py <copy> <out>`.

Script: `tools/expanded_resume_20261122/16_interim_package.sh`.

## Reading the numbers
- Unit of analysis is the dataset: seed-level paired differences are averaged within a
  dataset first. Do not treat 42 seeds × datasets as independent samples.
- The completed set is not random (see the size table in `INTERIM_FINDINGS.md`).
- Several large OpenML sources time out at 2,700 s per model (as they did on the original
  CI run); their final pairs may be largely missing.
