# LEM2 Teacher Demo — Metrics and Conflict/Selection Layer

## Purpose

This folder is a small, auditable demo for two questions raised in the teacher discussion:

1. What are the mean Accuracy, Balanced Accuracy, and Macro-F1 values across the three datasets?
2. Why does this study report `conflict` even though classical Rough Set / LEM2 normally finishes after inducing rules?

## Important terminology

The experiment must not describe the phenomenon as "Rough Set itself conflicts".

Classical Rough Set / LEM2 produces a rule set and may stop there. This study adds an inference layer:

`induced rules -> match an object -> collect candidate decisions -> require one winner`

The study defines a conflict when one object matches rules pointing to more than one decision class. The six policies (`FIRST`, `SIMPLE`, `STD`, `GS`, `PS`, `PG`) are resolver/selection policies applied after this ambiguity exists. They are not part of classical Rough Set / LEM2.

The 80/20 split is not required for conflict to be definable. It is an evaluation design that exposes the selection layer on unseen objects. Federated partitioning is also not required; it can change or amplify overlap because local rule sets are induced separately and then combined.

## Inputs

- `CENTRALIZED_VS_FEDERATED.csv`
- `CENTRALIZED_CONFLICT_STRUCTURE.csv`

## Run

```bash
python lem2_metric_and_selection_demo.py
```

## Expected centralized means across the 3 datasets

| Policy | Accuracy | Balanced Accuracy | Macro-F1 |
|---|---:|---:|---:|
| FIRST | 79.56% | 64.55% | 65.99% |
| SIMPLE | 78.18% | 62.69% | 64.30% |
| STD | 80.93% | 66.46% | 67.13% |
| GS | 80.65% | 66.75% | 66.82% |
| PS | 80.93% | 66.46% | 67.13% |
| PG | 80.65% | 66.75% | 66.82% |

Overall descriptive mean across all 18 centralized rows:

- Accuracy: **80.15%**
- Balanced Accuracy: **65.61%**
- Macro-F1: **66.37%**

## Centralized selection-layer conflict evidence

| Dataset | Conflict rows | Test rows | Conflict rate |
|---|---:|---:|---:|
| Balance Scale | 11 | 126 | 8.7% |
| Car Evaluation | 52 | 346 | 15.0% |
| Hayes-Roth | 3 | 26 | 11.5% |

These values do not mean classical Rough Set failed. They mean the study's added matching/selection layer found more than one candidate decision for those objects.
