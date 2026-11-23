# Federated Decision Making | Plugin-based Research Platform

Installable, algorithm-neutral experiment harness with optional algorithm adapters. See `docs/PACKAGING_AND_PLUGIN_GUIDE_ZH.md`.

```bash
pip install ./dist/federated_decision_making-0.1.0-py3-none-any.whl
fdm algorithms
fdm run --case case.json --output results/
```

Core: split/partition, metrics, checkpoint, receipts and task APIs.
LEM2: adapter to the existing `fedrs`/`roughset` repo implementation (requires legacy source modules to be available).
Third-party adapters: use entry-point group `federated_decision_making.algorithms` and implement `AlgorithmPlugin` v1.
PRISM/RIPPER/DRSA are intentionally not advertised as implemented.

This is an offline horizontal federation **simulation**; not an encrypted production federation or a single-model distributed Spark learner.
