# LEM2 Full Factorial Experiment Design

Date: 2026-10-29

## Goal

Run every combination requested for the three UCI datasets (Hayes-Roth, Car Evaluation, Balance Scale) while keeping classical Rough Set / LEM2 rule induction distinct from the study-added selection layer.

## Factors

1. System topology
   - CENTRALIZED
   - FEDERATED with C in {2,3,4,5}
2. Data use
   - FULL_DATA: 100% used to induce rules; if a selection policy is enabled, evaluation is resubstitution / in-sample on the same rows.
   - HOLDOUT_80_20: stratified seed=42, 80% rule induction and 20% holdout evaluation.
3. Selection layer
   - NONE: pure rule-induction baseline. Report rule/reduct/coverage/candidate/conflict diagnostics only. Accuracy, Balanced Accuracy, and Macro-F1 are intentionally NA because no unique winner is selected.
   - FIRST_MATCH
   - SIMPLE_VOTING
   - STANDARD_VOTING
   - GLOBAL_STRENGTH
   - POPULATION_STANDARD
   - POPULATION_GLOBAL

## Matrix size

Per dataset and per split mode:
- Centralized: 1 NONE + 6 policies = 7 rows
- Federated: 4 client counts x (1 NONE + 6 policies) = 28 rows
- Total per split mode = 35 rows

Two split modes -> 70 rows per dataset.
Three datasets -> 210 rows total.

## Required outputs

- FULL_FACTORIAL_RESULTS.csv (210 rows)
- FULL_FACTORIAL_BASELINES.csv (NONE rows only)
- FULL_FACTORIAL_POLICY_RESULTS.csv (six-policy rows only)
- FULL_FACTORIAL_POLICY_MEANS.csv
- FULL_FACTORIAL_MANIFEST.json

## Interpretation contract

`conflict` means a study-defined ambiguity in the matching/selection layer: one evaluated object matches induced rules that point to more than one decision class. This is not described as Rough Set itself failing. FULL_DATA and HOLDOUT_80_20 change where the rule set is evaluated. Federated partitioning can alter/amplify overlap because local rule sets are induced separately and unioned.
