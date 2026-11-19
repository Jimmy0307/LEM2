# 驗證進度（尚非全量實驗結果）

- 基準：`006dbe806d802a7fbb912109a0fed185dcaa2f4d`。
- 來源清單：212 筆；依指定同源清單排除 24 筆，188 筆待執行。這不是成功完成數。
- G5：14 個原先未截斷來源、5 個種子、6 種方法，共 420 個 Accuracy 值，
  使用本次模型核心比對歷史檔，容差 1e-12 內均一致。部分來源初次下載
  回應 HTTP 503，重試後成功；前期錯誤保留於
  `experiments/full_scale_20261118/FAILURES.csv`。
- 新增測試：最近分項執行實驗管線 34 項、一般等價測試 11 項及兩項
  大規模記憶體測試，均通過。
  30 萬列、2,000 條規則的 context 與 matching 同時存在時，已在約 2 GB
  位址空間限制下通過；另有 30 萬列、1,000 條規則的支援計算分塊測試。
  這些測試不保證任意規則數或資料集均不會記憶體不足。
- 本機預檢：5 個小型來源、1 個種子、4 個情境，共 20 個模型成功；兩個
  規則版本合計 240 筆方法結果。這不是 GitHub Actions smoke run。
- 全專案測試：最近一次執行 282 通過、2 略過、2 失敗。兩個失敗均因基準版本沒有
  `teacher_demo/CENTRALIZED_VS_FEDERATED.csv`。另有兩項 fork 相關警告。
- GitHub Actions 工作流程檔已通過 `actionlint`。但 GitHub 規定
  `workflow_dispatch` 的工作流程檔必須存在於預設分支；本 repo 的預設
  分支是 `main`，指定的新檔案不在該分支。原始任務禁止修改 `main`，
  將新分支推送後，已對指定 workflow 直接嘗試 `workflow_dispatch`；GitHub
  回傳 HTTP 404，未建立 workflow run。錯誤紀錄在
  `dispatch_attempt_20261119T014702+0800/FAILURES.csv`。因此遠端 smoke
  與全量執行尚未啟動，也沒有 run URL 或最終數據。

GitHub 規則：
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch

## 觸發方式調整（2026-11-19）

為了不修改 `main`，比照本 repo 其他研究分支（例如
`research/server-rule-cost-frontier-20261118`）的做法，在同一個 workflow 檔加入
`push` 觸發：只有本分支上的 `experiments/full_scale_20261118/RUN_REQUEST.json`
變動時才會執行，輸入參數（smoke、shard_count、seeds）從該檔讀取。
`workflow_dispatch` 觸發保留；兩種觸發都在 setup job 統一解析成相同的輸出。
`main_registration_draft.yml` 不會使用，也不會放到 `main`。

## 下載中斷補跑（2026-11-19）

全量 run https://github.com/Jimmy0307/LEM2/actions/runs/44381723802 中，有 3 個「資料集 × 情境」job 因 OpenML 下載中斷（IncompleteRead）而失敗，共 15 個模型：

- openml_40996 / CENTRALIZED
- openml_42732 / FED_A05
- openml_42769 / FED_IID（含規模階梯）

補跑只重跑這 3 個 job，其餘 job 沿用原 run 的 artifact。合併後的結果輸出到 `retry_<run_id>/`。
原 run 的輸出檔維持不變；原 run 對這 3 個 job 的失敗紀錄，在新的 FAILURES.csv 中以 `RETRIED_` 開頭保留。

### 第一次補跑無效，修正後重跑（2026-11-19）

- 第一次補跑（run 44458946036）在合併時遺失原 run 的 385 個模型結果，判定無效，詳見 `retry_44458946036/INVALID_MERGE_NOTE.md`。
- 修正一：合併改為用確切名稱下載原 run 已合併的 `shard-<k>` artifact，只刪掉要重跑的列（`retry_merge.py`）。
- 修正二：OpenML 下載遇到暫時性網路錯誤時，最多重試 3 次（`sources.py`），並新增 `test_retry.py`。
- 第二次補跑仍以原全量 run 44381723802 為基準，重跑同樣 3 個 job。

### 網頁

- Teacher Dashboard 新增 `full_scale/` 子頁，資料副本放在 `teacher_dashboard/data/full_scale_20261118/`；首頁導覽列與 README 各新增一個入口。
- 這個資料夾不在原任務指定的三個路徑內，是應使用者要求新增；只有新增內容，既有內容沒有修改。

### 第二次補跑結果（2026-11-19）

- Run：https://github.com/Jimmy0307/LEM2/actions/runs/44465026637，輸出 `retry_44465026637/`（commit f1332c4）。
- 成功模型 3,665 / 3,760（原 run 3,655 + openml_40996 集中式 5 + openml_42769 FED_IID 5）；G5 通過。
- openml_42732 / FED_A05 這次下載成功，但 5 個 Seeds 都超過 45 分鐘上限，記為 TIMEOUT，與它另外 3 個情境相同。未完成的 95 個模型全部是逾時。
- workflow 的 aggregate 步驟顯示失敗，原因是驗收條件「全部模型完成」與「規模階梯完成」未通過（與原 run 相同），輸出已照常 commit。
- 本機獨立檢查：
  - 19 欄順序、每組 6 法、covered + no_match = test_rows、百分比公式、true_in_candidate ≤ covered：0 違反。
  - 六法 Accuracy 最大差距 ≤ conflict_rate_pct：3,665 組 0 違反。
  - 非補跑的 21,930 列與原 run 逐列相同。
  - openml_40996 與 openml_42769 的補跑結果與第一次補跑（run 44458946036）逐列相同，可重現。
- 原 run 中 openml_42769 FED_IID 規模階梯缺少的 3 列已補齊；規模階梯完成 42 / 52 組，缺少的 10 組都是全量模型逾時。
- 依使用者指示，GitHub Actions 額度不足，本次之後不再啟動新的 run；剩餘逾時列為研究限制。
- Teacher Dashboard 的 `full_scale/` 頁與資料副本已改為此合併版。
