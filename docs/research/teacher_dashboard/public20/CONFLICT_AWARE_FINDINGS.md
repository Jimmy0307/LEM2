# Conflict-Aware Coverage Expansion：20 個公開資料集首次實測與失敗模式

> **實驗結果：PASS；研究假設：尚未支持「守門機制普遍改善實際衝突」。**
> 單 Seed 42、20 資料集、集中式與 Fed C3 共 40 組配對。
> 真正的 64% induction / 16% inner validation / 20% held-out TEST。
> 120 列三版本結果、423 筆補充規則選擇事件。
> 本研究方法是自定義簡化補充規則＋單次貪婪驗證守門，**不是**既有 VC-DomLEM／MLEM2 原典重現。

## 1. 獨立實驗的三個版本

- **BASE_LEM2**：正域約簡＋Classical LEM2，Global Strength 決策；No Match 仍回退 Train Majority Class。
- **ALL_TRAIN_SUPPLEMENTS**：在相同原始規則集合外，加入所有合格（Train purity≥90%、Support≥5、最多 80 條）的單一前件刪除補充規則；僅在原規則 No Match 時啟用。
- **VALIDATION_GATED_CONFLICT_AWARE**：使用相同候選，固定依訓練純度／支持數排序，逐條測試 Inner Validation 的覆蓋增幅、Accuracy／Balanced Accuracy、Active Conflict、組合收益，拒絕不合格候選；**Test 標籤從未參與規則選擇**。

與原本 20 資料集的第一輪 Seed42 研究相比，新的原始基線使用 64% 訓練資料而不是 80%，因為另外 16% 留作沒有資料洩漏的規則審查。**不能把兩批基線的百分比直接相減。**

## 2. 40 組配置等權平均的結果

| 測試指標 | 原始 LEM2 | 全部合格補充規則 | 衝突守門篩選後 |
|---|---:|---:|---:|
| Test Match Coverage (%) | 53.509 | 61.433 | 61.144 |
| 正確候選覆蓋率 (%) | 45.486 | 52.420 | 52.227 |
| Active Conflict Rate (%) | 8.654 | 8.712 | 8.705 |
| Shadow Conflict Rate (%) | 8.654 | 9.455 | 8.903 |
| Overall Accuracy (%) | 70.267 | 70.577 | 70.581 |
| Balanced Accuracy (%) | 61.942 | 62.450 | 62.427 |
| 每配置平均保留補充規則 | 0 | 10.575 | 2.675 |

數字源自 [120 列完整方法輸出](../data/CONFLICT_AWARE_20_RESULTS.csv) 及 [40 配置配對增減](../data/CONFLICT_AWARE_20_PAIRED.csv)。**所有數字均為單 Seed 的描述統計，不是多 Seed 或跨樣本推論。**

主要比較：
- 全部補充：Coverage **+7.924 pp**，Active Conflict **+0.058 pp**，Shadow Conflict **+0.801 pp**，Accuracy **+0.310 pp**，Balanced Accuracy **+0.509 pp**。
- 守門篩選：Coverage **+7.635 pp**，Active Conflict **+0.051 pp**，Shadow Conflict **+0.249 pp**，Accuracy **+0.314 pp**，Balanced Accuracy **+0.485 pp**。
- 比起全部補充，守門機制只讓 Test Active Conflict 平均下降 **0.007 pp**，在 **40 組中僅 1 組**確實降低；但 Shadow Conflict 平均下降 **0.553 pp**。
- 29／40 組至少淘汰部分合格候選，17／40 組仍選入至少一條規則；平均保留補充規則數由 10.575 降至 2.675（約少 74.7%）。

## 3. 為什麼沒有明顯降低衝突？

**我們把兩種衝突嚴格分開：**

1. **Active Conflict**：在實際的 *original exact rules first / supplement only on No Match* 流程中，一個物件於當前生效層同時得到多個不同決策。
2. **Shadow Conflict**：假設忽略生效優先序，把原始與補充規則直接合併後，同個物件得到多個不同決策的潛在衝突。

本批有 **28／40 組原始基線就已有 Active Conflict**。當補充規則只在原始 No Match 執行，原有衝突完全不受這一層的加減影響。

