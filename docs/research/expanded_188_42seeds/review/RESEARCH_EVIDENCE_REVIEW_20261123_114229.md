# 聯邦 LEM2｜擴充實驗研究證據審查（2026-11-23 上午快照）

> **Evidence review / snapshot-locked / NOT FINAL**  
> 本文為獨立分析與老師報告審查備忘錄，不是原始 checkpoint、不取代自動生成的 `INTERIM_FINDINGS.md`，也不修改任何科學程式。所有統計數字鎖定快照 `20261123T114229`（Asia/Taipei），來源版本 `fcf1f2b4466594b73595378e10e93659411c96c5`。分支發布器會持續更新主目錄；請勿混用不同時間點資料。

## A. 摘要與可證實完成度

| 項目 | 03:53 期中快照 | 11:42 期中快照 | 變動 |
|---|---:|---:|---:|
| 成功模型 | 12,341 / 31,584 | **30,078 / 31,584** | +17,737 |
| 完整資料集（168/168 全成功） | 71 / 188 | **179 / 188** | +108 |
| 結果列 | 148,092 | **360,936** | +212,844 |
| 已記錄 TIMEOUT | 58 | **98** | +40 |
| 可配對資料集（含尚未完整者） | 80 | **180** | +100 |

- 模型完成率 **95.2%**，**仍為 INCOMPLETE**；未成功完成模型 **1,506**。
- 有效分析單位為 **registry dataset**，而非模型列或個別 seed；先平均每個資料集 42 seeds 的同 seed 配對差，再跨資料集做統計。
- 六種方法、兩個 rule variants、三種聯邦場景（相對同 seed 集中式），以 **Wilcoxon signed-rank 雙尾檢定**進行比較；每個指標的 36 個比較使用 Holm 校正。
- 該 188 個任務不是 188 個獨立學術領域；結果偏向描述性跨資料集證據，不能直接解釋為獨立抽樣的外推推論。

## B. 重要的研究結論變化：71 → 179 個完整資料集

**Fed − Centralized、百分點（pp），A_ALL_RULES：**

| 情境 | 六策略平均 Accuracy 差異範圍 | 179 資料集 Holm 後顯著性 | 與凌晨結論的差異 |
|---|---:|---|---|
| FED_IID | +1.48 至 +2.30 | 六策略均顯著正向 | 正向依然存在；平均效果較凌晨收斂 |
| FED_A05 | −3.72 至 −0.28 | **5/6 顯著負向**；SIMPLE_VOTING p=0.113 | **重大翻轉：凌晨六策略均未顯著** |
| FED_A01 | −13.81 至 −5.48 | 六策略均顯著負向 | 負向效果在增加樣本後依舊穩健 |

**核心修正：不可以再將 a=0.5 寫作「無顯著差異」。** 對 A_ALL_RULES 而言，179 個資料集的五種策略已有顯著的負向 Accuracy 差異；SIMPLE_VOTING 例外。

### Accuracy 與 Balanced Accuracy 的指標依賴性

六策略各情境的 dataset-level **Balanced Accuracy 差異**及 Holm 校正後 p 值（取自同一 CSV；差距為 Fed − Central）：

| 情境 | 策略 | Accuracy 差異 pp | BA 差異 pp | BA Holm p |
|---|---|---:|---:|---:|
| A05 | FIRST_MATCH | −2.59 | +1.18 | 0.000987 |
| A05 | GLOBAL_STRENGTH | −2.91 | +0.65 | 0.017686 |
| A05 | POPULATION_GLOBAL | −3.72 | +0.17 | 0.099966 |
| A05 | POPULATION_STANDARD | −1.54 | +0.45 | 0.043656 |
| A05 | SIMPLE_VOTING | −0.28 | +1.85 | 0.0000138 |
| A05 | STANDARD_VOTING | −1.12 | +0.93 | 0.008182 |
| A01 | FIRST_MATCH | −12.41 | −3.16 | 0.208403 |
| A01 | GLOBAL_STRENGTH | −10.52 | −5.00 | 0.000800 |
| A01 | POPULATION_GLOBAL | −13.81 | −6.60 | 0.00000262 |
| A01 | POPULATION_STANDARD | −7.71 | −4.39 | 0.034119 |
| A01 | SIMPLE_VOTING | −5.48 | −1.32 | 0.698420 |
| A01 | STANDARD_VOTING | −6.73 | −3.31 | 0.147489 |

