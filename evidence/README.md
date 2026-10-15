# Evidence snapshot

This directory preserves recoverable evidence from the latest verified local run available before the canonical source tree was imported into this repository.

## Reference run

Run ID: `20261014_162216`

Known environment/config provenance is preserved in `20261014_162216/batch_manifest.json`.

Key result tables currently preserved here:

- `20261014_162216/structural_summary.csv`
- `20261014_162216/research_chain_summary.csv`

The original local archives had these SHA-256 digests:

- `20261014_162216.zip`  
  `4399a1547b08ac0428a380c68b219fbe8785e785fe5c2a261275a47683514bf5`
- `batch_runs.zip`  
  `89962487a7a22471dd91b8f8d30c84a4f2f753655c79a3fccbaaad9c69d3cf06`

These archive hashes identify the original recoverable experiment evidence from the active research session. The binary ZIP archives themselves are not yet committed here.

## Important boundary

These files are **experiment evidence**, not canonical production source.

Do not use them to reconstruct or replace the latest local implementation. The canonical source must come from the latest local workspace named:

`RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES`

See `../docs/CANONICAL_SOURCE_IMPORT.md`.
