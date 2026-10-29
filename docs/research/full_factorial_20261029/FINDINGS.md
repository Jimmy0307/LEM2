# LEM2 Full Factorial — Key Findings

## Scope

Canonical matrix: 3 datasets × 2 split modes × (centralized + federated C=2/3/4/5) × (NONE + 6 selection policies) = **210 rows**.

`NONE` is the pure rule-set / candidate baseline. It deliberately has no Accuracy / Balanced Accuracy / Macro-F1 because no unique winner is selected.

## Main empirical findings

1. **Centralized + FULL_DATA has zero conflict on all three datasets.**
   - Balance Scale: 0%
   - Car Evaluation: 0%
   - Hayes-Roth: 0%

2. **Centralized + 80/20 exposes conflict even without federation.**
   - Balance Scale: 8.73%
   - Car Evaluation: 15.03%
   - Hayes-Roth: 11.54%
   - Three-dataset mean: 11.77%

3. **Federated partition + rule UNION creates conflict even under FULL_DATA resubstitution.**
   - Mean conflict rate: C=2 17.93% → C=3 36.28% → C=4 51.56% → C=5 59.99%.

4. **Federated + 80/20 is the strongest conflict setting.**
   - Mean conflict rate: C=2 24.47% → C=3 47.26% → C=4 48.68% → C=5 63.98%.

5. **The six policies do not create conflict.**
   Conflict is measured before policy selection. The policies only choose a winner after multiple candidate decisions exist.

6. **Policy ranking depends on metric and regime.**
   - Centralized 80/20: highest mean Accuracy / Macro-F1 = STANDARD_VOTING and POPULATION_STANDARD (80.93% / 67.13%); highest BA = GLOBAL_STRENGTH and POPULATION_GLOBAL (66.75%).
   - Federated FULL_DATA: highest Accuracy = STANDARD_VOTING (90.53%); highest BA / Macro-F1 = GLOBAL_STRENGTH (83.08% / 81.02%).
   - Federated 80/20: highest Accuracy = STANDARD_VOTING (78.53%); highest BA / Macro-F1 = GLOBAL_STRENGTH (67.25% / 65.23%).

## Interpretation boundary

The experiment supports the statement that **holding out unseen objects and federated local-rule union both change the rule-matching candidate structure**. It does not, by itself, establish a universal causal law for every Rough Set / LEM2 implementation or dataset.
