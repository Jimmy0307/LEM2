# Federated LEM2 — Final Research Conclusion (2026-10-23)

> Branch: `research/conflict-client-sweep-20261020`  
> Frozen production baseline: `main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`  
> Scope: six-policy experiment + population correction + 15 target-case backtrace + all-conflict backtrace.

---

## 1. Research question

This project does **not** reinvent LEM2. The current research question is:

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

The focus is on what happens after local LEM2 rules are aggregated into a global federated ruleset.

---

## 2. Experimental protocol

All three UCI datasets use the same strict holdout protocol:

\[
80\%\ Training + 20\%\ Holdout
\]

The final 20% holdout does **not** participate in reduct construction, preprocessing/discretisation fit, local LEM2 induction, federated rule aggregation, support-set construction, or voting-weight construction. It is used only for final prediction and evaluation.

| Dataset | Rows | Condition attributes | Total data columns | Classes | Train | Test |
|---|---:|---:|---:|---:|---:|---:|
| Hayes-Roth | 132 | 4 | 5 | 3 | 106 | 26 |
| Car Evaluation | 1,728 | 6 | 7 | 4 | 1,382 | 346 |
| Balance Scale | 625 | 4 | 5 | 3 | 499 | 126 |

Client count:

\[
C\in\{2,3,4,5\}
\]

Six prediction methods are evaluated on the same learned artifact:

1. `FIRST_MATCH`
2. `SIMPLE_VOTING`
3. `STANDARD_VOTING`
4. `GLOBAL_STRENGTH`
5. `POPULATION_STANDARD` — project-defined experimental variant
6. `POPULATION_GLOBAL` — project-defined experimental variant

Thus the frozen experiment contains:

\[
3\times4\times6=72
\]

dataset-client-policy result rows.

---

## 3. UNION does not resolve rule conflict

Federated aggregation is:

\[
R_G=\bigcup_cR_c
\]

Rule identity is antecedent + decision. Therefore `X -> A` and `X -> B` are distinct rules and both survive UNION.

For a test case \(x\):

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

The main prediction-time conflict set is:

\[
\boxed{
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
}
\]

UNION is the aggregation layer. Conflict handling happens only when a test object matches rules that imply competing decisions.

---

## 4. Four established baselines use four kinds of evidence

\[
\boxed{
Order\rightarrow Rule\ Count\rightarrow Rule\ Support\ Sum\rightarrow Unique\ Class\ Coverage
}
\]

- `FIRST_MATCH`: ordered inference.
- `SIMPLE_VOTING`: one matching rule = one vote.
- `STANDARD_VOTING`: sum of positive support attached to matching rules.
- `GLOBAL_STRENGTH`: unique supporting population normalized by class size.

No single baseline is the universal winner across all datasets and client counts.

---

## 5. Why population correction was introduced

Assume two matching rules for decision \(A\):

```text
r1 -> A : {u1,u2,u3}
r2 -> A : {u2,u3,u4}
```

Standard Voting counts:

\[
3+3=6
\]

but there are only four unique supporting training objects.

Define:

\[
T_d=\sum_{r\in M_d(x)}|S_G(r)|
\]

\[
U_d=\left|\bigcup_{r\in M_d(x)}S_G(r)\right|
\]

\[
\boxed{P_d=\frac{U_d}{T_d}}
\]

For the example:

\[
T_A=6,\qquad U_A=4,\qquad P_A=\frac{4}{6}=\frac23
\]

`P_d` is the nonredundant proportion of raw support occurrences.

---

## 6. Two experimental population variants

These are **project-defined experimental designs**. They must not be cited as if they were established literature methods.

### POPULATION_STANDARD

\[
\boxed{S_{PS}(d|x)=U_d}
\]

Operationally, raw support occurrences are replaced by the unique supporting population.

### POPULATION_GLOBAL

Established GlobalStrength:

\[
GS(d|x)=\frac{U_d}{N_d}
\]

Experimental correction:

