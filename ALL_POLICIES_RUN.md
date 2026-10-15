# One-click all-policy experiment

Double-click `run.bat`.

The launcher will:

1. Prepare/check the Python environment.
2. Resolve optional adapters required by the current local/UCI inputs.
3. Discover all configured datasets.
4. Run FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING, and GLOBAL_STRENGTH.
5. For each policy, retain the configured client sweep (default C=2,3,4,5).
6. Write isolated policy outputs plus a combined `batch_summary.csv`.

`run_single.bat` is available when only the single policy in `config.json` is desired.

Evaluation mode is intentionally controlled by `config.json` and is not multiplied automatically. Default is HOLDOUT.
