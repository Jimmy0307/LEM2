# Python 3.14 bootstrap fix

## Root cause

The original ENV_READY bootstrap used `py -3`, which selects the newest installed Python. On the reported Windows machine that selected Python 3.14. The release simultaneously pinned `pandas==2.2.3`. Pandas 2.2.3 has Python 3.13 wheels, but not Python 3.14 wheels, so pip downloaded `pandas-2.2.3.tar.gz` and entered a Meson source-build path. The UnicodeDecodeError shown in the log occurred inside that unintended source-build path; it is not a Rough Set / LEM2 error.

## Corrected behavior

- Canonical runtime range is Python 3.11–3.13.
- `setup_environment.bat` explicitly tries 3.13, 3.12, then 3.11.
- Existing `.venv` created with Python 3.14+ is removed and recreated.
- `run.bat` detects an incompatible existing venv before dependency installation.
- Both BAT and Python-side pip installers use `--only-binary=:all:` for locked dependencies.
- `install_python_313.bat` is included as an optional convenience helper using winget.

## For the machine that already failed

Use the patched package. You do not need to manually clean the failed `.venv`: patched `run.bat` / `setup_environment.bat` detects the Python 3.14 venv and rebuilds it. If Python 3.13/3.12/3.11 is not installed, first run `install_python_313.bat`, then run `run.bat`.
