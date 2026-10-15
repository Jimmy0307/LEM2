# RoughSet Software V1 — Environment Setup

## Recommended path

### First use

Double-click:

```text
setup_environment.bat
```

This creates `.venv` and installs the exact direct runtime pins in `requirements-lock.txt`.

After setup, normal use is simply:

```text
run.bat
```

`run.bat` can also bootstrap automatically: it installs Core first, scans current data/config, then installs only the optional adapters actually needed.

## Dependency profiles

### Core

```text
numpy==2.3.5
pandas==2.2.3
```

Used for CSV and the mathematical pipeline.

### Excel adapter

```text
openpyxl==3.1.5
xlrd==2.0.2
```

Installed on demand when `.xlsx` / `.xls` data are detected.

### UCI adapter

```text
ucimlrepo==0.0.7
```

Installed on demand when `real_data/uci_sources.txt` contains active UCI sources.

## Python

Supported runtime range for this canonical locked release:

```text
Python 3.11 - 3.13
```

The lock deliberately rejects Python 3.14 for `pandas==2.2.3`. Pandas 2.2.3 was the first release compatible with Python 3.13; Python 3.14 compatibility starts in a later pandas generation. This release preserves the validated pandas 2.2.3 environment instead of silently changing the research runtime.

If only Python 3.14 is installed, run:

```text
install_python_313.bat
```

This uses `winget` to install Python 3.13 x64 side-by-side; it does not remove Python 3.14. `setup_environment.bat` now explicitly tries `py -3.13`, then `3.12`, then `3.11` and never uses unqualified `py -3` for environment creation.

If system Python is unavailable, put a portable Python 3.11–3.13 distribution with `venv` and `pip` support at:

```text
runtime/python.exe
```

The release does not ship a Python binary.

## Offline mode

Place all compatible wheel files (including transitive dependencies) under:

```text
wheels/
```

The environment installer will use:

```text
pip --no-index --find-links wheels
```

The wheelhouse must match the target Windows architecture and Python version.

## Diagnostics

Double-click:

```text
check_environment.bat
```

or run:

```text
.venv\Scripts\python.exe -m roughset.environment --config config.json --json
```

The checker reports:

- required dependency profiles for the current data/config
- missing packages
- direct-version lock mismatches
- Python/platform information
- installed versions of core/adapter packages

## Research provenance

Every execution records environment metadata in:

```text
outputs/run_manifest.json
outputs/<dataset>/dataset_manifest.json
```

This includes Python, OS/platform, installed direct-package versions, expected locked versions, and lock-match status.

## Important reproducibility note

`requirements-lock.txt` fixes this project's **direct runtime dependencies**. Pip may still resolve transitive packages. For the strongest offline reproducibility, keep a frozen `wheels/` directory alongside the release and archive it with the experiment materials.


## Python 3.14 failure fixed in V1.1

Observed failure:

```text
py -3 -> Python 3.14
pandas==2.2.3 -> no cp314 wheel -> pandas source tar.gz
Meson metadata/source build -> failure
```

The installer now prevents this path in three ways:

1. it selects Python 3.13/3.12/3.11 explicitly;
2. it rebuilds an existing `.venv` if that venv was created with Python 3.14+;
3. pip installs locked runtime dependencies with `--only-binary=:all:` so a missing binary wheel fails clearly instead of attempting an accidental compiler/source-build path.
