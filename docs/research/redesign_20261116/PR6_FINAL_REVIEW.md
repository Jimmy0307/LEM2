# PR #6 最終審查（Research Finalization，2026-11-16）

**PR**：https://github.com/Jimmy0307/LEM2/pull/6　**Head**：`research/federated-rule-degeneracy-redesign-20261116`　**Base**：`research/report-ready-dashboard-20261109`（`87e31c4`，未修改）
**前一份審查**：`PR6_MERGE_READINESS_AUDIT_20261116.md`（保留）。本檔是封版後的完整驗收。

## 1. 驗收清單
| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | GitHub 原始基準未修改 | **PASS** | 遠端 `research/report-ready-dashboard-20261109` = `87e31c4`；本 PR 對歷史檔案的差異只有首頁導覽、README 開頭的指引、`.gitignore` 一行、空的 `experiments/__init__.py` |
| 2 | 研究分支 Worktree Clean | **PASS**（推送後檢查） | `git status` 為空，與 `origin` 同步 |
| 3 | 原始 CSV 與主要確認性結果不變 | **PASS** | 既有資料檔都沒有被修改（`git diff ce5d1da -- data/` 只有新增）；SHA 索引 105 檔 |
| 4 | 主要假設可重算 | **PASS** | `verify_g5_independent --check`：13 項比較與已發布表逐值一致；126 個任務重新執行逐值相同 |
| 5 | 外部對照方向正確 | **PASS** | M2−R1／C1／C2 與 `G5_ARM_MEANS.csv` 一致；報告、網站、PR 說明的符號都已檢查 |
| 6 | 網站資料完整性 | **PASS（本機）／未公開部署** | 10 個資料表在無頭瀏覽器中全部載入；網站 Manifest SHA 測試通過；320／390／768／1366 px 檢查無水平溢出 |
| 7 | CI 全部綠燈 | 見第 4 節 | `redesign-fedrs-tests`：`test`＋`legacy-suite` |
| 8 | 沒有未處理的 P0 | **PASS** | 沒有發現 P0 |
| 9 | P1 已修復或列為研究限制 | **PASS** | 見第 2 節 |
| 10 | 報告與網站沒有超出證據的宣稱 | **PASS** | 新穎性、隱私、CART 比較、來源獨立性都已限定 |
| 11 | 原始資料與限制可追溯 | **PASS** | `RESEARCH_EVIDENCE_INDEX.md`、SHA 索引、Manifest、失敗紀錄 |
| 12 | PR 說明與最終文件一致 | **PASS** | PR 說明依本檔重寫 |

## 2. 本輪發現與處置
完整清單見 `FINALIZATION_REVISIONS_20261116.md`。

| 等級 | 項目 | 處置 |
|---|---|---|
| P1 | 第一版報告把外部對照方向寫反（`da088d7` 已更正） | 本輪獨立重算再次確認 |
| P1 | M2−R1 在 α=0.1：bootstrap CI 不含 0，但 Wilcoxon p=0.21 | 報告補上兩種方法不一致的說明 |
| P1 | `ada`、`gina` 很可能與歷史來源（Adult、MNIST）同源，預註冊的排除規則沒有攔下 | 預註冊不改；post-hoc 敏感度分析顯示結論不變；列為 Open Limitation |
| P1 | PR 說明寫「51 份未使用來源」 | 已改寫 |
| P2 | 完整性測試在 Windows 上失敗（cp950 編碼、CRLF SHA） | 已修正；新增 `.gitattributes` |
| P2 | 輸出 CSV 沒有 SHA 紀錄 | 新增 SHA 索引並納入 CI |
| P2 | 實驗程式會默默覆寫已發布證據 | 新增寫入保護與測試 |
| P2 | CI 沒有跑原始 Rough Set／LEM2 測試 | 新增 `legacy-suite` job |
| P3 | 網站缺可重現性、限制分區；窄螢幕溢出 | 已修正 |

## 3. 本機測試（2026-11-16）
執行環境：Windows 11，32 核。