所以全部補充雖使 Shadow Conflict 在 **17／40 組**上升，Active Conflict 卻只在 **2／40 組**上升。把驗證守門加到補充規則，對原本就有的衝突並沒有施力點。這是機制限制，而非單純調高懲罰參數就能解決。

## 4. 代表性案例：守門並非普遍勝出

### Banknote／集中式：成功攔截會造成測試錯誤的候選

- 全部補充：Test Coverage +21.17 pp，但 Accuracy **−0.73 pp**。
- 守門：Test Coverage +19.71 pp，Accuracy **+0.00 pp**（相對 Baseline）。
- 守門只接受 1／6 條候選，證明固定驗證風險管制有機會避免部分負面效應；但只是一組配置、單一 Seed。

### Adult Income／集中式：少了衝突，也犧牲一些準確性收益

- 全部補充：Coverage +9.17 pp，Active Conflict +0.56 pp，Accuracy +0.28 pp，BA +0.98 pp。
- 守門：Coverage +6.94 pp，Active Conflict +0.28 pp，Accuracy +0.00 pp，BA +0.00 pp。
- 守門把 Active Conflict 的增幅減半，但同時失去原本的分類增益；這不是無條件更好的方法。

### Breast Diagnostic／聯邦 C3：驗證集保護不等於測試集保證

- 全部補充：Accuracy 相對原始基線 **−1.77 pp**。
- 守門後依然 **−1.77 pp**，雖然其 Coverage 增加較少。
- 表示單一驗證分割、有限風險閾值的守門對 Test 不提供強保證；不適合直接在醫療情境部署。

## 5. 現階段支持與不支持的結論

**有證據支持的探索性觀察**：
- 補充規則能提高 Test Match Coverage 和正確候選覆蓋，但平均分類效果較小。
- 原始命中優先的兩層決策，有效限制補充規則干擾原始規則已覆蓋物件。
- 驗證守門能縮減需要保留／管理的補充規則集合，降低潛在直接合併時的 Shadow Conflict。
- 同一 Seed 的風險、覆蓋、衝突三者存在可觀測的取捨。

**此實驗尚未支持的論點**：
- 不能說 Conflict-Aware Gate 在這 20 個資料集顯著提高 Accuracy／Balanced Accuracy。
- 不能說它解決了 Federated 原始規則合併後的衝突。
- 不能說 64/16/20 一次測試證明有效；需要多 Seed、獨立資料特徵與統計不確定性估計。
- 不能把 No Match 直接叫做系統有真的執行 Reject；本專案目前 No Match 依然有 Train Majority fallback。

## 6. 下一步研究分岔

目前更值得研究的不是單純增加補充規則的衝突懲罰，而是**直接針對原始規則系統設計 Conflict-aware Core Rule Selection**：

- 首先辨識哪些原始規則造成跨決策重疊／錯誤候選，區分「正解已存在、Winner 選錯」和「正解不在候選集合」；
- 在*訓練／驗證*層級評估核心規則的刪減、權重修正、各類別候選保留與有效覆蓋成本；
- 再以補充規則處理剩餘 No Match，避免兩層決策的衝突指標混淆；
- 用資料集與 Seed 完整配對比較 BASE、ALL 補充、GATED 補充、CORE CONFLICT 整理及 CORE+SUPPLEMENT。

**這屬下一輪待實作及驗證的研究方向，不是本輪已證實的演算法能力。**

## 7. 可重現性

- [20 個來源與固定子集完整 Manifest](../data/PUBLIC20_MANIFEST.json)
- [120 列三版本結果](../data/CONFLICT_AWARE_20_RESULTS.csv)
- [40 組配對分析](../data/CONFLICT_AWARE_20_PAIRED.csv)
- [423 個候選規則的逐條審查事件](../data/CONFLICT_AWARE_20_GATE_EVENTS.csv)
- [40 組規則層診斷](../data/CONFLICT_AWARE_20_AUDIT.csv)
- [嵌套驗證、稽核與限制](../data/CONFLICT_AWARE_20_MANIFEST.json)
- [GitHub Actions 完整執行證據](https://github.com/Jimmy0307/LEM2/actions/workflows/conflict-aware-20-pilot.yml)
- 程式：`teacher_demo/conflict_aware_coverage_pilot.py`、`teacher_demo/summarize_conflict_aware_20.py`；測試：`teacher_demo/test_conflict_aware_coverage.py`。
