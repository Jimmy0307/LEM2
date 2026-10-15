# Reduct Pipeline Implementation Log

Date: 2026-10-14  
Package: `RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES`

## Phase 1 — Baseline Freeze

Environment: package `.venv`, CPython 3.12.10, NumPy 2.3.5, pandas 2.2.3, pytest 9.0.2. The environment initially lacked pytest; installed the package-declared `requirements-dev.txt` before running the baseline. Runtime pins remained NumPy 2.3.5 and pandas 2.2.3.

### BASELINE_TESTS

Command: `python -m pytest -q` (executed with `.venv/Scripts/python.exe`).  
Result: **60 passed in 2.56s**, exit code 0.  
Environment note: pytest emitted an ignored atexit `PermissionError` while cleaning a Windows temp symlink under `pytest-of-user`; the test process exit code remained 0 and all assertions passed.

### BASELINE_COMPILE

Command: `python -m compileall -q roughset main.py` (executed with `.venv/Scripts/python.exe`).  
Result: **PASS**, exit code 0, no output.

### BASELINE_BEHAVIOR

- Math / LEM2 regression: `pytest -q tests/test_math_core.py tests/test_reference_ast_parity.py tests/test_reduct.py` — **9 passed in 1.05s**.
- Existing single HOLDOUT application smoke: `pytest -q tests/test_app_end_to_end.py::test_local_folder_batch_run_creates_separate_outputs` — **1 passed in 0.90s**. It uses the deterministic local fixture and temporary output folder; it does not contact UCI.

No baseline test or compile failure was observed. No production code or existing tests were changed during this phase.

## Phase 2 — TDD

Added the six requested core contracts in `tests/test_reduct_pipeline.py`; the train-only case is parameterized for HOLDOUT and K_FOLD_CV (seven test cases total).

Command: `python -m pytest -q tests/test_reduct_pipeline.py` (package `.venv`).  
Observed: **7 failed**, as required for RED.  
Failure reasons:

1. Centralized path has no `central_reduct_result`; the current path passes all preprocessed condition columns to LEM2.
2. Federated result has no per-client `local_reduct_results`.
3. HOLDOUT and K_FOLD_CV produce no reduct calls at all; consequently no train-only reduct evidence exists for any split.
4. Policy batch results have no reusable `structural_artifact`.
5. `pairwise_reduct_jaccard` is not implemented.
6. `select_minimum_reduct` and its complete deterministic candidate metadata are not implemented.

The first draft of the client fixture attempted to partition by a schema-ignored `site` column; the loader correctly removes ignored columns. The fixture now partitions by stable `__row_id__` ranges and fails on the intended missing reduct contract. No production files were changed before observing RED.

After the RED run, the first production slices turned the core contracts green: canonical selection/metrics (2 passed), then centralized/local integration and train-only HOLDOUT/K-fold (4 passed), then shared batch artifact reuse (1 passed). Full new core test file: **7 passed**. The batch spy observes exactly three reduct calculations for one split with two clients (one central, two local), independent of the four policy evaluations.

## Implementation and Validation

### Implementation checkpoint

- Added `ReductSelectionResult` and `select_minimum_reduct()` around the existing exhaustive search. Candidate reduct tuples are normalized/sorted, all minimum candidates are retained, and the lexicographically first candidate is selected deterministically.
- Added `RuleSystemArtifact`, `build_rule_system()`, and resolver-only evaluation. Main HOLDOUT and each K-fold now fit preprocessing on training-side rows, then calculate the central reduct from processed train rows and each local reduct from that client's processed training rows. LEM2 receives only the corresponding selected reduct. `reduct.enabled=false` retains the all-condition-features ablation.
- Batch now builds each dataset × fold × client-count artifact once and resolves each configured policy against the shared structure. Output includes structural/resolver summaries, conflict-only and disagreement tables, candidate and frequency diagnostics, rule metrics, chain summary, and fold aggregates. Existing output paths are preserved rather than cleared before writing.
- The historical `roughset/paper.py` lane remains unchanged and separate. No edits were made to `roughset/core.py`, `roughset/evaluation.py`, or `roughset/federated.py`; the existing exhaustive search and dependency functions remain unchanged in `roughset/reduct.py`.

### RED/GREEN correction note

The runtime artifact test first observed a production `TypeError`: `RuleSystemArtifact` declared three timing fields while its builder did not provide them. The builder was corrected to record central/local reduct seconds and total structural-build seconds; the new pipeline tests then passed. This was an integration error, not a mathematical change. The legacy output test that expected a stale generated CSV to be deleted was updated to assert preservation, matching the explicit output-retention requirement.

### Final automated validation

- `python -m pytest -q`: **74 passed in 4.09s**, exit 0.
- `python -m compileall -q roughset main.py`: **PASS**, exit 0.
- Math/core/reference/reduct plus paper protocol regression: **10 passed in 0.93s**.
- Pytest continues to emit a nonfatal ignored Windows temp-symlink cleanup `PermissionError` after successful exit; it does not affect assertions or exit status.

### UCI3 smoke and same-seed reproducibility

