# Target Case Backtrace Analysis — 2026-10-23

## Scope

This follow-up uses the same frozen 80/20 holdout protocol and six Prediction Policies, then selects five representative holdout conflict cases from each of the three UCI datasets for mechanism-level backtrace.

A `target case` here means one selected holdout test object, not a new decision column.

For every candidate decision `d` in a conflict case:

- `T_d` = total support occurrences across matching same-decision rules.
- `U_d` = unique supporting training objects after support-set union.
- `P_d = U_d / T_d` = population nonredundancy ratio.
- Standard score = `T_d`.
- Population Standard score = `U_d`.
- Global Strength score = `U_d / N_d`.
- Population Global score = `(U_d / N_d) * P_d`.

The automated backtrace workflow also exports every matching rule, rule support size, provenance client(s), and support-object IDs.

## Main mechanism finding

Across all three datasets and C={2,3,4,5}, there are 908 prediction-time conflict case occurrences (the same holdout row may appear once for each client-count configuration). Population correction changed the selected decision in 43 method/case comparisons. In all 43 changed comparisons, the new winner had lower support redundancy than the old winner.

Therefore the new methods are behaving as designed: they systematically reduce the influence of repeated support occurrences. Whether that change is beneficial depends on which decision carries the redundancy.

- If the wrong baseline winner has high redundancy and the true decision has more independent support, population correction can correct the prediction.
- If the true baseline winner itself is supported by multiple overlapping but valid rules, the same penalty can over-correct and produce a wrong prediction.
- If the true class has no matching rule at all, population reweighting cannot recover it; it can only reorder the wrong candidate decisions.

### Changed-case counts

| Dataset | Method | Conflict cases across C | Corrected | Harmed | Changed, same correctness | Unchanged |
|---|---|---:|---:|---:|---:|---:|
| Balance Scale | Population Standard | 266 | 3 | 1 | 1 | 261 |
| Balance Scale | Population Global | 266 | 3 | 3 | 3 | 257 |
| Car Evaluation | Population Standard | 598 | 2 | 4 | 0 | 592 |
| Car Evaluation | Population Global | 598 | 7 | 6 | 1 | 584 |
| Hayes-Roth | Population Standard | 44 | 1 | 4 | 0 | 39 |
| Hayes-Roth | Population Global | 44 | 0 | 4 | 0 | 40 |

The small number of changed cases is itself informative: Population correction does not alter matching or rule induction; it only changes a final decision when redundancy adjustment is large enough to reverse the competing score ranking.

## Balance Scale — five representative targets

### Target 1 — C=2, row_id=54, true=R
Factors: right_distance=5, right_weight=1, left_distance=3, left_weight=1.

Standard: L=19, R=18, so Standard predicts L. L contains three redundant support occurrences, giving U_L=16, whereas R has U_R=18 and no redundancy. Population Standard therefore changes L -> R and corrects the case.

### Target 2 — C=2, row_id=102, true=L
Factors: right_distance=3, right_weight=1, left_distance=5, left_weight=1.

Global Strength: R=19/230=0.082609 and L=17/230=0.073913, so GS predicts R. R has P_R=19/23=0.826087. Population Global reduces R to 0.068242 while L remains 0.073913, changing R -> L and correcting the case.

### Target 3 — C=3, row_id=77, true=L
Factors: right_distance=3, right_weight=1, left_distance=4, left_weight=1.

Standard correctly prefers L: 21>19. However L has four redundant support occurrences, so U_L=17 while U_R=19. Population Standard changes L -> R and harms the case. This demonstrates that repeated support is not necessarily invalid evidence.

### Target 4 — C=4, row_id=329, true=L
Factors: right_distance=5, right_weight=1, left_distance=4, left_weight=3.

GS correctly gives L=0.073913 over R=0.069565. L has P_L=17/21=0.809524, so Population Global reduces L to 0.059834; R remains 0.069565 and becomes the wrong winner.

### Target 5 — C=4, row_id=78, true=B
Factors: right_distance=4, right_weight=1, left_distance=4, left_weight=1.

No matching rule predicts B. PG changes the winner from R to L after penalizing R's redundancy, but both answers remain wrong. This is a rule-coverage failure rather than a weighting failure.

## Car Evaluation — five representative targets

### Target 1 — C=2, row_id=1637, true=vgood
Factors: buying=low, maint=low, doors=2, persons=4, lug_boot=big, safety=high.

Standard has a 9-vs-9 contest between good and vgood and resolves to good. The good rules contain two duplicated support occurrences (U_good=7), while vgood keeps U_vgood=9. Population Standard changes the result to vgood and corrects the case.

### Target 2 — C=5, row_id=1231, true=good
Factors: buying=med, maint=low, doors=3, persons=4, lug_boot=big, safety=med.

