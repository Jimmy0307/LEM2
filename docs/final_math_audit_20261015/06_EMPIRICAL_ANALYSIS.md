# 06 — Empirical analysis

Labels: **OBSERVED** = read directly from the post-audit tables (`05_UCI3_RESULTS.md`,
`outputs/final_math_audit_20261015/*.csv`); **INTERPRETATION** = a mechanism consistent with the
observations, not tested here; **NOT PROVEN** = something these data cannot establish.

Evidence base: 3 datasets × C ∈ {2, 3, 4, 5} × 1 holdout split × seed 42 = 12 structural
observations and 48 resolver observations. Nothing below is a universal or causal claim.

Research chain examined:
`client partition → reduct / rule structural heterogeneity → inference conflict → resolver quality → prediction performance`.

---

## A. Reducts

**OBSERVED.**
- The central reduct never shrinks: it is the full attribute set in all three datasets, with a
  single minimum candidate (Hayes-Roth 4/4 with `γ_C = 0.811`; Car 6/6, `γ_C = 1`; Balance 4/4,
  `γ_C = 1`).
- Local reducts shrink only in Hayes-Roth: at C = 4, Client_1 and Client_2 drop `hobby`
  (size 3); at C = 5, Client_2 drops `hobby`. Every other local reduct, in every dataset and C, is
  the full attribute set.
- RI: Hayes-Roth 0, 0, 0.167, 0.100 (C = 2..5, non-monotonic); Car 0 at every C; Balance 0 at
  every C.
- Mean local–central reduct Jaccard: Hayes-Roth 1, 1, 0.875, 0.95; Car and Balance 1 at every C.
- **RI = 0 with high rule heterogeneity and high conflict**: Car has RI = 0 at all C while
  `H_rule` = 0.859–0.931 and the pre-resolution conflict rate = 0.246–0.607; Balance has RI = 0 while
  `H_rule` = 0.911–0.967 and conflict = 0.373–0.659. Hayes-Roth C = 3 has RI = 0 and conflict 0.538.

**Statement supported by these runs.**
> Within these benchmark runs, reduct heterogeneity is not a necessary condition for rule
> heterogeneity or inference conflict.

**NOT PROVEN.** That reduct heterogeneity never matters, or that this holds for higher-dimensional
data, where minimum reducts are usually much smaller than `C` and have more room to differ.

**INTERPRETATION.** With 4–6 attributes and near-consistent tables, almost every attribute is
indispensable (removing any one loses positive-region objects), so minimum-cardinality reducts
have no room to vary. Reduct instability is then a weak signal of client heterogeneity on these
datasets.

## B. Rule heterogeneity

**OBSERVED.** `H_rule = 1 − mean pairwise full-rule Jaccard`, C = 2 → 5:

| Dataset | C=2 | C=3 | C=4 | C=5 | Shape | Conflict rate C=2 → 5 |
|---|---|---|---|---|---|---|
| Hayes-Roth | 0.867 | 0.747 | 0.750 | 0.773 | non-monotonic | 0.115, 0.538, 0.385, 0.654 (non-monotonic) |
| Car Evaluation | 0.859 | 0.898 | 0.907 | 0.931 | increasing | 0.246, 0.387, 0.488, 0.607 (increasing) |
| Balance Scale | 0.967 | 0.946 | 0.911 | 0.926 | non-monotonic, net decrease | 0.373, 0.492, 0.587, 0.659 (increasing) |

- Car: `H_rule` and conflict rise together. Balance: conflict rises while `H_rule` falls overall
  (per-dataset Spearman ρ = −0.8). Hayes-Roth: both non-monotonic, ρ = −0.4.
- Identical selected feature subsets still give very different rule systems: at Car C = 5 all five
  clients select all six attributes, yet the mean pairwise full-rule Jaccard is 0.069
  (`H_rule` = 0.931).

**Why identical reducts do not imply identical rules (definitional, not empirical).** LEM2 output
on client `c` depends on `U_c`, not only on the attribute set: (i) the objects present determine
the condition classes and therefore which ones are pure; (ii) the decision distribution in `U_c`
determines each lower approximation `B_d,c`; (iii) LEM2 picks attribute–value pairs by their
overlap with the still-uncovered part of `B_d,c` and their block sizes in `U_c`, so different
objects lead to different greedy choices and different minimal complexes. Two clients with the same
reduct can therefore induce disjoint rule sets.

