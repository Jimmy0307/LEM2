# LEM2 2026-11-11：稽核問題修復、外部測試與最佳條件比較

## 修復一：Hayes-Roth 測試協定

原 8,820 筆資料中，Hayes-Roth 只使用 UCI 的 132 筆訓練子集，然後在其中執行 80/20 重複切分；其中多個測試物件的四項特徵組合也在訓練資料出現。因此此結果不等於 UCI 原始 28 筆獨立測試的成果。

新增兩個獨立的評估協定：

- UCI_OFFICIAL_132_28：132 筆固定訓練，28 筆固定外部測試。
- GROUP_HOLDOUT_80_20：132 筆內依全部四項特徵組合分組，確保 Train/Test 沒有相同特徵組合；分組時保留各真實類別並記錄 Test 數。

2 個協定 × 42 個 Seed × 5 種學習架構 × 6 個分類方法，共 2,520 列結果，獨立保存在 [Hayes 評估資料](data/HAYES_HOLDOUT_PROTOCOLS_42SEEDS.csv)。

以 BA 選最佳模型的數字如下：

| 協定 | 最佳模型（以 BA 排序） | Accuracy | Balanced Accuracy |
|---|---|---:|---:|
| 原本 132 筆內重複 80/20 | Centralized + GS／PG | 82.05% | 84.44% |
| 固定 132 訓練／28 測試 | Centralized，六策略並列 | 85.71% | 89.74% |
| Group-disjoint 80/20 | Centralized + GS／PG | 81.68% | 87.06% |

上述數值的資料母體／訓練量不同，不可以將百分比差值直接當成某個方法改善所造成的因果效果。UCI 官方測試使用固定 Test，且集中式訓練也固定，因此 42 Seed 下相同的集中式結果不能作 42 次獨立評估。

**測試資料來源與來源驗證限制**：UCI Hayes-Roth (https://archive.ics.uci.edu/dataset/44/hayes+roth) 列出 132 Train、28 Test。版本化的 28 列測試檔取自公開 GitHub 鏡像 LucasBoTang/Optimal_Classification_Trees/data/hayes-roth/hayes-roth.test，長度為 280 bytes。資料筆數與 UCI 格式一致，但尚未做與 UCI 原伺服器檔案的位元組／SHA 完全比對；正式投稿應補驗 checksum。

## 修復二：Conflict 準確分流

以下五組互斥且窮盡所有評估物件：

1. No Match：沒有規則命中。
2. 有規則命中、無正確候選、無跨類別 Conflict。
3. 有規則命中、有正確候選、無跨類別 Conflict。
4. 有 Conflict 且真實類別在 Candidate。
5. 有 Conflict 但真實類別不在 Candidate。

Conflict rate 是第 4 與第 5 組的合計，分母為全部 Test；它不是第 4 組單獨的占比。衝突解消 Accuracy 是衝突物件中最終答對者的比例。原網站把「衝突且有正解候選」標題搭配所有 Conflict 物件百分比的錯誤已改為只有在真實交集資料存在時才顯示正確值，否則標記未驗證。

逐筆資料來自已通過的 42 Seeds ROW_CASES GitHub Actions Run 42644663319。新增 [真實交集與決策錯誤統計](data/CONFLICT_EXACT_42SEEDS.csv)，共 7,560 個具選擇策略的配置，每筆計數都核對至凍結 8,820 主矩陣。

## 修復三：統計推論與最佳條件排名

[最佳條件互動看板](ranking/)只用未見測試的 HOLDOUT_80_20；禁止將 Full Data 回代加入泛化排名。

排名方法：同一 Dataset、Seed、Split、架構、Client 與策略先得到績效；跨 42 Seed 等權平均。三資料集同時比較時，先取每 Seed 三資料集的等權平均。Accuracy、Balanced Accuracy 和 Macro-F1 分別排序，不混用成自訂「綜合分數」。同時呈現 42 Seed 標準差、第一與第二名的百分點差距，以及 Conflict 和 Coverage。標準差只能反映相同資料集多次切分的變動，不能解讀為外部獨立樣本 95% 信賴區間；排名差異不是統計顯著性證明。

**原始 80/20 主矩陣，42 Seed 逐資料集最佳平均：**

| 資料集 | Accuracy 最佳 | Accuracy | BA 最佳 | BA | F1 最佳 | F1 |
|---|---|---:|---|---:|---|---:|
| Balance Scale | Fed C5 + PS | 82.80% | Fed C5 + PG | 61.08% | Fed C5 + PG | 60.24% |
| Car Evaluation | Centralized + STD／PS | 90.10% | Fed C3 + PG | 72.19% | Centralized + STD／PS | 74.64% |
| Hayes-Roth | Centralized + GS／PG | 82.05% | Centralized + GS／PG | 84.44% | Centralized + GS／PG | 84.10% |

**研究結論的限制**：只能說在這三組資料、此 Classical reduct/LEM2、指定切分與選擇器條件下，觀察到績效與候選衝突的取捨。不應宣稱已證明新方法對所有資料有普遍優勢、不同協定的精度差異由切分單因素造成，或將 8,820 筆配置當作 8,820 個獨立樣本。

## 程式與驗證

- [主報告](./)
- [哪個條件最好？](ranking/)
- [所有 8,820 筆](evidence/)
- [Hayes 新協定原始程式](../../../teacher_demo/hayes_protocol_validation.py)
- [Hayes 42 Seeds GitHub Actions](https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-hayes-protocols.yml)
- [Conflict 交集來源程式](../../../teacher_demo/build_exact_conflict.py)
- [Conflict 交集 GitHub Actions](https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-conflict-exact.yml)

原本凍結的 8,820 列維持不變。
