# RoughSet Software V1 — Final Validation Report

Date: 2026-10-10

## Canonical reference

Reference file:

`reference/lem2_control_panel_v6_1_reference.py`

SHA-256:

`6dc1732f83944d4b99e36d03f97297e35aaff5fab40c01cc50cdc7d3fb469177`

The reference copy is unchanged from the validated V6.1 source used for extraction.

## Mathematical freeze / parity

AST-parity tests directly compare the extracted implementation against V6.1 for:

- `Rule`
- equivalence classes
- lower approximation
- LEM2 blocks / complex intersection
- pair selection
- complex minimization
- local covering
- LEM2 induction
- positive-region size
- dependency degree
- Balanced Accuracy / Accuracy / Macro F1
- Standard Voting support weights
- Global Strength support sets
- Jaccard / conflict audits
- centralized execution
- stratified client partition
- Dirichlet label-skew partition
- client-order audit
- UNION + provenance
- federated execution

Result: **PASS**.

## Test evidence

Package suite:

`python -m pytest -q`

Result: **52 passed** (final environment-hardened package suite).

Original V6.1 validation suites:

`python -m pytest -q test_v6_1_math_validation.py test_v6_1_extensions.py`

Result: **17 passed**.

Compile verification:

`python -m compileall -q roughset main.py`

Result: **PASS / exit 0**.

## End-to-end smoke test

A temporary real-data folder was created with a CSV + sidecar schema and executed through:

`python main.py --config <temporary-config>`

Configuration included:

- AUTO source discovery
- local CSV
- explicit continuous + categorical schema
- Holdout split
- Centralized LEM2
- Federated LEM2
- Client sweep
- FIRST_MATCH

Observed:

- Centralized Balanced Accuracy = 1.0
- Federated Balanced Accuracy = 1.0
- expected output folder created
- `summary.json` created
- `dataset_manifest.json` created
- `client_sweep.csv` created
- schema roles persisted in dataset manifest

Result: **PASS**.

A separate K-Fold smoke run was also executed successfully.

## Windows BAT checks

`run.bat` was checked for:

- `%~dp0` project-directory resolution
- quoted paths
- `.venv\Scripts\python.exe`
- environment bootstrap
- dependency check/install
- non-zero exit-code propagation
- pause on error
- CRLF line endings

Result: **static checks PASS**.

Limitation: this Linux execution environment cannot execute `cmd.exe`, so the BAT was not natively executed on Windows in this validation session.

## Real-data behavior

Supported local files:

- CSV
- XLSX
- XLS

`real_data/local/` is batch-scanned. Each file is treated as an independent dataset and gets its own output directory.

Target selection is deliberately conservative:

- sidecar schema has priority
- without schema, only one exact normalized name among `target`, `class`, `label`, `decision` may be auto-selected
- the last column is never silently assumed to be the target

## Data-type separation

Separate modules now own:

- `sources.py` — where data comes from
- `adapters.py` — raw source → DatasetBundle
- `schema.py` — target / continuous / categorical / ordinal / ignore
- `splitting.py` — Holdout / K-Fold
- `preprocessing.py` — training-only discretization

Continuous bin boundaries are fitted on the training side only and reused on test data.

## UCI ID / DOI

`real_data/uci_sources.txt` accepts:

- `44`
- `uci_id:44`
- `10.24432/C5501T`
- `doi:10.24432/C5501T`
- `https://doi.org/10.24432/C5501T`

Known V6.1 UCI DOI mappings work offline. Unknown DOI-only entries require Internet on first resolution and are then cached.

Known V6.1 dataset semantics are preserved for UCI IDs 44, 19, and 12.

## Output provenance

Each dataset can emit:

- summary JSON/CSV
- dataset manifest including schema and preprocessing metadata
- centralized rules
- federated rules
- local client metrics
- pairwise Jaccard table
- exact conflict groups
- conflict cases
- client-order distribution
- client sweep
- paper-protocol outputs when enabled

Known generated output files are cleared before each dataset write to prevent stale diagnostics from a previous run being mistaken for current results.

## Paper replication lane

The Wang-2007-style lane is retained and disabled by default.

Its historical sequence remains:

`full labeled data → minimum-cardinality reduct → LEM2 → Global Strength → K-Fold`

The full-data reduct selection is intentionally labeled as historical replication behavior, not modern leakage-free evaluation.

## Final self-review

Final review type: **self-review (no independent subagent tool available in this session)**.

Critical findings: **0**  
Important findings remaining: **0**

Issues discovered during self-review and fixed before packaging:

1. schema files that specify only target now leave feature roles available for auto-detection instead of forcing them categorical;
2. generated diagnostic files are removed before rewriting to prevent stale results;
3. DOI source parsing accepts raw ID, raw DOI, labeled forms, and DOI URLs;
4. known DOI matching is case-insensitive;
5. resolved schema roles are written to `dataset_manifest.json`.

## Known limitations

