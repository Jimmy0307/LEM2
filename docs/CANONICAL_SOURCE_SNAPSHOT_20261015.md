# Canonical Source Snapshot

Source:
RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES

Import date:
2026-10-15

Target:
Jimmy0307/LEM2

Branch:
import/canonical-source-20261015 (from `main` @ `1dc05e5`)

Local source path at import time:
`C:\Users\user\Desktop\研究\RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES`

Nature of this change: **source import only**. No algorithmic, mathematical, or
Rough Set / LEM2 semantic change was intentionally introduced. The final mathematical
audit (`docs/FINAL_MATH_AUDIT_PROMPT.md`) has **not** been executed.

File hashes: `docs/CANONICAL_SOURCE_SHA256_20261015.txt` (verified byte-identical to
the local source tree with `sha256sum -c` at import time).

## Python source files imported (17)

- `main.py`
- `roughset/__init__.py`
- `roughset/adapters.py`
- `roughset/app.py`
- `roughset/artifacts.py`
- `roughset/batch.py`
- `roughset/core.py`
- `roughset/environment.py`
- `roughset/evaluation.py`
- `roughset/federated.py`
- `roughset/paper.py`
- `roughset/pipeline.py`
- `roughset/preprocessing.py`
- `roughset/reduct.py`
- `roughset/schema.py`
- `roughset/sources.py`
- `roughset/splitting.py`

## Tests imported (13 files: 12 test modules + conftest)

- `tests/conftest.py`
- `tests/test_app_end_to_end.py`
- `tests/test_architecture.py`
- `tests/test_batch_runner.py`
- `tests/test_data_layers.py`
- `tests/test_environment.py`
- `tests/test_evaluation.py`
- `tests/test_federated.py`
- `tests/test_math_core.py`
- `tests/test_paper.py`
- `tests/test_reduct.py`
- `tests/test_reduct_pipeline.py`
- `tests/test_reference_ast_parity.py`

## Config imported

- `config.json`
- `examples/demo_decision_table.csv`, `examples/demo_decision_table.schema.json`
- `real_data/README.txt`, `real_data/uci_sources.txt`,
  `real_data/local/PUT_DATA_HERE.txt`, `real_data/schemas/_TEMPLATE.schema.json`

## Launchers imported

- `run.bat`
- `run_single.bat`
- `setup_environment.bat`
- `check_environment.bat`
- `install_python_313.bat`

## Requirements imported

- `requirements.txt`
- `requirements-core.txt`
- `requirements-dev.txt`
- `requirements-excel.txt`
- `requirements-lock.txt`
- `requirements-uci.txt`

## Docs imported

- `README.md` (canonical source README, now at repository root)
- `ALL_POLICIES_RUN.md`, `ENVIRONMENT_SETUP.md`, `PYTHON_314_FIX.md`,
  `UCI3_RUN_NOTE.md`, `VALIDATION_REPORT.md`
- `docs/BATCH_OUTPUT_SCHEMA.md`
- `docs/REDUCT_METRICS.md`
- `docs/REDUCT_PIPELINE_AUDIT.md`
- `docs/REDUCT_PIPELINE_DESIGN.md`
- `docs/REDUCT_PIPELINE_IMPLEMENTATION_LOG.md`
- `docs/reviews/V6_1_CODE_vs_MATH_CORE_COMPARISON.md`
- `docs/superpowers/plans/2026-10-10-roughset-software-extraction.md`
- `docs/superpowers/specs/2026-10-09-roughset-software-architecture-design.md`

## Other supporting files imported

- `reference/lem2_control_panel_v6_1_reference.py`, `reference/SHA256.txt`
  (V6.1 reference used by `tests/test_reference_ast_parity.py`)
- `runtime/README.txt`, `wheels/README.txt` (placeholders; no binaries)
- `.gitignore` (from source, extended — see below)

## Excluded runtime / cache / output files

| Excluded | Reason |
|---|---|
| `.venv/` (~7,960 files, ~163 MB) | machine-specific virtual environment |
| `__pycache__/`, `*.pyc` (incl. `roughset/`, `tests/`, `reference/`, root) | bytecode cache |
| `.pytest_cache/` | test cache |
| `outputs/` (~1,486 files, ~40 MB: `batch_runs/20261014_015109`, `20261014_111141`, `20261014_162216`, `UCI3_HOLDOUT42_REDUCT`, `UCI3_HOLDOUT42_REPRO`, zip archives, `latest_batch.txt`) | historical run outputs; evidence for `20261014_162216` already preserved under `evidence/20261014_162216/` |

`outputs/` is **not** required for source execution: `roughset/app.py` and
`roughset/batch.py` create the configured output folder at runtime
(`mkdir(parents=True, exist_ok=True)`), so no `.gitkeep` was added.

No credentials, API keys, or `.env` files were found in the source tree.

`.gitignore` was extended with: `venv/`, `.mypy_cache/`, `.ruff_cache/`, `.env`,
`.env.*`, `.idea/`, `.vscode/`, `*.log` (source already ignored `.venv/`,
`__pycache__/`, `*.pyc`, `.pytest_cache/`, `outputs/`, `real_data/.cache/`,
`.superpowers/`, `runtime/*`).

## Filename collisions encountered

| Path | Resolution |
|---|---|
| `README.md` | Existed in both. The canonical source README (required by `docs/CANONICAL_SOURCE_IMPORT.md`) now occupies the root. The previous LEM2 bootstrap README was **moved, not deleted**, to `docs/LEM2_BOOTSTRAP_README.md` with content unchanged. |

No other collisions (the source `docs/` folder had no file with the same name as the
existing `docs/CANONICAL_SOURCE_IMPORT.md` or `docs/FINAL_MATH_AUDIT_PROMPT.md`).

## Existing GitHub bootstrap files preserved

- `docs/CANONICAL_SOURCE_IMPORT.md`: preserved, unchanged
- `docs/FINAL_MATH_AUDIT_PROMPT.md`: preserved, unchanged
- `evidence/README.md`: preserved, unchanged
- `evidence/20261014_162216/*` (4 files): preserved, unchanged
- `README.md` (bootstrap): preserved as `docs/LEM2_BOOTSTRAP_README.md`

## Import verification (before commit, no source modification)

Interpreter: the source workspace `.venv` (CPython 3.12.10).

- `python -m compileall -q roughset main.py` → exit 0 (**PASS**)
- `python -m pytest -q` → **74 passed** in 4.34 s, exit 0 (**PASS**).
  A non-fatal `PermissionError` was printed by pytest's at-exit temp-directory
  cleanup (`%TEMP%\pytest-of-user\pytest-current`); it is unrelated to any test.

## Reduct-integrated version check (confirmation only)

Confirmed present in source (no code added):

- `roughset/reduct.py`: `select_minimum_reduct`, `pairwise_reduct_jaccard`
  (`config.json` → `reduct.method = MINIMUM_CARDINALITY`, `selection = LEXICOGRAPHIC_FIRST`)
- `roughset/pipeline.py::build_rule_system`: central reduct on training data →
  central LEM2 on selected reduct → per-client local reduct → local LEM2 →
  `union_rules_with_provenance` → `RuleSystemArtifact` (`roughset/artifacts.py`)
- Four policies configured in `config.json` → `batch.prediction_policies`:
  `FIRST_MATCH`, `SIMPLE_VOTING`, `STANDARD_VOTING`, `GLOBAL_STRENGTH`
  (`roughset/batch.py`, `roughset/evaluation.py`)
- `roughset/paper.py`: separate Wang historical replication lane, unchanged
