# LEM2 / Federated — Evidence Completion and Decision-Mechanism Audit

## Frozen model benchmark (PASS)
- 3 datasets × 42 seeds × 2 data-split modes × 5 topologies × 7 decision modes = **8,820 rows**.
- Holdout 80/20 and Full Data (resubstitution) are deliberately different evaluation estimands; do not compare either as equal out-of-sample generalization.
- Dataset source and split/partition algorithm were pinned and Seed 42 cross-checked before the completed 42-seed sweep. [Passing Actions run](https://github.com/Jimmy0307/LEM2/actions/runs/42409836379).

## Decision mechanisms — code-verified mathematical distinction
For evaluation object `x`, take all matching rules `M(x)`, their decisions `Cand(x)`, and for each class `d` compute:
- `T_d = Σ_{r∈M(x), decision(r)=d} |S(r)|`: sum of rule support set cardinalities; note `STANDARD_VOTING` uses `fit_rule_weights` (antecedent match count) and **is not exactly this T** when rules have training false positives. Thus the object-audit exports both `STANDARD` and `T` separately.
- `U_d = |∪_{r∈M(x), decision(r)=d} S(r)|`: distinct training objects supporting the class.
- `N_d`: class size in training objects.
- `P_d=U_d/T_d`: nonredundancy ratio (T>0; zero otherwise).
- `GS_d=U_d/N_d`, `PS_d=U_d`, `PG_d=U_d²/(N_d T_d)` with zero-denominator guards.
- SIMPLE uses vote count, FIRST uses first matching rule, STANDARD uses separate antecedent weights.
- Tie handling follows repository code: default class if among max-scoring classes; otherwise lexicographic order.
- If no rule matches, the default class can still be correct. Separate `NO_MATCH` from `TRUE_MISSING` and `WINNER_SELECTION_ERROR`.

> Note the apparent distinction between Standard's antecedent count and T's decision-consistent supports; treat them as different, not interchangeable. See `roughset/evaluation.py`.

## 42-seed paired comparisons — 80/20, federated C2–C5, 3 datasets equally weighted
Mean paired changes (method A minus method B), in percentage points:
| Comparison | Accuracy | Balanced Accuracy | Macro-F1 |
|---|---:|---:|---:|
| GS − STD | +0.403 | +5.160 | +2.460 |
| GS − SIMPLE | +5.453 | +9.618 | +7.530 |
| GS − PG | +1.004 | +0.736 | +0.915 |

- GS minus STD Balanced Accuracy is positive for **42 of 42 seeds**, with Holm-adjusted Wilcoxon p<0.001 (5 prespecified contrasts per metric).
- GS minus STD Accuracy is only +0.403 percentage points, and the Holm-adjusted Wilcoxon p is **approximately 0.156**, not statistically significant at 0.05.
- Pairing is by seed after averaging the three datasets and C2–C5; repeated splits over the same three datasets are not 42 independent datasets.
- A percentile seed-resampling interval measures split sensitivity for this fixed dataset panel; not a universal confidence interval.

## Grounded object example (CI audited, seed 1)
Car Evaluation, seed 1, holdout 80/20, Federated C5, original row ID 239:
- True label: acc; candidates: acc and unacc; 3 matched rules.
- STANDARD_VOTING predicts unacc (wrong) because antecedent weights are 16 vs 25.
- GLOBAL_STRENGTH predicts acc (correct): U/N is 13/307=0.042345... vs 25/968=0.025826...
- Population Standard predicts unacc; Population Global predicts acc.
- Evidence is in the per-seed `OBJECT_CASES_seed01.csv`, `CLASS_COVERAGE_seed01.csv`, `RULE_INVENTORY_seed01.csv` artifact of [Object Evidence Audit workflow](https://github.com/Jimmy0307/LEM2/actions/workflows/object-evidence-audit.yml).

## Evidence status and caveats
- The all-42-seed object-level and per-class audit has its **own** gated CI and must not be called complete before all 42 jobs pass.
- A single-client vs union comparison is informative, but not full causal identification because rule learning is coupled to client sample assignment.
- No non-IID experiments, LERS original classification baseline, or DRSA reduct result is included in the 8,820-row benchmark.
- FULL_DATA contains resubstitution results, not independent held-out assessment.
- Public datasets include only 3 tasks, two deterministic enumerations and one small/noisy dataset; external validity remains limited.
- The earlier factor registry's statement “seed 7–41 in progress” is obsolete: the frozen 42-seed main benchmark is already completed. Object audit is a separate job.

## Acceptance conditions for object evidence
1. For each seed, each of the 30 model configurations reproduces exactly the canonical 7 modes and their 8,820 summary metrics within 1e-10.
2. Every evaluation row has an original row ID, source features, transformed features, list of matching rule indices, candidate decisions, decision score detail, six policy predictions, and error category.
3. Per-target-class total, coverage, candidate coverage, conflict, six-strategy recall and selection errors reconcile with the object audit.
4. Preserve complete rule inventories and client provenance, and publish compact class-level summaries; keep high-volume object/rule artifacts as CI evidence with explicit retention limits.
