# 期中結果（INTERIM）— 188 資料集 × 42 seeds 擴充實驗

> **狀態：INCOMPLETE，非最終結果。** 產生時間：2026-11-23 03:53（UTC+8）。
> 本文件只供進度報告；最終結論須待 STATUS.json 為 COMPLETE。數字會隨後續補跑改變。

## 1. 完成度
- 模型：**12,341 / 31,584**（39.1%）；結果列 148,092 / 379,008
- 完整完成的資料集（168/168 模型成功）：**71 / 188**；有任何配對結果的資料集：80
- 已記錄失敗：58 筆（全部狀態：TIMEOUT=58）

### 樣本偏誤（重要）
排程依預估運算量由重到輕排序、並受記憶體限制，因此已完成集合**不是隨機子集**：最大的資料集尚未完成，許多小型資料集也仍在佇列中。
- 已完成資料集原始列數中位數 **4,424**；全部 188 個為 1,970

| 原始列數 | 全部 | 已完整完成 | 完成比例 |
|---|---:|---:|---:|
| < 500 | 43 | 8 | 19% |
| 500 – 5,000 | 84 | 29 | 35% |
| 5,000 – 50,000 | 43 | 30 | 70% |
| ≥ 50,000 | 18 | 4 | 22% |

- 最大的未完成資料集（CI 上單一模型常達 2,700 秒上限）：
  - OML51:openml_42732（2,215,023 列，已成功 0/168）
  - OML51:openml_42769（1,000,000 列，已成功 4/168）
  - OML51:openml_42742（595,212 列，已成功 0/168）
  - UCI20:covertype（581,012 列，已成功 4/168）
  - OML51:openml_1169（539,383 列，已成功 0/168）
  - OML51:openml_41150（130,064 列，已成功 0/168）
  - PMLB:sleep（105,908 列，已成功 4/168）
  - PMLB:fars（100,968 列，已成功 56/168）
  - OML51:openml_23517（96,320 列，已成功 0/168）
  - OML51:openml_41168（83,733 列，已成功 0/168）
  - OML51:openml_41162（72,983 列，已成功 0/168）
  - OML51:openml_40996（70,000 列，已成功 0/168）

因此以下結論**只代表目前已完成的 71 個資料集**，不能推論到全部 188 個任務。

## 2. 主要比較：聯邦（C=3）− 集中式，準確率（百分點）
分析單位＝資料集：先在每個資料集內對 42 個 seeds 的配對差（同 seed、同規則版本、同決策策略、同來源 SHA）取平均，再跨資料集彙總。檢定為 Wilcoxon signed-rank（雙尾），36 個條件以 Holm 校正。負值＝聯邦較差。

- **Fed IID**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 2.17 至 2.67 個百分點；中位數介於 0.26 至 0.54；Fed 較差的資料集數 21–29 / 71。
- **Fed Dirichlet a=0.5**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 -1.49 至 0.85 個百分點；中位數介於 -0.52 至 -0.28；Fed 較差的資料集數 39–45 / 71。
- **Fed Dirichlet a=0.1**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 -12.64 至 -5.68 個百分點；中位數介於 -7.77 至 -3.66；Fed 較差的資料集數 51–56 / 71。

### 2a. A_ALL_RULES（完整資料集，n=71）
| 情境 | 決策策略 | 資料集數 | 平均差 | 中位數 | Fed 較差 / 持平 / 較好 | Wilcoxon p (Holm) |
|---|---|---:|---:|---:|---|---:|
| Fed IID | FIRST_MATCH | 71 | 2.17 | 0.26 | 29 / 2 / 40 | 0.011 |
| Fed IID | GLOBAL_STRENGTH | 71 | 2.52 | 0.44 | 25 / 2 / 44 | 0.001 |
| Fed IID | POPULATION_GLOBAL | 71 | 2.40 | 0.44 | 25 / 2 / 44 | 0.002 |
| Fed IID | POPULATION_STANDARD | 71 | 2.62 | 0.54 | 21 / 2 / 48 | <0.001 |
| Fed IID | SIMPLE_VOTING | 71 | 2.31 | 0.35 | 22 / 2 / 47 | <0.001 |
| Fed IID | STANDARD_VOTING | 71 | 2.67 | 0.54 | 21 / 2 / 48 | <0.001 |
| Fed Dirichlet a=0.5 | FIRST_MATCH | 71 | -0.93 | -0.52 | 45 / 1 / 25 | 1.000 |
| Fed Dirichlet a=0.5 | GLOBAL_STRENGTH | 71 | -0.65 | -0.52 | 43 / 1 / 27 | 1.000 |
| Fed Dirichlet a=0.5 | POPULATION_GLOBAL | 71 | -1.49 | -0.52 | 44 / 1 / 26 | 1.000 |
| Fed Dirichlet a=0.5 | POPULATION_STANDARD | 71 | 0.26 | -0.42 | 42 / 1 / 28 | 1.000 |
| Fed Dirichlet a=0.5 | SIMPLE_VOTING | 71 | 0.85 | -0.28 | 39 / 2 / 30 | 1.000 |
| Fed Dirichlet a=0.5 | STANDARD_VOTING | 71 | 0.59 | -0.36 | 41 / 1 / 29 | 1.000 |
| Fed Dirichlet a=0.1 | FIRST_MATCH | 71 | -11.68 | -7.77 | 54 / 1 / 16 | <0.001 |
| Fed Dirichlet a=0.1 | GLOBAL_STRENGTH | 71 | -9.93 | -4.91 | 56 / 1 / 14 | <0.001 |
| Fed Dirichlet a=0.1 | POPULATION_GLOBAL | 71 | -12.64 | -7.50 | 56 / 1 / 14 | <0.001 |
| Fed Dirichlet a=0.1 | POPULATION_STANDARD | 71 | -6.97 | -3.83 | 55 / 1 / 15 | <0.001 |
| Fed Dirichlet a=0.1 | SIMPLE_VOTING | 71 | -5.68 | -3.66 | 51 / 2 / 18 | <0.001 |
| Fed Dirichlet a=0.1 | STANDARD_VOTING | 71 | -5.97 | -3.83 | 54 / 1 / 16 | <0.001 |

### 2b. B2_TRUE_AS_FALLBACK（完整資料集）
| 情境 | 決策策略 | 資料集數 | 平均差 | 中位數 | Fed 較差 / 持平 / 較好 | Wilcoxon p (Holm) |
|---|---|---:|---:|---:|---|---:|
| Fed IID | FIRST_MATCH | 71 | 2.17 | 0.26 | 29 / 2 / 40 | 0.011 |
| Fed IID | GLOBAL_STRENGTH | 71 | 2.52 | 0.44 | 25 / 2 / 44 | 0.001 |
| Fed IID | POPULATION_GLOBAL | 71 | 2.40 | 0.44 | 25 / 2 / 44 | 0.002 |
| Fed IID | POPULATION_STANDARD | 71 | 2.62 | 0.54 | 21 / 2 / 48 | <0.001 |
| Fed IID | SIMPLE_VOTING | 71 | 2.31 | 0.35 | 22 / 2 / 47 | <0.001 |
| Fed IID | STANDARD_VOTING | 71 | 2.67 | 0.54 | 21 / 2 / 48 | <0.001 |
| Fed Dirichlet a=0.5 | FIRST_MATCH | 71 | -0.34 | -0.32 | 43 / 2 / 26 | 1.000 |
| Fed Dirichlet a=0.5 | GLOBAL_STRENGTH | 71 | 0.19 | -0.43 | 41 / 1 / 29 | 1.000 |
| Fed Dirichlet a=0.5 | POPULATION_GLOBAL | 71 | -0.30 | -0.52 | 43 / 1 / 27 | 1.000 |
| Fed Dirichlet a=0.5 | POPULATION_STANDARD | 71 | 0.90 | -0.34 | 40 / 1 / 30 | 1.000 |
| Fed Dirichlet a=0.5 | SIMPLE_VOTING | 71 | 0.98 | -0.28 | 38 / 2 / 31 | 1.000 |
| Fed Dirichlet a=0.5 | STANDARD_VOTING | 71 | 1.03 | -0.34 | 40 / 1 / 30 | 1.000 |
| Fed Dirichlet a=0.1 | FIRST_MATCH | 71 | -8.98 | -5.06 | 52 / 1 / 18 | <0.001 |
| Fed Dirichlet a=0.1 | GLOBAL_STRENGTH | 71 | -6.32 | -3.81 | 52 / 1 / 18 | 0.002 |
| Fed Dirichlet a=0.1 | POPULATION_GLOBAL | 71 | -6.56 | -4.32 | 52 / 1 / 18 | 0.001 |
| Fed Dirichlet a=0.1 | POPULATION_STANDARD | 71 | -5.30 | -3.28 | 52 / 1 / 18 | 0.003 |
| Fed Dirichlet a=0.1 | SIMPLE_VOTING | 71 | -5.78 | -3.50 | 51 / 1 / 19 | <0.001 |
| Fed Dirichlet a=0.1 | STANDARD_VOTING | 71 | -5.22 | -3.26 | 52 / 1 / 18 | 0.003 |

平衡準確率（balanced accuracy）的同型表格見 `interim_fed_minus_central_complete_datasets.csv`；
納入所有有配對資料集（含未跑完者，以現有 seeds 平均）的敏感度分析見 `interim_fed_minus_central_all_paired_datasets.csv`。

## 3. 結構面：覆蓋率、衝突率、規則數（A_ALL_RULES，資料集平均：集中式 → 聯邦）
| 情境 | 測試覆蓋率 % | 衝突率 % | 規則數 |
|---|---|---|---|
| Fed IID | 22.96 → 41.80 | 0.83 → 10.58 | 58.4 → 134.3 |
| Fed Dirichlet a=0.5 | 22.96 → 60.51 | 0.83 → 23.10 | 58.4 → 110.4 |
| Fed Dirichlet a=0.1 | 22.96 → 84.15 | 0.83 → 50.54 | 58.4 → 69.9 |

## 4. 六種決策策略（A_ALL_RULES）
資料集內排名（1＝準確率最高，同分取平均）跨資料集平均：