Configuration: HOLDOUT, test ratio 0.20, seed 42, STRATIFIED clients 2/3/4/5, reduct enabled, all four resolvers. The run produced 12 structural rows (3 datasets × 4 client counts) and 48 resolver rows. Structural rows have no policy column. At C=5:

| Dataset | Central selected reduct | Local mean size | Mean reduct Jaccard | Instability | Local-central Jaccard | Full-rule Jaccard | Pre-resolution conflict rate |
|---|---|---:|---:|---:|---:|---:|---:|
| Hayes-Roth | age, educational_level, hobby, marital_status | 3.8 | 0.9000 | 0.1000 | 0.9500 | 0.2272 | 0.6538 |
| Car Evaluation | buying, doors, lug_boot, maint, persons, safety | 6.0 | 1.0000 | 0.0000 | 1.0000 | 0.0686 | 0.6069 |
| Balance Scale | left_distance, left_weight, right_distance, right_weight | 4.0 | 1.0000 | 0.0000 | 1.0000 | 0.0739 | 0.6587 |

Hayes-Roth C=5 clients selected the full four-feature reduct for Clients 1, 3, 4, and 5; Client 2 selected `(age, educational_level, marital_status)`. Candidate count was 1 for each client. Car Evaluation and Balance Scale selected the full feature set on every client (candidate count 1 each). The actual local heterogeneity is therefore present in Hayes-Roth, not forced across all datasets.

C=5 resolver accuracy / conflict balanced accuracy:

| Dataset | FIRST_MATCH | SIMPLE_VOTING | STANDARD_VOTING | GLOBAL_STRENGTH |
|---|---:|---:|---:|---:|
| Hayes-Roth | 0.8333 / 0.8190 | 0.5222 / 0.4190 | 0.7444 / 0.7048 | 0.8000 / 0.7714 |
| Car Evaluation | 0.5964 / 0.5311 | 0.5399 / 0.4439 | 0.5340 / 0.4533 | 0.6368 / 0.5803 |
| Balance Scale | 0.4885 / 0.4167 | 0.5402 / 0.4975 | 0.5747 / 0.5593 | 0.5736 / 0.5405 |

FIRST_MATCH C=5 order-sensitivity rates were 0.5769, 0.2370, and 0.5794 respectively. The other three policies were marked `ORDER_INVARIANT_BY_DESIGN`. Policy disagreement against FIRST_MATCH was nonzero for the alternative resolvers. Conflict case identities were identical across all four policies for each dataset/client count.

The same configuration was rerun. **40 selected structural/resolver CSVs** (including reduct candidates, rules, conflicts, policy summaries, and research-chain summaries) matched after excluding timing columns. The structural summary had 12 unique dataset × fold × client-count rows; resolver summary had the expected 48 rows.

Measured seconds from the first run (`central reduct / mean local reduct / total structural build`, where total includes train-side preprocessing, partition, rule induction, and structural diagnostics):

| Dataset | C=2 | C=3 | C=4 | C=5 |
|---|---|---|---|---|
| Hayes-Roth | 0.0356 / 0.0345 / 0.3842 | 0.0348 / 0.0355 / 0.4129 | 0.0349 / 0.0326 / 0.4362 | 0.0370 / 0.0403 / 0.5523 |
| Car Evaluation | 0.2103 / 0.1951 / 35.1523 | 0.2567 / 0.2261 / 34.1772 | 0.2177 / 0.1963 / 26.3894 | 0.1980 / 0.1513 / 20.0664 |
| Balance Scale | 0.0416 / 0.1092 / 11.8095 | 0.0314 / 0.0431 / 11.6969 | 0.0439 / 0.0380 / 10.4525 | 0.0361 / 0.0382 / 10.2593 |

The reduct search itself remained sub-second in all measured configurations. The larger Car Evaluation and Balance Scale structural totals are dominated by induction/diagnostics, not a replacement or shortcut to exhaustive reduct search.

### Output locations

- Primary run: `outputs/batch_runs/UCI3_HOLDOUT42_REDUCT/`
- Same-seed repeat: `outputs/batch_runs/UCI3_HOLDOUT42_REPRO/`
- Batch-level files: `structural_summary.csv`, `structural_summary_aggregate.csv`, `resolver_summary.csv`, `resolver_summary_aggregate.csv`, `research_chain_summary.csv`, `policy_disagreement.csv`, `conflict_class_metrics.csv`, and `batch_manifest.json`.
- Dataset structural tables: `structural/Hayes-Roth/`, `structural/Car_Evaluation/`, and `structural/Balance_Scale/`.
- Resolver tables: `resolver/<POLICY>/<DATASET>/`.

### Remaining limitations

- Minimum-cardinality reduct search remains exhaustive and NP-hard in general. These benchmarks have only 4, 6, and 4 condition features; no heuristic was introduced.
- Central selected reducts for these three UCI datasets retain all pooled condition features. This is the observed result under the frozen dependency/reduct definitions, not a reason to alter them. Hayes-Roth has one local client reduct that drops `hobby`.
- Fold aggregate files summarize numeric metrics with population std/min/max; fold-level rows remain the evidence source. Conflict-only aggregate metrics remain undefined when a fold has no conflict cases.
