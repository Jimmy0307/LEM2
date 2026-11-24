# FDM 研究者邀請與操作（v0.1.0 Alpha）

**請在正式分享前核對：**授權決策和 Branch Rulesets 尚須維護者批准；[LICENSE_DECISION.md](../../../../LICENSE_DECISION.md) 尚未提供整個 Repo 的再散布授權。**目前適合讓有授權的合作者參與 PR 審查與實作，不要宣稱整個 LEM2 為 MIT 開源。**

## 研究者 5 分鐘起步

```bash
git clone --branch research/modular-platform-handover-20261123 \
  https://github.com/Jimmy0307/LEM2.git
cd LEM2
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pip install -e ./examples/fdm_lookup_adapter
fdm algorithms
python -m pytest -q tests/test_federated_decision_making_package.py
```

接著：請 Fork → 建 `feat/adapter-prism` 等功能分支 → 實作自己的獨立 Adapter → 附上參考論文、方法限制、合成測試資料與重現指令 → Pull Request **目標設為 `research/modular-platform-handover-20261123`**。沒有直接推送共用分支的必要。

### 每個 Adapter 獨立安裝

```bash
python -m pip install ./adapters/fdm_prism
fdm algorithms
```

對應的外掛 `pyproject.toml`：

```toml
[project.entry-points."federated_decision_making.algorithms"]
prism = "fdm_prism.adapter:PrismPlugin"
```

需自行提供符合 `Capabilities + FitRequest + Predictions` 契約的程式。PRISM、RIPPER、DRSA 尚未實作，這些名稱僅作為預留接口，不能假裝跑出數據。請參考 [Adapter 空白模板](../../../../adapters/_template/README.md) 與可執行的 [Lookup 範例](../../../../examples/fdm_lookup_adapter/README.md)。

## 維護者合併 Gate

- 分支上的 FDM CI（Wheel/外部插件、Docker、治理檢查）PASS；README 及測試案例明確、可再現。
- 研究比較先有具名 Baseline 的絕對 Accuracy，固定同 Dataset、Seed、Split、Scenario、Test，才談 Δpp。
- 需要真正的聯邦 client 合併實作，不能宣稱單機分表就是安全聯邦。
- 真實 Spark／SSH 尚未驗收；請勿把 Fork PR 直接送到帶私鑰或內部資料的研究叢集。

## 維護者手動啟用 GitHub Branch Protection

目前 GitHub API 顯示研究分支 **`protected: false`**。GitHub 介面需進入：

`Settings → Rules → Rulesets → New branch ruleset`，設定分支 `research/modular-platform-handover-20261123`。

建議：Require pull requests before merging、至少 **1 位非作者 Approval**、Require review from CODEOWNERS、Require status checks to pass（`pip-wheel-and-external-plugin`、`docker-smoke`、`governance-checks`）、阻止 Force push/Deletion、Require branch to be up to date（依專案負載）。確認規則**Active**並套用此分支後，再通知研究者提交。

**注意**：此文件與 CODEOWNERS 不會自行啟動 branch protection；若倉庫計畫／權限限制某些規則，維護者需依實際 GitHub 畫面確認。

### PR／Issue 範本自動出現的限制

目前專案預設分支仍是 `main`；我們只在研究隔離分支新增範本。依 [GitHub 官方文件](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)，**PR 範本要進入預設分支才會自動填入**；Issue 範本亦以預設分支為主要來源。因此研究者目前請**直接複製** [PR Checklist](../../../../.github/PULL_REQUEST_TEMPLATE.md) 的內容至 PR 描述；Issue 提案可直接參考 [Algorithm Adapter issue form](../../../../.github/ISSUE_TEMPLATE/algorithm-adapter.yml)。

不要只為了讓模板自動出現，就在未審查的情況下直接合併整個研究平台到 `main`。未來可以由維護者另送**僅包含社群模板的獨立 PR**到預設分支。真正的分支審查與強制 CI 仍需 GitHub Rulesets 啟用。
