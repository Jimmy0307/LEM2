# Evidence Manifest — 2026-10-23

## Experiment provenance

- Frozen production baseline: `31b078bb78c6754d04c56a2e1cc849c8feb221d7`
- Six-policy fresh run source commit: `19983125a5daef4f7af1fb9f55554e6fbf747017`
- Target-backtrace workflow source head: `a2e5be8750a1a952281ccdded7ad2a664abf13e9`
- Target-case analysis commit before final packaging: `b8838043abee2d98eac2e017d864bab88b065f44`

## Evidence files

The final packaging workflow populates this directory with:

- `SIX_POLICY_RESULTS_COMPACT.csv`
- `BALANCED_ACCURACY_WINNERS.csv`
- `MACRO_F1_WINNERS.csv`
- `SELECTED_15_TARGET_CASES.csv`
- `SELECTED_TARGET_DECISION_SCORES.csv`
- `SELECTED_TARGET_RULE_BACKTRACE.csv`
- `ALL_CONFLICT_CASES.csv`
- `ALL_CONFLICT_DECISION_SCORES.csv`

## Counts

- six-policy result rows: 72
- selected target cases: 15
- all conflict occurrences across C=2..5: 908
- Population Standard winner changes: 16
- Population Global winner changes: 27
- total winner changes: 43
- observed winner changes moving to lower-redundancy decision: 43 / 43

## Interpretation boundary

These are seed=42, single 80/20 holdout mechanism results. They are suitable for descriptive/mechanism analysis and hypothesis formation. Formal statistical claims require repeated matched seeds/splits.