- 在 **A05**，六策略 Accuracy 差距均為負，但 BA 差距均為正，五策略的 BA 正向差異通過 Holm 校正。這是新的研究焦點：**可能涉及不同類別的辨識取捨**；沒有 class-wise confusion matrix 前，不得聲稱已證明其機制。
- 在 **A01**，Accuracy 六策略顯著負向，但 BA 僅 GLOBAL_STRENGTH、POPULATION_GLOBAL、POPULATION_STANDARD 顯著負向。
- balanced accuracy 表示 macro recall，不等於 accuracy，也不應混稱為 macro F1。

## C. 結構證據：覆蓋與衝突同時上升

A_ALL_RULES，179 個資料集內 42 seeds 平均後再跨 dataset 平均：

| 比較 | Test coverage（Central→Fed） | Conflict rate（Central→Fed） | Rules（Central→Fed） |
|---|---|---|---|
| IID | 27.56%→46.75% | 1.26%→13.08% | 56.7→111.0 |
| A05 | 27.56%→64.63% | 1.26%→27.20% | 56.7→96.3 |
| A01 | 27.56%→86.54% | 1.26%→55.48% | 56.7→70.0 |

**判讀**：覆蓋提升不代表準確率提升；嚴重 non-IID 的聯邦模型雖有更高覆蓋率，也有更高衝突率。這是結構與績效的**共現描述**，尚非因果證明。A01 相較 IID 的規則數更少，不能簡化說成「所有聯邦模型一律規則暴增」。

## D. 策略效果與 B2 消融

- **A_ALL_RULES 的平均策略排名**：IID 最佳 STANDARD_VOTING (2.54)；A05 最佳 STANDARD_VOTING (2.32)；A01 最佳 SIMPLE_VOTING (2.26)，STANDARD_VOTING 接近 (2.31)。POPULATION_GLOBAL 在 A05 (4.97) 與 A01 (5.05) 排名最後。
- **排名不是策略間顯著性檢定**。如需支持「策略 A 優於策略 B」，需使用同資料集的策略對策略配對差、校正與效果量。
- **B2_TRUE_AS_FALLBACK** 定義為：若有匹配的具體前件規則，空前件 TRUE 規則不參與投票；只有沒有具體規則匹配時才啟用 TRUE 規則。定義以 `fedrs/predict.py::variant_matrix` 為準；**不是使用測試標籤做 fallback**。
- A01 下 B2−A 平均 Accuracy (pp)：FIRST +3.07、GLOBAL +4.49、POP_GLOBAL +7.55、POP_STANDARD +2.43、SIMPLE −0.01、STANDARD +1.52。其中 POP_GLOBAL 為 141/179 資料集改善、24 持平、14 退步；不應宣稱 B2 對全部策略普遍有利。
- B2 在 CENTRALIZED 與 IID 下六策略均顯示 0.00 pp 差異（目前完整資料集）。

## E. 樣本組成、可用性與終止條件

| Cohort | 已完整 / 全部 |
|---|---:|
| PMLB | 93 / 93 |
| UCI20 | 19 / 20 |
| NEXT12 | 12 / 12 |
| EXT7 | 7 / 7 |
| COMMERCE2 | 2 / 2 |
| O3 | 3 / 3 |
| OML51 | 43 / 51 |
| **合計** | **179 / 188** |

資料列數區間完成率：<500 為 43/43；500–4,999 為 84/84；5,000–49,999 為 39/43；≥50,000 為 13/18。剩下樣本集中於部分大型及計算困難資料集，仍有選擇偏差。

未完全成功九資料集：UCI20:adult_income（4/168）；OML51:openml_41027（2/168）；OML51:openml_1169、openml_4135、openml_41162、openml_42732、openml_42733、openml_42734、openml_42742（各 0/168）。

共 98 個逾時：openml_41027 ×70；openml_42732 ×28（每模型 2,700 秒限制）。**請分開標記 COMPLETE_SUCCESS、TERMINAL_WITH_FAILURES、INCOMPLETE**，避免將 timeout 當成功，或讓永遠無法全成功的 source 阻擋研究封存。

