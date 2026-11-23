# LEM2 目前資料推送與研究網頁更新｜2026-11-23 18:05（台灣）
**本紀錄屬執行進度回報（operator-reported），不是已驗證的新 model checkpoints。**
目前 GitHub 42-seed 基準已保存 **30,078 個成功模型、179/188 完整資料集**。GitHub `interim/FAILURES.csv` 有 **98 筆 TIMEOUT**，最新本機回報為 **154 筆 TIMEOUT**；**新增 56 筆的逐 Seed／Scenario／檢查點檔案不在此連線可存取的來源內**，因此不能冒充已上傳。
| 欄位 | GitHub 已存證 | 本機新回報 |
|---|---:|---:|
| 模型總目標 | 31,584 | 31,584 |
| SUCCESS | 30,078 | 30,078 |
| TIMEOUT | 98 | 154 |
| SUCCESS + TIMEOUT 紀錄 | 30,176 | 30,232 |
| 尚無成功／逾時紀錄 | 1,408 | 1,352 |
| 全配置成功的資料集 | 179 | 179 |
**相差 56 個 TIMEOUT = OpenML #41027 新增 36（70→106）＋ OpenML #42732 新增 20（28→48）。沒有新的 SUCCESS，不能用 30,232 / 31,584 當成功率。**
## 未完成的九個資料集
| `UCI20:adult_income` | SUCCESS 4 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 164 |
| `OML51:openml_1169` | SUCCESS 0 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 168 |
| `OML51:openml_4135` | SUCCESS 0 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 168 |
| `OML51:openml_41027` | SUCCESS 2 | GitHub TIMEOUT 70 | 本機 TIMEOUT 106 | 待執行或無結果 60 |
| `OML51:openml_41162` | SUCCESS 0 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 168 |
| `OML51:openml_42732` | SUCCESS 0 | GitHub TIMEOUT 28 | 本機 TIMEOUT 48 | 待執行或無結果 120 |
| `OML51:openml_42733` | SUCCESS 0 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 168 |
| `OML51:openml_42734` | SUCCESS 0 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 168 |
| `OML51:openml_42742` | SUCCESS 0 | GitHub TIMEOUT 0 | 本機 TIMEOUT 0 | 待執行或無結果 168 |
其中一筆為 **UCI20:adult_income**，另外八筆為 OpenML，並非九筆全是 OpenML。詳見 [RECONCILIATION_9_DATASETS.csv](./RECONCILIATION_9_DATASETS.csv)。
## 安全與可重現性
- 凍結 2026-11-23 11:42 的 188 資料集 Coverage／Conflict 與 Accuracy 仍以 30,078 SUCCESS 計算，沒有新 SUCCESS 就不重新計算。
- 從本機回報得知兩資料集多數執行達到 2,700 秒上限、剩餘 1,352 個模型；使用者自行調整 timeout。本次不觸碰跑程、排程器或現有成功 checkpoint。
- 4 筆良性重算衝突及剩 5–7 天為使用者提供的現場記錄，未逐筆驗證；網站會標注來源。
- 原始 SUCCESS checkpoints、先前已上傳 98 筆 TIMEOUT 保留於 `../interim/`，56 筆新增本機 TIMEOUT 的原始檔仍須由能存取本機工作目錄的執行環境推送。
