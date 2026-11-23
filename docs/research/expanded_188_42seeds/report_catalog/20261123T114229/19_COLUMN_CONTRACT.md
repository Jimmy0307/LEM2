# Exact 19-column scientific contract
From `experiments/full_scale_20261118/shard.py::FULL19`:

| # | Column | Definition |
|---:|---|---|
| 1 | dataset | Registry dataset identifier |
| 2 | seed | Random seed; old experiment seeds not the same as 42-seed run |
| 3 | distribution | IID or DIRICHLET_NONIID |
| 4 | dirichlet_alpha | 0.5 / 0.1, or missing in IID |
| 5 | split_mode | NESTED_64_16_20 |
| 6 | system | CENTRALIZED or FEDERATED |
| 7 | client_count | Client count (0 for centralized; 3 for federal) |
| 8 | selection_policy | One of six voting/resolution methods |
| 9 | train_rows | Count of training rows recorded by experiment |
| 10 | test_rows | Count of untouched test rows |
| 11 | rule_count | Number of induced/merged rules |
| 12 | no_match_count | Test rows not covered by any matching rule |
| 13 | covered_count | Test rows covered by at least one matching rule |
| 14 | test_coverage_pct | 100 × covered_count / test_rows |
| 15 | true_in_candidate_count | Covered test rows whose true label is among rule candidate decisions |
| 16 | candidate_coverage_pct | 100 × true_in_candidate_count / test_rows |
| 17 | accuracy_pct | Overall test accuracy, percentage |
| 18 | balanced_accuracy_pct | Balanced accuracy = macro recall, percentage |
| 19 | conflict_rate_pct | Fraction of test rows with >1 candidate decision, percentage |

**Invariant:** covered_count + no_match_count = test_rows, and true_in_candidate_count ≤ covered_count. Under the same dataset×seed×scenario×variant, coverage and conflict are policy-independent; only resolved Accuracy/BA differs by decision strategy.

The newest 42-seed JSON/CSV results include all 19 fields **plus rule_variant**. The 19-column historical tables are source-verified 5-seed records; 42-seed source is `interim/RESULTS.csv.gz`. For an exact 42-seed per-dataset 19-column workbook, extract this gzip and aggregate it while retaining each seed's data (do not paste 5-seed absolute metrics into 42-seed comparison tables).

Source links listed in README.md.