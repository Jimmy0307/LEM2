# 資料與儲存庫治理（2026-11-16 盤點）

本輪只做盤點、制定策略與非破壞性修正。**沒有刪除、搬移或改寫任何已提交的研究資料或歷史。**

## 1. 規模
| 項目 | 數值 |
|---|---|
| 重建研究資料 `docs/research/redesign_20261116/data/` | 105 檔，LF 正規化後 228.2 MB（`RESEARCH_DATA_SHA256_INDEX_20261116.json`） |
| 最大單檔 | `REDESIGN_G5_CONFIRMATORY_POLICIES.csv` 52.1 MB（GitHub 的警告門檻是 50 MB，硬上限 100 MB） |
| 其他 >10 MB 的檔案 | G2／G4／G3 的 POLICIES（31.2／28.4／23.1 MB）、G5 STRUCTURE（18.5 MB） |
| GitHub 儲存庫大小（壓縮後） | 約 31 MB（`gh api repos/Jimmy0307/LEM2 .size` = 31,378 KB） |
| 本機 `.git` | 約 34 MB |
| 未追蹤的本機快取 `data_cache/openml/` | 約 420 MB（git-ignore） |

結論：CSV 壓縮率很高，**目前的 Clone 與 CI 成本可接受**（CI 從 checkout 到測試約 1 分鐘）。真正的風險是未來檔案成長：單檔超過 100 MB 就無法推送，而且每次重新產生大型 CSV 都會在歷史中再存一份。

## 2. 分類
| 類別 | 內容 | 是否可取代 | 策略 |
|---|---|---|---|
| **A. 不可取代的正式研究證據** | `REDESIGN_G5_CONFIRMATORY_*`、`CONFIRMATORY_SOURCE_REGISTRY.csv`、`PREREGISTRATION_*`、全部 `*_MANIFEST.json`、`*_FAILURES.csv` | 否：確認性結果只能產生一次（重跑就不是同一次預註冊執行） | 保留在 Git；SHA 已索引；未來也複製一份到 Release |
| **B. 可重算的探索性原始輸出** | `REDESIGN_G1`–`G4_*`、`*_SMOKE_*` | 原則上可以重算（程式與 Seeds 都已固定），但需要 UCI 原始資料與數十分鐘計算 | 保留在 Git（是報告的直接依據）；未來可移到 Release |
| **C. 分析衍生表** | `G1_*`、`G2*`、`G3_*`、`G4_*`、`G5_*`（摘要） | 可以從 A／B 由 `analyze_*.py` 確定性重算 | 保留在 Git（體積小） |
| **D. 網站發布副本** | `docs/research/teacher_dashboard/data/redesign_20261116/` | 是 C 的位元組副本 | 保留；`REDESIGN_SITE_MANIFEST.json` 驗證 |
| **E. 可安全重建的快取** | `data_cache/`（OpenML 原始 parquet 與 prepared CSV）、`__pycache__/`、`.pytest_cache/` | 是，但 OpenML 下載可能暫時失敗 | 不進 Git；`data_cache/` **建議保留在本機**，直到有持久鏡像 |
| **F. 不確定用途的歷史資產** | 原始分支的 `outputs/`、`evidence/`、舊 workflow | 不屬於本研究 | 不處理 |

本輪清理：**無**。`__pycache__/` 與 `.pytest_cache/` 是 git-ignore 的可重建快取，留著不影響任何東西，因此不刪。

## 3. 本輪非破壞性修正
1. `.gitattributes`：研究資料、網站資料與研究頁一律 LF，讓 Windows 與 Linux 的檔案 SHA 一致（Git 中的 blob 本來就是 LF，所以沒有改到任何資料）。
2. `RESEARCH_DATA_SHA256_INDEX_20261116.json` 與 `evidence_index.py`：涵蓋全部研究資料的 SHA 索引，CI 每次都驗證。
3. 寫入保護：實驗程式不能再默默覆寫已發布的 Manifest、CSV 或來源登錄（`common.guard_published`）。
4. 本機 `D:\Desk\LEM2` 的 fetch refspec 加入研究分支，讓追蹤分支存在（`git remote set-branches --add`）。

