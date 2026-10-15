# 05 — UCI3 results (post-audit)

Run: `outputs/final_math_audit_20261015/UCI3_HOLDOUT42_FINAL/batch_runs/FINAL/`
(driver `scripts/run_uci3.py`, input `uci_snapshot/`). Settings: HOLDOUT, test ratio 0.2, seed 42,
STRATIFIED partition, C = 2, 3, 4, 5, `reduct.enabled = true`, four resolvers, structural
artifact built once per (dataset, C) and reused by all resolvers. The 2026-10-14 reference was
not overwritten. Full-precision tables: `uci3_structural_table.csv`, `uci3_resolver_table.csv`,
`resolver_winners.csv`, `old_vs_new.csv`.

Datasets: Hayes-Roth (UCI 44; 132 labelled rows; 106 train / 26 test; 4 attributes; 3 classes),
Car Evaluation (UCI 19; 1 728 rows; 1 382 / 346; 6 attributes; 4 classes),
Balance Scale (UCI 12; 625 rows; 499 / 126; 4 attributes; 3 classes).

## 1. Structural results (policy-independent)

Identical before and after the fix in every field
(`structural_prefix_vs_final_diff.csv` is empty): the fix touched only reduct cases that do not
occur here (A10) and support metadata.

| dataset | C | central reduct size | γ_C | mean local reduct size | RI | mean J(R_c,R_central) | H_rule | central rules | mean local rules | global rules | coverage | conflict rate | covered-conflict rate | exact-antecedent conflict rate | conflict cases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hayes-Roth | 2 | 4 | 0.8113 | 4.0000 | 0.0000 | 1.0000 | 0.8667 | 19 | 17.0000 | 30 | 0.9231 | 0.1154 | 0.1250 | 0.0345 | 3 |
| Hayes-Roth | 3 | 4 | 0.8113 | 4.0000 | 0.0000 | 1.0000 | 0.7470 | 19 | 13.3333 | 28 | 1.0000 | 0.5385 | 0.5385 | 0.0370 | 14 |
| Hayes-Roth | 4 | 4 | 0.8113 | 3.5000 | 0.1667 | 0.8750 | 0.7500 | 19 | 11.7500 | 29 | 1.0000 | 0.3846 | 0.3846 | 0.0357 | 10 |
| Hayes-Roth | 5 | 4 | 0.8113 | 3.8000 | 0.1000 | 0.9500 | 0.7728 | 19 | 11.0000 | 33 | 1.0000 | 0.6538 | 0.6538 | 0.0312 | 17 |
| Car Evaluation | 2 | 6 | 1.0000 | 6.0000 | 0.0000 | 1.0000 | 0.8587 | 180 | 105.0000 | 184 | 0.9769 | 0.2457 | 0.2515 | 0.0000 | 85 |
| Car Evaluation | 3 | 6 | 1.0000 | 6.0000 | 0.0000 | 1.0000 | 0.8977 | 180 | 81.0000 | 207 | 0.9827 | 0.3873 | 0.3941 | 0.0197 | 134 |
| Car Evaluation | 4 | 6 | 1.0000 | 6.0000 | 0.0000 | 1.0000 | 0.9072 | 180 | 66.7500 | 223 | 0.9942 | 0.4884 | 0.4913 | 0.0090 | 169 |
| Car Evaluation | 5 | 6 | 1.0000 | 6.0000 | 0.0000 | 1.0000 | 0.9314 | 180 | 52.4000 | 226 | 1.0000 | 0.6069 | 0.6069 | 0.0135 | 210 |
| Balance Scale | 2 | 4 | 1.0000 | 4.0000 | 0.0000 | 1.0000 | 0.9665 | 232 | 108.0000 | 209 | 0.9444 | 0.3730 | 0.3950 | 0.0146 | 47 |
| Balance Scale | 3 | 4 | 1.0000 | 4.0000 | 0.0000 | 1.0000 | 0.9457 | 232 | 74.0000 | 200 | 0.9841 | 0.4921 | 0.5000 | 0.0417 | 62 |
| Balance Scale | 4 | 4 | 1.0000 | 4.0000 | 0.0000 | 1.0000 | 0.9110 | 232 | 55.0000 | 181 | 1.0000 | 0.5873 | 0.5873 | 0.0526 | 74 |
| Balance Scale | 5 | 4 | 1.0000 | 4.0000 | 0.0000 | 1.0000 | 0.9261 | 232 | 46.2000 | 183 | 0.9921 | 0.6587 | 0.6640 | 0.0578 | 83 |

