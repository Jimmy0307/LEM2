# LEM2 × Federated｜教授報告入口

## 1. 開啟互動網站

本目錄的 [index.html](./index.html) 是研究控制台。若 GitHub Pages 已啟用並指向本研究分支的 /docs，預期網站路徑為：

https://jimmy0307.github.io/LEM2/research/teacher_dashboard/

**未驗證部署完成前，以上只是預期路徑。** 可以 clone GitHub repo，然後在本目錄使用 python -m http.server 8000，開啟 http://localhost:8000/ 使用。

## 2. 真正的 42 Seeds

舊版畫面錯誤地硬編碼 Seeds 1～6 和 42 為綠色；新網站從數據資料逐筆檢查每個 Seed 的完整 210 列（30 NONE + 180 六策略），因此 42/42 全部才會顯示綠色。

資料檔 data/baseline_8820.json 由 teacher_demo/build_teacher_dashboard_data.py 從 GitHub 42 Seeds 正式 8,820 列 CSV 生成，沒有更改基準實驗。

[42 Seeds 原始證據](../../seed_sweep_1_42/tables/SEED_SWEEP_8820.csv)

## 3. 上傳 CSV：真正執行 LEM2

Web Worker 透過 Pyodide 載入原 GitHub roughset Python 模組，並在瀏覽器記憶體中執行：

CSV → 依決策分層切分 → Train-only 離散化 → 最小基數 Reduct → LEM2 規則 → Federated Rule Union（選用）→ Rule Matching → 六策略 Winner → Coverage／Conflict／Accuracy／BA／Macro-F1／逐筆診斷。

自訂 CSV 不會上傳伺服器，也不會寫進 8,820 筆原實驗。

**限制：** 需能連上 Pyodide CDN 與 GitHub Raw；瀏覽器試算支援 4～600 筆及至多 8 個條件欄位。大資料請使用原本 repo 的 Python CLI：

1. 把 CSV 放到 real_data/local/。
2. 在 real_data/schemas/ 補充 target 等欄位資訊，或使用 class／label／decision／target 之一。
3. 調整 config.json 的切分模式、Seed 與 Federated 設定。
4. 在 Windows 執行 run.bat，並檢查 outputs/ 輸出及 run_manifest.json。

Pyodide 的 pandas／numpy 版本可能與 CI 的鎖定版本不同；正式論文結果以鎖定 CPython 重跑作準。

## 4. 指標定義

| 指標 | 操作性定義 | 解讀 |
|---|---|---|
| Rule Count | LEM2 結果的 IF–THEN 規則條數 | 不等於 Accuracy |
| Coverage | 任何規則命中數／全部測試物件 | 分辨 No Match |
| True-in-Candidate | 真實類別在匹配候選集合的物件數／全部測試物件 | 分辨候選生成失敗 |
| Conflict | 命中兩個以上不同候選類別的測試物件比例 | 不等於 Rough Set 的 Boundary |
| Accuracy | 全部評估物件中答對比例 | 類別失衡時可能誤導 |
| Balanced Accuracy | 每類 Recall 的算術平均 | 少數類別等權 |
| Macro-F1 | 每類 F1 的算術平均 | 統合 Precision 與 Recall |
| T / U / P | 支持總次數／唯一支持人口／U÷T | 評估跨規則重複支持 |

**Conflict 後的處理順序：**

1. 無規則命中 → 記錄 NO_MATCH；目前程式使用訓練多數類別 Fallback（可能答對，不能當成必錯）。
2. 命中規則但沒有正確類別 → 改善特徵與規則歸納；現有六策略沒有能力選不存在的候選。
3. 正確類別在候選集合，但最後選錯 → 比較 STD／GS／PS／PG 等打分與 Winner。
4. 高風險衝突 → 人工審查／拒答作為待驗證的未來機制，不可當成已完成改良。

## 5. CI 與研究界線

[Teacher Dashboard CI](https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-dashboard.yml)

檢查命令：

- python -m teacher_demo.build_teacher_dashboard_data
- python -m teacher_demo.test_teacher_dashboard_csv
- node --check docs/research/teacher_dashboard/dashboard.js

42 Seeds 8,820 列主矩陣已完成。non-IID、Client 順序是獨立擴充試驗。LERS 文獻分類基準與 DRSA reduct 尚未完成，不能當作本網站已驗證的成果。FULL_DATA 是回代，不可直接用來宣稱泛化優於 80/20。
