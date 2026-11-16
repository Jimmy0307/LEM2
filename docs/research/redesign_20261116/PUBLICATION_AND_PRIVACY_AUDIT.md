# 公開發布與隱私稽核（2026-11-16）

本稽核**只記錄路徑、類別、次數與風險**，不重複任何敏感值。工具：`experiments/redesign_20261116/public_release_audit.py`（掃描已追蹤檔案或網站產物）；Git 歷史用 `git log --all -G<pattern>` 只計算 commit 數。

## 1. 結果摘要
| 範圍 | CRITICAL | HIGH | MEDIUM | LOW | 狀態 |
|---|---:|---:|---:|---:|---|
| 目前所有已追蹤檔案（`60cdf63` 之後的工作樹） | 0 | 0 | 0 | 42 處（皆說明如下） | PASS |
| 全部 Git 歷史（649 個 commit，檔案內容；CSV 除外） | 0 | 0 | 0 | — | PASS |
| Git 歷史的 commit 作者／提交者 metadata | — | — | 1 個 commit | — | **已公開，無法在不改寫歷史下移除**（見 §3） |
| 網站白名單產物 `_site/`（298 檔，65.5 MB） | 0 | 0 | 0 | 1（誤判） | PASS |

掃描的類別：私鑰、GitHub／AWS／Slack／API 類 token、URL 內帳密、`password=`／`api_key=` 等字面值、不在公開白名單上的 e-mail 網域（公司或個人信箱）、本機使用者路徑、私有網段 IP。**沒有發現任何憑證**，因此沒有需要撤銷或輪替的金鑰。

## 2. 問題檔案（只列路徑）
| 路徑 | 類別 | 風險 | 狀態 |
|---|---|---|---|
| `outputs/final_math_audit_20261015/**`（37 檔：PRE_FIX_BASELINE 17、UCI3_HOLDOUT42_FINAL 17、baseline／final_regression／red_green 各 1） | 本機路徑中含個人使用者名稱 | LOW | 原始研究分支的歷史產物；**不在網站白名單內**；仍在公開 Git 中。未修改（屬原始研究證據）。若要從最新版本移除，需要擁有者決定；Git 歷史仍會保留 |
| `docs/CANONICAL_SOURCE_SNAPSHOT_20261015.md`、`evidence/20261014_162216/batch_manifest.json`、`docs/research/redesign_20261116/LOCAL_WORKTREE_SAFETY_20261116.md` | 本機路徑，使用者名稱為通用的 `user` | LOW | 不可識別個人；前兩個不在網站白名單內 |
| `docs/research/teacher_dashboard/browser_engine_worker.js` | `/home/pyodide/` | 誤判 | 瀏覽器內 Pyodide 的虛擬檔案系統，不是真實使用者 |
| `docs/research/redesign_20261116/data/G5_SOURCE_METADATA_AUDIT_20261116.csv` | 私有 IP 樣式 | 誤判 | 是 DOI 字串的一部分 |

## 3. Git 歷史中的公司信箱（commit metadata）
- 1 個 commit（`e68bbf7`，2026-10-15）的作者 e-mail 使用公司網域。檔案內容中**沒有**公司網域（全部歷史掃描 0 筆）。
- 這不是憑證，不需要輪替；但儲存庫是公開的，任何人都能從 `git log` 看到。
- 不改寫歷史的前提下，只能降低未來曝光：建議擁有者把本機 Git 設成 GitHub noreply 信箱（`git config user.email <id>+<login>@users.noreply.github.com`），並在 GitHub 設定中開啟「Block command line pushes that expose my email」。
- 若需要完全移除，必須改寫歷史並 force push，這超出本次授權，列為**擁有者決定**。

