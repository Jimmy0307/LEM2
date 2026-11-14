## 2026-11-15｜G4衝突類型路由、Coverage/Conflict聯合守門與G8約簡＋外測品質

- [新研究互動頁](./g4_g8/) · [正式實驗結論、失敗條件與G4–G8門檻](./g4_g8/G4_G2_G8_VALIDATED_FINDINGS_20261115.md)。
- **G4**：20份公開UCI×新Seeds11、23×IID、Dirichlet α=.5／.1、C3，120組相同規則、1080筆策略結果。Conflict Bucket Router相對固定SV在Non-IID α=.1 **BA +2.314pp**（20來源Bootstrap CI [+0.696,+4.157]）；α=.5 **+0.683pp**；但α=.5不如ValidationBest，不能宣稱原G4跨域Meta停止條件通過。來源稽核與Bootstrap [PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43622293509)。
- **Coverage/Conflict**：20份UCI×3 Seeds×C0/C3，120組凍結規則、360筆比較。集中式Validation-gated supplements 有效Coverage **+13.173pp**、BA **+1.582pp**，Active Conflict **+0.068pp**；聯邦式有效Coverage **+2.391pp**、Active Conflict不變、BA **−0.015pp**。這是有效補充覆蓋非原始Exact Coverage，不將NoMatch當作Rejection。來源實驗 [PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43621841892)。
- **G8 CPU**：4份公開來源、82組實測、36組精確約簡基準配對（候選集合及最小約簡完全一致）、最多6400筆／24特徵Greedy Train POS不變。另在Adult、Connect4、Spambase做**16組全LEM2相同Test配對**，14組BA一樣，1組 +1.099pp、1組 −3.719pp，說明Train POS不等於Test品質，也不能宣稱Greedy是最小基數或完整大數據加速。CPU原始實驗 [PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43621213749)，模型Test品質 [PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43622531133)。
- 只在研究分支新增模組／工作流程／網站，不更動封存基線或聲稱全面G4–G8驗收。資料來源、SHA與不利結果全數保留。

---

## 2026-11-14｜教授用 161 筆完整資料留底（原始／實驗 Rows、Features、分類目標）

- [互動可搜尋資料總目錄](./data_catalog/) · [161 筆 Excel 可開啟 CSV](./data/TEACHER_DATASET_MASTER_20261114.csv) · [161 筆全欄位 JSON](./data/TEACHER_DATASET_MASTER_20261114.json) · [逐筆可列印研究說明](./pmlb_117/TEACHER_ALL_DATASETS_ROWS_TASKS_20261114.md)。
- 範圍：PMLB117 候選（109成功、8失敗）、UCI 新20、追加12、極端7、電商／設備2、三份原始基線＝**161筆批次來源紀錄**。不是161個獨立來源：PMLB有合成、同源多任務，PMLB與UCI可重疊。
- 每筆清楚分開原始資料 Rows／實際進模型資料池 Rows、原始與本輪使用特徵數、類別數、預測任務、來源 URL、成功狀態、Seeds／分布、資料 SHA 與授權限制。
- PMLB 原始資料不重新散布，因單份任務的原始授權尚需查核；保留固定上游 commit、raw/prepared SHA、程式與完整 Test 指標。UCI 來源有明確 Prepared 子集的可下載存檔。
- 需對老師強調：109份PMLB完成981組、5886筆策略評估，但每個資料來源實際 Fit 最多900筆、6特徵，不能宣稱109個真實獨立產業領域或原始大資料全量測試。PMLB部分 `target` 類別語義待回上游原始資料卡確認。

---

## 2026-11-14｜G4–G8：117 預登錄、109 真正完成的 PMLB 六策略適用性驗證

