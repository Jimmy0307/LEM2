## 2026-11-12｜Train/Test Coverage 與 No Match 救回：真正可核對的實驗與研究發現

- **[教授報告：Test Coverage／Reject／Train-Test Gap](./coverage/)**：顯示同規則的訓練／測試覆蓋率、缺口、正解候選、Conflict 與降低 No Match 的 A/B 方法。
- 已完成 **42 Seeds × 3 UCI datasets × 5 Classical architectures = 630** 個配對配置；`TRAIN_TEST_COVERAGE_SUMMARY.json`／逐 Seed／逐類別 CSV 都以 `NONE` 凍結 Holdout 基準逐配置核對，Test 不參與規則或離散化擬合。
- **集中式 Train → Test Coverage**：Balance Scale 100.00 → 74.57%（−25.43 pp）；Car Evaluation 100.00 → 93.71%（−6.29 pp）；Hayes-Roth 79.47 → 81.50%（+2.03 pp）。因此不能用 Full Data 的回代 Coverage 直接代替 Train 使用相同 Holdout 規則的 Coverage。
- **僅兩 Seeds 的 Train-only 補充規則先導**：使用固定 90% Train purity、至少 5 筆支持及「刪一個 IF 前件」；只對原本 No Match 測試物件介入。Balance Scale Centralized（Seeds 1、42）Coverage 73.02%→85.71%，Accuracy 71.43%→74.60%，救回 32 筆中 25 筆正確（舊 fallback 答對 17 筆）。此法是作者自己的簡化 A/B，不是完整重現 MLEM2 原論文。
- **K=4 partial-match 先導為另一不同方法**：自訂最多四條、允許最多一個前件不同（Seed 1、7、21、42），不是已驗證的文獻「K4」。它雖把 assisted acceptance 推至 100%，但 Balance Scale Centralized Accuracy 72.02%→64.88%（**−7.14 pp**），Car Evaluation Centralized 88.73%→94.08%（**+5.35 pp**）。不能將 assisted coverage 當原始 exact-rule coverage，亦不能宣稱「更少拒判必然更準」。
- **現有模型沒有正式 reject/abstain**：No Match 仍以 Train majority 產生分類，不能把 No Match 比例直接稱為「已發生拒判率」。應獨立規劃 selective acceptance/rejection 與已接受子集風險。
- **已修正 19 的欄位含義**：正式 `POLICY_COMPARISON_19_HEADERS_42SEEDS.csv` 是**一張 19 表頭的比較表**，第 19 欄 `conflict_rate_pct`；各資料集六策略勝出次數見 `POLICY_WINS_BY_DATASET.csv`（同分分攤）。先前 `conflict_19/` 只是 19 個分析視角，保留作底層 evidence，不再以此當正式報告格式。
- **文獻來源**：Inuiguchi & Washimi（2015）DOI 10.20965/jaciii.2015.p0747；PLOS ONE 離散化／測試覆蓋（2020）DOI 10.1371/journal.pone.0231788；Sequential covering VC-DomLEM（2011）ScienceDirect PII S0020025510005359；El-Yaniv & Wiener（2010）JMLR 11:1605–1641。
- **下一個有效的科研門檻**：以完整 42 Seeds 驗證補充規則救回的正確率、macro BA、True-in-Candidate、Conflict、Test Coverage 及錯誤風險；至少加入多個有不同資料結構的外部資料集；門檻只能以 Train 內層 validation 選擇，不准 Test 調參。

---

## 2026-11-12｜Train vs Test Coverage／K=4 部分匹配／降低 No Match 實測

**驗證現況：** Classical LEM2 分層 IID 42 Seeds 的同規則 Train/Test 配對審核已通過（630 配置、3 資料集 × 5 架構 × 42 Seeds）；K=4（專案自定義，不是已確認的文獻 K4）4 Seeds 先導完整 84 配置已通過；兩者都保留原始 8,820 主矩陣。

