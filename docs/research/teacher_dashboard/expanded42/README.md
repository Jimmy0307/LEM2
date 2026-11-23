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
