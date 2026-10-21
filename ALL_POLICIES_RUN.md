# One-click all-policy experiment

Double-click `run.bat`.

The launcher will:

1. Prepare/check the Python environment.
2. Resolve optional adapters required by the current local/UCI inputs.
3. Discover all configured datasets.
4. Run the four **Prediction Policies**: FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING, and GLOBAL_STRENGTH.
5. For each policy, retain the configured client sweep (default \(C=2,3,4,5\)).
6. Write isolated policy outputs plus combined structural / policy summaries under `outputs/batch_runs/<run_id>/`.
7. Include the established client-order disagreement measure `mean_variation_ratio` for FIRST_MATCH; the three score-based policies are order-invariant by design under the frozen artifact.

`run_single.bat` is available when only the single policy in `config.json` is desired.

Evaluation mode is intentionally controlled by `config.json` and is not multiplied automatically. Default is HOLDOUT.

## Primary research outputs

The manuscript-facing comparison prioritizes established measures:

```text
balanced_accuracy
macro_f1
coverage
rule_jaccard_antecedent
conflict_cases_count / conflict-set proportion
conflict_balanced_accuracy
conflict_macro_f1
mean_variation_ratio
mean_variation_ratio_conflict
```

Legacy project-specific fields such as `conflict_resolution_accuracy`, `order_sensitivity_rate`, and `rule_heterogeneity` may remain in CSV files for backward compatibility, but they are not the primary theoretical metrics.

## Method / metric references

- Federated LEM2, FIRST_MATCH, Coverage, Jaccard, client-count design: Woźniak, Sousa, & Śnieżyński (2026), DOI `10.1007/978-3-032-29921-5_38`.
- Simple / Standard Voting: Lazo-Cortés et al. (2020), DOI `10.1007/978-3-030-49076-8_7`.
- GlobalStrength: Bazan et al. (2000), DOI `10.1007/978-3-7908-1840-6_3`.
- Rule conflict: Lindgren (2004), DOI `10.1007/978-3-540-30115-8_26`.
- Balanced Accuracy: Brodersen et al. (2010), DOI `10.1109/ICPR.2010.764`.
- Macro-F1 / classification measures: Sokolova & Lapalme (2009), DOI `10.1016/j.ipm.2009.03.002`.
- Variation Ratio: Gal (2016), §3.3.1, Eq. (3.19), citing Freeman (1965).

Teacher-facing overview: `docs/research/conflict_client_sweep_20261020/FINAL_TEACHER_HANDOFF.md`.
