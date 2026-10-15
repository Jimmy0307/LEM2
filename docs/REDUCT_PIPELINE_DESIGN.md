# Reduct Pipeline Design

## Main strict pipeline

For every HOLDOUT training split or K-fold training partition:

```text
split raw rows
  → fit preprocessing from training rows only
  → transform train and test with that fitted preprocessor
  → calculate pooled-training minimum-cardinality reduct candidates
  → select the canonical candidate
  → induce centralized LEM2 rules using only that reduct
```

For a federated configuration, partitioning is also limited to the training rows. After the training-fitted shared preprocessing transform, each client independently calculates its minimum-cardinality reduct candidates and induces LEM2 rules using only its own selected reduct. Local rules are then unioned with their existing rule identity and provenance semantics. Prediction matches each rule's own antecedent; test objects are not projected onto a global reduct.

The existing exhaustive search and dependency implementation are unchanged. Candidate reducts are normalized as sorted feature tuples and sorted lexicographically. The first tuple is selected. All candidates, candidate count, minimum size, dependency, and selection policy remain available on `ReductSelectionResult` and in structural CSVs.

With `reduct.enabled=false`, the main lane passes all condition columns to LEM2 as the legacy ablation. `method` currently accepts only `MINIMUM_CARDINALITY`; `selection` currently accepts only `LEXICOGRAPHIC_FIRST`.

## Build once, resolve many

`build_rule_system()` creates a `RuleSystemArtifact` for one dataset/split/client partition. It freezes row identities, reduct results, central/local/global rules, provenance and support information, default classes, pre-resolution conflict identities, structural metrics, and report tables. `evaluate_resolver(artifact, policy)` evaluates a policy without rebuilding the artifact. The batch runner reuses the exact same artifact objects across the configured policies. A different client count is a different structural configuration and receives its own artifact.

Pre-resolution conflict workload is computed from the set of all matching rules before a resolver selects a decision. It is therefore shared across policies. Resolver disagreement and conflict-only predictive metrics are evaluated afterward.

## Separate historical replication lane

The two protocols are intentionally not interchangeable:

```text
MAIN STRICT PIPELINE:
split → training-only preprocessing → train-only reduct → LEM2 → test evaluation

WANG HISTORICAL REPLICATION:
historical full-labeled table → historical reduct selection → CV protocol
```

`roughset/paper.py` remains on the Wang historical lane. It is not called to create the main-pipeline artifact, and its full-table reduct timing is not evidence of leakage-free main evaluation.

## Frozen mathematics

No changes are made to the existing Rough Set/LEM2 core, positive-region or dependency definitions, exhaustive reduct search, or `Rule.key` identity. New models, metrics, artifact construction, and reports sit around those existing operations.
