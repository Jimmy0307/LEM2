# Full Six-Policy Experiment Results — 2026-10-23

## Frozen run identity

- Source branch: `research/conflict-client-sweep-20261020`
- Experiment source commit: `19983125a5daef4f7af1fb9f55554e6fbf747017`
- GitHub Actions run: `39905627653` (`Full Six-Policy Experiment`, run #3)
- Verification before experiment: `114 passed`
- Workflow conclusion: `success`
- Artifact: `federated-lem2-six-policy-full-run`
- Artifact id: `12480623081`
- Artifact digest: `sha256:7ba10342ef4ae40c1f836cd131a1a9441c6381ff5dfc476431f1f3500599635d`

## Experimental protocol

The final matrix is:

```text
3 UCI datasets
× C = {2,3,4,5}
× 6 Prediction Policies
= 72 federated policy/configuration rows
```

Evaluation is a stratified 80/20 HOLDOUT with seed 42. The 20% test split is not used for reduct search, LEM2 induction, federated aggregation, rule-support construction, or rule-weight construction.

Policies:

1. `FIRST_MATCH`
2. `SIMPLE_VOTING`
3. `STANDARD_VOTING`
4. `GLOBAL_STRENGTH`
5. `POPULATION_STANDARD`
6. `POPULATION_GLOBAL`

The last two are project-defined experimental variants, not literature-derived baselines.

## Dataset sizes

| Dataset | Rows | Condition attributes | Classes | Train | Test |
|---|---:|---:|---:|---:|---:|
| Hayes-Roth | 132 | 4 | 3 | 106 | 26 |
| Car Evaluation | 1728 | 6 | 4 | 1382 | 346 |
| Balance Scale | 625 | 4 | 3 | 499 | 126 |

## Balanced Accuracy winners

Ties are retained.

| Dataset | C | Winner(s) | Balanced Accuracy |
|---|---:|---|---:|
| Balance Scale | 2 | POPULATION_STANDARD | 0.563218 |
| Balance Scale | 3 | STANDARD_VOTING; POPULATION_STANDARD | 0.586207 |
| Balance Scale | 4 | STANDARD_VOTING; POPULATION_STANDARD | 0.597701 |
| Balance Scale | 5 | GLOBAL_STRENGTH; POPULATION_GLOBAL | 0.590805 |
| Car Evaluation | 2 | GLOBAL_STRENGTH; POPULATION_GLOBAL | 0.717396 |
| Car Evaluation | 3 | POPULATION_GLOBAL | 0.800529 |
| Car Evaluation | 4 | GLOBAL_STRENGTH | 0.683169 |
| Car Evaluation | 5 | POPULATION_GLOBAL | 0.633821 |
| Hayes-Roth | 2 | FIRST_MATCH; STANDARD_VOTING; GLOBAL_STRENGTH; POPULATION_STANDARD; POPULATION_GLOBAL | 0.766667 |
| Hayes-Roth | 3 | FIRST_MATCH | 0.833333 |
| Hayes-Roth | 4 | FIRST_MATCH | 0.777778 |
| Hayes-Roth | 5 | FIRST_MATCH | 0.833333 |

## Macro-F1 winners

| Dataset | C | Winner(s) | Macro-F1 |
|---|---:|---|---:|
| Balance Scale | 2 | POPULATION_STANDARD | 0.549621 |
| Balance Scale | 3 | STANDARD_VOTING | 0.564166 |
| Balance Scale | 4 | STANDARD_VOTING; POPULATION_STANDARD | 0.573320 |
| Balance Scale | 5 | GLOBAL_STRENGTH | 0.591036 |
| Car Evaluation | 2 | POPULATION_STANDARD | 0.686556 |
| Car Evaluation | 3 | POPULATION_GLOBAL | 0.735028 |
| Car Evaluation | 4 | STANDARD_VOTING | 0.634665 |
| Car Evaluation | 5 | FIRST_MATCH | 0.606868 |
| Hayes-Roth | 2 | FIRST_MATCH; STANDARD_VOTING; GLOBAL_STRENGTH; POPULATION_STANDARD; POPULATION_GLOBAL | 0.766082 |
| Hayes-Roth | 3 | FIRST_MATCH | 0.832916 |
| Hayes-Roth | 4 | FIRST_MATCH | 0.791069 |
| Hayes-Roth | 5 | FIRST_MATCH | 0.829497 |

## What the fresh run supports

The population correction is not universally superior. It does, however, change the winner in several configurations:

- Car Evaluation, C=3: `POPULATION_GLOBAL` BA = 0.800529 vs `GLOBAL_STRENGTH` = 0.798463.
- Car Evaluation, C=5: `POPULATION_GLOBAL` BA = 0.633821 vs `GLOBAL_STRENGTH` = 0.623638.
- Balance Scale, C=2: `POPULATION_STANDARD` BA = 0.563218 vs `STANDARD_VOTING` = 0.557471.
- Several other configurations are exact/tolerance-level ties with their corresponding baseline.
- Hayes-Roth C=3..5 remains strongest under `FIRST_MATCH` in this single seed-42 holdout.

Therefore the current evidence supports a conditional-policy interpretation rather than a universal-best claim:

\[
Policy^*=f(Dataset, Rule\ Structure, Conflict\ Workload, Client\ Configuration)
\]

This remains one holdout seed. It is a mechanism / implementation result, not publication-level statistical evidence. Repeated matched splits are still required before Friedman / post-hoc or paired Wilcoxon inference.

## Output contract

The run exports the full `batch_summary.csv` plus compact results, winner tables, rule/conflict/order tables, logs, source code, configuration, tests, teaching/reference policy code, and research documentation. The reusable workflow is `.github/workflows/full-six-policy-experiment.yml`.
