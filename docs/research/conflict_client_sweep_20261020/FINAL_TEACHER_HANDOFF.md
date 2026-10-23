# Federated LEM2 — Final Teacher Handoff

> Last consolidated update: 2026-10-23  
> Frozen production baseline: `main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`  
> Research branch: `research/conflict-client-sweep-20261020`  
> PR #5: Draft / Open / Not merged

## Meeting-ready summary

The project now contains four established prediction baselines plus two project-defined population variants. All six are evaluated on the same frozen Federated LEM2 artifact under a strict 80/20 holdout protocol.

The updated research chain is:

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

The key new result is not that a population method is always better. The key result is that support redundancy explains a subset of conflict-resolution changes, and the sign of the effect depends on whether redundancy is concentrated in the wrong competitor or in the true decision.

## Experiment contract

- datasets: Hayes-Roth, Car Evaluation, Balance Scale;
- holdout: 80% train / 20% final prediction set;
- the 20% does **not** participate in reduct, LEM2, aggregation, support-set construction, or weight construction;
- client counts: C = 2, 3, 4, 5;
- six methods:
  - FIRST_MATCH
  - SIMPLE_VOTING
  - STANDARD_VOTING
  - GLOBAL_STRENGTH
  - POPULATION_STANDARD
  - POPULATION_GLOBAL
- total six-policy result rows: 72.

## Dataset metadata

| Dataset | Rows | Condition attrs | Data columns | Classes | Train | Test |
|---|---:|---:|---:|---:|---:|---:|
| Hayes-Roth | 132 | 4 | 5 | 3 | 106 | 26 |
| Car Evaluation | 1,728 | 6 | 7 | 4 | 1,382 | 346 |
| Balance Scale | 625 | 4 | 5 | 3 | 499 | 126 |

## Population quantities

For candidate decision d:

\[
T_d=\sum_{r\in M_d(x)}|S_G(r)|
\]

\[
U_d=\left|\bigcup_{r\in M_d(x)}S_G(r)\right|
\]

\[
P_d=\frac{U_d}{T_d}
\]

Meeting example:

```text
r1 -> A : {u1,u2,u3}
r2 -> A : {u2,u3,u4}

T_A = 6
U_A = 4
P_A = 4/6 = 2/3
```

Population Standard:

\[
S_{PS}(d|x)=U_d
\]

Population Global:

\[
S_{PG}(d|x)=\frac{U_d}{N_d}\frac{U_d}{T_d}
\]

These two formulas are project-defined experimental variants.

## Prediction-time conflict

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
\]

UNION is aggregation only. It does not remove or resolve conflicting rules.

## Final 20% evaluation

The final holdout reporting contract includes:

```text
Accuracy
Recall (macro)
Macro-F1
Balanced Accuracy
Overall Coverage
Target Coverage by class
Target Coverage macro
```

Target Coverage answers whether the rule system covers true target-class examples. Recall answers whether those examples are finally classified correctly.

## Six-policy result

There is no universal winner.

- Car: Population Global wins at C3 and C5.
- Balance: Population Standard wins or ties in C2-C4; Global / Population Global tie at C5.
- Hayes: FIRST_MATCH remains strongest in most configurations; population penalties can over-correct.

Therefore population correction must be framed as a redundancy correction, not as a universal accuracy improvement.

## Backtrace evidence

Three datasets × five target cases were traced through factors, rules, candidate decisions, T/U/P, and six predictions.

All conflict occurrences across C=2-5 were also exported:

\[
908\ conflict\ occurrences
\]

Population Standard changes 16 winners; Population Global changes 27 winners:

\[
43\ total\ winner\ changes
\]

Mechanism check:

\[
\boxed{43/43}
\]

Every changed winner moves to a lower-redundancy decision.

This proves the implementation is performing the intended redundancy correction. It does **not** prove that lower redundancy always corresponds to the true class.

## Three error modes

### 1. Corrected conflict

The wrong competitor is inflated by repeated support. Deduplication lowers its score and recovers the true decision.

### 2. Harmed / over-correction

The true decision itself is supported by several overlapping but valid rules. Population correction suppresses useful repeated evidence.

### 3. Coverage / induction failure

The true class has no matching rule at all. No prediction policy can recover it. This third case must not be blamed on voting.

## Current mechanism hypothesis

Define conceptually:

\[
A(x)=Redundancy_{competitor}-Redundancy_{true}
\]

- A(x) > 0: correction is more likely to help.
- A(x) < 0: correction is more likely to over-correct.

This is the next variable to test across repeated seeds/splits.

## Code map

Runtime:

```text
roughset/evaluation.py::predict_with_policy
roughset/pipeline.py
roughset/batch.py
roughset/app.py
```

Separated teaching/reference code:

```text
reference/policies/
├─ first_match.py
├─ simple_voting.py
├─ standard_voting.py
├─ global_strength.py
├─ population_standard.py
└─ population_global.py
```

Backtrace tool:

```text
tools/target_case_backtrace.py
.github/workflows/target-case-backtrace.yml
```

## Canonical files to open in a meeting

1. `FINAL_RESEARCH_CONCLUSION_20261023.md`
2. `FINAL_TEACHER_HANDOFF.md`
3. `FULL_SIX_POLICY_RESULTS_20261023.md`
4. `TARGET_CASE_BACKTRACE_ANALYSIS_20261023.md`
5. `POPULATION_EXPERIMENT_UPDATE_20261022.md`
6. `LITERATURE_REFERENCE_INDEX.md`
7. `presentation/Federated_LEM2_Final_Research_Update_20261023.pptx`

## Safe research claim

> Federated rule aggregation can produce overlapping rule supports in which the same training population contributes repeatedly to competing decision scores. Population-based correction reduces this duplicated influence, but its effect is conditional: it helps when redundancy inflates an incorrect competitor and can over-correct when the true decision itself is supported by overlapping but valid rules. The next research focus is therefore redundancy asymmetry rather than adding more voting variants.

## Next step

Do not add a seventh prediction method.

Run repeated matched seeds/splits, export per-case redundancy asymmetry, and then perform paired Wilcoxon / Friedman + post-hoc analyses.

## Literature boundary

Established:

- Woźniak et al. (2026): Federated LEM2 / FIRST_MATCH.
- Lazo-Cortés et al. (2020): Simple / Standard voting principle.
- Bazan et al. (2000): GlobalStrength.
- Lindgren (2004); Lindgren & Boström (2002): rule conflict.
- Brodersen et al. (2010): Balanced Accuracy.
- Sokolova & Lapalme (2009): classification metrics.
- Gal (2016): Variation Ratio.
- Demšar (2006): classifier comparison statistics.

Project-defined:

```text
POPULATION_STANDARD
POPULATION_GLOBAL
P_d = U_d / T_d
Redundancy Asymmetry
```
