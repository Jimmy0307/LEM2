# 期中結果（INTERIM）— 188 資料集 × 42 seeds 擴充實驗

> **狀態：INCOMPLETE，非最終結果。** 產生時間：2026-11-23 11:43（UTC+8）。
> 本文件只供進度報告；最終結論須待 STATUS.json 為 COMPLETE。數字會隨後續補跑改變。

## 1. 完成度
- 模型：**30,078 / 31,584**（95.2%）；結果列 360,936 / 379,008
- 完整完成的資料集（168/168 模型成功）：**179 / 188**；有任何配對結果的資料集：180
- 已記錄失敗：98 筆（全部狀態：TIMEOUT=98）

### 樣本偏誤（重要）
排程依預估運算量由重到輕排序、並受記憶體限制，因此已完成集合**不是隨機子集**。尚未全部完成的大小區間：5,000 – 50,000 列（39/43）、≥ 50,000 列（13/18）。
- 已完成資料集原始列數中位數 **1,600**；全部 188 個為 1,970

| 原始列數 | 全部 | 已完整完成 | 完成比例 |
|---|---:|---:|---:|
| < 500 | 43 | 43 | 100% |
| 500 – 5,000 | 84 | 84 | 100% |
| 5,000 – 50,000 | 43 | 39 | 91% |
| ≥ 50,000 | 18 | 13 | 72% |

- 最大的未完成資料集（CI 上單一模型常達 2,700 秒上限）：
  - OML51:openml_42732（2,215,023 列，已成功 0/168）
  - OML51:openml_42742（595,212 列，已成功 0/168）
  - OML51:openml_1169（539,383 列，已成功 0/168）
  - OML51:openml_41162（72,983 列，已成功 0/168）
  - OML51:openml_42734（50,789 列，已成功 0/168）
  - UCI20:adult_income（48,842 列，已成功 4/168）
  - OML51:openml_41027（44,819 列，已成功 2/168）
  - OML51:openml_42733（39,948 列，已成功 0/168）
  - OML51:openml_4135（32,769 列，已成功 0/168）

因此以下結論**只代表目前已完成的 179 個資料集**，不能推論到全部 188 個任務。

## 2. 主要比較：聯邦（C=3）− 集中式，準確率（百分點）
分析單位＝資料集：先在每個資料集內對 42 個 seeds 的配對差（同 seed、同規則版本、同決策策略、同來源 SHA）取平均，再跨資料集彙總。檢定為 Wilcoxon signed-rank（雙尾），36 個條件以 Holm 校正。負值＝聯邦較差。

- **Fed IID**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 1.48 至 2.30 個百分點；中位數介於 0.07 至 0.61；Fed 較差的資料集數 46–76 / 179。
- **Fed Dirichlet a=0.5**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 -3.72 至 -0.28 個百分點；中位數介於 -2.53 至 -0.48；Fed 較差的資料集數 110–125 / 179。
- **Fed Dirichlet a=0.1**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 -13.81 至 -5.48 個百分點；中位數介於 -11.68 至 -4.56；Fed 較差的資料集數 136–150 / 179。

### 2a. A_ALL_RULES（完整資料集，n=179）
| 情境 | 決策策略 | 資料集數 | 平均差 | 中位數 | Fed 較差 / 持平 / 較好 | Wilcoxon p (Holm) |
|---|---|---:|---:|---:|---|---:|
| Fed IID | FIRST_MATCH | 179 | 1.48 | 0.07 | 76 / 10 / 93 | 0.007 |
| Fed IID | GLOBAL_STRENGTH | 179 | 2.13 | 0.43 | 55 / 10 / 114 | <0.001 |
| Fed IID | POPULATION_GLOBAL | 179 | 2.01 | 0.36 | 55 / 10 / 114 | <0.001 |
| Fed IID | POPULATION_STANDARD | 179 | 2.26 | 0.54 | 46 / 10 / 123 | <0.001 |
| Fed IID | SIMPLE_VOTING | 179 | 2.06 | 0.32 | 49 / 9 / 121 | <0.001 |
| Fed IID | STANDARD_VOTING | 179 | 2.30 | 0.61 | 46 / 10 / 123 | <0.001 |
| Fed Dirichlet a=0.5 | FIRST_MATCH | 179 | -2.59 | -1.47 | 125 / 2 / 52 | <0.001 |
| Fed Dirichlet a=0.5 | GLOBAL_STRENGTH | 179 | -2.91 | -2.09 | 123 / 2 / 54 | <0.001 |
| Fed Dirichlet a=0.5 | POPULATION_GLOBAL | 179 | -3.72 | -2.53 | 124 / 2 / 53 | <0.001 |
| Fed Dirichlet a=0.5 | POPULATION_STANDARD | 179 | -1.54 | -0.85 | 116 / 2 / 61 | 0.004 |
| Fed Dirichlet a=0.5 | SIMPLE_VOTING | 179 | -0.28 | -0.48 | 110 / 3 / 66 | 0.113 |
| Fed Dirichlet a=0.5 | STANDARD_VOTING | 179 | -1.12 | -0.81 | 114 / 2 / 63 | 0.009 |
| Fed Dirichlet a=0.1 | FIRST_MATCH | 179 | -12.41 | -10.56 | 148 / 2 / 29 | <0.001 |
| Fed Dirichlet a=0.1 | GLOBAL_STRENGTH | 179 | -10.52 | -7.64 | 149 / 2 / 28 | <0.001 |
| Fed Dirichlet a=0.1 | POPULATION_GLOBAL | 179 | -13.81 | -11.68 | 150 / 2 / 27 | <0.001 |
| Fed Dirichlet a=0.1 | POPULATION_STANDARD | 179 | -7.71 | -4.95 | 143 / 2 / 34 | <0.001 |
| Fed Dirichlet a=0.1 | SIMPLE_VOTING | 179 | -5.48 | -4.56 | 136 / 3 / 40 | <0.001 |
| Fed Dirichlet a=0.1 | STANDARD_VOTING | 179 | -6.73 | -4.78 | 139 / 2 / 38 | <0.001 |

