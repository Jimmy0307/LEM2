# 01 — Baseline state (before any production change)

## Repository identity

| Field | Value |
|---|---|
| Remote | `origin https://github.com/Jimmy0307/LEM2.git` (owner `Jimmy0307`, repo `LEM2`) |
| Base branch | `main`, fast-forwarded from `origin/main` |
| Base commit | `5e649ef9d6065e98d472b024e2b50e025c271990` — "Import canonical RoughSet / Federated LEM2 source baseline" (matches the expected merge commit) |
| Audit branch | `audit/final-math-freeze-20261015`, created from `5e649ef` |
| Working tree at baseline | clean (`git status --porcelain` empty) |
| Canonical tree present | `roughset/`, `tests/`, `config.json`, `main.py`, `docs/FINAL_MATH_AUDIT_PROMPT.md`, `docs/CANONICAL_SOURCE_IMPORT.md`, `evidence/20261014_162216/` |
| Baseline timestamp | 2026-10-15T08:59:16Z (compileall/pytest start); state snapshot 2026-10-15T09:00:29Z |

Import integrity: SHA-256 of the committed (LF) content of all 45 Python, test, config and
requirements files listed in `docs/CANONICAL_SOURCE_SHA256_20261015.txt` equals that manifest.
The 5 `.bat` files differ only by line-ending handling and do not affect the mathematics.

## Runtime

| Field | Value |
|---|---|
| Python | 3.11.9 (CPython, `tags/v3.11.9:de54cf5`, MSC v.1938 64-bit), project `.venv` |
| Platform | Windows-10-10.0.26200-SP0 (Windows 11 Pro 10.0.26200) |
| numpy | 2.3.5 (lock 2.3.5) |
| pandas | 2.2.3 (lock 2.2.3) |
| openpyxl | 3.1.5 (lock) |
| xlrd | 2.0.2 (lock) |
| ucimlrepo | 0.0.7 (lock) |
| pytest | 9.0.2 (`requirements-dev.txt`) |
| truststore | 0.10.5 — installed only so the one-off UCI fetch could use the Windows certificate store behind a TLS-inspecting proxy; not imported by `roughset/` |

The 2026-10-14 reference used Python 3.12.10 with the same locked numpy/pandas/ucimlrepo
(`evidence/20261014_162216/batch_manifest.json`). The machine's global interpreter has pandas
3.0.5 / numpy 2.4.6, so a fresh `.venv` was built from `requirements-dev.txt` to match the lock.

## Config (`config.json`, unchanged by this audit)

`evaluation.mode = HOLDOUT`, `test_ratio = 0.2`, `seed = 42`; `federated.partition = STRATIFIED`,
`client_counts = [2, 3, 4, 5]`, `n_clients = 5`, `order_sensitivity_max_permutations = 120`;
`reduct.enabled = true`, `method = MINIMUM_CARDINALITY`, `selection = LEXICOGRAPHIC_FIRST`;
`batch.prediction_policies = [FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING, GLOBAL_STRENGTH]`;
`paper.enabled = false`. Identical to `base_config` in the reference manifest.
For the UCI3 reruns the driver sets `input.run_local_files = false` (the local folder holds only
a placeholder) and the output folder; everything else is read from `config.json`.

## SHA-256 at baseline (committed LF content at `5e649ef`)