\[
\boxed{
S_{PG}(d|x)=\frac{U_d}{N_d}\frac{U_d}{T_d}=\frac{U_d^2}{N_dT_d}
}
\]

This adds a redundancy penalty on top of unique class coverage.

---

## 7. Six-policy result: no universal winner

The population variants improve some configurations, tie others, and hurt others.

### Car Evaluation

- C=2: GLOBAL / POPULATION_GLOBAL = 0.717396
- C=3: **POPULATION_GLOBAL = 0.800529**
- C=4: GLOBAL_STRENGTH = 0.683169
- C=5: **POPULATION_GLOBAL = 0.633821**

### Balance Scale

- C=2: **POPULATION_STANDARD = 0.563218**
- C=3: STANDARD / POPULATION_STANDARD = 0.586207
- C=4: STANDARD / POPULATION_STANDARD = 0.597701
- C=5: GLOBAL / POPULATION_GLOBAL = 0.590805

### Hayes-Roth

FIRST_MATCH remains strongest in most settings. Population Global can substantially over-correct:

\[
C=5:\quad GS=0.733333\rightarrow PG=0.633333
\]

Therefore the safe conclusion is:

\[
\boxed{Population\ correction\neq universal\ accuracy\ improvement}
\]

It is a conditional redundancy correction.

---

## 8. Target-case backtrace

To identify the mechanism, three datasets were each assigned five representative holdout target cases:

\[
3\times5=15
\]

Each case was traced through:

\[
Factors\rightarrow Matching\ Rules\rightarrow Candidate\ Decisions\rightarrow T_d\rightarrow U_d\rightarrow P_d\rightarrow Six\ Predictions
\]

The analysis was then extended to **all prediction-time conflict occurrences** across C=2,3,4,5:

\[
\boxed{908\ conflict\ occurrences}
\]

---

## 9. What the backtrace shows

### Successful correction

When an incorrect competing decision has inflated support because the same training population is repeated across multiple rules, population correction can remove the inflation and recover the true decision.

### Over-correction

Repeated support is not necessarily wrong evidence. If the true decision is legitimately supported by several overlapping rules, the population penalty may suppress useful evidence and flip a correct prediction into an incorrect competitor.

Therefore:

\[
\boxed{Redundancy\neq Noise}
\]

---

## 10. Coverage error is different from conflict-ranking error

Some test cases have a true class that does not appear among matching-rule decisions:

\[
D(x)\notin\{d_r:r\in M(x)\}
\]

In this case no scoring method can recover the true class. This is a candidate-generation / rule-coverage error, not a conflict-ranking problem.

The analysis must therefore separate:

1. **Coverage / induction error** — true class absent from candidate set.
2. **Conflict ranking error** — true class present, but a competing decision receives the larger score.

This also motivates retaining both Overall Coverage and Target Coverage in the evaluation contract.

---

## 11. All-conflict mechanism result

Across all 908 conflict occurrences:

### Population Standard

- Corrected: 6
- Harmed: 9
- Changed but same correctness: 1
- Unchanged: 892

### Population Global

- Corrected: 10
- Harmed: 13
- Changed but same correctness: 4
- Unchanged: 881

Total winner changes:

\[
16+27=43
\]

The key mechanism check is:

\[
\boxed{43/43}
\]

All changed winners move toward a decision with **lower support redundancy**.

This confirms that the implementation behaves as designed: population correction reduces the influence of repeated support. However, this does **not** imply that the lower-redundancy decision is always the true class.

---

## 12. Redundancy Asymmetry is the next mechanism variable

The important quantity is no longer only `P_d`. The next analysis should compare redundancy between the true decision and its strongest competitor.

A useful conceptual quantity is:

\[
A(x)=Redundancy_{competitor}-Redundancy_{true}
\]

Interpretation:

- \(A(x)>0\): competing decision is more redundant; population correction is more likely to help.
- \(A(x)<0\): true decision itself carries more repeated support; population correction is more likely to over-correct.