**OBSERVED (supporting).** As C grows, clients hold fewer objects and induce shorter rules: mean
local rule length falls from 4.40 to 3.66 conditions (Car), 2.98 to 2.47 (Balance) and 2.24 to 1.84
(Hayes-Roth), against central rule lengths of 5.01, 3.32 and 2.53. Mean matching rules per test
object rises from 1.74 to 3.16 (Car), 2.43 to 3.74 (Balance) and 1.69 to 2.65 (Hayes-Roth).

**INTERPRETATION.** Shorter, more general local rules cover more of the attribute space, so more
global rules match each test object, and more of those carry different decisions. This tracks
conflict more closely than the set-identity measure `H_rule` does: `H_rule` counts whether whole
rules coincide, while conflict depends on how antecedents *overlap*. The Balance case (conflict
rising while `H_rule` falls) is consistent with that reading. **NOT PROVEN**: no intervention
separated rule length from client count here.

## C. Client count

**OBSERVED.**
- Coverage: Hayes-Roth 0.923, 1, 1, 1 (non-decreasing); Car 0.977, 0.983, 0.994, 1 (increasing);
  Balance 0.944, 0.984, 1, 0.992 (non-monotonic).
- Conflict rate: increasing in C for Car and Balance; **non-monotonic for Hayes-Roth**
  (0.115 → 0.538 → 0.385 → 0.654: it falls from C = 3 to C = 4).
- Resolver performance is not monotonic in C. Best federated BA per C: Hayes-Roth 0.767, 0.833,
  0.778, 0.833; Car 0.717, 0.799, 0.683, 0.624; Balance 0.558, 0.586, 0.598, 0.591.
- Pooled association client_count vs conflict rate: Pearson 0.840, Spearman 0.864 (n = 12).

**Statement supported.** Conflict increased with C in two of three datasets in this split; it did
not in Hayes-Roth. **NOT PROVEN**: `C↑ ⇒ conflict↑` in general. The Hayes-Roth test set has 26
objects, so one test object changes the conflict rate by 0.038; the C = 3 → 4 drop (14 → 10 conflict
cases) is within what a single split can produce by chance.

## D. Exact-antecedent conflict vs inference conflict

**OBSERVED.** Exact-antecedent conflict rate (share of distinct antecedents in `R_G` with more than
one decision) is 0–0.058 in all 12 configurations; the pre-resolution (inference) conflict rate is
0.115–0.659. Car C = 2 has **zero** exact-antecedent conflicts but 85 of 346 test objects
(24.6%) in conflict.

**Explanation (definitional).** Inference conflict needs only two matching rules with different
decisions. Example from Car C = 2 (test row 25: buying=vhigh, maint=vhigh, doors=2, persons=more,
lug_boot=big, safety=med; true `unacc`): it matches `maint=vhigh ∧ buying=vhigh → unacc`
(Client_1, Client_2) and `safety=med ∧ persons=more ∧ lug_boot=big ∧ doors=2 → acc` (Client_1).
The two antecedents share no attribute, yet one object satisfies both. So conflict arises mainly
from overlapping, non-identical antecedents; identical antecedents are not necessary for it and are
not the main source here.

## E. Resolver comparison

**OBSERVED** (`resolver_winners.csv`):

| Dataset | BA winner C=2/3/4/5 | Conflict-BA winner | Macro-F1 winner |
|---|---|---|---|
| Hayes-Roth | FM+STD+GS (tie) / FM / FM / FM | same as BA | same as BA |
| Car Evaluation | GS / GS / GS / GS | GS at all C | GS / GS / STD / FM |
| Balance Scale | STD / STD / STD / GS | STD / STD / STD / GS | STD / STD / STD / GS |

- No resolver wins every configuration on any of the three metrics.
- SIMPLE_VOTING is never the best resolver on any metric in any configuration.
- The best resolver depends on the dataset more than on C: FIRST_MATCH on Hayes-Roth, GLOBAL_STRENGTH
  on Car (BA, conflict BA), STANDARD_VOTING on Balance for C ≤ 4.

**Statement supported.**
> No single baseline resolver dominates across all tested dataset/client-count configurations.

**NOT PROVEN.** That any resolver is better in general; differences of a few test objects
(Hayes-Roth: 1 object ≈ 0.04 accuracy) are not separable from split noise with one seed.

## F. FIRST_MATCH: nominal performance vs order robustness