Covered-conflict rate = conflict rate / coverage (derived; every conflict case is covered).
"Exact-antecedent conflict rate" = share of distinct antecedents in `R_G` that carry more than one
decision.

### Selected reducts and local rule counts

| dataset | C | central reduct | local reducts (Client_1; …; Client_C) | local rule counts |
|---|---|---|---|---|
| Hayes-Roth | 2 | age+educational_level+hobby+marital_status | age+educational_level+hobby+marital_status; age+educational_level+hobby+marital_status | 18, 16 |
| Hayes-Roth | 3 | age+educational_level+hobby+marital_status | age+educational_level+hobby+marital_status; age+educational_level+hobby+marital_status; age+educational_level+hobby+marital_status | 13, 14, 13 |
| Hayes-Roth | 4 | age+educational_level+hobby+marital_status | age+educational_level+marital_status; age+educational_level+marital_status; age+educational_level+hobby+marital_status; age+educational_level+hobby+marital_status | 11, 11, 15, 10 |
| Hayes-Roth | 5 | age+educational_level+hobby+marital_status | age+educational_level+hobby+marital_status; age+educational_level+marital_status; age+educational_level+hobby+marital_status; age+educational_level+hobby+marital_status; age+educational_level+hobby+marital_status | 11, 10, 11, 12, 11 |
| Car Evaluation | 2 | buying+doors+lug_boot+maint+persons+safety | buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety | 108, 102 |
| Car Evaluation | 3 | buying+doors+lug_boot+maint+persons+safety | buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety | 81, 84, 78 |
| Car Evaluation | 4 | buying+doors+lug_boot+maint+persons+safety | buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety | 65, 63, 70, 69 |
| Car Evaluation | 5 | buying+doors+lug_boot+maint+persons+safety | buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety; buying+doors+lug_boot+maint+persons+safety | 51, 52, 55, 56, 48 |
| Balance Scale | 2 | left_distance+left_weight+right_distance+right_weight | left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight | 105, 111 |
| Balance Scale | 3 | left_distance+left_weight+right_distance+right_weight | left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight | 66, 80, 76 |
| Balance Scale | 4 | left_distance+left_weight+right_distance+right_weight | left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight | 58, 55, 55, 52 |
| Balance Scale | 5 | left_distance+left_weight+right_distance+right_weight | left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight; left_distance+left_weight+right_distance+right_weight | 45, 47, 43, 47, 49 |

## 2. Resolver results (federated, all 3 datasets × C = 2..5)

FM = FIRST_MATCH, SV = SIMPLE_VOTING, STD = STANDARD_VOTING, GS = GLOBAL_STRENGTH.
Conflict metrics are restricted to the pre-resolution conflict cases, which are the same cases
for every policy (`uci_distributed_vs_pooled.csv`, column `conflict_case_ids_identical_across_4_resolvers`).
STD and GS rows are the corrected (post-audit) values; prior STD/GS values are superseded (§5).

