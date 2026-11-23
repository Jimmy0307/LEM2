# LEM2｜逾時、推論成本與外推可信度稽核（2026-11-23）
**狀態：SOURCE REVIEWED · INTERIM · 不改動既有實驗協定。**
研究問題：為什麼 44,819 Rows 的資料集可逾時，但 1,000,000 Rows 的另一資料集卻可在一兩分鐘內完成？瓶頸出現在真正的 LEM2/Reduct 步驟，還是六種 Rule Resolution Policies 的推論階段？

## 0. 來源範圍與時間點
- 使用者於 2026-11-23 提供本地 `TIMEOUT_ANALYSIS.md`、`per_source_observed.csv`、`per_source_scaling.csv` 與兩張圖。上傳的原始檔 SHA256 記錄於本頁最後；CSV 的**原始位元資料**以 gzip 封存於研究分支。
- `per_source_observed.csv`：**181 個有成功模型的資料集**的觀測最大模型耗時、規則數中位數、Rows；含 179 個完整及兩個部分結果來源。這一表**不是 31,584 個單模型的逐筆計時表**；只有成功模型才能得到完整計時。
- `per_source_scaling.csv`：**48 個（dataset, scenario）縮放紀錄**，其中 11 組 `degenerate_ladder=True`、17 組 `many_rules=True`。包含 1,800／10,000 Rows 梯度、CI full-scale 的已完成數、TIMEOUT 數、外推結果。
- 期中成功模型為 30,078；來源 `interim/FAILURES.csv` 於 **11:42 快照**有 98 筆 TIMEOUT；**18:05 本機操作彙總**另報告累計 154 筆，其中 56 筆未提供逐 Seed／Scenario 的原始 checkpoint。二者是不同時間／證據等級，不可混合成一個已驗證的失敗明細。
- `per_source_observed.csv` 中 `timeouts` 欄合計 **70**，因為完全無成功模型的 openml_42732 不在這張觀測表，**不能將 70 稱為全部 TIMEOUT**。原始 98 條另見 `interim/FAILURES.csv`。
- 所有模型仍按 `NESTED_64_16_20`、最多六 Features、Centralized vs 三 Client IID／Dirichlet α=.5/.1；本文件是計算成本診斷，不是新增訓練結果。

## 1. 可直接支持的結果
1. **Rows 不單獨決定逾時。** 同一份 CSV 有 `OML51:openml_42769`：1,000,000 Rows、中位數 55.5 規則、完成模型的最慢一次 87.8s；`UCI20:covertype`：581,012 Rows、96 規則、最慢 50.0s；相對於 `OML51:openml_41027`：44,819 Rows、約 1,284.5 規則、只有兩個成功模型，其成功模型的最慢一次達 2,227.8s，11:42 已有 70 筆 TIMEOUT。
2. 上傳的原始分析報告統計在**成功完成且 wall>60 秒的模型**中：Predict 佔 91.9%、LEM2 5.1%、Reduct 0.9%。此階段歸因是**使用者報告的匯總**，原本上傳的兩份*per-source* CSV 不含逐模型 phase timings，無法單靠這兩份 CSV 獨立重算 91.9%。因此不能以它直接證明每個被中止的模型一定卡在 Predict。
3. 程式機制 `fedrs/predict.py::resolve_scalable` 先依規則匹配布林樣式對 Test Rows 去重；支持集型策略 `GLOBAL_STRENGTH`、`POPULATION_STANDARD`、`POPULATION_GLOBAL` 對候選類別計算符合規則的 pooled training support union。運算成本與 `U`（獨立匹配樣式數）、`R`（規則數）、`N_train`（Dev 訓練列數）高度相關，密集運算主項可近似為 `O(U×R×N_train)`。**U 不一定等於 Test Rows**，R 也因資料集而異；大樣本但少規則／少獨立匹配樣式可很快。
4. `fedrs/experiment.py` 和 `model.py` 將六種決策策略在同一次模型評估內完成後才返回 12 筆結果。因此即使 FIRST_MATCH 等策略快，只要後面的支持集策略到 2,700s timeout，原先流程便**沒有保留這次模型的前面策略分數**。這是輸出原子性（atomicity）／協定瓶頸，不代表所有六種策略都無法完成。

## 2. 外推模型如何讀
原報告的候選模型為 `T(n)=T(10000)*(n/10000)^(2+g)`，假定 `U≈Test Rows∝n`，`R(n)∝n^g`，且 pooled Dev ≈0.64n；僅在 U 隨 Rows 持續變化且規則數依實測成長時才有近似意義。報告又以少數 high-rule 無逾時樣本的 ratio 中位數 **2.02** 校正。

