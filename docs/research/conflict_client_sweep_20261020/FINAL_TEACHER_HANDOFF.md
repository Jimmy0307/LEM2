# Federated LEM2 — Final Teacher Handoff

> Last consolidated update: 2026-10-23  
> Frozen production baseline: `main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`  
> Research branch: `research/conflict-client-sweep-20261020`  
> PR #5: Draft / Open / Not merged

## What the professor asked — now answered directly

This handoff is organized around the professor's previous questions rather than around later exploratory findings:

1. How large are the three datasets, including row count and total headers?
2. Is the 20% prediction set completely excluded from model construction?
3. What are Accuracy, Recall, F1, and Balanced Accuracy for all six methods on the same 20% holdout?
4. What are Overall Coverage and target-level coverage?
5. Why can Standard Voting's support sum double-count the same population, and how does the modified method change the final winner?
6. How does the population correction modify GlobalStrength?
7. For five selected targets in each dataset, what factors/rules/support structures explain corrected, harmed, and unrecoverable cases?

The code now emits canonical teacher-facing evidence tables for all seven questions.

## Experiment contract

- datasets: Hayes-Roth, Car Evaluation, Balance Scale;
- holdout: 80% train / 20% final prediction set;
- the final 20% does **not** participate in reduct, LEM2 induction, client aggregation, support-set construction, class-size construction, or voting-weight construction;
- client counts: `C = 2, 3, 4, 5`;
- six methods on the same learned artifact:
  - `FIRST_MATCH`
  - `SIMPLE_VOTING`
  - `STANDARD_VOTING`
  - `GLOBAL_STRENGTH`
  - `POPULATION_STANDARD`
  - `POPULATION_GLOBAL`
- total six-policy result rows: 72.

## Dataset metadata

| Dataset | Rows | Total headers | Condition attrs | Decision | Classes | Train | Test |
|---|---:|---:|---:|---|---:|---:|---:|
| Hayes-Roth | 132 | 5 | 4 | class | 3 | 106 | 26 |
| Car Evaluation | 1,728 | 7 | 6 | class | 4 | 1,382 | 346 |
| Balance Scale | 625 | 5 | 4 | class | 3 | 499 | 126 |

Canonical source: `evidence/20261023/teacher/TEACHER_DATASET_METADATA.csv`.

## Prediction-time conflict

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
\]

UNION is aggregation only. It does not remove or resolve conflicting rules.

## Six prediction methods

The four established baselines use different evidence levels:

\[
Order\rightarrow Rule\ Count\rightarrow Support\ Sum\rightarrow Unique\ Class\ Coverage
\]

The two experimental population variants keep the same global rule artifact and change only conflict-ranking scores.

For candidate decision `d`:

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

### Population Standard

Original Standard ranks by support occurrences `T_d`. Population Standard ranks by unique supporting objects:

\[
S_{PS}(d|x)=U_d
\]

Thus duplicated appearances of the same training object are counted once; additional *unique* supporting objects are not treated as a penalty.

### Population Global

Original GlobalStrength is:

\[
GS(d|x)=\frac{U_d}{N_d}
\]

Population Global applies the same nonredundancy factor:

\[
S_{PG}(d|x)=\frac{U_d}{N_d}\frac{U_d}{T_d}=\frac{U_d^2}{N_dT_d}
\]

These two formulas are project-defined experimental variants; they are not attributed to Lazo-Cortés or Bazan as pre-existing methods.

## Final 20% evaluation

The final holdout reporting contract now includes:

```text
Accuracy
Recall (macro)
Macro-F1
Balanced Accuracy
Overall Coverage
Target Coverage by class / macro
Target Candidate Coverage by class / macro
```

In this multiclass implementation, macro Recall is numerically equal to Balanced Accuracy because both are the mean class-wise recall. They are retained as separate named outputs only to answer the requested reporting contract explicitly.

Canonical source: `evidence/20261023/teacher/TEACHER_SIX_POLICY_METRICS.csv`.

## Coverage now has three distinct meanings

### 1. Overall Coverage

\[
Coverage_{overall}=\frac{|\{x\in U_{test}:M(x)\neq\emptyset\}|}{|U_{test}|}
\]

### 2. Target Coverage

For true class `d`, asks whether **any** rule matches:

\[
Coverage_d=\frac{|\{x:y(x)=d,\ M(x)\neq\emptyset\}|}{|\{x:y(x)=d\}|}
\]

### 3. Target Candidate Coverage — added in this update

This stricter diagnostic asks whether the true class itself appears among matching-rule decisions:

\[
CandidateCoverage_d=\frac{|\{x:y(x)=d,\exists r\in M(x):d_r=d\}|}{|\{x:y(x)=d\}|}
\]

This separates **candidate-generation / rule-induction failure** from later **candidate-ranking / conflict-resolution failure**.

Examples from the refreshed holdout evidence:

- Balance C2: target-any-rule macro = 93.2%, but target-candidate macro = 57.5%.
- Balance class B: candidate coverage is 0% at C2 and C3, despite ordinary target coverage of 90% and 100%.
- Car class `good`: candidate coverage is only 57.1% at C2.

Canonical source: `evidence/20261023/teacher/TEACHER_COVERAGE_BY_CLASS.csv`.

## Six-policy result

There is no universal winner.

The complete 72-row table contains Accuracy, macro Recall / Balanced Accuracy, Macro-F1, Coverage, and conflict-subset metrics for every Dataset × C × Policy combination.