| dataset | C | policy | acc | BA | macro-F1 | coverage | conflict acc | conflict BA | conflict macro-F1 | disagree vs FM | conflict disagree vs FM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hayes-Roth | 2 | FM | 0.7308 | 0.7667 | 0.7661 | 0.9231 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| Hayes-Roth | 2 | SV | 0.6538 | 0.6556 | 0.6788 | 0.9231 | 0.3333 | 0.5000 | 0.2222 | 0.0769 | 0.6667 |
| Hayes-Roth | 2 | STD | 0.7308 | 0.7667 | 0.7661 | 0.9231 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| Hayes-Roth | 2 | GS | 0.7308 | 0.7667 | 0.7661 | 0.9231 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| Hayes-Roth | 3 | FM | 0.8077 | 0.8333 | 0.8329 | 1.0000 | 0.7857 | 0.7302 | 0.7333 | 0.0000 | 0.0000 |
| Hayes-Roth | 3 | SV | 0.6538 | 0.6111 | 0.6172 | 1.0000 | 0.5000 | 0.3333 | 0.2456 | 0.2308 | 0.4286 |
| Hayes-Roth | 3 | STD | 0.7308 | 0.7444 | 0.7560 | 1.0000 | 0.6429 | 0.5357 | 0.5357 | 0.1538 | 0.2857 |
| Hayes-Roth | 3 | GS | 0.6923 | 0.7333 | 0.7333 | 1.0000 | 0.5714 | 0.5238 | 0.5238 | 0.1923 | 0.3571 |
| Hayes-Roth | 4 | FM | 0.7692 | 0.7778 | 0.7911 | 1.0000 | 0.8000 | 0.8056 | 0.8024 | 0.0000 | 0.0000 |
| Hayes-Roth | 4 | SV | 0.5769 | 0.5667 | 0.5945 | 1.0000 | 0.3000 | 0.2778 | 0.2315 | 0.1923 | 0.5000 |
| Hayes-Roth | 4 | STD | 0.6154 | 0.6222 | 0.6463 | 1.0000 | 0.4000 | 0.3611 | 0.3333 | 0.3077 | 0.8000 |
| Hayes-Roth | 4 | GS | 0.6923 | 0.7333 | 0.7306 | 1.0000 | 0.6000 | 0.5833 | 0.5333 | 0.2308 | 0.6000 |
| Hayes-Roth | 5 | FM | 0.8077 | 0.8333 | 0.8295 | 1.0000 | 0.8235 | 0.8190 | 0.8222 | 0.0000 | 0.0000 |
| Hayes-Roth | 5 | SV | 0.5769 | 0.5222 | 0.5026 | 1.0000 | 0.4706 | 0.4190 | 0.3439 | 0.2308 | 0.3529 |
| Hayes-Roth | 5 | STD | 0.6154 | 0.5778 | 0.5826 | 1.0000 | 0.5294 | 0.4857 | 0.4667 | 0.1923 | 0.2941 |
| Hayes-Roth | 5 | GS | 0.6923 | 0.7333 | 0.7306 | 1.0000 | 0.6471 | 0.6571 | 0.6571 | 0.1154 | 0.1765 |
| Car Evaluation | 2 | FM | 0.8988 | 0.6639 | 0.6578 | 0.9769 | 0.8353 | 0.6363 | 0.6347 | 0.0000 | 0.0000 |
| Car Evaluation | 2 | SV | 0.8757 | 0.6215 | 0.6294 | 0.9769 | 0.7412 | 0.5561 | 0.5723 | 0.0578 | 0.2353 |
| Car Evaluation | 2 | STD | 0.9017 | 0.6694 | 0.6723 | 0.9769 | 0.8471 | 0.6611 | 0.6762 | 0.0434 | 0.1765 |
| Car Evaluation | 2 | GS | 0.8873 | 0.7174 | 0.6755 | 0.9769 | 0.7882 | 0.7051 | 0.6316 | 0.0636 | 0.2588 |
| Car Evaluation | 3 | FM | 0.9046 | 0.6740 | 0.6815 | 0.9827 | 0.8134 | 0.5783 | 0.5635 | 0.0000 | 0.0000 |
| Car Evaluation | 3 | SV | 0.8873 | 0.7103 | 0.7137 | 0.9827 | 0.7687 | 0.6215 | 0.5975 | 0.0867 | 0.2239 |
| Car Evaluation | 3 | STD | 0.9104 | 0.7089 | 0.7076 | 0.9827 | 0.8284 | 0.6458 | 0.6033 | 0.0694 | 0.1791 |
| Car Evaluation | 3 | GS | 0.8873 | 0.7985 | 0.7345 | 0.9827 | 0.7687 | 0.7151 | 0.5957 | 0.0954 | 0.2463 |
| Car Evaluation | 4 | FM | 0.8873 | 0.6314 | 0.6296 | 0.9942 | 0.7988 | 0.5904 | 0.5787 | 0.0000 | 0.0000 |
| Car Evaluation | 4 | SV | 0.8410 | 0.5815 | 0.5979 | 0.9942 | 0.7041 | 0.4982 | 0.5034 | 0.1358 | 0.2781 |
| Car Evaluation | 4 | STD | 0.8786 | 0.5927 | 0.6347 | 0.9942 | 0.7811 | 0.5135 | 0.5327 | 0.1185 | 0.2426 |
| Car Evaluation | 4 | GS | 0.8526 | 0.6832 | 0.6305 | 0.9942 | 0.7278 | 0.6035 | 0.5405 | 0.1301 | 0.2663 |
| Car Evaluation | 5 | FM | 0.8728 | 0.5964 | 0.6069 | 1.0000 | 0.8143 | 0.5311 | 0.5377 | 0.0000 | 0.0000 |
| Car Evaluation | 5 | SV | 0.8064 | 0.5399 | 0.5269 | 1.0000 | 0.7048 | 0.4439 | 0.4252 | 0.1590 | 0.2619 |
| Car Evaluation | 5 | STD | 0.8584 | 0.5435 | 0.5675 | 1.0000 | 0.7905 | 0.4653 | 0.4762 | 0.0983 | 0.1619 |
| Car Evaluation | 5 | GS | 0.8295 | 0.6236 | 0.5723 | 1.0000 | 0.7429 | 0.5596 | 0.5122 | 0.1590 | 0.2619 |
| Balance Scale | 2 | FM | 0.6746 | 0.4885 | 0.5038 | 0.9444 | 0.3830 | 0.2750 | 0.2870 | 0.0000 | 0.0000 |
| Balance Scale | 2 | SV | 0.7222 | 0.5230 | 0.5228 | 0.9444 | 0.5106 | 0.3750 | 0.3651 | 0.1587 | 0.4255 |
| Balance Scale | 2 | STD | 0.7698 | 0.5575 | 0.5440 | 0.9444 | 0.6383 | 0.5000 | 0.4603 | 0.1667 | 0.4468 |
| Balance Scale | 2 | GS | 0.7381 | 0.5345 | 0.5372 | 0.9444 | 0.5532 | 0.4278 | 0.4283 | 0.1508 | 0.4043 |
| Balance Scale | 3 | FM | 0.6508 | 0.4713 | 0.4885 | 0.9841 | 0.4516 | 0.3351 | 0.3663 | 0.0000 | 0.0000 |
| Balance Scale | 3 | SV | 0.7381 | 0.5345 | 0.5293 | 0.9841 | 0.6290 | 0.4655 | 0.4613 | 0.2540 | 0.5161 |
| Balance Scale | 3 | STD | 0.8095 | 0.5862 | 0.5642 | 0.9841 | 0.7742 | 0.5836 | 0.5470 | 0.2619 | 0.5323 |
| Balance Scale | 3 | GS | 0.7857 | 0.5690 | 0.5546 | 0.9841 | 0.7258 | 0.5451 | 0.5264 | 0.2460 | 0.5000 |
| Balance Scale | 4 | FM | 0.7063 | 0.5115 | 0.5104 | 1.0000 | 0.5405 | 0.3969 | 0.3978 | 0.0000 | 0.0000 |
| Balance Scale | 4 | SV | 0.7937 | 0.5747 | 0.5577 | 1.0000 | 0.6892 | 0.5078 | 0.4911 | 0.2063 | 0.3514 |
| Balance Scale | 4 | STD | 0.8254 | 0.5977 | 0.5733 | 1.0000 | 0.7432 | 0.5521 | 0.5245 | 0.2063 | 0.3514 |
| Balance Scale | 4 | GS | 0.8095 | 0.5862 | 0.5715 | 1.0000 | 0.7162 | 0.5318 | 0.5189 | 0.2063 | 0.3514 |
| Balance Scale | 5 | FM | 0.6746 | 0.4885 | 0.4839 | 0.9921 | 0.5663 | 0.4167 | 0.4101 | 0.0000 | 0.0000 |
| Balance Scale | 5 | SV | 0.7460 | 0.5402 | 0.5245 | 0.9921 | 0.6747 | 0.4975 | 0.4767 | 0.2063 | 0.3133 |
| Balance Scale | 5 | STD | 0.7778 | 0.5632 | 0.5424 | 0.9921 | 0.7229 | 0.5412 | 0.5102 | 0.2460 | 0.3735 |
| Balance Scale | 5 | GS | 0.7778 | 0.5908 | 0.5910 | 0.9921 | 0.7229 | 0.5699 | 0.5668 | 0.2778 | 0.4217 |

