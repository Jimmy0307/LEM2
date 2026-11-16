# 終版稽核修訂日誌（Research Finalization，2026-11-16）

本日誌記錄封版稽核期間的所有修正。原則：**只修正文字解讀與稽核工具，不改原始 CSV、不改預註冊、不重跑模型**。修正前的文字保留在 Git 歷史，可用 `git log -p` 查到。

## A. 先前已更正、本輪重新驗證的方向錯誤（來自 commit `da088d7`）

第一版報告（`54f0282`）與當時給使用者的回覆把 `G5_SECONDARY_DESCRIPTIVE.csv` 的 `mean_diff`（定義為 treatment − baseline，baseline = M2）直接當成 M2 − 對照，方向因此寫反：

| 項目 | 第一版寫法（錯） | 正確值（M2 − 對照） |
|---|---|---|
| M2 vs R1，IID | M2 高 +1.77 pp | **−1.77 pp**（R1 較高） |
| M2 vs C2，IID／α=0.5 | M2 高 +3.27／+2.08 pp | **−3.27／−2.08 pp**（聯邦 CART 較高） |
| M2 vs C2，α=0.1 | M2 −0.84 pp | **+0.84 pp**（不顯著） |

本輪用不依賴原分析模組的程式（`experiments/redesign_20261116/verify_g5_independent.py`）從逐任務原始 CSV 重算，確認更正後的方向正確，13 項比較逐值一致（`data/G5_INDEPENDENT_RECOMPUTATION_20261116.*`）。

## B. 本輪新增修正

| # | 等級 | 位置 | 問題 | 處置 |
|---|---|---|---|---|
| B1 | P1 | 報告 §6.2、§6.2.1、Q5 | 寫「R1 只有 IID 有配對證據」。重算顯示 α=0.1 的 M2−R1 bootstrap 95% CI 為 [−2.03, −0.08] pp，不含 0，但 Wilcoxon p=0.209，兩種方法不一致 | 補上這個不一致，結論改為「平均方向偏向 R1，秩檢定未確認」 |
| B2 | P1 | 報告 §6.4 結論句 | 只寫「α=0.1 未優於聯邦 CART」，漏掉 IID／α=0.5 時 M2 較低 | 改成完整三個分布 |
| B3 | P1 | 來源獨立性 | 預註冊寫「161 份來源家族全部排除」。文獻與 metadata 顯示 `ada`（41156）很可能源自 UCI Adult、`gina`（41158）很可能源自 MNIST，E1 規則沒有攔下 | 預註冊不改；新增 post-hoc 敏感度分析（排除 2 份或 3 份後，H1／H2 全部仍通過）；報告 §7.1、`SOURCE_INDEPENDENCE_REVIEW` 與網站揭露 |
| B4 | P1 | PR #6 說明 | 寫「51 份未使用 OpenML 來源」 | 改為「依預先凍結的名稱／別名規則排除，其中 2 份很可能同源」 |
| B5 | P2 | `tests/test_fedrs_publication_integrity.py` | Windows 預設 cp950 讀 UTF-8 文件失敗；SHA 依 checkout 的換行而變 | 明確 `encoding="utf-8"`；SHA 改用 LF 正規化（等於 Git blob 內容） |
| B6 | P2 | 資料完整性 | 實驗 Manifest 只列輸出檔名，沒有輸出檔 SHA | 新增 `RESEARCH_DATA_SHA256_INDEX_20261116.json`（全部研究資料檔）與驗證工具；加入 CI |
| B7 | P2 | 跨平台 | Windows autocrlf checkout 為 CRLF，Linux 為 LF，檔案 SHA 不同 | 新增 `.gitattributes`，研究資料一律 LF |
| B8 | P2 | CI 範圍 | CI 沒有跑原始 Rough Set／LEM2 測試，也沒有資料 Schema 檢查 | 新增 `legacy-suite` job（鎖定版本、全套測試）、`test_fedrs_data_quality.py`、獨立重算與 SHA 索引步驟 |
| B9 | P3 | 網站 | 缺可重現性與限制分區；320 px 寬時長路徑溢出 | 新增分區、頁內導覽、`code` 斷行；首頁加上新舊證據等級說明 |
| B10 | P3 | 本機 Git 設定 | fetch refspec 只含原始分支，追蹤分支 `origin/research/federated-...` 不存在 | `git remote set-branches --add`，非破壞性 |
| B11 | P2 | p 值的跨平台穩定性 | CI（Linux）重算時，M2−C2 α=0.1 的未校正 Wilcoxon p 是 0.0990，已發布值（Windows）是 0.0980。原因：兩份資料集的 \|差異\| 在 Windows 上完全相等（套用平手校正），在 Linux 上因浮點加總順序差了約 1e-16（不算平手）。所有平均差與 CI 都一致 | 已發布值不改。驗證程式改為：p 值的判定（α=0.05）必須一致且差距 ≤0.005，較小的漂移列為警告；另外輸出四捨五入到 1e-12 後的 `wilcoxon_p_tie_rounded`。結論：未校正 p 值在第 3–4 位小數會受平台影響，**沒有任何判定改變** |

## C. 確認未變更

- `PREREGISTRATION_CONFIRMATORY_20261116.md`：未改（Git 歷史只有 `89fd52b` 一個版本）。
- `data/` 內既有 CSV 與 Manifest：未改；新增檔都使用新檔名（`*_20261116.csv`）。
- 原始研究分支 `research/report-ready-dashboard-20261109`：仍為 `87e31c4`。