| File | SHA-256 |
|---|---|
| `roughset/core.py` | `61ba3d305f40ea44243fd21501cc3d81070d5651f9567680589486dc8cc9e1f7` |
| `roughset/reduct.py` | `a5a54cd7b2efdbb6a3765d145787793dc3f76302bbd739692ea34d316f411e45` |
| `roughset/pipeline.py` | `3b9130f943a2abbdc41a7f026786612f42db295ef6f691fb2b01cfbd9b3ad52b` |
| `roughset/artifacts.py` | `d6cf0eb8f5e899f59422862dabefafec8ab4b16337e69f8dc8d60325dd9fb082` |
| `roughset/evaluation.py` | `ad9785259c6c5a1bde8b3706e0185ebd32437e3e4a70e31eb376e0d4ee022bac` |
| `roughset/federated.py` | `3373de9068507167147b84d841e30dbdc58f3447fcdeb23af631cd2447480d5b` |
| `roughset/app.py` | `c4f9676cec98d902840657a4be422aca8f78a31445f884d6e230a8231eebbbd6` |
| `roughset/batch.py` | `7e61ba5d677cc68d63c9a1ca5335d41ad0902c435812d6e1e4a874dafdaf2672` |
| `roughset/paper.py` | `15aa94d1bc3e253e0af9683fa1d32335f7dc163d40cf1836ff83c631217d01e6` |
| `config.json` | `24c5a1bafd98a86916f26a317f3914ff7200d6006d9e65377ae6599488d672d8` |
| `main.py` | `47acfe580d41af7f08740da2942c6af91228ebbc7dc6e729bee44b67d9246b34` |
| `tests/test_math_core.py` | `f52e7066bb67d962a96748b0b66e0bd69e28d34b8d55d6d58c2fbe30f0307562` |
| `tests/test_reduct.py` | `b44cf9c46948d5d58cfcfaefc62e6dc3ab75c7718dfd9cfe01b2961986488801` |
| `tests/test_reduct_pipeline.py` | `0cbaca7841c2532056faa947f22b052a9e07f4f28712c0dfa437bd585a29f4d4` |
| `tests/test_evaluation.py` | `d2a18f61c21d024dd47ddfd2a6c29fa0543d684974037d5332aa76bb7ed65bb6` |
| `tests/test_federated.py` | `7f94fce55e046e05bbf4b6a4720ef031b04ea6ee85024242e895b845be17e1ea` |
| `tests/test_paper.py` | `3a5551fd03f07886699e6816d2af6fe96fa17c9c052e5fc8e40cb57b33ed43ef` |
| `tests/test_reference_ast_parity.py` | `dcbb7c9be130f8b7b7f5083cf54fb4ba031da11ead3e8c5853d1604b63888490` |

Working-tree (CRLF, `core.autocrlf = true`) hashes of every source and test file are in
`outputs/final_math_audit_20261015/baseline/baseline_state.json`.

## Baseline verification (unmodified source)

| Command | Result |
|---|---|
| `python -m compileall -q roughset main.py` | exit 0, no output |
| `python -m pytest -q` | **74 passed, 0 failed**, exit 0, 30.11 s (first run, cold) |

No Windows temp-cleanup `PermissionError` was printed. Logs:
`outputs/final_math_audit_20261015/baseline/{compileall.txt,pytest_full.txt,test_groups.json}`.

## PRE_AUDIT_REFERENCE_RUN

`outputs/batch_runs/20261014_162216` is not present in this clone (outputs are git-ignored).
The repository keeps its evidence snapshot at `evidence/20261014_162216/`, which is treated as
`PRE_AUDIT_REFERENCE_RUN` and was not modified:

| File | SHA-256 |
|---|---|
| `structural_summary.csv` | `634e5b8b9bfb91694efac6bf6e54a04a7aa137289ccf64e3b5d6c744841ec1d7` |
| `research_chain_summary.csv` | `208dddc07032115d155219245700b30831230c7a4d852670eb2bac163968c9c9` |
| `batch_manifest.json` | `0d7faaf27f326944d2c923fd67c35b78d9ee990ad7fe24d5e64e77861af67a3c` |
| `REFERENCE_ARCHIVE_SHA256.txt` | `75c744f4a5c2cb74153437b15c78562f0ff853617902ad54c27af04080c47603` |

The evidence holds structural metrics and per-policy balanced accuracy / conflict balanced
accuracy only. To get every metric for the old-vs-new comparison, the unmodified source was rerun
on the same config (`outputs/final_math_audit_20261015/PRE_FIX_BASELINE/`). That rerun reproduces
**both** evidence tables exactly: all 12 rows, every non-timing column, absolute tolerance 1e-12
(`analysis_checks.json → reference_vs_prefix_rerun_nontiming_differences = 0`).

## UCI data snapshot

Fetched once on 2026-10-15 with ucimlrepo 0.0.7 and frozen to
`outputs/final_math_audit_20261015/uci_snapshot/` (CSV + pickle + `meta.json` with SHA-256).
Hayes-Roth 160 rows × 4 features (132 after dropping missing targets), Car Evaluation 1 728 × 6,
Balance Scale 625 × 4. Both reruns read this snapshot, so pre-fix and post-fix runs see identical
input bytes.