## 3.1 2026-11-16 整合決定
- 228 MB 研究 CSV **暫時保留在 Git**；不刪除、不改寫歷史、不搬到 Release。
- GitHub Release 與 Zenodo 只列為**未來的備援保存方案**。
- 涉及第三方資料（OpenML、UCI）時，在授權逐份確認並由擁有者核准之前，**不建立任何新的公開永久鏡像**（見 `PUBLICATION_AND_PRIVACY_AUDIT.md` §4）。
- 網站改由白名單產物發布，研究原始 CSV 不放上網站（只留在 Git）。

## 4. 未來遷移方案（本輪不執行）
若要把 A／B 類大型 CSV 移出 Git 的工作樹，必須同時滿足以下條件：

1. **不改寫歷史**：只能在新的 commit 中把檔案換成指標檔；舊 commit 仍保有完整資料。不使用 `git filter-repo` 或 BFG。
2. **版本化保存**：建立 GitHub Release（例如 `redesign-data-20261116`），上傳每個 CSV（或 zstd 壓縮檔）。GitHub Release 單一資產上限 2 GB，沒有保留期限，但會隨儲存庫刪除而消失。另外把同一份資料存到 Zenodo（取得 DOI，長期保存），或存到學校的研究資料庫。
3. **可驗證**：Release 中附 `RESEARCH_DATA_SHA256_INDEX_20261116.json`；新增 `fetch_research_data.py`，下載後逐檔核對 SHA，不一致就停止。
4. **可用性測試**：在乾淨環境（CI）執行「下載 → SHA 驗證 → `verify_g5_independent --check` → 全部測試」，全部通過才能把 Git 內的檔案換成指標。
5. **DVC 選項**：若未來資料持續成長，可以改用 DVC 搭配遠端儲存（S3／GDrive／學校 NAS）。代價是協作者要安裝 DVC，遠端權限也要長期維護。目前規模不需要。
6. **需要人類決定**：保存地點（Release、Zenodo 或學校儲存庫）、授權（OpenML 衍生資料的再散布條件）、保留期限。

## 5. CI 與 Workflow
| Workflow | 觸發 | 權限 | 狀態 |
|---|---|---|---|
| `redesign-fedrs-tests.yml` | push 到研究分支（限相關路徑）、對原始分支的 PR、手動 | `contents: read` | 兩個 job：`test`（重建研究的單元、一致性、發布完整性、資料品質、SHA 索引、獨立重算、提交順序）與 `legacy-suite`（鎖定版本的全套測試） |
| `redesign-manifest-reconcile.yml` | — | — | **2026-11-16 已刪除**：一次性雜湊修復已完成（run 43812533165 → `647b5e9`；25 個網站檔案與 Git blob 逐一相符）。修復工具 `reconcile_publication_manifest.py` 與 Git 歷史保留 |
| `redesign-site-publish.yml` | push 到研究分支與整合分支（限網站相關路徑）、PR 到整合分支、手動 | 預設 `contents: read`；只有 deploy job 有 `pages: write`／`id-token: write` | 白名單建置、隱私稽核、Chromium 驗收；擁有者設定 `LEM2_PAGES_DEPLOY_REF` 之前不會部署 |
| `teacher-dashboard-pages.yml` | 手動 | `pages: write` | 改成只上傳白名單產物（原本上傳整個 `docs/`） |
| 原始分支的 48 個有 `contents: write` 的舊 workflow | 都限定在其他分支，或只在修改自身檔案時觸發 | `contents: write`（會把結果 commit 回去，這是它們的功能） | 已檢查：沒有任何一個會在研究分支或整合分支上觸發。屬於原始研究，不修改 |