## 3. FIRST_MATCH order sensitivity

All `C!` client orders were evaluated (C! ≤ 120). OSR = share of test objects whose FIRST_MATCH
prediction changes across orders. The other three resolvers are order-invariant by construction
(OSR = 0, order-BA range collapses to the nominal BA).

| dataset | C | nominal BA | OSR | order BA mean | order BA std | order BA min | order BA max |
|---|---|---|---|---|---|---|---|
| Hayes-Roth | 2 | 0.7667 | 0.0385 | 0.7389 | 0.0278 | 0.7111 | 0.7667 |
| Hayes-Roth | 3 | 0.8333 | 0.3462 | 0.7907 | 0.1213 | 0.6222 | 0.9000 |
| Hayes-Roth | 4 | 0.7778 | 0.3462 | 0.7306 | 0.0372 | 0.6778 | 0.7778 |
| Hayes-Roth | 5 | 0.8333 | 0.5769 | 0.7348 | 0.0570 | 0.6778 | 0.8667 |
| Car Evaluation | 2 | 0.6639 | 0.0462 | 0.6634 | 0.0005 | 0.6629 | 0.6639 |
| Car Evaluation | 3 | 0.6740 | 0.1156 | 0.6871 | 0.0164 | 0.6675 | 0.7081 |
| Car Evaluation | 4 | 0.6314 | 0.1763 | 0.6268 | 0.0320 | 0.5796 | 0.6716 |
| Car Evaluation | 5 | 0.5964 | 0.2370 | 0.5891 | 0.0315 | 0.5287 | 0.6453 |
| Balance Scale | 2 | 0.4885 | 0.2222 | 0.4971 | 0.0086 | 0.4885 | 0.5057 |
| Balance Scale | 3 | 0.4713 | 0.3730 | 0.4856 | 0.0136 | 0.4655 | 0.5057 |
| Balance Scale | 4 | 0.5115 | 0.4603 | 0.5315 | 0.0282 | 0.4943 | 0.5782 |
| Balance Scale | 5 | 0.4885 | 0.5794 | 0.4898 | 0.0174 | 0.4713 | 0.5448 |

