# LEM2 Full Factorial Experiment — Canonical Package (2026-10-29)

這個資料夾是本次老師討論用的 **唯一正式結果入口**。

## 實驗矩陣

- Datasets: Balance Scale / Car Evaluation / Hayes-Roth
- Split modes:
  - `FULL_DATA`: 同一份完整資料建規則並做 resubstitution 檢查
  - `HOLDOUT_80_20`: 80% 建規則、20% unseen holdout 評估
- Systems:
  - `CENTRALIZED`
  - `FEDERATED`, client count C = 2, 3, 4, 5
- Selection layer:
  - `NONE`: 不選 winner，只看 rules / coverage / candidates / conflict
  - `FIRST_MATCH`
  - `SIMPLE_VOTING`
  - `STANDARD_VOTING`
  - `GLOBAL_STRENGTH`
  - `POPULATION_STANDARD`
  - `POPULATION_GLOBAL`

總共 **210 rows = 30 baseline rows + 180 policy rows**。

## 最重要的概念

`conflict_case_rate` 是在六種 selection policy **之前**計算。

因此：**六種方法不是 conflict 的來源。**

它們只是在同一筆 object 已經 match 到多個不同 decision candidates 之後，決定最後 winner。

本實驗最乾淨的結果是：

- Centralized + FULL_DATA：三資料集 conflict = 0%
- Centralized + 80/20：平均 conflict = 11.77%
- Federated + FULL_DATA：C=2 → C=5 平均 conflict 由 17.93% 上升到 59.99%
- Federated + 80/20：C=2 → C=5 平均 conflict 由 24.47% 上升到 63.98%

## Directory

- `tables/`：正式 CSV，`FULL_FACTORIAL_RESULTS.csv` 為 canonical master table
- `figures/`：SVG + 300 dpi PNG，由同一支 script 產生
- `FINDINGS.md`：研究結果與解釋邊界
- `MANIFEST_SHA256.txt`：檔案完整性

## Figure index

1. `fig01_conflict_rate_by_regime` — FULL_DATA / 80-20 與 client count 對 conflict 的影響
2. `fig02_centralized_conflict_by_dataset` — centralized full-data 0 conflict，但 80/20 暴露 conflict
3. `fig03_federated_holdout_conflict_by_dataset` — 三資料集 client-count sensitivity
4. `fig04_rule_coverage_by_regime` — coverage 與 conflict 不是同一件事
5. `fig05_policy_accuracy_heatmap` — 六方法 Accuracy
6. `fig06_policy_balanced_accuracy_heatmap` — 六方法 Balanced Accuracy
7. `fig07_policy_macro_f1_heatmap` — 六方法 Macro-F1
8. `fig08_federated_holdout_accuracy_by_client_count` — federated 80/20 下 policy 對 C 的敏感度
9. `fig09_true_in_candidate_by_regime` — selection 前正確類別是否存在 candidate set

所有圖都從 canonical CSV 自動重建，不使用 PPT 手抄數字。