- [109 份資料 G4–G8 互動教授報告](./pmlb_117/) · [正式研究結論、統計與限制](./pmlb_117/G4_G8_109_DATASET_VALIDATION_REPORT.md) · [原始來源完整性 Manifest](./data/PMLB_117_3SEED_MANIFEST.json)。
- Penn Machine Learning Benchmarks（來源 commit `7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68`），預登錄 117 份分類基準資料表，**109 份真實模型成功且來源/Prepared SHA 不重複**、8 份不合格且保留失敗紀錄。實際為 88 個**初步**相關來源家族，不等於 109 個獨立真實產業。
- IID、Dirichlet Label Skew α=.5／.1 × Seeds 1／7／42 × Federated C3；**981 組規則系統、5886 筆六策略測試、32373 筆策略選擇結果**；Train 64%、Inner Validation 16%、Outer Test 20%，測試集不參與選法。**實際 Fit ≤900 筆、≤6 特徵**，不是來源完整大型資料訓練。
- G4 在 Non-IID 有條件 PASS：α=.5 原 109 資料表等權平均 ValidationBest BA **54.113%**，固定 Simple Voting **52.429%**；α=.1 分別 **49.524%** vs **47.707%**；IID ValidationBest **55.718%** vs 固定 Global Strength **55.877%**，無提升。
- G6 五項預先指定的來源家族分群 Wilcoxon/Holm：α=.5、.1 ValidationBest 相對 Simple Voting 均通過多重比較校正（Holm p≈0.000560／0.00000105），但 GuardedSkew 與 LOFO Meta KNN7 **未**證實優於固定 Simple Voting，不能直接視為新的自適應演算法已成功。
- G5 已核驗 Client Label Skew＋資料形態／候選 Coverage／Conflict 條件，但未核驗 Feature/Quantity/Temporal Drift。G7 六方法對固定規則的結構不變性、候選正確率上界已用測試確認，**學術首創仍待證明**。G8 四公開來源、600/1600/3200 筆×4/6/8特徵的 **36組真實 CPU/Memory**，只完成有限規模可行性，不能宣稱 700GB 等級驗證。
- 可重現原始 117 三 Seed [實驗 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43576756817) · [G6 完整性稽核 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43577032785) · [G7 實驗 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43577343600) · [G8 36組 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43576899493)。

---

## 2026-11-14｜34 份公開資料逐 row／column + 32 組 Coverage × Conflict 配對與三條規則機制

- [可互動的資料型態／類別與 Coverage × Conflict 散佈圖](./atlas/)：**34 個公開子集**（原先20、新增12、前期電商／工業2）；已驗證 **195 個實驗特徵欄位紀錄、121 筆類別分布紀錄**。逐資料集保留 UCI 來源、匯入筆數、實際經抽樣／缺值處理後筆數、欄位資料型態、唯一值、缺失值、三個最常見值、數值 p10/p50/p90、重複完整列和 prepared CSV SHA。原始全部特徵數若先前未保存，維持空值而不是臆造。
- [32 組完整 C0/C3 配對](./conflict_atlas/PUBLIC32_COVERAGE_CONFLICT_PAIRS.csv) 與 [來源細節](./conflict_atlas/README.md) 均是 Seed42 固定協定；原先20單獨留在 `PUBLIC20_COVERAGE_CONFLICT_PAIRS.csv`，新增12單獨留在 `PUBLIC_NEXT12_COVERAGE_CONFLICT_PAIRS.csv`，不混成原本三資料集 42 Seeds 基線。
- 32資料集等權探索性平均：**Δ Test Coverage +21.43 pp、Δ Conflict Rate +11.93 pp、Δ (Coverage−Conflict) +9.51 pp；6/32 的無衝突覆蓋反而下降**。此為兩個獨立學習架構的差異，不是「單條規則造成衝突」的因果證明。
- [三條真實規則層級研究](./three_tracks/)：Track A 使用 Letter 的 26 類 × 兩架構（52列）、逐 Test 物件（364列）、逐條規則（1137列）鑑別正確候選是否缺失；Track B 在 Wine/Grid 以 Train-only 剪枝，比較正解候選與 Conflict 下降的代價（Wine C3 Accuracy +2.78pp，Grid C3 −1.94pp）；Track C 以 Haberman/Banknote/Rice 對照 38 條邊際候選規則，測 Coverage／Conflict／Candidate／Accuracy。六份來源驗證通過，僅 Seed42，未完成巢狀調參。
- [額外12份 UCI 來源](./next12/README.md) 和 [Manifest](./data/PUBLIC_NEXT12_MANIFEST.json) 已全部完成、**12／12 成功、零個未補值來源**；168列基線＋24列Train-only補充規則，公開子集在 `docs/research/public_datasets_next12/`，可獨立下載。Ionosphere、Yeast、Image Segmentation、Vehicle Silhouettes、Heart Disease、Raisin、Wine Quality、Student Performance、Vertebral Column、Student Dropout、Blood Donation、Fertility。因原 Seeds 236／QSAR 254 的官方 Python 匯入無法使用，使用有公開目標標籤的替代來源；車輛輪廓資料還明確記錄 846 匯入→845 完整列，Wine Quality 與 Student Performance 都有**預先指定的二元目標衍生規則**。
- 嚴格學術邊界：新32來源只有1個Seed 42／最多6個特徵的可行性掃描；原來源 rows 不等於完整原始 feature space／全量訓練。繼續推進時必須使用多 Seeds、內層 Train/Validation、來源完整列的訓練規模階梯及未見 Test 分布偏移來確認穩定性。

