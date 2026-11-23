# LEM2 188 × 42｜真正測試什麼？80/20、Nested Split 與驗證有效性稽核
**審閱狀態：SOURCE-VERIFIED METHODS AUDIT，2026-11-23。**
**重點結論：研究所寫的「full rows」指保留每筆資料集經前處理可用的原始列數作為切分母體，不代表模型使用 100% Rows 訓練。** 所有本批成功模型都是先外層 80/20，再把外層 80% 拆成 80/20，因此大約是 **64% Development / 16% Validation / 20% Test**。

## A. 實際程式流程（逐層可核對）
1. `experiments/full_scale_20261118/sources.py`：先按資料來源載入全部合格的列，選 **最多六個候選 Features**，處理缺失、去除少於十筆的目標類別；得到 `source.frame`（資料列數可以小於原始來源，絕非一定 100% 無剔除）。
2. `fedrs/experiment.py::nested_split`：針對每個 seed，先做 stratified `train=80% / test=20%`（seed），接著在原 80% 內再做 `dev=80% / val=20%`（seed+1000）。概略對原始 source.frame：**Dev 64%、Val 16%、Test 20%**。每個類別採 round 與至少一筆 holdout，因此實際比例可有整數誤差。三者記錄列 ID 不重疊。
3. `experiments/full_scale_20261118/model.py::run_model`：若 CENTRALIZED，`clients={"central": dev}`；若聯邦，`original_partition(dev, target, 3, ...)`，IID 或 Dirichlet label-skew α=.5/.1。原分割失敗才使用 `constrained_partition`。三 client **共享同一組最多六個 features 及同一來源 Target，但各有不同 Rows**。
4. `fedrs/experiment.py::fit_model`：只從 `raw_clients`（Dev）學離散化切點 `EQUAL_WIDTH_3`，每個 client 局部尋找 Classical Exact Minimum Reduct、學 LEM2 規則，再 `union_rules` 合併、去重；支援度與預設類別根據合併的 Dev。**不是真正跨公司異質特徵聯邦，也不是隱私保護加密協定；目前是同構 HFL 模擬**。切點與 pooled supports 亦涉及 Dev 的跨 client 共用計算。
5. `model.py` 中的 A `A_ALL_RULES` 與 B2 `B2_TRUE_AS_FALLBACK`：使用同一組誘導規則，改變空前件 TRUE 規則在推論時的啟用方式；不做第二次規則訓練。
6. 每個 A/B2 分別套入六種固定決策策略：FIRST_MATCH、SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH、POPULATION_STANDARD、POPULATION_GLOBAL。使用 Test Truth 算 Accuracy、BA、Test Coverage、Candidate Coverage、Conflict。**每資料集×Seed×情境只有一個誘導的規則模型；兩版本×六決策策略產生12條報表列，而不是訓練12個獨立規則模型。**
7. 每資料集計畫 **42 Seeds × 4 情境 = 168 個擬合配置**；每配置12列評分 ⇒ 188×168=31,584 擬合配置、預期 379,008 策略結果列。42 Seeds 是**42次重複分層隨機保留測試集（repeated stratified holdout）**，不是 42-fold CV，也不代表每一筆資料都有被保證只測一次。

## B. 研究問題與哪些變數被真正操作

| Research Question | 被操作的自變數 | 固定的控制 | 實際量測的因變數 |
|---|---|---|---|
| RQ1: Local LEM2→Union 與 Centralized LEM2 同 Test 的差異？ | CENTRALIZED vs FED_IID (固定策略、同 Seed) | 同 source, Features, Dev/Test, discretizer, reduct, LEM2 | Accuracy、BA、rule count、Coverage、Conflict、paired Δ |
| RQ2: 在 Client Label-Skew 下是否有非單調 trade-off？ | Fed IID vs α=0.5 vs α=0.1 | 3 clients、同 source Target 和 Features、同外層 Test | Accuracy/BA、Coverage、Candidate、Conflict、rule count |
| RQ3: 有多個互斥決策被命中時，六種投票策略如何不同？ | 6 固定 selection_policy | 同一模型/同一規則集合/Test | 每策略的 Accuracy、BA；同模型六策略差距 |
| RQ4: 空前件 TRUE 規則是否製造衝突、使 Coverage 虛高？ | A_ALL_RULES vs B2_TRUE_AS_FALLBACK | 同 source/seed/scenario/local rules | Candidate Coverage、Conflict、Accuracy、BA |
| RQ5: 是否對隨機切分、來源規模與特徵截斷敏感？ | 42 Seed、188 來源（觀察性分層） | 固定 64/16/20、最多六特徵、C=3 | 跨 seed／dataset 分布；**不是** feature count 或 client count 因果消融 |

**本次沒有操作／無法主張已測試的變數：** 
- 不同 Train/Test 比例（如 70/30、90/10、100% Train）
- 不同 Features Budget（6 vs 8/12/ALL）
- 在 188 主矩陣中改變 Client Count（3 vs 5/10）
- 跨 client 不同 Features／不同 Target、真實加密的私有聯邦
- 由 Validation 選六種策略再以 Test 評估的正式 policy-selection procedure
- 模型沿資料量增長的受控同來源 **Learning Curve**；來源間大小與表現的關聯不等於訓練規模造成變化。

## C. 比「80/20」更重要的風險：Validation 雖然切出來，但這批沒有拿來選策略
`fedrs/experiment.py` 的通用 `policy_rows` 中有 `VALIDATION_BEST` 和 router 程式，但 **188 ×42 本批執行的是 `experiments/full_scale_20261118/model.py::run_model`**，此函式只傳 `val` 進 `fit_model` 做 cut-application；之後只使用 `fm.frames["test"]` 形成六策略預測、比較與 metrics，**沒有呼叫 `policy_rows`、沒有用 Val 導出可事先套用的 winner**。

因此網站過去以每個 dataset×scenario×variant 的六種 Test 42-seed mean 的最高值做「Best Accuracy」，它只能是 **Test-selected descriptive oracle**。不能宣稱：「利用 Validation 在六策略中選出最佳方法並在 Test 上獲得 X% 泛化效能」。也不能用這個 post-hoc 最大值直接當作新演算法優於基線的假說檢定。

### 可以嚴謹拿來說的結果（固定 STANDARD_VOTING，同來源同 Seed paired）
截至 2026-11-23 11:42:29 的完整來源 179/188；基於 `interim/INTERIM_FINDINGS.md`，**A_ALL_RULES、STANDARD_VOTING** 平均 Fed − Central Accuracy 差（pp，179資料集等權）：
- FED_IID **+2.30 pp**（配對 Wilcoxon Holm p<0.001；Fed較差46、持平10、較好123）。
- FED_A05 **−1.12 pp**（Holm p=0.009；Fed較差114、持平2、較好63）。
- FED_A01 **−6.73 pp**（Holm p<0.001；Fed較差139、持平2、較好38）。

以上比較已包含測試分割與策略固定，但不能解讀成「聯邦平均必然比集中式好／差」或代表全部188個來源，因為有九筆大型來源尚未完整且缺漏不是隨機。

### 規則結構結果（A_ALL_RULES，179資料集等權）
- Centralized Coverage 27.56%、Conflict 1.26%。
- FED_IID Coverage 46.75%、Conflict 13.08%。
- FED_A05 Coverage 64.63%、Conflict 27.20%。
- FED_A01 Coverage 86.54%、Conflict 55.48%。
在同一 source 與 Test 上，聯邦規則 union 可能提高候選覆蓋，也會使不同類別規則同時命中。**Conflict Rate ≠ error rate；Coverage ≠ 正確分類率。**

## D. 報告中的「Full Data」正確定義
**Full source rows**：消除過去在資料來源採樣 1,800 Rows 的硬上限；在任何 split 前可用的全部經整理資料列作為母體。**並不表示100% Rows 都進入 Rule Training**。例如 Dataset 有 10,000 個合格 Rows，通常 Dev 6,400、Val 1,600、Test 2,000，三個聯邦 Client 從 6,400 分割（IID 時平均各約 2,133筆，non-IID 不保證相等）。

`train_rows` 這個 19欄欄名在本批 `model.py` **是 `len(dev)`**，也就是**原母體約64%的真正訓練筆數**，不是外層80%的 80/20「Train」。
單一資料集的三個 client 不是6 features÷3=2 features/client；每個 client都持有相同六特徵，但資料列不同。

## D.1. 為何舊版可以選 Full Data，但本次只有 64/16/20？
在已發布的歷史三資料集展示頁 `docs/research/teacher_dashboard/federated_comparison/index.html`，UI 區分 `FULL_DATA` 與 `HOLDOUT_80_20`。其技術報告明確指出：Full Data 是 **訓練資料回代評估（resubstitution）**，不能代表未見樣本泛化。本批 188 × 42 使用另外凍結的 `NESTED_64_16_20` 協定，**並沒有 `FULL_DATA` 配對版本**。因此不能只因兩邊都寫 Full Dataset／42 Seeds 就把數字放在同一個表裡檢定。
**若指導教授要「全部資料學規則」**：可以將原始可用100% Rows學規則的 `FULL_DATA` 作為不同目的的補充探索，但其 in-sample Accuracy 需和 held-out Test Accuracy 完全分開，不可稱作前者較高就是優秀的泛化性能。

## E. 應該如何標記結果有效性

**已測試並可呈現**：固定最多六特徵、三 Client 的 HFL 模擬，與 Centralized 配對的 Holdout Test 指標、六種固定策略差異、A/B2 規則版本、non-IID 的結構權衡；各比較須同一 source/seed/rule-variant/policy。  
**僅供探索**：事後最高策略、來源間特徵數/樣本數分層與非單調曲線、TIMEOUT 來源的部分 Seed。  
**尚未測試**：將16% Val加入 Dev重新訓練的部署終版、90/10 等比例敏感性、特徵擴張與 Client Count 擴張、不同 Feature Schema/Target 的真實跨機構聯邦。

**建議下一階段（不干擾本輪剩餘模型）：**先在相同 holdout 下實作 ValidationBest（只用 Val 選 policy，Test 只評一次）；可再獨立測 Dev+Val 重訓並使用固定 Test 比較。若目標是研究 Split Ratio 影響，另外 preregister `{70/15/15,64/16/20,80/0/20,90/0/10}`，不可將其與本批 baseline 覆寫混算。

## F. 原始證據
- `experiments/full_scale_20261118/model.py`：`run_model`、`split_mode="NESTED_64_16_20"`、直接 Test 6 policies
- `fedrs/experiment.py`：`nested_split`、`fit_model`、通用程式內另有 `VALIDATION_BEST` 但本主批沒有使用
- `roughset/splitting.py`：分層列切分、按類別四捨五入與最少一筆
- `fedrs/partition.py`：原始 IID/Dirichlet 與 constrained resampling
- `fedrs/predict.py`：六種策略、空前件規則 A/B2 與多類衝突
- `docs/research/full_scale_20261118/PROTOCOL.md`：正式凍結方法；`interim/INTERIM_FINDINGS.md`：179完整來源的配對結果

**本次僅補充方法學解釋與網頁呈現，不更動分割、模型、TIMEOUT、成功 checkpoint、原始量測結果。**
