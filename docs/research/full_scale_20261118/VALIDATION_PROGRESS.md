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
  因此遠端 smoke 與全量執行尚未啟動，也沒有 run URL 或最終數據。

GitHub 規則：
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch
