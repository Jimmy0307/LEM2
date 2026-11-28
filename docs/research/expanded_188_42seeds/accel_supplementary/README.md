# 加速程式與不設時限補跑（2026-11-25 ～ 11-28）

## 為什麼要補跑
主實驗（程式 `56e293c`，每個模型上限 2,700 秒）有 8 份資料大量逾時。逾時分析顯示，其中 6 份的時間主要花在**策略計分**：計算「命中規則的支持集聯集大小」時，原本對所有規則做稠密矩陣乘法。

## 加速程式（分支 `accel/bitset-union-20261125`，commit `805ade0`）
- 只修改 `fedrs/predict.py` 的 `_resolve_support_chunked`：
  - 支持集聯集大小改用「只對實際命中的規則做位元集合 OR、再數 1 的個數」計算；
  - 依（類別, 命中樣式）快取，三種支持型策略共用同一個結果。
- 聯集大小是同一個整數，所以分數與預測**完全相同**；沒有改動約簡、LEM2、切分、分割、離散化或任何評估定義。
- **驗證**：
  - `tests/test_bitset_union_equivalence.py`：36 個隨機比對，與原始稠密實作逐值相同；
  - 原有的 `test_full_scale_resolve_equivalence.py` 與 `test_fedrs_parity.py`（16 個）全部通過；
  - 真實資料：`PARITY_RESULTS.txt`。凡是主實驗中有完成的模型，重跑後**全部 IDENTICAL（8/8，0 個不同）**，預測步驟約快 30 倍。

## 補跑結果（WSL `/home/user/lem2_runs/expanded_accel_nolimit`）
- 合約：程式 `805ade0`，`timeout_seconds = 1e9`（實際上不設時限），見 `NOLIMIT_RUN_MANIFEST.json`。
- `openml_41027`、`41162`、`4135`、`42733`、`42734`、`42742`：**各 168/168 完成，0 失敗**。
- `openml_1169`、`openml_42732`：此機器資源無法完成（見 `../status_20261128/`）。
- 沿用與合併的檔案都記錄在 `NOLIMIT_PROVENANCE.json`：
  - 先前 4 小時版本已完成的模型（91 個）；
  - 同合約的 `42742` 專用線（168 個）。
  - 兩者都先通過 `validate_record`，且只沿用已完成的模型，逾時一律重跑。
- **主實驗的逾時紀錄不改**；補跑是另一份補充結果，時限不同，要分開陳述。

## 檔案
- `tools/expanded_resume_20261122/accel/`：
  - 套用與驗證工具（`apply_bitset_patch.py`、`test_bitset_union_equivalence.py`、`compare_parity.py`）；
  - 驗證執行腳本（`parity_run*.sh`）；
  - 補跑資料夾的建立與合併工具（`seed_nolimit_dir.py`、`merge_42742_lane.py`）。
- 啟動腳本：`tools/expanded_resume_20261122/18_*.sh`（4 小時版本）、`19_*.sh`（不設時限）、`20_*.sh`（42742 專用線）。
- 排程器新增 `--defer`（只改順序）與 `--timeout`（只傳給 run.py）兩個選項，並新增 `test_orchestrate.py` 測試，共 14 個通過。
- 補跑的原始檢查點（約 1,300 個 JSON）目前在 WSL 本機，**尚未推上 GitHub**。
