# G4–G8 跨 109 份公開資料集的六策略適用性驗證與演算法成熟度報告

**版本**：2026-11-14（G4–G6 三 Seed、G7 結構性質、G8 實測 CPU 規模）  
**方法**：Classical Positive-Region Exact Minimum-Cardinality Reduct + LEM2；Federated C3；固定規則後比較六個不同 Winner Resolver。  
**主結論**：**「Inner Validation 選擇六策略」在 Non-IID α=.5、α=.1 的 Balanced Accuracy 勝過最佳固定六策略，但在 IID 不勝出。** 此效益是條件式、依賴可使用具標籤的內層驗證資料；不是六個全新規則歸納演算法，也尚未證明 Meta KNN、硬式偏斜守門或原始規則衝突控制有新穎性。

## 一、資料與稽核結果：不是用 100 個檔名湊出一個結論

原始候選共 117 個 [Penn Machine Learning Benchmarks (PMLB)](https://github.com/EpistasisLab/pmlb) 分類表格，預先固定來源 commit `7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68` 及篩選：非 deprecated、原始筆數至少150、2–12類、至少2個特徵。只在真正取得公開原始 gzip、核對來源 SHA-256、保留 Prepared SHA-256、成功跑完六策略及 64%／16%／20% 切分後計數。

| 稽核項目 | 事實 |
|---|---:|
| 固定候選資料表 | 117 |
| 真正成功下載並跑出完整 IID 六策略 | **109** |
| 源 gzip SHA-256 不重複 | **109** |
| Prepared CSV SHA-256 不重複 | **109** |
| 未通過最低樣本／類別要求 | 8，保留失敗紀錄 |
| 相關資料家族（初步人工規則分群） | **88**，**不能宣稱88個完全獨立真實領域** |
| 來源 PMLB 模型設置 | 109 × 3 Seeds × 3 分布 = **981** |
| 真正規則解析測試輸出 | 981 × 6 = **5,886** |
| 方法選擇評估輸出（含不可部署 Test Oracle） | **32,373** |

未通過的8個候選為 `allbp`、`allhyper`、`auto_insurance_symboling`、`fars`、`page_blocks`、`shuttle`、`wine_quality_red`、`wine_quality_white`。需查逐筆來源失敗報告，不能直接把它們算進績效分母。

**關鍵限制**：實驗使用原始公開 PMLB 資料的固定抽樣（模型實際最多900筆，最多前6特徵）；來源包含合成資料、相同原始資料的不同任務及變體。不能聲稱這是 109 個彼此獨立的自然領域，亦不能宣稱把原始數十萬／百萬筆資料直接丟進了 LEM2。公開的上游套件授權不保證每個原始資料表可以再散布；因此只發布來源連結、原始雜湊與指標，不重新散布 PMLB raw rows。

## 二、方法與評估協定

- Seeds：**1、7、42**，各資料表獨立分層切分為 64% 規則歸納、16% 內層驗證、20% 真正未見測試。不使用測試集挑策略。
- Clients：**3**。IID 採 STRATIFIED，Non-IID 用 Dirichlet Label Skew α=.5、.1；**這是 Client Label Skew，不是數量偏斜、特徵偏斜、時間概念漂移**。
- 六個解析器依現有程式 `roughset/evaluation.py`：FIRST_MATCH、SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH、POPULATION_STANDARD、POPULATION_GLOBAL；使用**完全相同**的 Reduct/LEM2 規則集合，並且共享預設多數類別 No-Match fallback。
- **VALIDATION_BEST**：只在16% Inner Validation 上按主要目標 Balanced Accuracy 排序六策略，確定後固定策略，在20% Test 評估。
- **GUARDED_SKEW_V1**：預先固定 Client label JS≥.10 且 Validation Conflict≥.10 且 Validation BA Simple Voting 比 Global Strength 多至少2pp 才切換，否則沿用 Global Strength。
- **LOFO_META_KNN7**：用另外的資料家族的訓練／內部驗證特徵，預測六策略的期望內部驗證 BA。排除整個目標資料家族及三個 Seeds，與 VALIDATION_BEST 不同；K=7 在結果前固定。
- **TEST_ORACLE_DIAGNOSTIC**：僅事後使用 Test 真實最好成績作診斷上限，不是策略，不可部署。
- 評估：Balanced Accuracy（主要）、Macro-F1、Accuracy，以及 Match Coverage、Conflict、候選正確覆蓋、訓練類別比例與 Client label JS。

## 三、在什麼資料條件更好：Balanced Accuracy 的實測矩陣

三 Seeds、109 個公開表格，**每分布327個配置**。分數為配置等權 Test 平均，單位%。

| 事前 Client 分布條件 | 內部驗證平均 JS divergence | Validation Conflict | Validation Coverage | 最好固定策略（六種） | VALIDATION_BEST | 差距（pp） |
|---|---:|---:|---:|---:|---:|---:|
| **IID** | 0.000026 | 21.10% | 69.43% | **Global Strength 55.88%** | 55.72% | **−0.16** |
| **Non-IID α=0.5** | 0.1363 | 44.66% | 87.61% | **Simple Voting 52.43%** | **54.11%** | **+1.68** |
| **Non-IID α=0.1** | 0.2897 | 75.70% | 95.36% | **Simple Voting 47.71%** | **49.52%** | **+1.82** |

### 與「資料偏鋒」相關的交叉條件

以下均為 109 表 × 3 Seeds 的**觀察性事後分組**，群組特徵來自 Train／Inner Validation，Test 只用於報告結果。這些不是已經成立的因果法則。

| 主要條件 | 比較配置數 | 兩固定策略與自動選法（BA %） | 可支持的判斷 |
|---|---:|---|---|
| Non-IID α=.1，**Validation Conflict≥40%** | 270 | GS **43.57** / Simple **49.49** / ValBest **51.41** | 衝突密集且 Client 偏斜時，選法的增益大於 IID |
| Non-IID α=.1，**Validation Conflict<10%** | 12 | GS 37.59 / Simple **38.48** / ValBest 38.46 | 低衝突時選擇器通常沒有額外增益；樣本只有12配置 |
| Non-IID α=.5，**Validation Conflict≥40%** | 178 | GS 50.69 / Simple 54.06 / ValBest **56.55** | 中偏斜而高衝突仍有明顯優勢 |
| IID，**Validation Coverage<30%** | 47 | GS **39.47** / Simple 39.26 / ValBest 39.31 | 無命中主導時，改投票不能解決規則來源不足 |
| Non-IID α=.1，**少數類<10%** | 78 | GS 32.88 / Simple 33.56 / ValBest **36.55** | 有相對提升，但絕對 BA 仍低，不能當已解決稀有類別 |
| Non-IID α=.1，**6類以上** | 54 | GS 28.69 / Simple 27.14 / ValBest **30.29** | 多類別下策略選擇依然有限；規則與候選生成更重要 |
| Non-IID α=.1，**全數值型（Train 判斷）** | 93 | GS 43.46 / Simple 47.69 / ValBest **50.32** | 無論資料是否為連續型，都可能有非IID選法效益 |
| Non-IID α=.1，**全類別型（Train 判斷）** | 107 | GS 42.57 / Simple 51.20 / ValBest **53.30** | 原始資料型態並非唯一選法依據 |

**所以最準確的「什麼時候更好」不是按連續／離散二分，而是：**
1. 訓練集 Client 標籤分布有明顯差異；
2. 規則在內部驗證的跨類別 Conflict 不低；
3. 六策略在驗證集的 Balanced Accuracy 有可觀測的差異；
4. 有足夠代表少數類別的**有標籤內部驗證資料**可比較。

反過來：IID、原本少衝突、規則無命中、驗證集太小，以及真正的正確候選不存在時，不應只靠動態切換投票法。

## 四、G4–G6 的統計核驗：多 Seed、按來源家族做保守分群

五組主要對比在三 Seeds 完成前預先指定。按初步來源家族等權（88組）聚合 Seeds／相關來源變體，再做單尾配對 Wilcoxon；針對五個比較作 Holm 校正；同時提供2500次家族層級探索性 Bootstrap。

| 預先指定 Balanced Accuracy 對比 | 家族等權平均變化（pp） | 95% Bootstrap CI（pp） | Holm p | 判定 |
|---|---:|---:|---:|---|
| IID：ValidationBest − GlobalStrength | **−0.160** | [−0.474, +0.175] | 1.000000 | 沒有優越性 |
| α=.5：ValidationBest − SimpleVoting | **+1.825** | [+1.006, +2.769] | **0.000560** | 有正向基準證據 |
| α=.1：ValidationBest − SimpleVoting | **+1.956** | [+1.240, +2.745] | **0.00000105** | 有正向基準證據 |
| α=.1：GuardedSkewV1 − SimpleVoting | +0.418 | [−0.106, +0.952] | 0.130317 | 尚未建立穩定優越性 |
| α=.1：LOFO Meta KNN7 − SimpleVoting | −0.190 | [−0.637, +0.250] | 1.000000 | 尚未建立優越性 |

**這很關鍵**：目前真正被驗證支持的演算法型態是**有標籤 Inner Validation 的策略選擇**，不是特徵自動推理 Meta KNN7 或固定 JS/Conflict 守門。後兩者的選擇效果不足，不能直接把它們視為論文主貢獻。

此外，以 88 個初步來源家族比較六個固定策略的 Friedman 檢驗，在 IID、α=.5、α=.1 皆觀察到差異（p值分別約 6.7e-12、.001412、<1e-12）。但 PMLB 相關變體與原始來源未完全人工去重，仍需另一套真正獨立資料基準驗證。

## 五、G7：形式化性質能證明什麼？學術新穎性還欠什麼？

固定規則集合 \(R\)，對物件 \(x\)：

\[
M_R(x)=\{r\in R : x\models\mathrm{Ante}(r)\},\quad
C_R(x)=\{d(r):r\in M_R(x)\}.
\]

對**不重新歸納規則**且使用相同 No-Match fallback 的六種決策解析器，有下列直接可驗的形式性質：

1. **結構不變性**：`ExactCoverage(R)`、`ConflictRate(R)` 不因策略變更。換投票公式不能增加真正的規則命中。
2. **衝突上界**：當 \(|C_R(x)|\le1\) 時，六策略的最終預測一致。因此任何兩策略預測不一致的物件，只可能在 \(|C_R(x)|>1\) 的衝突子集；其 **Accuracy 差距的絕對值不可能超過 ConflictRate**。
3. **候選正確率上界**：規則已命中而真實類別 \(y\notin C_R(x)\)，則六策略都無法選到正確類別。整體 Accuracy 上界可寫成「正確類別已在規則候選集合的物件比例 ＋ No-Match 且多數類別 fallback 剛好正確的比例」，不得把 fallback 視為規則 Coverage。

這些是對現行實作的數學稽核與適用性界限，**不是可據此認定學術首創的定理**。程式測試 `teacher_demo/test_six_strategy_properties.py` 驗證了結構性質；測試通過並不等於已經完成所有可能輸入的形式化證明。

### 最新相關先行研究與新穎性風險

| 研究 | 已經做到 | 對本專案的邊界 |
|---|---|---|
| [Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7297591/) | 約簡、規則與 Voting 策略選擇 | 不能宣稱「加權規則投票」是新發明 |
| [Decision rules for dispersed data using a federated learning approach (2023)](https://www.sciencedirect.com/science/article/pii/S1877050923015855) | 分散式粗糙集、Global Reduct、決策規則與 Majority Voting | 不能宣稱首次將 Rough Set 規則聯邦化 |
| [Algorithm selection on a meta level (2022)](https://link.springer.com/article/10.1007/s10994-022-06161-4) | 基於 Meta-learning 的演算法選擇與組合 | 單純的 KNN Meta-selector 本身不是新發明 |
| [Towards Rule-Based Knowledge Sharing in Federated Learning (2026)](https://proceedings.mlr.press/v306/qin26g.html) | 高覆蓋、稀疏有益規則選取與跨模型異質協作 | 不能宣稱「選有益規則減少傳輸」是首創 |
| [SEMTRA (2026)](https://www.mdpi.com/2504-4990/8/7/181) | Conflict-aware Rulebook、加權決策與 Soft Matching | Conflict-aware + Soft Matching 組合已有直接相關前例 |
| [Demšar (2006)](https://jmlr.org/papers/v7/demsar06a.html) | 多資料集非參數統計比較框架 | 要避免依賴 981 組相關配置虛增統計獨立性 |
| [Cawley & Talbot (2010)](https://jmlr.org/papers/v11/cawley10a.html) | Model Selection 本身也會過擬合 | 必須避免用 Test 對 Selector 選參數後又宣稱有效 |

**結論：G7「實作與結構稽核」有成果；G7「新演算法新穎性」未通過。** 若要成為新的 Rough-Set/LEM2 演算法貢獻，需要提出本質上不同的規則／衝突表示、可檢驗的風險性質或超越一般 Validate-the-Six 的新選擇機制，再以消融證明其獨立貢獻。

## 六、G8：真實 CPU 規模階梯（不靠理論猜時間）

另外抽出四份 PMLB 公開來源（Adult、MAGIC、Connect-4、Spambase），測試**同一 Classical LEM2 管線**在 600、1600、3200 筆，以及 4、6、8 個特徵的**36組真實**實驗。

| 資料筆數 | 4特徵 Fit 中位秒 | 6特徵 Fit 中位秒 | 8特徵 Fit 中位秒 |
|---|---:|---:|---:|
| 600 | 0.422 | 0.773 | 2.282 |
| 1,600 | 0.781 | 1.515 | 3.825 |
| 3,200 | 1.481 | 2.425 | **7.003** |

Adult 單一來源的 600筆×4特徵與 3200筆×8特徵分別為 1.039 秒與 25.949 秒，約 **25倍**。這是 Rows 與 Features 同時變動的實測，不應拆成單獨的線性或指數歸因。

程式 `roughset/reduct.py` 目前透過 `itertools.combinations` 從0特徵一路搜尋最小正域不變的約簡，最壞可能搜尋 \(2^m\) 個特徵子集，加上逐組 groupby 正域計算。這解釋高特徵維度具有**組合式搜尋瓶頸**；資料庫／快取／GPU 及近似約簡等替代實作仍待獨立公平對照。

**G8 僅能稱「有限規模 CPU 實測 PASS」**：沒有測到20+特徵、十萬筆實際訓練、700GB資料庫、企業 GPU/多裝置、Client 10–100 或完整大資料 I/O；不能憑此宣稱工程擴展性完成。Peak RSS 是各流程啟動後的最大記憶體，不是每配置的邊際記憶體，解讀時要保留限制。

## 研究一致性補充：原始 G4 Stop Condition 不能因新實驗而重訂

早期 `public20/ADAPTIVE_SIX_ALGORITHM_SPEC.md` 將 G4 的完整條件定義為：**跨資料集的 Meta Selector 在獨立未見資料集上不輸／優於最佳固定策略**。本輪 **LOFO Meta KNN7 在嚴重 Non-IID 並未打敗固定 Simple Voting**（α=.1，BA 47.604% 對 47.707%；家族層級配對平均差 −0.190 pp、Holm p=1.0）。因此 **原訂 G4 完整 Gate 仍是 NOT PASS**。把本輪 VALBEST（依每份目標資料集自身的16%內驗證標籤選策略）的正向效果稱為 **G4b：可驗證有標籤情境的條件式收益**，是另一個應用子軌，不能取代原 G4。

**同理，G5 原訂包含 Feature／Quantity／Temporal shift、G6 原訂真正獨立資料領域、G7 原訂新穎性、G8 原訂全量大型資料。** 本輪在每一 Gate 均有真實實驗／稽核輸出，但未因此聲稱原訂完整標準已經通過。

---

## 七、G4–G8 最終驗收看板

| Gate | 本次真實完成內容 | 結論 |
|---|---|---|
| **G4 泛化績效** | 109份 ×3Seeds ×3分布；自身內驗證選法在 α=.5/.1 的BA優於任何固定單法，但跨家族 Meta KNN 未贏 | **原訂跨資料集 Meta 優越性 NOT PASS；有標籤 VALBEST 條件式 PASS** |
| **G5 偏斜穩健性** | IID、Client Label α=.5/.1、Train JS 與規則 Conflict、不同類別比例/類型實際比較 | **Label Skew PASS**；Quantity/Feature/Temporal shift 尚未驗證 |
| **G6 統計** | 88個初步家族、3 Seeds、五項事前指定 Wilcoxon/Holm、Friedman、Bootstrap | **Benchmark 內 PASS**；原始來源家族人工去重與跨基準外推未完成 |
| **G7 新穎性** | 三條核心結構性質、程式回歸測試、2020–2026 先行研究對照 | **技術稽核完成，學術首創 NOT VERIFIED** |
| **G8 大型運算** | 四個公開來源、36個真正 CPU/記憶體規模階梯 | **小／中型實測 PASS，企業級擴展 NOT VERIFIED** |

**如果「完成」定義是有來源、有程式、有真正跑過的 G4–G8 研究稽核，這輪已把主要證據產出；如果「完成」定義是所有 Gate 通過到可投稿新演算法與企業級部署，尚未達到。** 目前不應把 G7/G8 標綠或宣稱完整通過。

## 八、可重現證據與下一個真正的演算法貢獻

### 原始研究證據
- [117 預先登錄來源名冊](https://github.com/Jimmy0307/LEM2/blob/research/report-ready-dashboard-20261109/teacher_demo/pmlb_117_source_registry.json)
- [109 份、3 Seeds 完整來源與計算契約](../data/PMLB_117_3SEED_MANIFEST.json)
- [117 份的成功／失敗完整稽核](../data/PMLB_117_3SEED_SOURCE_AUDIT.csv)
- [5,886筆六策略實測](../data/PMLB_117_3SEED_SIX_POLICY_RAW.csv)
- [32,373筆選擇決策與 Regret](../data/PMLB_117_3SEED_POLICY_SELECTIONS.csv)
- [109份×3 Seeds×不同條件的適用性](../data/PMLB_117_3SEED_CONDITIONAL_EFFECTS.csv)
- [G6 五項 Holm 檢定](../data/PMLB_117_3SEED_G6_WILCOXON_HOLM.csv)
- [G6 Friedman 六策略檢定](../data/PMLB_117_3SEED_G6_FRIEDMAN.csv)
- [G8 36次 CPU 規模原始結果](../data/PMLB_G8_REAL_CPU_STAIRCASE_36.csv)
- [G8 範圍及限制](../data/PMLB_G8_REAL_CPU_STAIRCASE_MANIFEST.json)

### GitHub Actions 實際證據
- [117份候選、單 Seed × 三分布原始執行 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43576124536)
- [117份候選、三 Seeds × 三分布原始執行 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43576756817)
- [三 Seed 109資料的 G6 稽核與數字發布 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43577032785)
- [G7 結構回歸與 G5 逐條件分析 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43577343600)
- [G8 四來源、36次 CPU 實驗 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43576654666)
- [G8 數據封版 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43576899493)

### 研究上下一個必須突破的問題

**不應將 VALIDATION_BEST 直接包裝成全新演算法。** 這是既有模型選擇方法在六個 LEM2 規則解析器上的嚴格實驗。其正向效果可以作為方法研究的必要性與設計動機。

真正有機會形成增量學術貢獻的是：設計**在 Non-IID 下具備可解釋風險界限的 Rule-Conflict-Aware Policy Router**，只觀察 Train/Inner Validation 的 Client divergence、Rule Conflict、Candidate correctness 與最低類別樣本，必要時才切換解析器。之後還須與全部六策略固定法、VALIDATION_BEST、目前 Guard、一般 LOFO Meta KNN、更新文獻提出的規則選擇法做公平消融。

**尤其本次 LOFO Meta KNN7 與硬式 Guard 沒能通過相對 Simple Voting 的 Holm 正向檢定，說明「不用目標標籤就事前推估最佳法」仍是尚未解決的關鍵難題，不能被有標籤的 ValidationBest 成績替代。**