**OBSERVED.**
- Hayes-Roth: FIRST_MATCH has the highest nominal BA at C = 3, 4, 5 (0.833, 0.778, 0.833), but with
  OSR = 0.346, 0.346, 0.577. Its BA over all client orders spans [0.622, 0.900] at C = 3 and
  [0.678, 0.867] at C = 5; the order-mean BA is 0.791 (C = 3) and 0.735 (C = 5). At C = 5 the
  order-mean (0.735) is about equal to GLOBAL_STRENGTH's order-invariant BA (0.733), so the nominal
  lead (0.833) comes from the particular order `Client_1 → … → Client_5`.
- Car: nominal BA close to the order mean; order BA range widens with C (0.001 at C = 2 to 0.117 at
  C = 5); OSR 0.046 → 0.237.
- Balance: highest OSR (0.222 → 0.579) but a narrow BA range (≤ 0.084); FIRST_MATCH has the lowest
  BA of the four resolvers at every C.

**Statement supported.** FIRST_MATCH's prediction performance and its order robustness are
different properties: in these runs a high nominal score can coexist with a large share of test
objects whose prediction depends on client order. Nominal FIRST_MATCH scores should be reported with
the order distribution. STANDARD_VOTING, SIMPLE_VOTING and GLOBAL_STRENGTH are order-invariant by
construction.

## G. STANDARD_VOTING / GLOBAL_STRENGTH after the scope correction

**OBSERVED.** The audit proved a real bug: federated STANDARD weights and GLOBAL_STRENGTH support
sets were computed only on clients that induced each rule (`03_IMPLEMENTATION_AUDIT.md` B3/B4).
After the fix, distributed values equal the pooled calculation for every rule and every test object
in all 12 configurations (`uci_distributed_vs_pooled.csv`). Between 51% and 87% of global rules per
configuration have supporting objects on non-producing clients.

Changed configurations (all metrics in `old_vs_new.csv`): STANDARD_VOTING 11/12, GLOBAL_STRENGTH
11/12; only Hayes-Roth C = 2 kept identical predictions. Direction is mixed:
- Hayes-Roth: both fall at C = 3..5 (e.g. STD BA 0.744 → 0.578 and GS 0.800 → 0.733 at C = 5).
- Car: GS BA falls at C = 2, 4, 5 and rises slightly at C = 3; STD mixed.
- Balance: GS BA rises at every C (by +0.017 to +0.023); STD mixed.

Winner changes caused by the correction: Car C = 4 macro-F1 (GS → STD), Balance C = 5 BA and
conflict BA (STD → GS). All other winner cells are unchanged.

**Consequence.** All previous federated STANDARD_VOTING and GLOBAL_STRENGTH results (2026-10-14
reference and anything derived from it) are **superseded**. The correction is a fix to mathematical
correctness (pooled-equivalent support), not a performance tuning; it does not make either resolver
uniformly better. FIRST_MATCH and SIMPLE_VOTING results are unchanged and remain valid.

**INTERPRETATION.** Counting support from all clients gives large, general rules (which collect
support everywhere) more weight relative to the producing client's view. On Hayes-Roth, where
many short rules contradict each other across clients, this appears to favour the wrong decision
more often. **NOT PROVEN**.

## Structural associations (exploratory)

`structural_associations.csv` — **exploratory descriptive association only**; n = 12 pooled
(n = 4 per dataset), single seed, no inference.

| Pair | Pooled Pearson | Pooled Spearman | Hayes-Roth ρ | Car ρ | Balance ρ |
|---|---|---|---|---|---|
| C vs RI | 0.338 | 0.382 | 0.738 | undefined (RI constant) | undefined (RI constant) |
| C vs H_rule | −0.105 | 0.022 | −0.200 | 1.000 | −0.800 |
| C vs conflict | 0.840 | 0.864 | 0.800 | 1.000 | 1.000 |
| RI vs H_rule | −0.674 | −0.521 | −0.105 | undefined | undefined |
| H_rule vs conflict | 0.018 | 0.140 | −0.400 | 1.000 | −0.800 |
| RI vs conflict | 0.066 | 0.091 | 0.211 | undefined | undefined |

Pooled correlations mix three datasets with different baselines; the per-dataset trajectories
(`structural_trajectories.csv`) are the more informative description. The only association that is
consistent in sign across all three datasets is client count vs conflict rate.

## Dataset-specific sections