This is the current mechanism hypothesis to test with repeated seeds / splits.

---

## 13. Updated research chain

\[
\boxed{
Client\ Fragmentation
\rightarrow Local\ Rule\ Structure
\rightarrow Global\ Rule\ Overlap
\rightarrow Prediction\text{-}time\ Conflict
\rightarrow Support\ Redundancy
\rightarrow Redundancy\ Asymmetry
\rightarrow Prediction\ Policy
\rightarrow Performance
}
\]

This is stronger and more precise than the earlier \(C\rightarrow Conflict\rightarrow Policy\rightarrow Performance\) framing because it introduces a mechanism explaining why the same population correction can help one case and hurt another.

---

## 14. Safe conclusions

The current evidence supports the following statements:

1. Federated UNION aggregates local rules but does not resolve prediction-time conflict.
2. Client fragmentation changes local rule structure and is associated with changes in global conflict workload.
3. FIRST_MATCH, SIMPLE, STANDARD, and GLOBAL use different evidence semantics; there is no universal winner.
4. STANDARD can repeatedly count the same supporting object across multiple matching rules.
5. Population correction removes or penalizes repeated support and behaves consistently with that design.
6. Population correction is conditional: it can correct inflated wrong evidence or over-correct valid repeated evidence.
7. The mechanism is concentrated in a small number of borderline conflict cases rather than all conflict cases.
8. In all 43 observed winner changes, the new winner has lower support redundancy.
9. Coverage/induction errors must be separated from conflict-ranking errors.
10. The next research variable is redundancy asymmetry between the true decision and the competing decision.

The current single-seed 80/20 evidence is descriptive and mechanism-oriented. It is **not yet sufficient** for strong statistical or causal claims.

---

## 15. Next experiment

Do not add a seventh voting method.

Instead:

1. run repeated matched seeds / splits;
2. export per-conflict-case true and competitor redundancy;
3. compute redundancy asymmetry, score margin, coverage state, and corrected/harmed labels;
4. test whether asymmetry consistently predicts population-method success/failure;
5. use paired Wilcoxon for paired two-method comparisons;
6. use Friedman + multiplicity-controlled post-hoc analysis across the six methods;
7. avoid treating individual test rows as independent algorithm-level replicates.

---

## 16. Canonical evidence files

- `FULL_SIX_POLICY_RESULTS_20261023.md`
- `TARGET_CASE_BACKTRACE_ANALYSIS_20261023.md`
- `FINAL_RESEARCH_CONCLUSION_20261023.md`
- `evidence/20261023/SIX_POLICY_RESULTS_COMPACT.csv`
- `evidence/20261023/SELECTED_15_TARGET_CASES.csv`
- `evidence/20261023/SELECTED_TARGET_DECISION_SCORES.csv`
- `evidence/20261023/SELECTED_TARGET_RULE_BACKTRACE.csv`
- `evidence/20261023/ALL_CONFLICT_CASES.csv`
- `evidence/20261023/ALL_CONFLICT_DECISION_SCORES.csv`
- `presentation/Federated_LEM2_Final_Research_Update_20261023.pptx`
- `presentation/Federated_LEM2_Final_Research_Update_20261023.pdf`

---

## 17. Literature boundary

Established literature anchors remain:

- Woźniak et al. (2026): Federated LEM2 source architecture and FIRST_MATCH.
- Lazo-Cortés et al. (2020): Simple / Standard voting principle.
- Bazan et al. (2000): GlobalStrength.
- Lindgren (2004); Lindgren & Boström (2002): rule conflict.
- Brodersen et al. (2010): Balanced Accuracy.
- Sokolova & Lapalme (2009): classification performance metrics.
- Gal (2016): Variation Ratio.
- Demšar (2006): classifier comparison statistics.

The following remain **project-defined experimental concepts**:

```text
POPULATION_STANDARD
POPULATION_GLOBAL
P_d = U_d / T_d
Redundancy Asymmetry A(x)
```

They must not be presented as previously established Federated LEM2 methods.
