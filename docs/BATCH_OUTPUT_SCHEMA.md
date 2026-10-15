# Batch Output Schema

For a batch id `<run_id>`, outputs are written beneath `outputs/batch_runs/<run_id>/`. Existing per-policy output trees and legacy CSV names are retained; the run does not clear previous output files before writing.

```text
<run_id>/
  structural_summary.csv                 # dataset × fold × client_count; no policy dimension
  structural_summary_aggregate.csv       # dataset × client_count; fold mean/std/min/max
  resolver_summary.csv                   # dataset × fold × client_count × policy
  resolver_summary_aggregate.csv         # dataset × client_count × policy; fold mean/std/min/max
  research_chain_summary.csv             # reduct → rule → conflict → resolver → performance
  policy_disagreement.csv
  conflict_class_metrics.csv
  batch_manifest.json
  structural/<dataset>/
    central_reduct.csv
    local_reducts.csv
    reduct_candidates.csv
    pairwise_reduct_jaccard.csv
    feature_selection_frequency.csv
    centralized_rules.csv
    local_rules.csv
    federated_rules.csv
    rule_metrics.csv
    pairwise_rule_jaccard.csv
    conflict_groups.csv
    conflict_cases.csv
    structural_manifest.json
  resolver/<policy>/<dataset>/
    resolver_summary.csv
    conflict_cases.csv
    conflict_class_metrics.csv
    policy_disagreement.csv
    resolver_manifest.json
```

`central_reduct.csv` contains split identity, train rows, full dependency, minimum size, candidate count, selected reduct/dependency, all candidates, selection policy, and measured reduct seconds. `local_reducts.csv` has one row per client and includes the corresponding client row count, local reduct metadata, pooled reduct, local-central Jaccard, and reduct seconds. `reduct_candidates.csv` has one row per candidate and records scope (`CENTRAL`/`LOCAL`), client, feature tuple, size, and dependency.

`local_rules.csv` records client id, selected reduct, reduct size, condition expression, decision, rule key, source, and provenance. `rule_metrics.csv` has one row per central model, local client, or federated union with rule count and average/median/min/max condition count.

`structural_summary.csv` stores one row for each structural configuration, never one row per policy. Resolver rows carry accuracy, balanced accuracy, macro-F1, coverage, conflict-only metrics, disagreement with `FIRST_MATCH`, and order-invariance labels. `coverage` is repeated for readability but is shared by policies on the same artifact.

For K-fold runs, each fold remains in fold-level CSVs. The two `*_aggregate.csv` files summarize numeric fields with population standard deviation and min/max; rows with no defined conflict-only metric remain `NaN` in the fold-level evidence and are excluded from finite aggregate calculations.

The structural manifest defines conflict rate as a pre-resolution workload: among all rules matching a case, more than one distinct decision. `conflict_case_rate` may appear in legacy outputs as an alias; new summaries use `pre_resolution_conflict_case_rate`.
