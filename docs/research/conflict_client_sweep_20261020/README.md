# Federated LEM2 Research — Conflict, Population Correction, and Backtrace

> Frozen production baseline: `main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`  
> Research branch: `research/conflict-client-sweep-20261020`  
> PR #5: Draft / Open / Not merged

## Latest canonical reading order

1. `FINAL_RESEARCH_CONCLUSION_20261023.md` — current full conclusion and research model.
2. `FINAL_TEACHER_HANDOFF.md` — meeting-ready scope, formulas, code map, and safe claims.
3. `FULL_SIX_POLICY_RESULTS_20261023.md` — 3 UCI × C=2..5 × six-policy holdout results.
4. `TARGET_CASE_BACKTRACE_ANALYSIS_20261023.md` — 15 target cases + mechanism analysis.
5. `POPULATION_EXPERIMENT_UPDATE_20261022.md` — formal population-method specification.
6. `TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md` — established baselines and conflict.
7. `TEAM_EVALUATION_METRICS_ESTABLISHED.md` — established metrics / citation boundary.
8. `LITERATURE_REFERENCE_INDEX.md` — provenance.
9. `presentation/Federated_LEM2_Final_Research_Update_20261023.pptx` — latest presentation.
10. `evidence/20261023/` — compact results and case-level CSV evidence.

## Current research chain

\[
\boxed{
Client\ Fragmentation
\rightarrow
Rule\ Structure
\rightarrow
Prediction\text{-}time\ Conflict
\rightarrow
Support\ Redundancy
\rightarrow
Redundancy\ Asymmetry
\rightarrow
Prediction\ Policy
\rightarrow
Performance
}
\]

## Six methods

Established baselines:

```text
FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH
```

Project-defined experimental variants:

```text
POPULATION_STANDARD
POPULATION_GLOBAL
```

For candidate decision d:

\[
T_d=\sum_r|S_G(r)|,
\qquad
U_d=\left|\bigcup_rS_G(r)\right|,
\qquad
P_d=\frac{U_d}{T_d}
\]

\[
S_{PS}=U_d
\]

\[
S_{PG}=\frac{U_d}{N_d}\frac{U_d}{T_d}
\]

## Experiment protocol

```text
3 UCI datasets
× C = 2,3,4,5
× 6 methods
= 72 result rows
```

Strict 80/20 holdout. The 20% holdout is untouched until final prediction/evaluation.

## Latest mechanism evidence

All prediction-time conflict occurrences across C=2..5:

\[
908
\]

Population winner changes:

\[
43
\]

Mechanism check:

\[
\boxed{43/43}
\]

All changed winners move toward a lower-support-redundancy decision.

This confirms the implementation behavior, but lower redundancy is not always the true class. Population correction can therefore either correct inflated wrong evidence or over-correct valid repeated evidence.

## Important distinction

Two error types must be separated:

1. candidate-generation / rule-coverage failure;
2. candidate-ranking / conflict-resolution failure.

If the true class has no matching rule, no voting method can recover it.

## Next research step

Do **not** add another prediction method.

Run repeated matched seeds/splits and test whether:

\[
Redundancy_{competitor}-Redundancy_{true}
\]

predicts corrected vs harmed cases.

## Code map

| Layer | Code |
|---|---|
| LEM2 | `roughset/core.py` |
| Reduct | `roughset/reduct.py` |
| Runtime policies | `roughset/evaluation.py::predict_with_policy` |
| Federated UNION / partition | `roughset/federated.py` |
| Structural artifact / conflict | `roughset/pipeline.py` |
| Batch experiment | `roughset/batch.py` |
| Variation Ratio | `roughset/established_metrics.py` |
| Target backtrace | `tools/target_case_backtrace.py` |
| Reference policy implementations | `reference/policies/` |

## Literature boundary

The four baseline mechanisms and established metrics remain literature-grounded.

The population variants, `P_d = U_d/T_d`, and redundancy-asymmetry hypothesis are project-defined and must be presented as experimental contributions rather than inherited methods.