---

## 2026-11-14｜六策略自適應選擇：20 公開資料集 × 3 Seeds × Cross-Domain LODO 正式外測

- [研究互動頁面](./public20/adaptive_six.html) · [源證據、實測結果與負面結論](./public20/ADAPTIVE_SIX_FINDINGS.md) · [演算法 G0–G8 成熟度規格](./public20/ADAPTIVE_SIX_ALGORITHM_SPEC.md)。
- 20 已驗證 UCI 來源 × 3 Seeds [1,7,42] × 2 架構 [C0,C3]，形成 **120 組真正凍結規則系統**；六策略共 **720 筆**獨立外層測試、3,600 筆跨方法比較。64% 開發＋16% 內層驗證＋20% 未見測試；LODO 嚴格排除整份目標資料集所有 Seeds。
- 可實作比較：固定六方法、Inner Validation Best、用 19 個其他資料集驗證成績挑固定方法、其他 19 資料集 Train+Validation Meta-KNN5；Test Oracle 僅不可部署診斷上限。
- 主指標 Balanced Accuracy：固定 GS **61.892%**；LODO Meta **61.744%**；同資料集驗證選法 **61.627%**；不可實施 Test Oracle **62.142%**。Meta 相對固定 GS **−0.148 pp**（20 資料集 Cluster Bootstrap 95% CI 約 [−0.286, −0.038]）。**不能宣稱自適應策略優於固定 GS**。
- 本輪 IID 20 資料集的最佳策略空間非常小，Test Oracle 對固定 GS 也僅 **+0.250 pp**。原 42 Seeds Non-IID α=.1 的更大策略反轉，仍需另做 Train-only 可操作的非 IID 自適應選法驗證，不可把現有 Test 得分當訓練資料。
- [GitHub Actions 原始 60 個實驗來源 PASS（彙整先遇到報表語法錯誤）](https://github.com/Jimmy0307/LEM2/actions/runs/43571344581)；[復用原始 artifacts 完成封版稽核 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43571781178)。
- 學術定位：六方法是共享 Classical LEM2 規則的決策解析程序，Meta-learning/Algorithm Selection 不是新發明；要具備新演算法貢獻仍需 G4 收益、G5 嚴重 Non-IID 穩健、G6 跨資料集統計、G7 消融與理論新穎、G8 大樣本運算成本評估。

---

## 2026-11-14｜六種策略與資料型態／類別偏斜／Client 分布偏斜的適用性分析

- [六策略適用性互動頁](./public20/policy_suitability.html)；[方法定義、適用性矩陣與限制](./public20/POLICY_SUITABILITY_FINDINGS.md)。
- 以 20 個新資料集 Seed 42 的 40 組規則架構 × 六種選法 × Accuracy／Balanced Accuracy／Macro-F1 建立 **720 列保留平票的策略對照**、270 列資料形態分組；形態包括連續／類別／混合、類別多寡與 class imbalance。特徵型態效應尚未能以單 Seed 推論。
- 重新核算原三資料集 42 Seeds 的 **IID／non-IID α=.5／α=.1**，統一各分布 Federated C2–C5 的 **504 組配對比較**；從原始 8,820 矩陣直接重算 IID 聯邦獲勝次數，避免把 Centralized C0 混進 IID 分母。受控 Dirichlet α=.1 下，Simple Voting 平均 BA=49.22% 優於 Global Strength 的 37.93%；IID 則 Global Strength BA=69.25%，Simple Voting 59.63%。
- 保留每組資料的原始來源與 20 資料集的完整子集類別占比（僅做事後描述）；Test Conflict、Test 正確候選不得作為正式 Meta-Selector 的輸入。正式方法需 Train-only profiles 與 Inner Validation 的規則結構指標，並使用跨資料集留一測試。
- 輸出：`data/POLICY_SUITABILITY_20_MATCHUPS.csv`、`data/POLICY_SUITABILITY_20_GROUPS.csv`、`data/POLICY_SUITABILITY_42_DISTRIBUTIONS.csv`、`data/POLICY_SUITABILITY_MANIFEST.json`。GitHub Actions: `policy-suitability-atlas.yml`。

---

## 2026-11-14｜Conflict-Aware 補充規則：三版本研究原型與負面結果

- [互動頁面](./public20/conflict_aware.html) · [研究報告](./public20/CONFLICT_AWARE_FINDINGS.md) · [完整性 Manifest](./data/CONFLICT_AWARE_20_MANIFEST.json)。20 個公開來源 ×（集中式、Fed C3）× 3 個版本，**120 列結果、423 筆逐規則驗證事件**。
- 為防 Test 調參洩漏，固定開發／驗證／測試 = 64%／16%／20%，先用 64% 產生 Classical LEM2、再用 16% 決定 Train-only 補充規則是否入選，最後在完全未接觸的 20% 評估；不直接與前輪 80% 訓練集版本的數字比較。
- 三版本分別為原始 LEM2、全部合格補充規則、驗證集 Conflict-Aware 選擇後補充規則；它們在 40 配置上的 Test Coverage 平均為 53.51%、61.43%、61.14%；Active Conflict 平均為 8.65%、8.71%、8.71%，Accuracy 70.27%、70.58%、70.58%。
- **重要負面結果：Conflict-Aware 篩選只讓 1/40 組 Active Conflict 降低**；因補充規則僅在原始 No Match 時生效，無法影響原始規則的衝突。假設不分層直接合併規則的 Shadow Conflict 確有降低（9.46%→8.90%），但不能混為實際衝突解決能力。
- 已通過規則擬合／驗證／測試隔離、衝突優先序、類別標籤長度、單元測試與 20/20 完整性稽核。**只有單 Seed 42，尚未證明推廣性與統計顯著性**；下一輪需要核心規則 Conflict-Aware 選擇及多 Seed 驗證。

---

## 2026-11-12｜新增 20 個公開資料領域：Classical／Federated LEM2 訓練覆蓋率壓力測試

- 研究頁：[20 份不同特性 UCI 資料集與 Train-only Supplement 測試](./public20/)；來源註冊檔 `teacher_demo/public_20_registry.py`，獨立於原三份基線和之前 9 份外部資料（七份壓力資料與兩份商業／工業）。
- 20 個 UCI 來源：Bank Marketing（222）、Adult Income（2）、Mushroom（73）、Phishing Websites（327）、Spambase（94）、Banknote（267）、Dry Bean（602）、Rice（545）、Letter Recognition（59）、Iris（53）、Wine（109）、Wisconsin Diagnostic（17）、MAGIC Gamma（159）、HTRU2（372）、EEG Eye State（264）、German Credit（144）、Sonar（151）、Haberman（43）、Covertype（31）、Electrical Grid Stability（471）。
- 第一輪 Seed 42 的固定來源／最多六特徵、C0 與 C3、NONE＋六策略，保留 Train/Test exact coverage、Conflict、候選覆蓋率與 Accuracy/BA；外加 **Train-only purity≥90%、support≥5、最多 80 條的作者定義簡化補充規則**，比較 Train/Test Coverage、Accuracy、Balanced Accuracy、被救回數量。此法非原典 MLEM2 補充規則。
- 導入來源完整性：原曾嘗試 UCI Occupancy（357），由官方 Python 介面取得目標欄全缺；UCI Sensorless Drive（325）官方 Python 介面拒絕匯入。保留失敗稽核，改以 EEG（264）及 Electrical Grid（471）維持 20 個真正可評估的來源。
- 最完整來源追溯：`docs/research/teacher_dashboard/data/PUBLIC20_MANIFEST.json`；可重現執行：`.github/workflows/public-20-uci-coverage-benchmark.yml` 及 `public20-finalize-reuse-artifacts.yml`。
- 重要限制：原始 Covertype 581,012 與 Adult 48,842 等較大來源確有下載與固定抽樣；模型只以固定子集訓練，不是原始全量基準。此第一輪只有 **1 Seed**，不能推論普遍適用性或統計顯著性。下一步對最有價值的模型失敗類型再完成完整 42 Seeds、更多 Feature budget、non-IID 與時間／群組外部分割。
- 研究文獻：Inuiguchi & Washimi（2015）https://doi.org/10.20965/jaciii.2015.p0747、Cohen（1995）https://doi.org/10.1016/B978-1-55860-377-6.50023-2、VC-DomLEM（2011）https://doi.org/10.1016/j.ins.2010.10.030、El-Yaniv & Wiener（2010）https://jmlr.org/papers/v11/el-yaniv10a.html。

---

## 2026-11-12｜公開電商／設備故障資料獨立四 Seed 實驗

- 實驗設計及網站：[公開電商與技術設備研究](./public_data/)；新增 UCI Online Shoppers（ID 468, DOI 10.24432/C5F88Q）與 AI4I Predictive Maintenance（ID 601, DOI 10.24432/C5HS5C），皆為 CC BY 4.0 公開資料。AI4I 為合成工業觀測，必須明確註明。
- 固定來源、特徵及抽樣：前者原始 12,330 筆，抽 1,600 筆／6 特徵；後者原始 10,000 筆，抽 2,400 筆／6 特徵。排除電商 PageValues、工業識別欄及故障結果相關欄，以免帶入答案。正式 README 與實驗使用的公開子集在 `docs/research/public_datasets/`（完成核驗後發布）。
- 實際 LEM2 管線：80/20 Holdout，Seeds 1、7、21、42，Centralized / Federated C2–C5，NONE＋六策略，預期 8 個 jobs × 35＝280 結果。額外保存正類 Recall、Train／Test Exact Coverage 差距、No Match fallback accuracy、候選覆蓋及 Conflict。
- GitHub Actions：[公共資料四 Seeds 執行流程](https://github.com/Jimmy0307/LEM2/actions/workflows/public-commerce-tech-uci.yml)。**先導實驗需通過資料雜湊、版本、分母及 8/8 job 完整驗證才能將網頁狀態提升為 PASS**；這不是原主矩陣 42 Seeds，也不能當成新資料的 42-Seed 結論。
- 研究問題：是否不同的資料生成機制（電商購物行為 vs 少數故障）會導致不同的六策略勝者；不能只看 Accuracy，需比較 BA、少數類別 Recall、Conflict 與 Candidate Coverage。

---

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
