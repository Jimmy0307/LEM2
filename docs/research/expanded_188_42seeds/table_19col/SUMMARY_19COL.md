# 19 欄總表（188 資料集 × 42 seeds，期中）

逐筆總表（與 full_scale 的 FULL19 欄位、`check_19` 驗證完全相同）：
- `FULL_SCALE_19COL_42SEEDS.csv.gz`（A_ALL_RULES）：180,468 列
- `FULL_SCALE_19COL_42SEEDS_B2.csv.gz`（B2_TRUE_AS_FALLBACK）：180,468 列

每一列＝一個資料集 × 一個 seed × 一個情境 × 一種決策策略。情境由 system / distribution / dirichlet_alpha 三欄決定
（集中式：CENTRALIZED, IID, 空；Fed IID：FEDERATED, IID, 空；Fed α=0.5 / 0.1：FEDERATED, DIRICHLET_NONIID, 0.5 / 0.1）。
TIMEOUT 等未完成模型不在逐筆表內，列於 MISSING.csv / FAILURES.csv。

下方彙總表為同樣 19 欄、每列一個「情境 × 決策策略」：先在每個完整資料集內對 42 個 seeds 取平均，再跨資料集彙總——
百分比欄位與 rule_count 取資料集平均；計數欄位（train_rows、test_rows、no_match_count、covered_count、
true_in_candidate_count）取資料集中位數，避免被大型資料集主導。

## A_ALL_RULES
| scenario | dataset | seed | distribution | dirichlet_alpha | split_mode | system | client_count | selection_policy | train_rows | test_rows | rule_count | no_match_count | covered_count | test_coverage_pct | true_in_candidate_count | candidate_coverage_pct | accuracy_pct | balanced_accuracy_pct | conflict_rate_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | FIRST_MATCH | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.00 | 46.28 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | SIMPLE_VOTING | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.00 | 46.21 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | STANDARD_VOTING | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.15 | 46.39 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | GLOBAL_STRENGTH | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.10 | 46.47 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | POPULATION_STANDARD | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.15 | 46.39 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | POPULATION_GLOBAL | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.10 | 46.47 | 1.26 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | FIRST_MATCH | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 61.48 | 49.18 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | SIMPLE_VOTING | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.06 | 49.01 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | STANDARD_VOTING | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.45 | 49.35 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | GLOBAL_STRENGTH | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.23 | 49.96 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_STANDARD | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.41 | 49.28 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_GLOBAL | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.11 | 49.87 | 13.08 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | FIRST_MATCH | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 112 | 51.78 | 57.41 | 47.46 | 27.20 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | SIMPLE_VOTING | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 112 | 51.78 | 59.72 | 48.06 | 27.20 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | STANDARD_VOTING | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 112 | 51.78 | 59.02 | 47.32 | 27.20 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | GLOBAL_STRENGTH | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 112 | 51.78 | 57.19 | 47.12 | 27.20 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_STANDARD | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 112 | 51.78 | 58.61 | 46.84 | 27.20 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_GLOBAL | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 112 | 51.78 | 56.38 | 46.63 | 27.20 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | FIRST_MATCH | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 186 | 68.50 | 47.59 | 43.12 | 55.48 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | SIMPLE_VOTING | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 186 | 68.50 | 54.52 | 44.89 | 55.48 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | STANDARD_VOTING | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 186 | 68.50 | 53.41 | 43.08 | 55.48 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | GLOBAL_STRENGTH | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 186 | 68.50 | 49.58 | 41.47 | 55.48 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_STANDARD | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 186 | 68.50 | 52.44 | 42.00 | 55.48 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_GLOBAL | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 186 | 68.50 | 46.28 | 39.87 | 55.48 |

## B2_TRUE_AS_FALLBACK
| scenario | dataset | seed | distribution | dirichlet_alpha | split_mode | system | client_count | selection_policy | train_rows | test_rows | rule_count | no_match_count | covered_count | test_coverage_pct | true_in_candidate_count | candidate_coverage_pct | accuracy_pct | balanced_accuracy_pct | conflict_rate_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | FIRST_MATCH | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.00 | 46.28 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | SIMPLE_VOTING | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.00 | 46.21 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | STANDARD_VOTING | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.15 | 46.39 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | GLOBAL_STRENGTH | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.10 | 46.47 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | POPULATION_STANDARD | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.15 | 46.39 | 1.26 |
| CENTRALIZED | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | CENTRALIZED | 0 | POPULATION_GLOBAL | 1,024 | 320 | 56.68 | 271 | 36 | 27.56 | 28 | 23.01 | 60.10 | 46.47 | 1.26 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | FIRST_MATCH | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 61.48 | 49.18 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | SIMPLE_VOTING | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.06 | 49.01 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | STANDARD_VOTING | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.45 | 49.35 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | GLOBAL_STRENGTH | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.23 | 49.96 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_STANDARD | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.41 | 49.28 | 13.08 |
| FED_IID | 179 complete datasets | 1-42 | IID |  | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_GLOBAL | 1,024 | 320 | 110.98 | 187 | 88 | 46.75 | 68 | 39.06 | 62.11 | 49.87 | 13.08 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | FIRST_MATCH | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 109 | 50.40 | 58.18 | 48.25 | 22.33 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | SIMPLE_VOTING | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 109 | 50.40 | 59.85 | 48.52 | 22.33 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | STANDARD_VOTING | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 109 | 50.40 | 59.89 | 48.61 | 22.33 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | GLOBAL_STRENGTH | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 109 | 50.40 | 58.80 | 48.96 | 22.33 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_STANDARD | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 109 | 50.40 | 59.74 | 48.40 | 22.33 |
| FED_A05 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.5 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_GLOBAL | 1,024 | 320 | 96.31 | 79 | 141 | 64.63 | 109 | 50.40 | 58.37 | 48.64 | 22.33 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | FIRST_MATCH | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 163 | 61.42 | 50.66 | 45.87 | 33.93 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | SIMPLE_VOTING | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 163 | 61.42 | 54.51 | 45.94 | 33.93 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | STANDARD_VOTING | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 163 | 61.42 | 54.94 | 46.45 | 33.93 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | GLOBAL_STRENGTH | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 163 | 61.42 | 54.07 | 46.73 | 33.93 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_STANDARD | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 163 | 61.42 | 54.87 | 46.35 | 33.93 |
| FED_A01 | 179 complete datasets | 1-42 | DIRICHLET_NONIID | 0.1 | NESTED_64_16_20 | FEDERATED | 3 | POPULATION_GLOBAL | 1,024 | 320 | 70.01 | 7 | 263 | 86.54 | 163 | 61.42 | 53.83 | 46.54 | 33.93 |

## 聯邦客戶端的分配方式（partition_status，已完成模型）
| scenario | ORIGINAL_OK |
|---|---:|
| FED_A01 | 7,521 |
| FED_A05 | 7,519 |
| FED_IID | 7,519 |
