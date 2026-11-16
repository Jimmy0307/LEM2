# PR #6 最終審查（Research Finalization，2026-11-16）

**PR**：https://github.com/Jimmy0307/LEM2/pull/6　**Head**：`research/federated-rule-degeneracy-redesign-20261116`　**Base**：`research/finalized-20261116`（2026-11-16 由 `87e31c4` 建立的整合分支；原 base `research/report-ready-dashboard-20261109` 仍為 `87e31c4`，未修改）
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
| P2 | 未校正 Wilcoxon p 值有平台差異（M2−C2 α=0.1：Windows 0.0980、Linux 0.0990；原因是浮點近似平手） | 驗證改成要求判定一致（差距 ≤0.005）；已發布值不改；沒有判定改變 |
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
Workflow `redesign-fedrs-tests`，commit `f42afd4`（ubuntu-latest，Python 3.12）：

| Run | 觸發 | Job | 結果 | 內容 |
|---|---|---|---|---|
| [43820904331](https://github.com/Jimmy0307/LEM2/actions/runs/43820904331) | push | `test` | success | 單元 15 passed；一致性 3 passed；發布完整性 10 passed；資料品質 33 passed／2 skipped；SHA 索引 PASS；獨立重算 PASS（1 個 p 值漂移警告，見 B11）；預註冊提交順序 PASS |
| 同上 | push | `legacy-suite` | success | 鎖定版本全套測試 185 passed、2 skipped |
| [43820911581](https://github.com/Jimmy0307/LEM2/actions/runs/43820911581) | pull_request | `test`、`legacy-suite` | success | 同上 |

前一個 commit `6c43d60` 的 `test` job 失敗（run 43819276508）：獨立重算的 p 值比對太嚴格，抓到跨平台浮點平手差異。依 B11 修正驗證程式後通過。**已發布的數據沒有改。**

### 整合階段 CI（commit `13f85ce`，PR base = `research/finalized-20261116`）
| Run | Workflow | 觸發 | Job | 結果 |
|---|---|---|---|---|
| [43830662244](https://github.com/Jimmy0307/LEM2/actions/runs/43830662244) | redesign-fedrs-tests | push | `test`、`legacy-suite` | success |
| [43830674210](https://github.com/Jimmy0307/LEM2/actions/runs/43830674210) | redesign-fedrs-tests | pull_request | `test`、`legacy-suite` | success |
| [43830662381](https://github.com/Jimmy0307/LEM2/actions/runs/43830662381) | redesign-site-publish | push | `build` success；`deploy` 依設計 skipped（擁有者尚未開啟） | success |
| [43830671395](https://github.com/Jimmy0307/LEM2/actions/runs/43830671395) | redesign-site-publish | pull_request | `build` | success |

`build` 的內容：白名單 298 檔／65.2 MB；網站 CSV 與研究表 SHA 一致；入口頁與研究頁沒有斷連結；隱私稽核沒有 MEDIUM 以上的發現；Linux Chromium 在 320／390／1366 px 下 10 張表都載入、兩個狀態徽章為 PASS、無水平溢出、伺服器回傳資料的 SHA 一致。Pages 產物 `github-pages`（壓縮後 7.1 MB）已上傳，等擁有者開啟部署。

整合期間有兩次 CI 失敗，都已修正：
- `0b3ed27`：Python 3.12 的 `glob("x/**")` 只匹配目錄，產物缺檔。
- `ceb49ed`：隱私稽核沒有處理相對路徑。

## 5. 方法學限制（合併後仍然存在）
- 受限設定（前 6 特徵、≤1,800 列、3 Client）；絕對 BA 約 44–50%。
- FED_MD 只是模擬：沒有通訊協定、安全聚合或 DP。
- 來源獨立性只做到 metadata 層級（PARTIALLY VERIFIED）。
- 外部對照是描述性比較，沒有非劣性檢定。
- 沒有外部團隊重現。

## 5.1 整合階段（2026-11-16）
| 項目 | 結果 |
|---|---|
| 整合分支 `research/finalized-20261116` | 由 `87e31c4` 建立並推送；PR #6 的 base 已改成它 |
| CI 的 PR 觸發 | `redesign-fedrs-tests` 與 `redesign-site-publish` 都納入新的 base |
| 一次性 `redesign-manifest-reconcile.yml` | 已刪除：25 個網站檔案與 Git blob 逐一相符；工具與歷史保留 |
| 其他 workflow 的 `contents: write` | 48 個歷史 workflow 有寫入權限（用途是把結果 commit 回去），都不會在研究分支或整合分支上觸發；新 workflow 預設唯讀 |
| 公開資料與隱私稽核 | 沒有憑證；1 個 commit 的作者 metadata 含公司信箱（無法不改寫歷史就移除）；詳見 `PUBLICATION_AND_PRIVACY_AUDIT.md` |
| 網站 | 白名單產物與瀏覽器驗收通過；**正式部署 = OWNER ACTION REQUIRED**（需要改 Pages 設定） |

## 6. 是否建議合併
**工程面：建議可以合併到整合分支 `research/finalized-20261116`。** Base 已不是原始研究分支，所以合併**不會**改動 `research/report-ready-dashboard-20261109`，也不會改動目前的公開網站。

合併仍需人類核准，原因：
1. **研究結論需要指導教授審閱**，特別是 §5 的限制與來源獨立性揭露（`ada`、`gina`）。
2. **網站上線**需要改 Pages 設定（`PUBLICATION_AND_PRIVACY_AUDIT.md` §6）。合併本身不會讓網站上線。
3. **資料存放**：合併會把約 228 MB 的 CSV 帶進整合分支（依決定暫時保留在 Git）。
