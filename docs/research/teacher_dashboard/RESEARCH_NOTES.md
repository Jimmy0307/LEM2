# 教授報告的研究結論與證據地圖

**基線：** 3 資料集 × 42 Seeds × 2 Split Modes × 5 Topologies × 7（NONE＋6 Policies）＝ 8,820 組。來源為 GitHub 原始 LEM2／Classical reduct 實驗，不代表 DRSA 或 LERS 分類基準已完成。

## 1. 明確區分 LEM2、NONE 與六種分類

1. **純 LEM2：** 輸出 IF–THEN 規則集合，不是直接輸出唯一分類結果。
2. **NONE：** 將規則匹配到測試物件，取得 Coverage、No Match、Conflict、True-in-Candidate，但不報 Accuracy。
3. **六種策略：** FIRST、SIMPLE、STD、GS、PS、PG 使用固定規則集合產生最終 Winner，才能計算 Accuracy／Balanced Accuracy／Macro-F1。

## 2. 42 Seeds 觀察到的現象

在三資料集等權平均、80/20 未見資料的範圍內：

| 拓樸 | 跨決策規則 Conflict rate |
|---|---:|
| Centralized | 10.57% |
| Federated C2 | 27.75% |
| Federated C3 | 46.07% |
| Federated C4 | 59.72% |
| Federated C5 | 68.67% |

隨 Client 增加，平均 Conflict 上升。但此為特定三資料集和分層切分的觀察，不能直接推廣到所有 non-IID 任務。

**GS vs STD：** 在同一資料集／Seed／Client 的配對設計中，GS 的 Federated Balanced Accuracy 平均增益約 +5.16 個百分點；但是分資料集比較的 GS−STD 差異約為 Balance Scale −0.11、Car Evaluation +9.85、Hayes-Roth +5.74 個百分點。不能說 GS 在所有資料集都比較好。

### 獨立擴充實驗

- **non-IID Dirichlet（7 Seeds）：** IID 分層、α=0.5、α=0.1 會造成明顯不同的 Conflict／GS 成績。該 588 列結果不是 8,820 正式基線的一部分。
- **Client 順序（Seed 42）：** 每個資料集對 C2/C3/C4/C5 完整枚舉 2、6、24、120 種 FIRST_MATCH 合併順序；三資料集合計 456 組。FIRST_MATCH Winner 可受順序影響。
- **DRSA reduct／完整 LERS 原典分類器：** 尚未執行，不可以 Classical Reduct 或 GS 冒充。

## 3. Conflict 後不是「一律套六種公式」就能解決

給任意測試物件 x：

- Rule Matching：M(x)＝所有條件匹配的規則
- Candidate(x)＝這些規則提出的決策類別
- Conflict(x)＝候選決策數 ≥ 2

**四種類型要分開管理：**

| 類型 | 判斷 | 問題所在 | 對應改善 |
|---|---|---|---|
| NO_MATCH | M(x) 為空 | 規則覆蓋不足 | 規則歸納、特徵分箱、Fallback／Abstain |
| TRUE_NOT_IN_CANDIDATE | 有規則但真實類別不在候選 | 候選生成失敗 | 修改資料分割／特徵／Local LEM2 |
| WRONG_RANKING | 真實類別在候選，但最後選錯 | 衝突解消／排序失誤 | 比較六策略的 T/U/N 與 Winner |
| CORRECT | 最終預測正確 | 保留可稽核證據 | 對照規則支持與穩健性 |

原程式 No Match 使用訓練資料多數類別 Fallback，可能恰巧答對；不能把 No Match 全部算成錯誤。新的人工覆核或拒答 Gate 仍待正式實驗驗證。

## 4. 報告可核對的資料鏈

- 研究基線：[42 Seeds 8,820 列](../../seed_sweep_1_42/tables/SEED_SWEEP_8820.csv)
- 規則歸納：[roughset/core.py](../../../roughset/core.py)
- 約簡：[roughset/reduct.py](../../../roughset/reduct.py)
- 集中／聯邦流程：[roughset/pipeline.py](../../../roughset/pipeline.py)
- 規則投票：[roughset/evaluation.py](../../../roughset/evaluation.py)
- 網站來源：[teacher_dashboard](./README.md)
- 真實瀏覽器測試：[Teacher Dashboard Browser QA](https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-dashboard-browser.yml)

## 5. 簡報時應注意

- Full Data 是回代，80/20 才是未見資料。兩個指標不能直接當成相同測試基準比較。
- 42 Seeds 是同三個資料集的重複切分，具有統計相依性；不要把 8,820 列當成 8,820 個獨立樣本。
- Population 方法並非在所有情境超越對應原方法。
- Browser 中跑出的自訂 CSV 是新實驗，不可直接加入固定 42 Seeds 基線而不記錄變因。
