OPTIONAL PORTABLE PYTHON RUNTIME
===============================

This folder is intentionally empty in the normal release.

If the target Windows PC does not have Python installed, you may place a PORTABLE
Python distribution here so that this path exists:

    runtime\python.exe

The portable distribution must support `python -m venv` and `python -m pip`.
`setup_environment.bat` will prefer runtime\python.exe before system Python.

The release ZIP does NOT redistribute Python binaries. This avoids silently
shipping a third-party runtime and keeps the package auditable.
