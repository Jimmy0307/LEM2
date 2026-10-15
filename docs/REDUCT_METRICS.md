# Reduct and Structural Metrics

This document separates original Rough Set quantities from derived diagnostics introduced for this experiment pipeline. Derived diagnostics are research-reporting choices; they are **not** presented as Pawlak or LEM2-native measures.

## Original Rough Set quantities

- **Positive region** `POS_C(D)`: the objects in the universe whose condition-attribute equivalence classes are contained in one decision class. The implementation's existing definition is unchanged.
- **Dependency** `gamma_C(D) = |POS_C(D)| / |U|`.
- **Reduct**: a subset `R ⊆ C` with `gamma_R(D) = gamma_C(D)`. A minimum-cardinality reduct additionally minimizes `|R|`. The existing exhaustive search is unchanged.

## Derived reduct diagnostics

- **Pairwise reduct Jaccard**: `|R_i ∩ R_j| / |R_i ∪ R_j|` for selected local reducts. The explicit convention for two empty reducts is `1.0`; this is set-similarity behavior, not a Rough Set quantity.
- **Reduct instability**: `1 - mean(pairwise reduct Jaccard)`. If fewer than two clients exist, it is `NaN` because there are no client pairs.
- **Feature selection frequency**: for feature `a`, the number of clients whose selected reduct contains `a`, divided by client count. Frequencies are emitted over all condition features, including zero-frequency features.
- **Local-central reduct similarity**: Jaccard similarity between each client's selected reduct and the selected pooled-training reduct; aggregate mean/std/min/max are reported.
- **Candidate multiplicity**: number of minimum-cardinality candidate reducts. All candidates are preserved as normalized tuples, alongside the deterministic selected tuple.

## Derived rule and conflict diagnostics

- **Rule heterogeneity** is defined here as `1 - mean pairwise full-rule Jaccard` across client rule sets. Antecedent-only and full-rule Jaccard are both retained in the pairwise table.
- **Pre-resolution conflict**: a test object is a conflict case when the union of all rules matching that object has more than one distinct decision. `pre_resolution_conflict_case_rate` is the count of such cases divided by test rows. The older `conflict_case_rate` alias is retained only for compatibility.
- Conflict workload also reports matching-rule counts and distinct decision counts. Exact conflict antecedents are rule antecedent groups associated with multiple decisions; their rate is the conflicting-group count divided by unique antecedent count (zero when no antecedent exists).
- **Conflict-only resolver metrics** (`conflict_resolution_accuracy`, `conflict_balanced_accuracy`, `conflict_macro_f1`, and class rows) use only pre-resolution conflict cases. If there are no conflict cases, aggregate conflict-only metrics are `NaN`, not zero.
- `FIRST_MATCH` order effects are measured. Voting policies are marked `ORDER_INVARIANT_BY_DESIGN`; a numeric zero may remain for compatibility but is not presented as an empirical finding.
- Coverage is a shared structural metric for a fixed artifact, not a resolver-quality metric.