GS ranks acc=0.114007 above good=0.090909. The acc support has 30% redundancy (T=50, U=35, P=0.70), reducing its Population Global score to 0.079805. Good remains 0.090909, so PG corrects acc -> good.

### Target 3 — C=5, row_id=938, true=acc
Factors: buying=med, maint=vhigh, doors=4, persons=more, lug_boot=small, safety=high.

Standard correctly ranks acc=38 over unacc=27. Acc has T=38 but U=25, whereas unacc has T=U=27. Population Standard therefore changes acc -> unacc and harms the case.

### Target 4 — C=5, row_id=821, true=acc
Factors: buying=high, maint=low, doors=4, persons=4, lug_boot=small, safety=high.

GS correctly ranks acc=0.127036 over unacc=0.109504. Acc is highly redundant (T=67, U=39, P=0.58209), so PG reduces it to 0.073946, while unacc stays at 0.109504. The result flips to the wrong unacc class.

### Target 5 — C=3, row_id=1253, true=good
Factors: buying=med, maint=low, doors=4, persons=4, lug_boot=small, safety=high.

The matching rules only nominate acc and vgood; no good rule matches. PG changes acc -> vgood, but both are wrong. Again this identifies a coverage/induction limitation that weighting cannot repair.

## Hayes-Roth — five representative targets

### Target 1 — C=5, row_id=116, true=3
Factors: hobby=2, age=3, educational_level=4, marital_status=1.

Standard predicts class 1 because 10>9. Class 1 reduces to U=7 after deduplication, while true class 3 remains U=9. Population Standard changes 1 -> 3 and corrects the case.

### Target 2 — C=3, row_id=114, true=1
Factors: hobby=3, age=1, educational_level=1, marital_status=2.

Standard correctly has class1=15 over class2=9. Class1 contains seven redundant occurrences and drops to U=8. Class2 remains U=9, so Population Standard over-corrects to class2.

### Target 3 — C=5, row_id=125, true=1
Factors: hobby=2, age=1, educational_level=1, marital_status=2.

GS correctly has class1=0.341463 over class2=0.219512. For class1, T=23, U=14 and P=0.608696; PG reduces it to 0.207847. Class2 remains 0.219512, so PG changes to the wrong class2.

### Target 4 — C=4, row_id=53, true=1
Factors: hobby=3, age=1, educational_level=2, marital_status=1.

Both competing decisions are redundant. Population correction changes the scores but does not reverse the existing wrong class2 winner. This is a high-redundancy but unchanged example.

### Target 5 — C=5, row_id=82, true=1
Factors: hobby=1, age=1, educational_level=3, marital_status=2.

Class2 has 22.2% redundancy and PG reduces its score from 0.170732 to 0.132791. However true class1 remains only 0.121951, so the ranking does not change. This is a case where the correction acts but is not strong enough to reverse the decision.

## Relationship to aggregate performance

The case-level backtrace explains the aggregate BA changes very closely. Descriptively across the 12 dataset×C blocks:

- For Population Standard, the Spearman association between `(corrected cases - harmed cases)` and BA change is approximately 0.945.
- For Population Global, the corresponding Spearman association is approximately 0.893.

These values are descriptive only (n=12 blocks for each method), not inferential evidence.

A particularly useful exception is Car C=5 Population Global: four conflict cases are corrected and four are harmed, so total accuracy does not change, yet Balanced Accuracy improves. That is consistent with the earlier observation that population correction can redistribute errors among classes without increasing the total number of correct predictions.

## Research implication

The next explanatory variable should not be only conflict rate. The stronger candidate is **support redundancy asymmetry** between competing decisions.

A useful case-level quantity for future repeated experiments is:

`A(x) = redundancy(wrong/competing decision) - redundancy(true decision)`

or an equivalent signed difference in `P_d`.

The working hypothesis is:

> Population correction is beneficial when the baseline wrong winner is disproportionately supported by repeated evidence, but harmful when the true decision itself carries the larger redundancy burden.

This is currently a mechanism hypothesis supported by seed=42 single-split backtrace evidence, not a causal or generalizable conclusion. Repeated matched splits/seeds are required before inferential claims.

## Reproducibility

Automated backtrace implementation:

- `tools/target_case_backtrace.py`
- `.github/workflows/target-case-backtrace.yml`

Successful workflow run: `39912420604`.

Backtrace source head: `a2e5be8750a1a952281ccdded7ad2a664abf13e9`.

The workflow artifact contains:

- `ALL_CONFLICT_CASES.csv`
- `ALL_CONFLICT_DECISION_SCORES.csv`
- `ALL_CONFLICT_MATCHED_RULES.csv`
- `SELECTED_5_TARGET_CASES_PER_DATASET.csv`
- `SELECTED_TARGET_DECISION_SCORES.csv`
- `SELECTED_TARGET_RULE_BACKTRACE.csv`
- `TARGET_BACKTRACE_README.md`
- `TARGET_BACKTRACE_MANIFEST.json`