## 4. 第三方資料授權
| 資料 | 在 Git 中的形式 | 授權狀態 | 處置 |
|---|---|---|---|
| Gate 5 的 51 份 OpenML 來源 | 只有 metadata、SHA 與衍生指標；**沒有原始資料列**（`data_cache/` 已 git-ignore） | OpenML 標示：48 份「Public」、3 份 CC0。「Public」不是正式的開放授權 | 不建立原始資料的公開永久鏡像；若未來要放上 Release／Zenodo，必須逐份確認授權 |
| `docs/research/public_datasets_20/*_prepared.csv`（原始分支） | 已整理的 UCI 資料表，原本就在公開網站上 | UCI 資料多數為 CC BY 4.0，需要標示來源 | 維持原狀（屬原始研究）；網站白名單照舊公開，與目前網站相同。建議擁有者確認 README 有逐份來源標示 |
| `docs/research/public_datasets/*_public_stratified_subset.csv` | 公開資料的分層子集 | 同上 | 同上 |

## 5. 網站發布白名單
`experiments/redesign_20261116/build_public_site.py` 只發布以下內容：

- `docs/index.html`
- `docs/research/teacher_dashboard/**`
- `docs/research/full_factorial_20261029/figures/**`
- `docs/research/public_datasets/`（README 與兩個子集）
- `docs/research/public_datasets_20/**`

**不再出現在網站上**（但仍在公開 Git 中）：`docs/*.md` 內部稽核筆記、`docs/reviews/`、`docs/superpowers/`、`docs/final_math_audit_20261015/`、228 MB 的研究原始 CSV，以及其他研究資料夾。目前的舊網站（legacy Jekyll，整個 `docs/`）仍公開這些檔案，例如 `/LEM2/FINAL_MATH_AUDIT_PROMPT.md` 回傳 200。

建置時會檢查：網站 CSV 與研究正式表的 SHA 一致、入口頁與研究頁沒有斷連結、隱私稽核沒有 MEDIUM 以上、大小 < 300 MB。CI 再用真正的 Chromium 驗收：10 張表、兩個狀態徽章、320／390／1366 px 無水平溢出、伺服器回傳檔案的 SHA。

## 6. GitHub Pages 部署：OWNER ACTION REQUIRED
目前的設定：Pages 用 legacy 模式，從 `research/report-ready-dashboard-20261109:/docs` 建置；`github-pages` 環境只允許這個分支部署。要在**不合併 PR、不修改原始分支**的情況下上線，必須由擁有者修改儲存庫設定：

```bash
# 1) 把 Pages 來源改成 GitHub Actions
#    （一般情況下，目前的網站會繼續顯示到下一次部署；保險起見，請在同一時段完成 1–4 步）
gh api -X PUT repos/Jimmy0307/LEM2/pages -f build_type=workflow
# 2) 允許研究分支部署到 github-pages 環境
gh api -X POST repos/Jimmy0307/LEM2/environments/github-pages/deployment-branch-policies \
   -f name=research/federated-rule-degeneracy-redesign-20261116 -f type=branch
# 3) 開啟部署（workflow 只在這個變數等於分支名稱時才部署）
gh variable set LEM2_PAGES_DEPLOY_REF --body research/federated-rule-degeneracy-redesign-20261116
# 4) 重新執行該分支最新一次 redesign-site-publish（push 觸發）
gh run rerun $(gh run list --workflow redesign-site-publish.yml \
   --branch research/federated-rule-degeneracy-redesign-20261116 --event push --limit 1 --json databaseId -q '.[0].databaseId')
```
部署 job 會在上線後對正式網址再跑一次瀏覽器驗收。

**回復方式**：`gh api -X PUT repos/Jimmy0307/LEM2/pages -f build_type=legacy -F "source[branch]=research/report-ready-dashboard-20261109" -F "source[path]=/docs"`，再 `gh variable delete LEM2_PAGES_DEPLOY_REF`。

**影響**：網站內容變成「原始 Dashboard＋新研究頁」，只保留白名單內的檔案。§5 列出的內部筆記網址會變成 404。PR 合併到 `research/finalized-20261116` 之後，把第 2、3 步的分支名稱改成 `research/finalized-20261116`。