## 4. Centralized reference (same split; independent of C)

| dataset | central acc | central BA | central macro-F1 | central coverage |
|---|---|---|---|---|
| Hayes-Roth | 0.7692 | 0.7778 | 0.7883 | 0.8462 |
| Car Evaluation | 0.8873 | 0.6300 | 0.6859 | 0.9249 |
| Balance Scale | 0.7302 | 0.5287 | 0.5055 | 0.7222 |

(FIRST_MATCH on the central rule set; listed for context only.)

## 5. Best resolver per configuration

Ties are listed with `+` (absolute tolerance 1e-12).

| dataset | C | best BA | BA winner | best conflict BA | conflict BA winner | best macro-F1 | macro-F1 winner |
|---|---|---|---|---|---|---|---|
| Hayes-Roth | 2 | 0.7667 | FM+STD+GS | 1.0000 | FM+STD+GS | 0.7661 | FM+STD+GS |
| Hayes-Roth | 3 | 0.8333 | FM | 0.7302 | FM | 0.8329 | FM |
| Hayes-Roth | 4 | 0.7778 | FM | 0.8056 | FM | 0.7911 | FM |
| Hayes-Roth | 5 | 0.8333 | FM | 0.8190 | FM | 0.8295 | FM |
| Car Evaluation | 2 | 0.7174 | GS | 0.7051 | GS | 0.6755 | GS |
| Car Evaluation | 3 | 0.7985 | GS | 0.7151 | GS | 0.7345 | GS |
| Car Evaluation | 4 | 0.6832 | GS | 0.6035 | GS | 0.6347 | STD |
| Car Evaluation | 5 | 0.6236 | GS | 0.5596 | GS | 0.6069 | FM |
| Balance Scale | 2 | 0.5575 | STD | 0.5000 | STD | 0.5440 | STD |
| Balance Scale | 3 | 0.5862 | STD | 0.5836 | STD | 0.5642 | STD |
| Balance Scale | 4 | 0.5977 | STD | 0.5521 | STD | 0.5733 | STD |
| Balance Scale | 5 | 0.5908 | GS | 0.5699 | GS | 0.5910 | GS |

