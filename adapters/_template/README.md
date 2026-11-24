# Template: a separate algorithm adapter (not an algorithm implementation)

Copy this directory to `adapters/fdm_prism` (or keep it in a new independent repository). Rename the Python distribution, entry-point name, module, and capability descriptor. Replace the intentionally unimplemented `fit` and `predict` methods with **the actual algorithm**.

```bash
python -m pip install -e '.[test]'
python -m pip install -e ./adapters/_template
fdm algorithms
```

**Template status:** importing/discovering it succeeds as `algorithm_template`, but `fit()` deliberately raises `NotImplementedError` until replaced. Never rename this placeholder to `prism`, `ripper` or `drsa` without implementing the real scientific algorithm and tests.

Your final package must declare entry point group `federated_decision_making.algorithms`, implement `AlgorithmPlugin` v1, and pass the [contributor checklist](../../CONTRIBUTING.md). If your algorithm does not really support federated rule merging, declare only `CENTRALIZED`.

Bundled LEM2 engine is not required to write an algorithm adapter.
