# LEM2

Canonical repository for the current RoughSet / Federated LEM2 research software baseline.

## Current state

This repository has been initialized and now preserves:

- the canonical-source import contract
- the final mathematical audit / rerun / empirical-analysis prompt
- a recoverable evidence snapshot from reference run `20261014_162216`

The **latest production source tree is not yet imported**. The canonical source must come from the user's latest local workspace:

`RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES`

Do not reconstruct that source from outputs or from older RoughSet / DRSA prototypes.

## Start here

- `docs/CANONICAL_SOURCE_IMPORT.md`
- `docs/FINAL_MATH_AUDIT_PROMPT.md`
- `evidence/README.md`
- GitHub Issue #1: final mathematical audit + canonical source import

## Research baseline scope

Current non-collaborative pipeline target:

`Data → split → preprocessing → central/local reduct → LEM2 → local rules → UNION → structural diagnostics → pre-resolution conflict → four existing resolvers → performance`

Existing resolvers:

- FIRST_MATCH
- SIMPLE_VOTING
- STANDARD_VOTING
- GLOBAL_STRENGTH

Collaborative resolution is intentionally out of scope for this baseline.

## Next required step

Import the latest local production source, run baseline verification, then execute `docs/FINAL_MATH_AUDIT_PROMPT.md`.
