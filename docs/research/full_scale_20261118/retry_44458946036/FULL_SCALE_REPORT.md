# 全量六策略實驗報告

執行模式：全量。去重後預定來源 188 個；有完整四種情境及全部指定種子的來源 131 個。
預定模型 3760 個，成功 3280 個，未成功 480 個。歷次重試失敗也列於 FAILURES.csv，與模型失敗數分開計算。
完整來源的特徵型態數：{'連續': 53, '混合': 47, '類別/離散': 31}；另有 0 個來源的型態、0 個來源的連續比例因跨種子變動無法以單一值表示。至少 100 個來源且每種型態至少 20 個的條件：通過。

## 型態 × 規模（已準備來源）

| feature_type | 中 | 大 | 小 | 超大 |
| --- | --- | --- | --- | --- |
| 混合 | 23 | 11 | 20 | 10 |
| 連續 | 31 | 26 | 16 | 6 |
| 類別/離散 | 30 | 6 | 7 | 2 |

## 四種情境的最佳方法次數（完整種子組）

| scenario | policy | datasets | wins |
| --- | --- | --- | --- |
| CENTRALIZED | FIRST_MATCH | 165 | 28.0 |
| CENTRALIZED | SIMPLE_VOTING | 165 | 27.266666666666666 |
| CENTRALIZED | STANDARD_VOTING | 165 | 28.85 |
| CENTRALIZED | GLOBAL_STRENGTH | 165 | 26.016666666666666 |
| CENTRALIZED | POPULATION_STANDARD | 165 | 28.85 |
| CENTRALIZED | POPULATION_GLOBAL | 165 | 26.016666666666666 |
| FED_A01 | FIRST_MATCH | 171 | 13.45 |
| FED_A01 | SIMPLE_VOTING | 171 | 80.23333333333333 |
| FED_A01 | STANDARD_VOTING | 171 | 34.483333333333334 |
| FED_A01 | GLOBAL_STRENGTH | 171 | 8.483333333333333 |
| FED_A01 | POPULATION_STANDARD | 171 | 21.316666666666663 |
| FED_A01 | POPULATION_GLOBAL | 171 | 13.033333333333333 |
| FED_A05 | FIRST_MATCH | 154 | 13.416666666666668 |
| FED_A05 | SIMPLE_VOTING | 154 | 73.28333333333333 |
| FED_A05 | STANDARD_VOTING | 154 | 29.783333333333335 |
| FED_A05 | GLOBAL_STRENGTH | 154 | 12.200000000000001 |
| FED_A05 | POPULATION_STANDARD | 154 | 14.116666666666667 |
| FED_A05 | POPULATION_GLOBAL | 154 | 11.200000000000001 |
| FED_IID | FIRST_MATCH | 162 | 15.816666666666666 |
| FED_IID | SIMPLE_VOTING | 162 | 32.13333333333333 |
| FED_IID | STANDARD_VOTING | 162 | 37.7 |
| FED_IID | GLOBAL_STRENGTH | 162 | 23.616666666666667 |
| FED_IID | POPULATION_STANDARD | 162 | 31.950000000000003 |
| FED_IID | POPULATION_GLOBAL | 162 | 20.78333333333333 |

## 失敗摘要

| status | 次數 |
| --- | --- |
| FAILED | 5 |
| FULL_MODEL_FAILED | 10 |
| HTTP_404 | 1 |
| IncompleteRead | 20 |
| MISSING_DATASET_JOB_ARTIFACT | 391 |
| TIMEOUT | 90 |

## 運算時間與驗收

模型 wall time 秒數分位數：`{0.0: 0.016, 0.5: 0.3, 0.9: 2.125, 1.0: 2698.388}`。G5 對照：未完成：至少一個必要配置或種子缺失。規模階梯缺少 13 個資料集／情境／規模組合。未完成種子的資料集與情境不列入 DATASET_BEST 與 SUMMARY。
Smoke workflow：https://github.com/Jimmy0307/LEM2/actions/runs/44381227952；全量 workflow：https://github.com/Jimmy0307/LEM2/actions/runs/44458946036。Artifact：https://github.com/Jimmy0307/LEM2/actions/runs/44458946036#artifacts。

本結果為補跑合併版：原全量 workflow https://github.com/Jimmy0307/LEM2/actions/runs/44381723802 中，下列因資料下載中斷（IncompleteRead）而失敗的資料集／情境 job 已重跑並以本次結果取代，其餘 job 沿用原 run 的 artifact：[('OML51:openml_40996', 'CENTRALIZED'), ('OML51:openml_42732', 'FED_A05'), ('OML51:openml_42769', 'FED_IID')]。原 run 對這些 job 的失敗紀錄以 `RETRIED_` 開頭保留於 FAILURES.csv，不計入模型失敗數。原 run 的輸出檔保持不變。

## 限制

僅使用前六個符合各來源既有選欄規則的特徵；不同 seed 不是新資料。欄位型態或連續比例若隨 seed 變化，REGISTRY 保留各 seed 的實際值；無法用單一比例表示時留空並記錄失敗，未分類來源不計入三種型態的最低數量。Accuracy 偏向多數類；聯邦式為模擬，沒有隱私保證。結果僅描述成功執行的配置，不以重複來源補數。