### Hayes-Roth
1. **Reduct stability.** Central reduct = all 4 attributes (`γ_C = 0.811`: the table is inconsistent).
   Local reducts identical at C = 2, 3 (RI = 0); `hobby` dropped by 2 of 4 clients at C = 4 and 1 of 5
   at C = 5 (RI 0.167, 0.100). The only dataset with non-zero RI.
2. **Rule heterogeneity.** High (0.747–0.867), non-monotonic in C.
3. **Conflict vs C.** Non-monotonic: 0.115, 0.538, 0.385, 0.654.
4. **Best resolver.** FIRST_MATCH at C = 3, 4, 5 (BA, conflict BA, macro-F1); three-way tie
   FM/STD/GS at C = 2.
5. **FIRST_MATCH order risk.** Highest relative risk: OSR up to 0.577; order BA range 0.278 at C = 3.
   The nominal lead is order-dependent (F).
6. **Unusual behaviour.** Non-monotonic conflict and RI; very small test set (26 objects).
7. **Evidence for the mechanism.** The only dataset where reduct heterogeneity appears; RI does not
   track conflict (ρ = 0.211). Conflict tracks C (ρ = 0.8) but not monotonically.

### Car Evaluation
1. **Reduct stability.** Fully stable: every reduct is all 6 attributes; RI = 0 at every C.
2. **Rule heterogeneity.** High and increasing (0.859 → 0.931).
3. **Conflict vs C.** Strictly increasing (0.246 → 0.607); exact-antecedent conflict ≤ 0.020.
4. **Best resolver.** GLOBAL_STRENGTH for BA and conflict BA at every C; macro-F1 GS (C = 2, 3),
   STD (C = 4), FM (C = 5).
5. **FIRST_MATCH order risk.** Moderate: OSR 0.046 → 0.237; BA range up to 0.117 (C = 5).
6. **Unusual behaviour.** Accuracy (0.81–0.91) far above BA (0.54–0.80) because of class imbalance;
   BA is the more informative metric here.
7. **Evidence for the mechanism.** Clearest case of RI = 0 with high rule heterogeneity and high
   conflict, and the one dataset where `H_rule` and conflict move together.

### Balance Scale
1. **Reduct stability.** Fully stable: every reduct is all 4 attributes; RI = 0 at every C.
2. **Rule heterogeneity.** Highest of the three (0.911–0.967), with a net decrease over C.
3. **Conflict vs C.** Strictly increasing (0.373 → 0.659).
4. **Best resolver.** STANDARD_VOTING at C = 2, 3, 4 on all three metrics; GLOBAL_STRENGTH at C = 5.
5. **FIRST_MATCH order risk.** Highest OSR (up to 0.579) but narrow BA range; FIRST_MATCH has the
   lowest BA at every C.
6. **Unusual behaviour.** Conflict rises while `H_rule` falls; coverage dips at C = 5 (0.992).
7. **Evidence for the mechanism.** RI = 0, so reduct heterogeneity cannot explain conflict here;
   `H_rule` does not explain the rise either. Rule generality (rule length, matches per object) is
   the structural quantity that moves with conflict (B).

## Cross-dataset synthesis

- **Common to all three datasets (OBSERVED):** central reduct = full attribute set; rule
  heterogeneity ≥ 0.747 at every C; inference conflict far above exact-antecedent conflict; local
  rules shorten and matches per test object rise as C grows; FIRST_MATCH OSR > 0 at every C.
- **Only in some datasets:** non-zero RI (Hayes-Roth only); monotone conflict growth (Car,
  Balance); `H_rule` moving with conflict (Car only).
- **Is reduct heterogeneity necessary?** No, in these runs (A).
- **Is rule heterogeneity more directly aligned with conflict than reduct heterogeneity?**
  Partially. Rule heterogeneity is present wherever conflict is, which reduct heterogeneity is not.
  But `H_rule`'s C-trajectory follows conflict only in Car and runs opposite in Balance, so as a
  set-identity measure it is not a reliable proxy for conflict level. Rule generality (overlap)
  aligned better in these runs (B, INTERPRETATION).
- **Does resolver quality depend on dataset / client count?** Yes, in these runs: the winner is
  mostly dataset-specific, with C-dependent changes in Car (macro-F1) and Balance (C = 5).
- **FIRST_MATCH trade-off?** Yes, in these runs: nominal scores can be high while predictions for
  up to 58% of test objects depend on client order (F).
- **Not supported:** any causal claim along the research chain; any ranking of resolvers beyond these
  12 configurations; any statement about other datasets, partitions or seeds.
