# 07 — Limitations

## Evidence scope

1. **Three datasets only**: Hayes-Roth (UCI 44), Car Evaluation (UCI 19), Balance Scale (UCI 12).
2. **One HOLDOUT split** (test ratio 0.2, stratified) — no repeated splits, no cross-validation in
   this audit run. Every number is a single realisation.
3. **One seed (42)** for the split, the client partition and the order-sampling RNG. No
   seed-to-seed variance is estimated, so no confidence intervals or significance tests are given.
4. **Small feature counts**: 4 (Hayes-Roth after dropping `name`), 6 (Car), 4 (Balance).
5. **Exhaustive minimum-cardinality reduct search** is `O(2^|C|)` positive-region evaluations.
   It is feasible here (≤ 64 subsets) and says nothing about scalability to high-dimensional data.
6. **Small-sample associations**: the structural associations in
   `outputs/final_math_audit_20261015/structural_associations.csv` use n = 12 pooled observations
   (n = 4 per dataset). They are exploratory descriptions, not tests.

## Metric status

7. **Reduct instability (RI), rule heterogeneity (H_rule), pre-resolution conflict rate,
   covered-conflict rate, order sensitivity** are derived research metrics defined in this project
   (`02_MATHEMATICAL_DEFINITIONS.md` §4.9–4.12). They are not original Pawlak or Grzymała-Busse
   (LEM2/LERS) measures. Conventions such as `J_R(∅, ∅) = 1` are project choices.
8. **Covered-conflict rate** is not stored by the pipeline; it is derived in the analysis as
   `pre_resolution_conflict_case_rate / coverage` (every conflict case is covered by definition).

## Method scope

9. **Partitioned-data simulation**, not a distributed systems or network benchmark: clients are
   in-process data frames; no communication, privacy, latency or failure model is evaluated.
   "Distributed = pooled" is an arithmetic identity for a fixed global rule set, not a
   protocol claim. Computing `Supp_c(r)` for every global rule on every client assumes each client
   can evaluate the shared global rules on its own rows; how that is done privately is out of scope.
10. **Local certainty is not pooled certainty.** Every local rule is certain on its own client;
    the UNION `R_G` is an aggregated set of locally certain rules and can contain contradictory
    rules (e.g. toy `B=1 → Y` and `B=1 → N`). `R_G` is not `LEM2(U_train)`.
11. **No collaborative resolver** is part of this baseline. The four resolvers are
    FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING and GLOBAL_STRENGTH.
12. **Stratified partition only** in this run (`DIRICHLET_LABEL_SKEW` exists but was not run).
    Conclusions about label-skewed federations are not supported.

## Code scope

13. **Legacy `federated.run_federated`** (V6.1, AST-frozen by `tests/test_reference_ast_parity.py`)
    still aggregates STANDARD weights and GLOBAL_STRENGTH support over producing clients only.
    It is not called by the production pipeline (`app` → `pipeline.build_rule_system`) and was
    deliberately not modified. Any external caller of that function would get the pre-audit,
    provenance-scoped weights.
14. **`paper.py` historical lane** keeps the V6.1 reduct search (`np.isclose`, sizes from 1). For
    the Wang datasets (`n ≤ 1 728`, `γ_C > 0`, ≥ 2 classes) this is provably identical to the exact
    search (03, item A10), but the historical lane would not select `R = ∅` and could accept a
    non-reduct for `n ≳ 10^5`.
15. **Runtime environment**: the reference run used Python 3.12.10; this audit used Python 3.11.9
    with the same locked packages (numpy 2.3.5, pandas 2.2.3, ucimlrepo 0.0.7). The pre-fix rerun
    reproduced the reference tables exactly, so the interpreter difference had no observable
    effect on these results.
16. **UCI data** were fetched once (2026-10-15) and frozen to
    `outputs/final_math_audit_20261015/uci_snapshot/` (SHA-256 in `meta.json`). Both reruns read
    the same bytes. The 2026-10-14 reference fetched live; equality of results is the evidence that
    the data were the same.

## Claims

17. **No universal causal claim** is supported. Statements in `06_EMPIRICAL_ANALYSIS.md` are
    labelled OBSERVED / INTERPRETATION / NOT PROVEN, and observations are limited to these
    3 datasets × 4 client counts × 1 split.
