# LEM2 data-size regimes, conflicts, and non-monotonicity

**EXPLORATORY / NOT A PROVEN PHASE TRANSITION.** 42-seed primary snapshot 20261123T114229
179 completely paired datasets. All outcomes use A_ALL_RULES and fixed STANDARD_VOTING.

## Predefined original-row-size bands

| Size | n | Δ Conflict pp (FED_A01 - Central) | Δ Accuracy pp | Absolute FED_A01 Conflict % | >=50% conflict datasets |
|---|---:|---:|---:|---:|---:|
| <500 | 43 | 75.86 | -8.98 | 78.37 | 42 |
| 500–4,999 | 84 | 55.07 | -6.63 | 56.36 | 53 |
| 5,000–49,999 | 39 | 42.21 | -5.24 | 42.42 | 17 |
| >=50,000 | 13 | 13.22 | -4.44 | 13.23 | 1 |

**Cross-dataset trend is a size association, not a within-dataset threshold.**
Some of the largest datasets are missing due to timeout; class and domain mixes vary by size.

## Exploratory adjusted change-point fits (candidate, NOT established)

| Outcome | Per 10× rows adjusted slope (bootstrap 95% CI) | Candidate cut rows | Cut IQR (bootstrap, conflict only) | 5-fold linear RMSE | 5-fold hinge RMSE |
|---|---:|---:|---:|---:|---:|
| conflict_delta_pp | -14.52 [-18.52, -10.79] | 7,200 | 1,664–8,237 | 14.95 | 14.93 |
| accuracy_delta_pp | +1.86 [+0.02, +3.60] | 1,728 | nan–nan | 9.36 | 9.41 |
| coverage_delta_pp | +9.29 [+3.82, +17.10] | 2,109 | nan–nan | 28.61 | 26.97 |

Hinge breakpoint optimized inside train folds and evaluated on held-out folds. Apparent cut points are data-driven and subject to source-family confounding. Do not interpret a particular row number as a physical phase transition.

## Within-source three-level ladder (only one seed, selected large datasets)

| Scenario | Metric | 3-level datasets | decreasing | increasing | peak | valley | other |
|---|---|---:|---:|---:|---:|---:|---:|
| FED_IID | conflict | 19 | 9 | 0 | 0 | 0 | 10 |
| FED_IID | accuracy | 19 | 3 | 2 | 0 | 0 | 14 |
| FED_IID | coverage | 19 | 13 | 1 | 0 | 0 | 5 |
| FED_A01 | conflict | 22 | 9 | 2 | 4 | 1 | 6 |
| FED_A01 | accuracy | 22 | 1 | 3 | 2 | 6 | 10 |
| FED_A01 | coverage | 22 | 3 | 0 | 2 | 2 | 15 |

The scale ladder uses different sampled datasets at 1,800, 10,000 and FULL. It is not a controlled nested expansion. One seed cannot establish replicable thresholds.

## Verification path

- `SIZE_REGIMES_179.csv`: 4 predefined bins × 3 scenarios, within-bin dispersion and conflict >=50 counts
- `SIZE_QUANTILES_179.csv`: 6 data-driven size quantiles for visualizing smooth or nonmonotone curves
- `EXPLORATORY_CHANGEPOINT_CV.csv`: adjusted coefficients, bootstrap intervals, train-selected hinge and out-of-sample RMSE
- `WITHIN_SOURCE_SCALE_LADDER_1SEED.csv`: full per-source 3-level curves with shape labels
- `LADDER_SHAPE_COUNTS.csv`: aggregated falling/rising/peak/valley counts
- `SPEARMAN_DESCRIPTIVE.csv`: rank relationships

## Next experimental controls before a threshold claim

1. Select and preregister candidate row budgets (e.g. 500, 1,800, 5,000, 10,000, 25,000, FULL).
2. Re-run the **same datasets** at each row budget with nested, class-stratified samples, fixed identical feature selection and 5+ seeds.
3. Measure conflict rate, rule count, candidate coverage, class-wise recall, TRUE-rule incidence, min client-class support, throughput, timeouts and memory.
4. Use held-out datasets or previously unexamined seeds to validate a candidate threshold rather than selecting and testing on the same cases.
5. Compare one-hinge, monotone and no-threshold baselines; report uncertainty and subgroup disagreements.

### Bias to avoid

The 'best Accuracy' obtained by selecting a voting policy using TEST labels is a post-hoc oracle, not deployable performance; this analysis uses a fixed voting policy to avoid it.