**重要校準限制（可直接從 scaling CSV 驗證）：**
- 用 `many_rules=True`、非退化且 CI 全部成功作校正的組合只有 **4**：openml_42734 α=.1、adult_income IID、letter IID、letter α=.1。預測/實測比例中位數約 2.015。四組不足以支持普遍誤差 ±30%–40% 的置信表述。
- 48 梯度紀錄有 **11 組退化**（小樣本規則數極低或劇變）不能用固定幂律外推；至少部分 CI full-scale 的 median 只計算**沒有逾時**的模型，存在右設限／完成者選擇偏誤。
- 在記錄中，`openml_42742 FED_IID` 的外推與實測差約 50 倍、`covertype FED_IID` 約 216 倍、`openml_42769 FED_IID` 約 332 倍；這些低規則數案例直接否定「一律按 n²×R 推算」。
- `openml_42732` 的 Fedora IID 從 10k 外推到 221 萬 Rows，跨度 221 倍，得到極端不穩定的超長時間預測。**只可將其解釋成高風險警訊，不能當精確所需 CPU 時間**。
- 研究圖上的 `2,700s` 是**預先規定的停止門檻**；對未完成模型記為 `T>2700`（或已達截止停止），不能把 2,700 當成真正完成所需時間做普通迴歸。不同硬體的 CI／Local 也應分層或校正。

## 3. 具體來源：實際證據與臨界點估計分開
下列 `rows_reaching_2700s_cal` 取自 10k 梯度和小樣本校正的外推（**不是實測閾值**），CI 欄是 5-seed full-scale 歷史結果：

| Dataset／Fed IID | 原始 Rows | 10k Rules | 外推超時 Rows | CI full-scale TIMEOUT | 解讀 |
|---|---:|---:|---:|---:|---|
| openml_1169 | 539,383 | 3,566 | 25,401 | 5／5 | 極高風險；遠超外推有效區間 |
| openml_42732 | 2,215,023 | 3,275 | 28,465 | 5／5 | 高風險；不能推算實際完工時間 |
| openml_42733 | 39,948 | 4,896 | 35,208 | 5／5 | 有明確 CI timeout 證據 |
| openml_41162 | 72,983 | 1,861 | 42,496 | 5／5 | 有明確 CI timeout 證據 |
| openml_41027 | 44,819 | 2,108 | 43,679 | 5／5 | 本機大量 TIMEOUT 亦支持 |
| openml_42734 | 50,789 | 1,723 | 51,079 | 1／5 | 多數能完成，適合先補成功 |
| adult_income | 48,842 | 928 | 72,917 | 0／5 | CI 五筆成功，可優先補跑 |

表格按風險分類供排程參考，**不是承諾在某個精確 N 會必然超時**；本次沒有更改任何執行、排程順序或 timeout 秒數。

## 4. 工程與研究決策
**不建議僅為追求 188/188 完成度而全面拉高 timeout**。研究主矩陣是 179 完整來源＋9 非隨機缺漏；如果對 high-risk 來源加時，其成功率／額外 CPU 成本仍不確定。

優先保留 2,700s 的凍結基線，用現有 CI 記錄安排先跑高成功機率的來源（adult_income、openml_42734、openml_42742 等）；這是**建議**，非已執行排程變更。對反覆 timeout 的模型設獨立的 `TIMEOUT_CENSORED` 與失敗率、資源消耗報告，**不將它填成 Accuracy=0 或 No-Rule**。

新增下一版**隔離實驗**：在相同 Rule Set 下逐策略計時、逐策略 checkpoint，並做計算語意一致（parity）驗證；針對三種 support-union 策略評估 bitset / sparse support、候選集合去重、預先聚合，量測 (U,R,N_{train},K) 和 peak RSS，評估 time/memory budget。這些修改**不可直接替換目前 frozen 六策略 Test 主結果**。

## 5. 原始資料與驗證憑證
- [逐來源觀察，181 列（原始 CSV.gz）](./per_source_observed.csv.gz) — SHA256 解壓後原始 CSV：`cd76a5bca6e9cee37dce5cfc9f94bf5b5e4d309955212db52dcb81afc4a05ffc`
- [來源×分布縮放，48 列（原始 CSV.gz）](./per_source_scaling.csv.gz) — SHA256 解壓後原始 CSV：`935e632e0da9aa62ec70fc9d314370259c03c1451a8f9bbfaca736c90f002090`
- 使用者原報告 `TIMEOUT_ANALYSIS.md` SHA256 `c1d6a33e716e25a09bd456ae329504209ee89408961831a4396ced9cb213258e`；原始兩張 PNG SHA256 分別為 `eb0dc177ccd4fcc25877f5ea337975d3c9d07fba3bda52d8cd3fd94423552222` 和 `8d7c159675f6c28028e69b899db7eb4dedac60ba6b09f9e241759ea79e4436be`。
- [已驗證 11:42 的 TIMEOUT 原始明細](../interim/FAILURES.csv) 與 [當日 18:05 本機彙總對帳](../operations/PROGRESS_RECONCILIATION_20261123T1805.md)
- [NESTED 64/16/20 主實驗口徑](../review/WHAT_WAS_ACTUALLY_TESTED_20261123.md)

**展示備註：網頁散點圖將由上傳的 181 列 CSV 在瀏覽器重新繪製；不是已知 31,584 個模型的完整失敗時間分布。**
