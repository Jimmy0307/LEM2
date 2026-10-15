OPTIONAL OFFLINE WHEELHOUSE
===========================

If the target computer has no Internet access, place compatible `.whl` files here
for every package listed in requirements-lock.txt (and their transitive dependencies).

When one or more wheel files are present, the environment installer uses:

    pip install --no-index --find-links wheels ...

This release does not bundle third-party wheel binaries. Use wheels that match the
target Windows Python version and architecture (normally 64-bit CPython).
