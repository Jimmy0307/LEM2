# Independent lookup Adapter example (not PRISM)

This is a runnable **example classification plugin** for exercising FDM's Entry Point Registry. Its simple prediction logic must never be represented as PRISM, RIPPER or DRSA.

From the complete repository:

```bash
python -m pip install -e '.[test]'
python -m pip install -e ./examples/fdm_lookup_adapter
fdm algorithms
```

The package registers `lookup_example` in `[project.entry-points."federated_decision_making.algorithms"]` and can be selected in a `fdm run` Case. New algorithm implementations should copy [the blank template](../../adapters/_template/README.md), then replace `fit` / `predict` and add scientific tests and a methodology reference.

The adapter template's `fit()` intentionally raises `NotImplementedError`; it is not a working PRISM algorithm.
