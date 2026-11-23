## 2026-11-23｜先看研究到底在測什麼
- [方法學稽核：真正的 188 ×42 配對設計與 64/16/20](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/docs/research/expanded_188_42seeds/review/WHAT_WAS_ACTUALLY_TESTED_20261123.md)：外層80/20+內層80/20，64% Dev、16% Val未用來選六策略、20% Holdout Test。
- [研究網頁上方的 Research Contract](./#protocol-verified)：四個研究問題、固定決策策略之配對效果、42 Seeds 不是42-fold；逐資料集明細顯示已觀測的 Dev／Val／Test 筆數。
- 舊三資料集 `FULL_DATA` 為回代（resubstitution），與 188 資料集的 holdout 不可合併檢定。

---

## 2026-11-23 18:05｜操作進度與凍結實驗結果分離
- GitHub 成功模型 30,078、179 來源完整（42-seed verified）。
- 本機最新回報 TIMEOUT 154（GitHub 中已存證 98，額外 56 尚無逐 Seed checkpoint），另 1,352 模型無執行結果；成功率仍為 30,078/31,584。
- 網頁最新 operational 區塊載入 [ops_progress.json](./ops_progress.json)；與 11:42 的 42-seed Coverage/Conflict 科學指標來源分離。
- 完整資料與 TIMEOUT 原始存證留在 GitHub research/expanded-42seeds-20261120 分支。
- 本次不調整 timeout／本地排程，也不將 timeout 對應 Accuracy=0。

---

# Teacher-facing 188-dataset × 42-seed feature-cap audit
Source snapshot: 20261123T114229, frozen. 179/188 complete, 30078/31584 models, 360936/379008 metric rows.
- original ≤6: 26 datasets, 25 complete; used all original features (9 exactly 6, 17 below 6).
- original >6: 162 datasets, 154 complete; all were capped at 6.
- sources: docs/research/expanded_188_42seeds/review/FEATURE_SELECTION_AUDIT_188.csv and report_catalog/20261123T114229/full42_generated/DATASET_SCENARIO_BEST_42SEED.csv.
- group descriptive statistics: report_catalog/20261123T114229/grouped_analysis/DATASET_DIAGNOSTICS_179.csv.
- 42-seed best Accuracy = max of policy averages on TEST, *descriptive oracle* not deployable strategy, with ties preserved.
- no SHA256 or private source headers are copied to page JSON.
- partial datasets are never imputed. Snapshot is static, not a live run.
- historic full_scale page remains 5 seeds.
This page is included in whitelisted GitHub Pages site build by being under docs/research/teacher_dashboard/**.


## 2026-11-23 Coverage / Conflict 完整深入版
- [可讀研究判讀報告](./RESEARCH_FINDINGS_COVERAGE_CONFLICT_20261123.md)：六案例、指標定義、風險條件、A/B2 效益與成本。
- [1,504 筆完整資料集 × 情境 × 規則版指標](./coverage_conflict_188.csv)，包含 test/covered/no-match/true-in-candidate 逐 seed 平均筆數，未完成保留為空。
- [24 筆條件群組統計](./coverage_conflict_group_summary.csv)，完整 179 個資料集才計入平均。
