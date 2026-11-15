"""fedrs: federated rough-set rule-degeneracy redesign (research branch 2026-11-16).

This package is an *analysis and experiment* layer on top of the frozen
``roughset`` package.  Rule induction (minimum-cardinality positive-region
reduct + LEM2) is delegated to the original ``roughset`` functions so that the
object of study is unchanged.  Only rule matching / resolution is re-implemented
in vectorised form, and parity with ``roughset.evaluation.predict_with_policy``
is enforced by tests (tests/test_fedrs_parity.py).

Nothing in this package overwrites the historical baseline outputs.
"""

__version__ = "0.1.0-20261116"