- 研究頁：[Test Coverage vs Train Coverage](./coverage/)；GitHub 稽核：[Train/Test 42-Seed workflow](https://github.com/Jimmy0307/LEM2/actions/workflows/teacher-train-test-coverage.yml) 與 [K4 pilot workflow](https://github.com/Jimmy0307/LEM2/actions/workflows/coverage-k4-pilot.yml)。
- **Test Rule Coverage**＝有至少一條嚴格匹配規則的 Test 筆數／全部 Test；**Train Rule Coverage** 同理，但分母為 Train，採同一份 Train-fitted Reduct／規則。
- **No Match**＝嚴格規則未命中。既有系統會輸出 Train 多數類別而不是「拒判」，所以正式原模型沒有顯式 Reject Rate；不可把 No Match 當已實現的拒判機制。
- **Candidate Coverage**＝真實類別出現在命中規則提出的候選中的 Test 比例。**Covered-only Accuracy**＝已命中規則的 Test 中最終答對比例。Test Coverage 不能代替後兩者。
- **Train/Test 42 Seeds**（分層 IID，Classical）：Balance Centralized Train 100.00%、Test 74.57%；Car Centralized Train 100.00%、Test 93.71%；Hayes Centralized Train 79.47%、Test 81.50%。Test 與 Train 的差異只能在同規則／相同 Seed 配對後解讀。
- **K4 四個 Seeds**（1、7、21、42，Centralized，First Match）：Balance Test Coverage 75.40%→Assisted Acceptance 100.00%，Accuracy 72.02%→64.88%（−7.14 pp）；Car Coverage 92.70%→Assisted 100.00%，Accuracy 88.73%→94.08%（+5.35 pp）；Hayes Coverage 85.58%→Assisted 100.00%，Accuracy 75.00%→74.04%（−0.96 pp）。**Assisted Acceptance 不等於原始嚴格規則 Coverage 提升**，也沒有理由保證 Accuracy 上升。
- **K4 方法的定義與限制**：只有嚴格 No Match 時啟動；最多容許一個規則前件不符合，取距離最近四條條件規則加權選類別；無補充候選則回退 Train 多數類別。這是研究線 A1 的先導，不應直接稱為 RSES 或正式文獻既有的「K4」方法；未經 Train-only 校準，不能作最終方法優越結論。
- **19 欄表格已更正**：主檔 [POLICY_COMPARISON_19_HEADERS_42SEEDS.csv](data/POLICY_COMPARISON_19_HEADERS_42SEEDS.csv) 是「18 個欄位＋第 19 欄 conflict_rate_pct」；[POLICY_WINS_BY_DATASET.csv](data/POLICY_WINS_BY_DATASET.csv) 列各資料集六策略勝出次數及平票分攤。先前的 conflict_19/ 是 19 個分析視角，不是使用者原來的 19 欄需求，保留為歷史稽核而非主表。
- **跨資料集擴充**：新增 7 個 UCI 來源、2 Seeds × 基線／Train-only 20% 標籤雜訊（28 個任務、980 列），檔案為 data/EXTREME_UCI_PILOT_*；屬於獨立探索，尚不能與三資料集 42 Seeds 直接合併做統計推論。
- **接下來要測試的介入**：A0 exact rule matching；A1 部分匹配（K1／K4／K8），僅在 No Match 時使用；A2 Train-only 補充規則；A3 可變一致性或粒度；A4 正式 selective reject／risk–coverage curve。所有參數必須在 Train 的內部分割選定，Test 僅做最後評估；比較 NoMatch、Candidate Coverage、Conflict、BA、Accuracy、各類別失誤率與新增回答的正確率，不能只優化可回答比例。
- **相關經核對文獻**：Inuiguchi & Washimi 2015（https://doi.org/10.20965/jaciii.2015.p0747）、Stańczyk et al. 2020（https://doi.org/10.1371/journal.pone.0231788）、El-Yaniv & Wiener 2010（https://jmlr.org/papers/v11/el-yaniv10a.html）、VC-DomLEM（https://doi.org/10.1016/j.ins.2010.10.030）；文獻中的各種 Coverage 分母不可直接視為同一指標。

---

## 2026-11-12｜新增獨立 42-Seed non-IID 延伸執行流程（與 Classical IID 主基線隔離）

- **已建立且已啟動** [non-IID 42-Seed GitHub Actions](https://github.com/Jimmy0307/LEM2/actions/workflows/noniid-42-extension.yml)：以 Seed 1–42、三資料集、Federated C2～C5、Dirichlet alpha 0.5/0.1、HOLDOUT_80_20、NONE＋六策略執行，預期最多 7,056 列有效模型結果。
- **研究定位**：此擴充仍是 Classical reduct + LEM2，只變更 Client 資料分配為 non-IID；不等於 DRSA、LERS 或原本的分層 IID 8,820 列。
- **結果可用性**：工作流程在 42 個 Seed 都執行完成、完成配對驗證並成功發布 `data/NONIID_42_SUMMARY.json` 之前，網站僅能顯示原有 Seed 1、42 的先導狀態，不得宣稱延伸研究的 42-Seed 數值已完成。
- **完整性檢查**：每個有效非 IID 配置必須能對應同 Seed、同 Dataset、同 Client、同 Policy 的 IID 結果；無效 Client partition 記錄於獨立 ERROR CSV，不填 0。比較時先固定資料集、再計算相同 Seed 的配對差距。
- **發布資料**：完成後分支將包含 `NONIID_42_RESULTS.csv`、`NONIID_42_ERRORS.csv`、`NONIID_42_PAIRED_IID.csv` 與 `NONIID_42_SUMMARY.json`。網站只有讀到符合契約的 JSON，才會解除「僅先導」標示。

---

## 2026-11-12｜Classical／Federated 42-Seed 對照與統計單位

- 新增 [42 Seeds／版本與 pp 解釋](./versions/)：自凍結 8,820 主矩陣讀取、驗證每 Seed 210 列，展示 Classical 集中式與聯邦式 C2–C5、六策略的 42-Seed 實測比較，以及前 1／7／21／42 Seeds 的均值與 SD。
- **方法標籤**：正式 42 Seeds 全部屬於 Classical positive-region reduct + LEM2（不是 DRSA reduct 或文獻原典 LERS）。
- **證據邊界**：non-IID Dirichlet 先導僅有 Seed 1 與 Seed 42；Client-order 先導亦為 Seed 1、42；Hayes 另有 42-Seed 特定協定；DRSA/LERS 無等價 42 Seed 主矩陣。
- **pp = 百分點**；70% → 75% 是 +5 pp，相對變化約 +7.14%。表中差距取固定 Seed 的配對平均，不能將 42 次切分當 42 個外部獨立資料集。
- 主矩陣的分層 IID 42 Seeds 已完成；任何 non-IID 或其他 reduct 實驗均須保存個別 evidence manifest，不能冒充舊的 8,820 列。

---

## 2026-11-12｜教授報告：Conflict、無衝突、No Match 與平票決勝說明

新增 [Conflict 決策與指標教學頁](./conflict/)；報告首頁也提供導覽入口及精簡的三狀態流程。

- **No Match**：無命中規則；六策略均使用訓練資料多數類別預設預測。
- **Matched without Conflict**：命中規則只提出單一候選類別；六策略均輸出該類別。
- **Conflict**：不同決策候選同時出現；六策略在同一固定規則集合上選 Winner。Conflict 診斷獨立於策略、發生在策略計分之前。FIRST_MATCH 只回傳首條匹配規則，不代表原規則集合沒有 Conflict。
- **Tie-breaking**：FIRST_MATCH 不使用計分；其餘五種計分策略共用 roughset/evaluation.py::_resolve_vote()，先以 np.isclose 判定最高分候選；訓練集多數類別若在同分集合內優先勝出，否則字串排序取第一。
- **評估分母**：Overall Accuracy、Balanced Accuracy、Macro-F1 包含整個測試集；Conflict-only accuracy 只用獨立標記的衝突子集。N_conflict=0 時後者未定義（NaN），不可填 0。
- **教學互動**：可修改類別分數與多數類別觀察平票決勝；100 筆示意資料可調各群組正確數以理解 Overall 與 Conflict-only 差異；非正式實測資料。
- 不修改模型程式、既有實驗數字、凍結基線或資料切分，僅新增研究展示與解釋。

**驗證來源：** roughset/evaluation.py::predict_with_policy、_resolve_vote；roughset/pipeline.py::_evaluate_system（事前 Conflict 旗標與 conflict_resolution_accuracy）。

---

## 2026-11-11｜教授報告 V2：以可點選全流程為主視覺

本次修復六個報告問題：
1. 42 Seeds 每格顯示指定條件的真實數值；選 Seed 立即同步更新流程節點、42-Seed 分布、五種學習配置、六策略及最後結論。
2. 所有報告圖共用同一套 Dataset／Seed／Split／System／Client／Policy 控制條件；原 8,820 筆仍可在 /evidence/ 查完整列。
3. 原「拓樸」更精確稱「規則學習架構」（Centralized vs Federated C2–C5）；Seed 是隨機抽樣重複，不是時間；42-Seed 圖採散點，不宣稱趨勢。
4. 將 37 欄正式基準資料完整導入網站：Train/Test 筆數、Reduct 大小、Local Rule 指標、No Match／Conflict 筆數與衝突子集準確率都有明確分母。
5. 將 Conflict 解釋成有順序的判斷：No Match → 正確類別未入候選 → 正確候選存在但選錯 → 最終評估。候選分解可由 Coverage／True-in-Candidate 推導，但「候選有正解卻選錯的筆數」不能從 8,820 列摘要單憑 Accuracy 還原，須用逐筆 trace。
6. 完整流程（Train／Reduct／LEM2／Local Rule Set／Union／Matching／NONE／六策略／42 Seeds）移到報告首頁，按節點看輸入、公式、輸出、實測數值、程式位置；可展開全部階段；總結集中在最末章。

**重大公式註記：** 舊版把 STANDARD 權重和 Population 的 T/U 當成普遍相同。原始程式實際上：集中式 STANDARD 使用符合 Antecedent 的訓練物件數；聯邦式 STANDARD 的 Global Rule 權重由所有 Client 的 Antecedent 且 Consequent 正確支持數組成。因此在 Federated 上 W_d=T_d，但 Centralized 不必成立。需依據 roughset/evaluation.py 與 roughset/pipeline.py 各自描述，不能混用。

GitHub Pages 入口仍固定：https://jimmy0307.github.io/LEM2/ 。本次沒有更動原始 8,820 列觀測結果，只擴充可視化資料契約與解釋。

---

# LEM2 × Federated：教授報告整合網站

**這是完整的研究報告入口，不是純 CSV 測試頁。** 原本分開的完整報告與 CSV 試算頁已整合成一個 GitHub Pages 網站：同一份 8,820 列實測基線、統一導覽、按功能分 URL 子路徑。

## 2026-11-11 已稽核修正與最佳條件

- **[最佳配置與決策看板](ranking/)**：依 Accuracy、Balanced Accuracy、Macro-F1、Coverage、Conflict 自動排名；每個資料集獨立顯示前幾名、42 Seed 標準差與差距。
- **[研究修正完整說明](VALIDATION_20261111.md)**：Hayes-Roth 新增 UCI 132/28 及四特徵組合不重疊 80/20，共 2,520 列獨立證據；42 Seed 7,560 組逐筆 Conflict 精確交集；限制推論措辭。
- [Hayes 額外協定 CSV](data/HAYES_HOLDOUT_PROTOCOLS_42SEEDS.csv)｜[Conflict 精確分解 CSV](data/CONFLICT_EXACT_42SEEDS.csv)。原 8,820 筆不變。

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
| /versions/ | versions/index.html | **Classical／Federated 42-Seed 實測比較**、其他版本證據完整度、Seed 數量與 pp 定義 |
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