Population correction must therefore be framed as a **support-redundancy correction**, not as a universal accuracy improvement.

## Target 1–5 backtrace

Three datasets × five selected 20% holdout targets are traced through:

```text
factor values
→ matching rules
→ candidate decisions
→ T_d / U_d / P_d
→ six predictions
→ baseline winner
→ population winner
→ corrected / harmed / unchanged
→ true-candidate present / absent
```

Canonical sources:

- `evidence/20261023/teacher/TEACHER_TARGET_1_TO_5.csv`
- `evidence/20261023/teacher/TEACHER_STANDARD_TRANSITIONS.csv`
- `evidence/20261023/teacher/TEACHER_GLOBAL_TRANSITIONS.csv`

## All conflict evidence

Across `C=2..5`, the three datasets contain:

\[
908\ conflict\ occurrences
\]

Population Standard changes 16 winners:

- corrected: 6
- harmed: 9
- changed but same correctness: 1

Population Global changes 27 winners:

- corrected: 10
- harmed: 13
- changed but same correctness: 4

Total:

\[
43\ population\text{-}induced\ winner\ changes
\]

Mechanism check:

\[
\boxed{43/43}
\]

Every changed winner moves to a lower-redundancy decision. This proves the implementation performs the intended redundancy correction. It does **not** prove that the lower-redundancy decision is always the true class.

There are also 45 prediction-time conflict occurrences in which the true class is absent from the candidate-decision set. Those cases are not solvable by changing the voting score alone.

## Error decomposition

### 1. Corrected conflict

The wrong competitor is inflated by repeated support; deduplication or the population penalty recovers the true decision.

### 2. Harmed / over-correction

The true decision itself is supported by overlapping but valid rules; population correction suppresses useful repeated evidence.

### 3. Coverage / induction failure

The true class is absent from the matching-rule candidate set. No prediction policy can recover it.

Canonical source: `evidence/20261023/teacher/TEACHER_ERROR_DECOMPOSITION.csv`.

## Redundancy Asymmetry — now formalized in code

Define decision redundancy as:

\[
R_d=1-P_d
\]

For corrected or harmed transitions:

\[
A(x)=R_{competitor}-R_{true}
\]

The implementation now exports this value per conflict transition.

- corrected PS cases: `A(x)` is positive in all 6 current cases;
- harmed PS cases: `A(x)` is negative in all 9 current cases;
- corrected PG cases: `A(x)` is positive in all 10 current cases;
- harmed PG cases: `A(x)` is negative in all 13 current cases.

This is a mechanism-consistency diagnostic. Because the competitor role is defined from the observed transition, its sign in changed cases is **not** an independent predictive test. The next research step is to test whether pre-resolution support structure can predict corrected/harmed behavior across repeated matched splits.

Canonical source: `evidence/20261023/teacher/TEACHER_REDUNDANCY_ASYMMETRY.csv`.

## Code map

Runtime:

```text
roughset/evaluation.py
roughset/pipeline.py
roughset/batch.py
roughset/app.py
```

Research evidence helpers:

```text
roughset/research_evidence.py
```

Backtrace / teacher evidence generator:

```text
tools/target_case_backtrace.py
.github/workflows/target-case-backtrace.yml
```

Separated teaching/reference policies:

```text
reference/policies/
├─ first_match.py
├─ simple_voting.py
├─ standard_voting.py
├─ global_strength.py
├─ population_standard.py
└─ population_global.py
```

## Teacher-facing evidence files

```text
evidence/20261023/teacher/
├─ TEACHER_DATASET_METADATA.csv
├─ TEACHER_SIX_POLICY_METRICS.csv
├─ TEACHER_COVERAGE_BY_CLASS.csv
├─ TEACHER_TARGET_1_TO_5.csv
├─ TEACHER_STANDARD_TRANSITIONS.csv
├─ TEACHER_GLOBAL_TRANSITIONS.csv
├─ TEACHER_ERROR_DECOMPOSITION.csv
├─ TEACHER_REDUNDANCY_ASYMMETRY.csv
├─ TARGET_BACKTRACE_MANIFEST.json
└─ PROVENANCE.txt
```

## Verification

The teacher-evidence implementation followed a real TDD RED → GREEN cycle:

- RED: CI failed because `target_candidate_coverage_by_class` and `roughset.research_evidence` did not exist.
- GREEN: implementation added candidate coverage, redundancy evidence, transition exports, and teacher-facing tables.
- compile: PASS.
- pytest: **118 passed in 10.32s**.
- refreshed target-backtrace workflow: SUCCESS.

Frozen production `main` was not changed.

## Safe research claim

> Federated rule aggregation can produce overlapping rule supports in which the same training population contributes repeatedly to competing decision scores. Population-based correction reduces this duplicated influence, but its effect is conditional: it helps when redundancy inflates an incorrect competitor and can over-correct when the true decision itself is supported by overlapping but valid rules. A separate target-candidate coverage diagnostic is required because some errors occur before voting: the true class is never generated by any matching rule.

## Next step

Do not add a seventh prediction method.

Run repeated matched seeds/splits, export pre-resolution candidate coverage and support structure per case, and test the relationship between support redundancy, score margins, corrected/harmed transitions, and final performance using matched statistical blocks.

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
Target Candidate Coverage diagnostic
Redundancy Asymmetry diagnostic
```