| 決策策略 | CENTRALIZED | FED_A01 | FED_A05 | FED_IID |
|---|---:|---:|---:|---:|
| FIRST_MATCH | 3.93 | 4.47 | 4.46 | 4.84 |
| GLOBAL_STRENGTH | 3.46 | 3.89 | 3.98 | 3.23 |
| POPULATION_GLOBAL | 3.48 | 5.01 | 4.82 | 3.87 |
| POPULATION_STANDARD | 3.02 | 2.94 | 2.96 | 2.86 |
| SIMPLE_VOTING | 4.14 | 2.46 | 2.47 | 3.70 |
| STANDARD_VOTING | 2.96 | 2.22 | 2.32 | 2.51 |

同一模型下六種策略的準確率最大差距（資料集平均）：
- CENTRALIZED：平均 0.20、中位數 0.01、最大 7.51 百分點
- FED_A01：平均 9.51、中位數 4.69、最大 47.77 百分點
- FED_A05：平均 3.23、中位數 1.17、最大 26.64 百分點
- FED_IID：平均 1.00、中位數 0.23、最大 12.18 百分點

（依程式內建檢查，策略間差距必然不超過該模型的衝突率。）

## 5. 規則版本：B2_TRUE_AS_FALLBACK − A_ALL_RULES（準確率，完整資料集）
| 情境 | 決策策略 | B2−A 平均 | 中位數 | B2 較好 / 持平 / 較差 |
|---|---|---:|---:|---|
| CENTRALIZED | FIRST_MATCH | 0.00 | 0.00 | 0 / 71 / 0 |
| CENTRALIZED | GLOBAL_STRENGTH | 0.00 | 0.00 | 0 / 71 / 0 |
| CENTRALIZED | POPULATION_GLOBAL | 0.00 | 0.00 | 0 / 71 / 0 |
| CENTRALIZED | POPULATION_STANDARD | 0.00 | 0.00 | 0 / 71 / 0 |
| CENTRALIZED | SIMPLE_VOTING | 0.00 | 0.00 | 0 / 71 / 0 |
| CENTRALIZED | STANDARD_VOTING | 0.00 | 0.00 | 0 / 71 / 0 |
| FED_A01 | FIRST_MATCH | 2.69 | 0.53 | 46 / 15 / 10 |
| FED_A01 | GLOBAL_STRENGTH | 3.61 | 0.92 | 48 / 13 / 10 |
| FED_A01 | POPULATION_GLOBAL | 6.08 | 1.59 | 54 / 12 / 5 |
| FED_A01 | POPULATION_STANDARD | 1.67 | 0.12 | 39 / 13 / 19 |
| FED_A01 | SIMPLE_VOTING | -0.10 | 0.00 | 27 / 12 / 32 |
| FED_A01 | STANDARD_VOTING | 0.75 | 0.10 | 40 / 12 / 19 |
| FED_A05 | FIRST_MATCH | 0.59 | 0.00 | 33 / 30 / 8 |
| FED_A05 | GLOBAL_STRENGTH | 0.84 | 0.00 | 34 / 30 / 7 |
| FED_A05 | POPULATION_GLOBAL | 1.20 | 0.00 | 34 / 30 / 7 |
| FED_A05 | POPULATION_STANDARD | 0.64 | 0.00 | 31 / 30 / 10 |
| FED_A05 | SIMPLE_VOTING | 0.13 | 0.00 | 24 / 31 / 16 |
| FED_A05 | STANDARD_VOTING | 0.44 | 0.00 | 32 / 30 / 9 |
| FED_IID | FIRST_MATCH | 0.00 | 0.00 | 0 / 71 / 0 |
| FED_IID | GLOBAL_STRENGTH | 0.00 | 0.00 | 0 / 71 / 0 |
| FED_IID | POPULATION_GLOBAL | 0.00 | 0.00 | 0 / 71 / 0 |
| FED_IID | POPULATION_STANDARD | 0.00 | 0.00 | 0 / 71 / 0 |
| FED_IID | SIMPLE_VOTING | 0.00 | 0.00 | 0 / 71 / 0 |
| FED_IID | STANDARD_VOTING | 0.00 | 0.00 | 0 / 71 / 0 |

## 6. 已記錄失敗
- OML51:openml_41027：TIMEOUT × 34
- OML51:openml_42732：TIMEOUT × 24

TIMEOUT 為協定規定的單一模型 2,700 秒上限；這些資料集在原 full_scale CI 執行中同樣大多逾時。失敗保留在分母中（MISSING.csv / FAILURES.csv）。

## 7. 判讀限制
1. 期中、非隨機缺漏：大型資料集尚未完成，且其中部分資料集的集中式模型系統性逾時，最終配對可能大量缺漏。
2. 188 個是 registry 任務，不是 188 個獨立領域；Wilcoxon 檢定把資料集視為交換單位，僅作描述性參考。
3. 與原三資料集 factorial 實驗屬不同協定，不可合併。
4. 本期中結果取自 checkpoint 快照當下（見 SNAPSHOT_STAMP 與 INTERIM_README.md）。