## 6. Old vs new (STANDARD_VOTING and GLOBAL_STRENGTH)

"Old" = unmodified source rerun (`PRE_FIX_BASELINE`), which equals the 2026-10-14 reference on
every value the reference stores. FIRST_MATCH and SIMPLE_VOTING: **0 of 24 rows changed** in any
metric. STANDARD_VOTING: 11 of 12 configurations changed; GLOBAL_STRENGTH: 11 of 12 changed
(Hayes-Roth C = 2 unchanged for both). Coverage never changes (resolvers do not alter matching).

| dataset | C | policy | acc old | acc new | BA old | BA new | ΔBA | F1 old | F1 new | cBA old | cBA new | ΔcBA | Δcoverage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hayes-Roth | 2 | STD | 0.7308 | 0.7308 | 0.7667 | 0.7667 | 0.0000 | 0.7661 | 0.7661 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| Hayes-Roth | 2 | GS | 0.7308 | 0.7308 | 0.7667 | 0.7667 | 0.0000 | 0.7661 | 0.7661 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| Hayes-Roth | 3 | STD | 0.7308 | 0.7308 | 0.7667 | 0.7444 | -0.0222 | 0.7661 | 0.7560 | 0.5714 | 0.5357 | -0.0357 | 0.0000 |
| Hayes-Roth | 3 | GS | 0.7308 | 0.6923 | 0.7667 | 0.7333 | -0.0333 | 0.7661 | 0.7333 | 0.5714 | 0.5238 | -0.0476 | 0.0000 |
| Hayes-Roth | 4 | STD | 0.6923 | 0.6154 | 0.7111 | 0.6222 | -0.0889 | 0.7253 | 0.6463 | 0.6111 | 0.3611 | -0.2500 | 0.0000 |
| Hayes-Roth | 4 | GS | 0.7308 | 0.6923 | 0.7667 | 0.7333 | -0.0333 | 0.7661 | 0.7306 | 0.7222 | 0.5833 | -0.1389 | 0.0000 |
| Hayes-Roth | 5 | STD | 0.7308 | 0.6154 | 0.7444 | 0.5778 | -0.1667 | 0.7560 | 0.5826 | 0.7048 | 0.4857 | -0.2190 | 0.0000 |
| Hayes-Roth | 5 | GS | 0.7692 | 0.6923 | 0.8000 | 0.7333 | -0.0667 | 0.7980 | 0.7306 | 0.7714 | 0.6571 | -0.1143 | 0.0000 |
| Car Evaluation | 2 | STD | 0.9017 | 0.9017 | 0.6854 | 0.6694 | -0.0160 | 0.6784 | 0.6723 | 0.6776 | 0.6611 | -0.0165 | 0.0000 |
| Car Evaluation | 2 | GS | 0.8902 | 0.8873 | 0.7388 | 0.7174 | -0.0214 | 0.6924 | 0.6755 | 0.7465 | 0.7051 | -0.0413 | 0.0000 |
| Car Evaluation | 3 | STD | 0.9191 | 0.9104 | 0.6756 | 0.7089 | 0.0333 | 0.6850 | 0.7076 | 0.6039 | 0.6458 | 0.0419 | 0.0000 |
| Car Evaluation | 3 | GS | 0.8873 | 0.8873 | 0.7976 | 0.7985 | 0.0008 | 0.7152 | 0.7345 | 0.7372 | 0.7151 | -0.0221 | 0.0000 |
| Car Evaluation | 4 | STD | 0.8815 | 0.8786 | 0.6009 | 0.5927 | -0.0082 | 0.6472 | 0.6347 | 0.5392 | 0.5135 | -0.0258 | 0.0000 |
| Car Evaluation | 4 | GS | 0.8699 | 0.8526 | 0.7250 | 0.6832 | -0.0418 | 0.6633 | 0.6305 | 0.6878 | 0.6035 | -0.0843 | 0.0000 |
| Car Evaluation | 5 | STD | 0.8642 | 0.8584 | 0.5340 | 0.5435 | 0.0095 | 0.5475 | 0.5675 | 0.4533 | 0.4653 | 0.0121 | 0.0000 |
| Car Evaluation | 5 | GS | 0.8439 | 0.8295 | 0.6368 | 0.6236 | -0.0131 | 0.5797 | 0.5723 | 0.5803 | 0.5596 | -0.0208 | 0.0000 |
| Balance Scale | 2 | STD | 0.7540 | 0.7698 | 0.5460 | 0.5575 | 0.0115 | 0.5327 | 0.5440 | 0.4639 | 0.5000 | 0.0361 | 0.0000 |
| Balance Scale | 2 | GS | 0.7063 | 0.7381 | 0.5115 | 0.5345 | 0.0230 | 0.5161 | 0.5372 | 0.3556 | 0.4278 | 0.0722 | 0.0000 |
| Balance Scale | 3 | STD | 0.8175 | 0.8095 | 0.5920 | 0.5862 | -0.0057 | 0.5722 | 0.5642 | 0.5911 | 0.5836 | -0.0075 | 0.0000 |
| Balance Scale | 3 | GS | 0.7619 | 0.7857 | 0.5517 | 0.5690 | 0.0172 | 0.5540 | 0.5546 | 0.5040 | 0.5451 | 0.0411 | 0.0000 |
| Balance Scale | 4 | STD | 0.8254 | 0.8254 | 0.5977 | 0.5977 | 0.0000 | 0.5731 | 0.5733 | 0.5533 | 0.5521 | -0.0012 | 0.0000 |
| Balance Scale | 4 | GS | 0.7857 | 0.8095 | 0.5690 | 0.5862 | 0.0172 | 0.5662 | 0.5715 | 0.5008 | 0.5318 | 0.0310 | 0.0000 |
| Balance Scale | 5 | STD | 0.7937 | 0.7778 | 0.5747 | 0.5632 | -0.0115 | 0.5535 | 0.5424 | 0.5593 | 0.5412 | -0.0181 | 0.0000 |
| Balance Scale | 5 | GS | 0.7540 | 0.7778 | 0.5736 | 0.5908 | 0.0172 | 0.5735 | 0.5910 | 0.5405 | 0.5699 | 0.0294 | 0.0000 |

**The 2026-10-14 STANDARD_VOTING and GLOBAL_STRENGTH results are superseded** for every
configuration above (including the two unchanged Hayes-Roth C = 2 rows, whose weights were also
computed under the wrong scope even though no prediction flipped).