| 測試 | 指令 | 結果 | 時間 |
|---|---|---|---|
| 語法編譯 | `python -m compileall -q fedrs experiments roughset teacher_demo tests` | PASS | <10 s |
| Import | 26 個 `fedrs`／`experiments.redesign_20261116` 模組 | PASS（0 失敗） | <5 s |
| 全套測試，鎖定環境 Python 3.12.10（numpy 2.3.5、pandas 2.2.3） | `pytest tests` | **185 passed, 2 skipped, 0 failed** | 66 s |
| 全套測試，Python 3.14.2 | `pytest tests` | 182 passed, 2 skipped, 3 failed（見下） | 75 s |
| 原始 Rough Set／LEM2（含於全套） | `tests/test_reduct*.py`、`test_math_core.py`、`test_final_math_audit.py`… | PASS | — |
| 聯邦規則引擎、FED_MD、B2 | `tests/test_fedrs_units.py` | PASS | — |
| 原始模型一致性 | `tests/test_fedrs_parity.py`（3 案例） | PASS | 約 45 s |
| 確認性研究完整性 | `tests/test_fedrs_publication_integrity.py`（10 項） | PASS | 約 1 s |
| CSV Schema／重複鍵／缺漏／Manifest 計數／寫入保護 | `tests/test_fedrs_data_quality.py` | PASS（2 skip：記憶體量測只有 CONFIG 表） | 約 15 s |
| 資料 SHA-256 | `python -m experiments.redesign_20261116.evidence_index` | PASS（105 檔） | <5 s |
| 獨立重算 | `python -m experiments.redesign_20261116.verify_g5_independent --check` | PASS | 約 5 s |
| 重新執行抽查 | `python -m experiments.redesign_20261116.spotcheck_g5_rerun --scratch <tmp>` | PASS（126 任務、3 張表逐值相同） | 約 80 s |
| Smoke 重跑 | `gate5_confirmatory --limit 14`（輸出到暫存） | PASS（與已發布 Smoke 的 test_ba 差 0） | 約 10 s |
| 網站 JS／CSV 載入 | 本機 `http.server` ＋ Edge headless `--dump-dom` | PASS（10/10 表格有資料，兩個狀態徽章正確） | 約 15 s |

Python 3.14 上有 3 個 `tests/test_environment.py` 失敗，這是原始軟體**刻意**拒絕 3.14（pandas 2.2.3 沒有 3.14 wheel），不是缺陷；在鎖定的 3.12 環境中全部通過。

## 4. CI
（推送後補上，見下一個 commit。）

## 5. 方法學限制（合併後仍然存在）
- 受限設定（前 6 特徵、≤1,800 列、3 Client）；絕對 BA 約 44–50%。
- FED_MD 只是模擬：沒有通訊協定、安全聚合或 DP。
- 來源獨立性只做到 metadata 層級（PARTIALLY VERIFIED）。
- 外部對照是描述性比較，沒有非劣性檢定。
- 沒有外部團隊重現。

## 6. 是否建議合併
**工程面：可以進入正式審閱（Ready for Review）。** 全部可自動驗證的條件都通過，也沒有已知的 P0／P1 缺陷尚未處理。

**合併本身需要人類決定**，原因有三：
1. **Base 是原始研究分支。** 合併會改變 `research/report-ready-dashboard-20261109`，而這個分支是被要求「不可覆寫」的原始基準，也是 GitHub Pages 的發布來源。替代做法：合併到新的整合分支（例如 `research/finalized-20261116`），讓原始分支保持凍結。
2. **公開網站。** 研究頁目前只在研究分支中（公開網址 `/research/teacher_dashboard/redesign/` 回傳 404）。上線方式有兩種，都需要人類決定：(a) 合併 PR #6，Pages 自動重建（同時改變原始分支）；(b) 把 Pages 來源改成研究分支或整合分支的 `/docs`。研究分支包含原始網站的全部頁面，加上新頁面與首頁的一個連結和一段說明。
3. **大型資料。** 合併會把約 228 MB（壓縮後約 30 MB）的 CSV 帶進基準分支。可以接受，也可以先依 `DATA_GOVERNANCE.md` 改用 Release 存放。

另外建議在合併前決定是否刪除 `.github/workflows/redesign-manifest-reconcile.yml`。這個 workflow 有 `contents: write` 權限並會自動推送，它的一次性任務已經完成。