### 2b. B2_TRUE_AS_FALLBACK（完整資料集）
| 情境 | 決策策略 | 資料集數 | 平均差 | 中位數 | Fed 較差 / 持平 / 較好 | Wilcoxon p (Holm) |
|---|---|---:|---:|---:|---|---:|
| Fed IID | FIRST_MATCH | 179 | 1.48 | 0.07 | 76 / 10 / 93 | 0.007 |
| Fed IID | GLOBAL_STRENGTH | 179 | 2.13 | 0.43 | 55 / 10 / 114 | <0.001 |
| Fed IID | POPULATION_GLOBAL | 179 | 2.01 | 0.36 | 55 / 10 / 114 | <0.001 |
| Fed IID | POPULATION_STANDARD | 179 | 2.26 | 0.54 | 46 / 10 / 123 | <0.001 |
| Fed IID | SIMPLE_VOTING | 179 | 2.06 | 0.32 | 49 / 9 / 121 | <0.001 |
| Fed IID | STANDARD_VOTING | 179 | 2.30 | 0.61 | 46 / 10 / 123 | <0.001 |
| Fed Dirichlet a=0.5 | FIRST_MATCH | 179 | -1.81 | -1.07 | 120 / 3 / 56 | <0.001 |
| Fed Dirichlet a=0.5 | GLOBAL_STRENGTH | 179 | -1.30 | -0.94 | 115 / 2 / 62 | 0.006 |
| Fed Dirichlet a=0.5 | POPULATION_GLOBAL | 179 | -1.72 | -1.00 | 118 / 2 / 59 | 0.001 |
| Fed Dirichlet a=0.5 | POPULATION_STANDARD | 179 | -0.41 | -0.51 | 111 / 2 / 66 | 0.113 |
| Fed Dirichlet a=0.5 | SIMPLE_VOTING | 179 | -0.15 | -0.46 | 109 / 3 / 67 | 0.113 |
| Fed Dirichlet a=0.5 | STANDARD_VOTING | 179 | -0.25 | -0.49 | 111 / 2 / 66 | 0.113 |
| Fed Dirichlet a=0.1 | FIRST_MATCH | 179 | -9.34 | -7.58 | 144 / 2 / 33 | <0.001 |
| Fed Dirichlet a=0.1 | GLOBAL_STRENGTH | 179 | -6.03 | -5.16 | 141 / 2 / 36 | <0.001 |
| Fed Dirichlet a=0.1 | POPULATION_GLOBAL | 179 | -6.26 | -5.66 | 141 / 2 / 36 | <0.001 |
| Fed Dirichlet a=0.1 | POPULATION_STANDARD | 179 | -5.28 | -4.59 | 135 / 2 / 42 | <0.001 |
| Fed Dirichlet a=0.1 | SIMPLE_VOTING | 179 | -5.49 | -4.39 | 137 / 2 / 40 | <0.001 |
| Fed Dirichlet a=0.1 | STANDARD_VOTING | 179 | -5.21 | -4.71 | 135 / 2 / 42 | <0.001 |

平衡準確率（balanced accuracy）的同型表格見 `interim_fed_minus_central_complete_datasets.csv`；
納入所有有配對資料集（含未跑完者，以現有 seeds 平均）的敏感度分析見 `interim_fed_minus_central_all_paired_datasets.csv`。

## 3. 結構面：覆蓋率、衝突率、規則數（A_ALL_RULES，資料集平均：集中式 → 聯邦）
| 情境 | 測試覆蓋率 % | 衝突率 % | 規則數 |
|---|---|---|---|
| Fed IID | 27.56 → 46.75 | 1.26 → 13.08 | 56.7 → 111.0 |
| Fed Dirichlet a=0.5 | 27.56 → 64.63 | 1.26 → 27.20 | 56.7 → 96.3 |
| Fed Dirichlet a=0.1 | 27.56 → 86.54 | 1.26 → 55.48 | 56.7 → 70.0 |

## 4. 六種決策策略（A_ALL_RULES）
資料集內排名（1＝準確率最高，同分取平均）跨資料集平均：

