# 全量六策略實驗報告

執行模式：全量。去重後預定來源 188 個；有完整四種情境及全部指定種子的來源 181 個。
預定模型 3760 個，成功 3665 個，未成功 95 個。歷次重試失敗也列於 FAILURES.csv，與模型失敗數分開計算。
完整來源的特徵型態數：{'連續': 79, '混合': 59, '類別/離散': 43}；另有 0 個來源的型態、0 個來源的連續比例因跨種子變動無法以單一值表示。至少 100 個來源且每種型態至少 20 個的條件：通過。

## 型態 × 規模（已準備來源）

| feature_type | 中 | 大 | 小 | 超大 |
| --- | --- | --- | --- | --- |
| 混合 | 23 | 11 | 20 | 10 |
| 連續 | 31 | 26 | 16 | 6 |
| 類別/離散 | 30 | 6 | 7 | 2 |

## 四種情境的最佳方法次數（完整種子組）

| scenario | policy | datasets | wins |
| --- | --- | --- | --- |
| CENTRALIZED | FIRST_MATCH | 184 | 31.53333333333333 |
| CENTRALIZED | SIMPLE_VOTING | 184 | 30.799999999999997 |
| CENTRALIZED | STANDARD_VOTING | 184 | 31.333333333333332 |
| CENTRALIZED | GLOBAL_STRENGTH | 184 | 29.5 |
| CENTRALIZED | POPULATION_STANDARD | 184 | 31.333333333333332 |
| CENTRALIZED | POPULATION_GLOBAL | 184 | 29.5 |
| FED_A01 | FIRST_MATCH | 182 | 15.116666666666667 |
| FED_A01 | SIMPLE_VOTING | 182 | 86.9 |
| FED_A01 | STANDARD_VOTING | 182 | 35.15 |
| FED_A01 | GLOBAL_STRENGTH | 182 | 8.65 |
| FED_A01 | POPULATION_STANDARD | 182 | 22.983333333333334 |
| FED_A01 | POPULATION_GLOBAL | 182 | 13.2 |
| FED_A05 | FIRST_MATCH | 182 | 20.25 |
| FED_A05 | SIMPLE_VOTING | 182 | 81.78333333333333 |
| FED_A05 | STANDARD_VOTING | 182 | 34.36666666666667 |
| FED_A05 | GLOBAL_STRENGTH | 182 | 14.950000000000001 |
| FED_A05 | POPULATION_STANDARD | 182 | 16.7 |
| FED_A05 | POPULATION_GLOBAL | 182 | 13.950000000000001 |
| FED_IID | FIRST_MATCH | 181 | 18.31666666666667 |
| FED_IID | SIMPLE_VOTING | 181 | 39.3 |
| FED_IID | STANDARD_VOTING | 181 | 39.36666666666666 |
| FED_IID | GLOBAL_STRENGTH | 181 | 25.78333333333333 |
| FED_IID | POPULATION_STANDARD | 181 | 36.78333333333333 |
| FED_IID | POPULATION_GLOBAL | 181 | 21.450000000000003 |

## 失敗摘要

| status | 次數 |
| --- | --- |
| FAILED | 5 |
| FULL_MODEL_FAILED | 10 |
| HTTP_404 | 1 |
| IncompleteRead | 15 |
| MISSING_DATASET_JOB_ARTIFACT | 3 |
| TIMEOUT | 95 |

## 運算時間與驗收

模型 wall time 秒數分位數：`{0.0: 0.016, 0.5: 0.3, 0.9: 2.013, 1.0: 2698.388}`。G5 對照：完整通過。規模階梯缺少 10 個資料集／情境／規模組合。未完成種子的資料集與情境不列入 DATASET_BEST 與 SUMMARY。
Smoke workflow：https://github.com/Jimmy0307/LEM2/actions/runs/44381227952；全量 workflow：https://github.com/Jimmy0307/LEM2/actions/runs/44465026637。Artifact：https://github.com/Jimmy0307/LEM2/actions/runs/44465026637#artifacts。

本結果為補跑合併版：原全量 workflow https://github.com/Jimmy0307/LEM2/actions/runs/44381723802 中，下列因資料下載中斷（IncompleteRead）而失敗的資料集／情境 job 已重跑並以本次結果取代，其餘 job 沿用原 run 的 artifact：[('OML51:openml_40996', 'CENTRALIZED'), ('OML51:openml_42732', 'FED_A05'), ('OML51:openml_42769', 'FED_IID')]。原 run 對這些 job 的失敗紀錄以 `RETRIED_` 開頭保留於 FAILURES.csv，不計入模型失敗數。原 run 的輸出檔保持不變。

## 限制

僅使用前六個符合各來源既有選欄規則的特徵；不同 seed 不是新資料。欄位型態或連續比例若隨 seed 變化，REGISTRY 保留各 seed 的實際值；無法用單一比例表示時留空並記錄失敗，未分類來源不計入三種型態的最低數量。Accuracy 偏向多數類；聯邦式為模擬，沒有隱私保證。結果僅描述成功執行的配置，不以重複來源補數。