1. Actual Windows BAT execution was not possible in this Linux environment; only static/path/CRLF checks were possible.
2. Arbitrary unseen DOI online resolution could not be network-integration-tested here; known UCI DOI mappings are covered offline and the online resolver fails explicitly rather than guessing.
3. Collaborative-Filtering-inspired conflict resolution is intentionally not included yet; the package contains the provenance/conflict/order baselines needed to add it next.

## Environment dependency hardening (2026-10-11)

Added:

- `setup_environment.bat`
- `check_environment.bat`
- `requirements-core.txt`
- `requirements-excel.txt`
- `requirements-uci.txt`
- `requirements-lock.txt`
- `roughset/environment.py`
- optional `runtime/python.exe` bootstrap convention documented in `runtime/README.txt`

Behavior:

- Core dependencies are isolated from Excel/UCI adapter dependencies.
- `run.bat` creates the core environment when needed, inspects configured data sources, installs only required optional adapters, verifies the environment, then starts the experiment.
- Exact runtime pins are recorded in `requirements-lock.txt`.
- `run_manifest.json` and every `dataset_manifest.json` now record Python/platform/package versions.
- Batch files use `%~dp0`, quoted paths, delayed expansion for error propagation, and CRLF line endings.

Validation note: optional `xlrd` and `ucimlrepo` installation could not be downloaded in this offline Linux validation environment. Their pinned requirement files and on-demand detection paths are covered by static/unit tests; actual first-time Windows/PyPI installation still requires network unless packages are already available or a prepared environment is supplied.

## Final environment-hardened verification (2026-10-11)

Fresh release verification after dependency hardening:

- package suite: **52 passed**
- original V6.1 mathematical regression: **11/11 passed**
- original V6.1 extension regression: **6/6 passed**
- `python -m compileall -q roughset main.py`: **PASS**
- canonical V6.1 reference SHA-256 unchanged: `6dc1732f83944d4b99e36d03f97297e35aaff5fab40c01cc50cdc7d3fb469177`
- `run.bat`, `setup_environment.bat`, `check_environment.bat`: CRLF **PASS**
- local CSV environment profile detection: Core only, **PASS**
- CLI end-to-end local CSV smoke: **PASS**
- run/dataset manifests record Python version and direct dependency lock compliance: **PASS**

Environment design now checks both package presence **and exact direct-package version**. An existing `.venv` with a mismatched direct dependency is treated as unsatisfied and repaired by `run.bat --ensure`.

Offline support: if compatible `.whl` files are placed under `wheels/`, pip installs with `--no-index --find-links`. The release does not redistribute Python or third-party wheel binaries.


## V1.1 Python 3.14 bootstrap regression fix (2026-10-12)

User reproduction evidence showed `py -3` selecting `C:\Program Files\Python314`, after which `numpy==2.3.5` resolved to a cp314 wheel but `pandas==2.2.3` resolved to a source distribution. That entered an unintended Meson source-build path and failed before metadata generation.

Root-cause correction:

- canonical locked runtime constrained to Python 3.11–3.13;
- explicit launcher preference: 3.13 -> 3.12 -> 3.11;
- incompatible existing `.venv` is rebuilt;
- source builds disabled for locked dependencies with `--only-binary=:all:`;
- optional `install_python_313.bat` added;
- environment manifest now records maximum supported Python boundary.

Fresh verification after the fix is recorded in the release packaging step.

### Fresh verification after Python 3.14 bootstrap fix

- package test suite: **57 passed**
- original V6.1 mathematical regression: **11/11 passed**
- original V6.1 extension regression: **6/6 passed**
- `python -m compileall -q roughset main.py`: **PASS**
- BAT CRLF check (`run.bat`, `setup_environment.bat`, `check_environment.bat`, `install_python_313.bat`): **PASS**
- environment manifest on validated runtime: Python **3.13.5**, supported range **3.11 <= Python < 3.14**, Core lock matches (`numpy==2.3.5`, `pandas==2.2.3`)
- canonical V6.1 reference SHA-256 unchanged: `6dc1732f83944d4b99e36d03f97297e35aaff5fab40c01cc50cdc7d3fb469177`

Windows limitation remains: this Linux validation host cannot execute `cmd.exe`; the exact user-reported Windows failure path is instead pinned by compatibility and BAT static regression tests. The failing dependency combination was independently verified against pandas release metadata: pandas 2.2.3 added Python 3.13 compatibility, while Python 3.14 compatibility appears in pandas 2.3.3 rather than 2.2.3.


## Full-policy batch runner validation

- Default `run.bat`: invokes `main.py --all-policies`.
- `run_single.bat`: preserves the previous one-policy behavior.
- Batch output isolation: each policy writes to its own timestamped folder.
- Combined comparison: `batch_summary.csv`.
- Batch provenance: `batch_manifest.json`.
- Automated suite after this change: 60 tests passed.
- Local CLI smoke: all four policies completed from one `--all-policies` invocation.
