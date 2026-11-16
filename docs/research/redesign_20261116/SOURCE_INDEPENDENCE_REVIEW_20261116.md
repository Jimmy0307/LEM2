# Gate 5 來源獨立性稽核：修正證據宣稱（2026-11-16）

## 結論與範圍

Gate 5 預註冊採 OpenML-CC18（study 99）及 OpenML AutoML benchmark（study 271）的候選池。公開註冊表共112筆，依原本 E1–E6b 條件選出51個 `ELIGIBLE_PREPARED`，標記37個來源家族；其餘61筆保留排除或失敗原因（E1 45、E2 6、E3 1、E4 6、E5/E6 3）。所有51筆均含 Raw／Prepared SHA-256、來源ID與原始上游連結。沒有重新挑選、刪除、重新訓練或覆寫確認性結果。

本次獨立**重新比對已提交的** `TEACHER_DATASET_MASTER_20261114.csv`（161筆）與 `CONFIRMATORY_SOURCE_REGISTRY.csv`（51筆）：對原資料 `name`、`domain_family` 正規化後做**名稱層級的精確交集，得到0筆**。再做保守字串包含篩查，出現以下3組**尚未證明同源**的提醒：

| OpenML來源 | 歷史資料 | 為何要人工審查 | 目前判定 |
|---|---|---|---|
| Fashion-MNIST | PMLB MNIST | 名稱重疊，但 Fashion-MNIST是服飾影像、MNIST是手寫數字；不能只因名字相似就視為同一來源 | **不同任務／未見同源證據；保留** |
| jungle_chess_2pcs_raw_endgame_complete | PMLB chess | 一方為不同棋類的棋局狀態，名稱含 `chess` 但不表示同一棋譜 | **尚無重複證據；保留** |
| GesturePhaseSegmentationProcessed | PMLB segmentation | 只共用一般詞 `segmentation`，不能據此判定同一原始資料 | **尚無重複證據；保留** |

另外，`diabetes`（OpenML 37）與 `Diabetes130US`（OpenML 4541）都涉及糖尿病相關任務，來源定義與受試者群體必須用原始 OpenML metadata／資料 DOI 分辨，不得因名稱領域相似直接合併。`Diabetes130US` 實際選入 `patient_nbr` 已由預註冊文件揭露，存在**識別碼型特徵**可能影響分類品質的限制；它不是「缺乏分類效力」的充分證據，也不能事後擅自把這筆來源刪除。

**這個稽核不是原始列級去重**：沒有重新下載歷史161份與51份的全部 raw、沒有使用 fingerprint/join 交叉比對樣本，也沒有獨立驗證 OpenML 每筆數據原始採集鏈。當來源中部分記錄無Raw雜湊時，亦無法從來源登錄檔單獨作出無交疊保證。

因此允許的研究說法為：**「在預先固定的名稱及家族別名排除規則下，51份OpenML資料未出現在已登錄的歷史來源清單；37個來源家族以現有標註為準，家族敏感度分析已附上。」** 不允許的說法為：「已證明與全部161份原始資料完全獨立、51個毫無相依性的領域」。

## 必須保留的初始確認性分析

- `data/G5_PRIMARY_HYPOTHESES.csv`：51份來源×10配對Seeds，H1與H2結果；資料集級統計單位。
- `data/G5_H1_FAMILY_SENSITIVITY.csv`：37個已標記家族內先平均的敏感度檢查，三個H1比較均通過。
- `data/CONFIRMATORY_SOURCE_REGISTRY.csv`：112候選、狀態／排除原因／OpenML DID／source、Prepared SHA。
- `PREREGISTRATION_CONFIRMATORY_20261116.md`：當時凍結的資料選法、超參數、統計方法，**不可修訂既有凍結文檔**。
- `PREREGISTRATION_AMENDMENTS_20261116.md`：修訂順序與首次停止的證據。

## 後續真正的原始來源交叉驗證（非這次已完成）

1. 追溯51份資料各自的 OpenML source citation／download URL、原始採集任務及外部資料家族。
2. 以資料集原始列的 stable provenance、採集事件ID或允許的非個資性特徵 fingerprint 比對舊161來源；不得只比 CSV 順序或字串名稱。
3. 審核 NASA MDP 六份與 AutoML Challenge 多份資料的家族獨立性、來源變體與任何共享樣本。
4. 若發現確定同源，保留原始預註冊分析，**另作標明為 post-hoc 的排除敏感度分析**；不得回頭改寫51來源的預註冊定義。
5. 若準備投稿，需提供第三方可重跑的來源鏈、授權及必要的持久鏡像（目前 `data_cache/` 未提交）。

## 品質閘門

新增 `tests/test_fedrs_publication_integrity.py` 驗證：(a) 161與51來源名稱精確無交疊、(b) 已標記37家族、(c) 51筆Hash與OpenML DID齊全、(d) 主要對照方向與原始CSV相同，且次要比較不能寫反。這個檢查**不取代人工原始來源核對**。