| 決策策略 | CENTRALIZED | FED_A01 | FED_A05 | FED_IID |
|---|---:|---:|---:|---:|
| FIRST_MATCH | 4.05 | 4.67 | 4.28 | 4.83 |
| GLOBAL_STRENGTH | 3.48 | 3.89 | 4.04 | 3.28 |
| POPULATION_GLOBAL | 3.46 | 5.05 | 4.97 | 3.98 |
| POPULATION_STANDARD | 3.07 | 2.82 | 2.94 | 2.85 |
| SIMPLE_VOTING | 3.87 | 2.26 | 2.46 | 3.53 |
| STANDARD_VOTING | 3.07 | 2.31 | 2.32 | 2.54 |

同一模型下六種策略的準確率最大差距（資料集平均）：
- CENTRALIZED：平均 0.30、中位數 0.02、最大 8.25 百分點
- FED_A01：平均 10.73、中位數 7.91、最大 47.77 百分點
- FED_A05：平均 4.19、中位數 2.23、最大 26.64 百分點
- FED_IID：平均 1.32、中位數 0.41、最大 13.15 百分點

（依程式內建檢查，策略間差距必然不超過該模型的衝突率。）

## 5. 規則版本：B2_TRUE_AS_FALLBACK − A_ALL_RULES（準確率，完整資料集）
| 情境 | 決策策略 | B2−A 平均 | 中位數 | B2 較好 / 持平 / 較差 |
|---|---|---:|---:|---|
| CENTRALIZED | FIRST_MATCH | 0.00 | 0.00 | 0 / 179 / 0 |
| CENTRALIZED | GLOBAL_STRENGTH | 0.00 | 0.00 | 0 / 179 / 0 |
| CENTRALIZED | POPULATION_GLOBAL | 0.00 | 0.00 | 0 / 179 / 0 |
| CENTRALIZED | POPULATION_STANDARD | 0.00 | 0.00 | 0 / 179 / 0 |
| CENTRALIZED | SIMPLE_VOTING | 0.00 | 0.00 | 0 / 179 / 0 |
| CENTRALIZED | STANDARD_VOTING | 0.00 | 0.00 | 0 / 179 / 0 |
| FED_A01 | FIRST_MATCH | 3.07 | 0.96 | 127 / 29 / 23 |
| FED_A01 | GLOBAL_STRENGTH | 4.49 | 1.27 | 127 / 26 / 26 |
| FED_A01 | POPULATION_GLOBAL | 7.55 | 2.77 | 141 / 24 / 14 |
| FED_A01 | POPULATION_STANDARD | 2.43 | 0.27 | 107 / 25 / 47 |
| FED_A01 | SIMPLE_VOTING | -0.01 | 0.00 | 74 / 24 / 81 |
| FED_A01 | STANDARD_VOTING | 1.52 | 0.24 | 110 / 24 / 45 |
| FED_A05 | FIRST_MATCH | 0.77 | 0.00 | 90 / 62 / 27 |
| FED_A05 | GLOBAL_STRENGTH | 1.61 | 0.13 | 106 / 56 / 17 |
| FED_A05 | POPULATION_GLOBAL | 1.99 | 0.15 | 107 / 56 / 16 |
| FED_A05 | POPULATION_STANDARD | 1.13 | 0.01 | 95 / 56 / 28 |
| FED_A05 | SIMPLE_VOTING | 0.13 | 0.00 | 65 / 65 / 49 |
| FED_A05 | STANDARD_VOTING | 0.87 | 0.01 | 95 / 56 / 28 |
| FED_IID | FIRST_MATCH | 0.00 | 0.00 | 0 / 179 / 0 |
| FED_IID | GLOBAL_STRENGTH | 0.00 | 0.00 | 0 / 179 / 0 |
| FED_IID | POPULATION_GLOBAL | 0.00 | 0.00 | 0 / 179 / 0 |
| FED_IID | POPULATION_STANDARD | 0.00 | 0.00 | 0 / 179 / 0 |
| FED_IID | SIMPLE_VOTING | 0.00 | 0.00 | 0 / 179 / 0 |
| FED_IID | STANDARD_VOTING | 0.00 | 0.00 | 0 / 179 / 0 |

## 6. 已記錄失敗
- OML51:openml_41027：TIMEOUT × 70
- OML51:openml_42732：TIMEOUT × 28

TIMEOUT 為協定規定的單一模型 2,700 秒上限；這些資料集在原 full_scale CI 執行中同樣大多逾時。失敗保留在分母中（MISSING.csv / FAILURES.csv）。

## 7. 判讀限制
1. 期中、非隨機缺漏：大型資料集尚未完成，且其中部分資料集的集中式模型系統性逾時，最終配對可能大量缺漏。
2. 188 個是 registry 任務，不是 188 個獨立領域；Wilcoxon 檢定把資料集視為交換單位，僅作描述性參考。
3. 與原三資料集 factorial 實驗屬不同協定，不可合併。
4. 本期中結果取自 checkpoint 快照當下（見 SNAPSHOT_STAMP 與 INTERIM_README.md）。