敏感度樣本 **n=180**（有配對資料即納入）與主要 **n=179** 的方向及關鍵結論大致一致；但含不完整 seeds 的敏感度集合可能產生不同權重，不能替代主要分析。

## F. 資料發布與治理風險

- 在相同最新 HEAD 的主目錄 `docs/research/expanded_188_42seeds/STATUS.json` 顯示 **177 datasets / 30,014 models**，而 `interim/STATUS.json` 顯示 **179 / 30,078**。兩檔並非同一時點 snapshot；**本審查只採 interim/SNAPSHOT_STAMP = 20261123T114229 的鎖定數值**，不得跨快照混用分母。
- 來源追溯使用 `SOURCE_REGISTRY.csv` 與 checkpoints 的 `SOURCE.json`；188 是待分析 registry 任務，不代表彼此完全獨立。
- 檢核表應明列 source SHA、split contract `NESTED_64_16_20`、seed、rule variant、policy、失敗處理、freeze timestamp、計算程式 SHA；主程式與外掛排程器分開驗證。
- 此次核對了 GitHub 已發布的摘要、統計 CSV、`fedrs/predict.py::variant_matrix` 與 `COMPLETENESS.csv`，**未**對全部 gz 原始結果及二進位 checkpoint 做獨立全量重算，亦**未**執行簡報 PDF/PPTX 的逐頁視覺驗收。

## G. 給老師的報告修訂優先序

1. **P0｜更新主結論**：A05 不能再寫「均不顯著」；增加 Accuracy vs BA 分歧，以及其 Holm p 值；明確註記 n=179。
2. **P0｜快照一致性**：所有圖表同時標示 `snapshot=20261123T114229`、`commit=fcf1f2b`、`n=179`；不能從 root STATUS 混抓 n=177。
3. **P0｜方法學界線**：教師原 3-dataset factorial、歷史 8,820 紀錄、本輪 188×42 expansion 使用不同協定；不要合併檢定或混稱。
4. **P1｜機制證據**：加入 class-wise recall/confusion matrix、prediction shares、conflict subset performance；檢驗 A05 的 Accuracy−、BA+ 是否與類別分布改變有關。
5. **P1｜推論穩健性**：對 179 datasets 依資料來源群組及 size bin 做分層／剔除敏感度分析；如同源或高度相關任務存在，需適當降權或叢集處理。
6. **P1｜策略優劣**：補方法對方法的 paired comparison，不能單憑平均 rank 宣稱勝出。
7. **P1｜報告 UX**：老師首頁依研究問題→方法→比較→機制→限制鋪排；每個主張附原始表、來源 checkpoint、腳本與限制。現有 dashboard 偏向歷史 42-seed／8,820 rows，需有最新 expansion 入口；該頁尚未做瀏覽器實際渲染驗收。

## H. 來源／可重現路徑

- [Snapshot findings](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/docs/research/expanded_188_42seeds/interim/INTERIM_FINDINGS.md)
- [Snapshot status](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/docs/research/expanded_188_42seeds/interim/STATUS.json)
- [Primary paired stats including BA and Holm p](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/docs/research/expanded_188_42seeds/interim/interim_fed_minus_central_complete_datasets.csv)
- [Sensitivity paired stats](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/docs/research/expanded_188_42seeds/interim/interim_fed_minus_central_all_paired_datasets.csv)
- [Completeness](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/docs/research/expanded_188_42seeds/interim/COMPLETENESS.csv)
- [Analysis script](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/tools/expanded_resume_20261122/interim_findings.py)
- [Rule variant source](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/fedrs/predict.py)
- [Snapshot stamp](https://github.com/Jimmy0307/LEM2/blob/fcf1f2b4466594b73595378e10e93659411c96c5/docs/research/expanded_188_42seeds/interim/SNAPSHOT_STAMP)

**結論：** 本版已可做「接近全量、但尚有選擇偏差的期中進度報告」，不宜宣告 188 任務全面完成；最有研究價值的新訊號是 A05 下 Accuracy 降、Balanced Accuracy 升的指標分歧，以及 A01 下覆蓋與衝突同步增長、策略排名差異擴大。
