# LEM2 × Federated：教授報告整合網站

**這是完整的研究報告入口，不是純 CSV 測試頁。** 原本分開的完整報告與 CSV 試算頁已整合成一個 GitHub Pages 網站：同一份 8,820 列實測基線、統一導覽、按功能分 URL 子路徑。

## 主入口

- [正式研究報告](./)
- GitHub Pages 根網址：https://jimmy0307.github.io/LEM2/
- 研究分支：https://github.com/Jimmy0307/LEM2/tree/research/report-ready-dashboard-20261109

Git branch 管理整份網站的版本。不同功能用同一分支內的子目錄（網站 URL path）分開，不用另外建立分支導致報告與工具失去一致性。

## 網站功能路由

| 網址（在 /LEM2/research/teacher_dashboard/ 之後） | GitHub 檔案 | 用途 |
|---|---|---|
| 根 /LEM2/ | docs/index.html | 直接導向研究報告 |
| / | teacher_dashboard/index.html | **正式研究報告**：研究問題、流程、42 Seeds、六策略、Conflict、研究限制 |
| /evidence/ | evidence/index.html | **8,820 列完整實測資料**：依 Seed／資料集／拓樸／Client／策略篩選、成對 A/B 比較、下載 CSV |
| /methods/ | methods/index.html | **數學與方法**：Rough Set、Reduct、LEM2、T/U/N/P、指標定義及研究變因 |
| /figures/ | figures/index.html | **前一輪九張原始 SVG**：從 GitHub 原圖檔讀取，與新版 42 Seeds 重算圖分開 |
| /lab/ | lab/index.html | **原始 Python CSV 試算**：分割、Local Rule Union、六策略、逐筆 Conflict 與 Winner |

## 這次的合併方式

**原本完整研究報告：** 保留老師七問、Centralized/Federated 雙路徑、42 Seeds 8,820 筆、四張動態圖、六策略公式、Full Data/80:20 與 Conflict 解釋、non-IID／順序敏感性，以及正式九張歷史研究圖。

**原本「蒜的」試算網頁：** 移到獨立 /lab/。上傳 CSV，選 target、Seed、Full Data/80:20、Centralized/Federated C2-5、IID/non-IID、離散化 bins、Reduct 啟停，執行 repo 原始 LEM2 Python，展示 Train/Test/Client 逐筆切分、Rule Count、Coverage、Accuracy、BA、Macro-F1、匹配規則、支持度與六個 Winner。

**新增完整數據頁：** /evidence/ 嚴格取自已驗證的 8,820 列，與 CSV 自訂試算各自保存；可以對同一 Seed、Dataset、Client 做成對比較。

## 數據可信度與方法界線

- 凍結原始資料：docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv
- 網站 JSON：data/baseline_8820.json。由 teacher_demo/build_teacher_dashboard_data.py 生成；逐 Seed 確認 210 列，NONE 30 列。
- 42 Seeds × 210 = 8,820 列；其中 NONE 1,260 列是規則診斷，不定義 Accuracy，六策略有 7,560 列。
- Full Data 是同資料回代；80/20 是未見資料測試。
- Conflict 是候選類別至少兩種，不是 Rough Set Boundary。應區分 No Match、True Not in Candidate、Candidate Present But Wrong Ranking。
- Reduct 為 Classical positive-region minimum-cardinality reduct，與 DRSA reduct 不是同一方法。
- LERS 原典分類器、DRSA reduct、高風險 Abstain Gate 未在本主矩陣中完成。
- 使用者上傳 CSV 跑出的結果是新實驗，不回填 8,820 列。

## 建議教授報告順序

1. 先開主報告，三分鐘看研究問題。
2. 確認 Centralized 和 Federated 的規則產生路徑；先 LEM2 再 Rule Union。
3. 用 42 Seeds 動態圖說明 Coverage／True-in-Candidate／Conflict 的取捨。
4. 切到 /evidence/，針對 Seed、Dataset、Client、Policy 查核數字與成對比較。
5. 用 /methods/ 說清楚每個分母和六種 Winner 公式。
6. 用 /figures/ 對照原研究九張正式 SVG。
7. 在 /lab/ 現場上傳 CSV，展示逐筆的 Train/Test／Client 分配、規則、Conflict 與 Winner。
8. 以 LERS、DRSA、non-IID 的限制結案，不冒稱未完成成果。

## 驗證與發布

- Chromium 多路由實測：https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-dashboard-browser.yml
- Python CSV 與 8,820 列資料驗證：https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-dashboard.yml
- GitHub Pages 自動部署紀錄：https://github.com/Jimmy0307/LEM2/actions

瀏覽器 QA 檢查首頁直接導向報告，42 Seeds 格子與圖表、evidence Seed 27 的 210 筆、公式頁、九張 SVG，以及 /lab/ 使用 81 筆資料真正執行 Python LEM2，得到六策略、逐筆 Winner 與資料切分。

自訂 CSV 的 Python 執行環境由 Pyodide 載入；需可連 CDN 與 GitHub Raw。大型資料或企業網路受限時，請改用 repo 的正式 Python CLI／run.bat。若要本機預覽，進入 docs 資料夾執行 python -m http.server 8000，再開 http://localhost:8000/。
