# Canonical source import

## Repository purpose

This repository is the canonical version-control home for the current **RoughSet / Federated LEM2 non-collaborative baseline**.

## Source-of-truth rule

The canonical source tree to import is the latest local workspace named:

`RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES`

Do **not** reconstruct the canonical source from experiment outputs, an older housing prototype, or any other RoughSet/DRSA repository.

## Required source tree

Import at minimum:

- `roughset/`
- `tests/`
- `docs/`
- `config.json`
- `main.py`
- `run.bat`
- `setup_environment.bat`
- `check_environment.bat`
- `requirements*.txt`
- `README.md`

Preserve the latest verified reference run under:

`outputs/batch_runs/20261014_162216/`

or keep an equivalent evidence snapshot under `evidence/` with hashes.

## Current verified pre-import state

The recoverable 2026-10-14 experiment outputs show the Reduct-integrated, all-policies pipeline completed for Hayes-Roth, Car Evaluation, and Balance Scale. However, these outputs are **evidence only** and are not sufficient to recreate the production implementation.

The source import must preserve the currently intended boundaries:

- Rough Set / LEM2 core mathematics unchanged unless a mathematical audit proves a bug.
- Main pipeline uses train-scoped reduct selection.
- Federated clients select local reducts independently.
- LEM2 receives only the selected reduct features.
- Four resolvers reuse the same structural rule-system artifact.
- `paper.py` Wang historical replication remains a separate historical lane.
- No collaborative resolver is part of this baseline.

## Import verification

After importing the local source, before any new modifications:

1. Run `pytest -q`.
2. Run `python -m compileall -q roughset main.py`.
3. Verify the latest local reference outputs are still present or copied into the repository as evidence.
4. Verify `FIRST_MATCH`, `SIMPLE_VOTING`, `STANDARD_VOTING`, and `GLOBAL_STRENGTH` all operate from the same structural artifact.
5. Only then run `docs/FINAL_MATH_AUDIT_PROMPT.md`.

## Prohibited substitutions

Do not silently replace the canonical source with:

- the old housing prototype,
- `Jimmy0307/drsa-research`,
- reconstructed code inferred from CSV outputs,
- a new implementation written merely to reproduce the same numbers.

If the latest local source cannot be obtained, mark the import as blocked rather than fabricating a canonical baseline.
