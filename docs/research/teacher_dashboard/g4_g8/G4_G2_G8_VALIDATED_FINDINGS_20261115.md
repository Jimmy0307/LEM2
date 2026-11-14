# G4 自適應六策略、Coverage/Conflict 聯合控制、G8 約簡計算：三項實證完成報告

**實驗完成：2026-11-15**。所有研究實作與發佈皆只在 `research/report-ready-dashboard-20261109`，沒有改動 `main`、既有 8,820 frozen baseline 或舊的 PMLB 109 資料。成功指運算、來源和資料協定通過；**不等於原 G4–G8 學術與企業級驗收門檻全部通過**。

## 1. G4：原始跨域 Meta 未通過；新的 Conflict-Bucket Router 有明確 Non-IID 效益訊號

**研究設計**：UCI20 同一批已證實公開的 Prepared CSV。這次新增 Seeds **11、23**，分三種 Client C3 分布（IID / Dirichlet α=.5 / α=.1），每配置用 64% induction / 16% inner validation / 20% outer Test，規則集合以 Classical positive-region exact reduct + LEM2 歸納一次，六策略共享。20×2×3＝**120** 個固定規則系統，6固定策略＋Validation Best＋Conflict Bucket Router＋不可部署 Oracle＝**1,080** 筆配對實驗，原始 prepared SHA 逐筆核對通過。

**方法機制**：
- 先依已觀察的先前基準將 IID 的 Default 設為 Global Strength，Non-IID 設為 Simple Voting；這是**探索性決策，並非這輪外測推導**。
- Inner Validation 上，只對原始規則先驗產生的**多決策衝突**分組：二類且少規則命中、二類且多規則命中、≥3類衝突。策略切換必須有至少10個有效衝突驗證物件、至少兩筆淨正確改善、整體 Validation BA 增加0.2pp、Accuracy 相對原始基線不低於0.5pp，且最多兩個分組切換；低證據時保留 Default。
- Test 規則結構不改，**原始 Exact Coverage／Conflict 在六策略及新路由器之間完全相同**。這是決策解析路由，不是 Rule Pruning 或 Supplement。

### 實測 Balanced Accuracy（20來源×2新Seeds，Config 等權）

| 分布 | 原強固定策略 | 強固定 BA | Conflict Router BA | 提升（pp） | 分群Bootstrap 95% CI |
|---|---|---:|---:|---:|---|
| IID | Global Strength | 62.533% | 62.782% | **+0.249** | [−0.128, +0.903] |
| Non-IID α=.5 | Simple Voting | 60.265% | 60.948% | **+0.683** | [+0.070, +1.509] |
| Non-IID α=.1 | Simple Voting | 53.320% | 55.633% | **+2.314** | [+0.696, +4.157] |

與已有的 **Validation Best** 比較：
- IID：Router +0.352 pp，探索 CI [+0.024,+0.688]；
- α=.5：Router **−0.578 pp**，CI [−1.045,−0.141]；
- α=.1：Router +0.005 pp，CI [−1.353,+1.553]，效果無法區分。

**精確結論**：這個條件式路由方法相比固定策略在Non-IID有正向改善訊號，尤其α=.1，但是尚不能宣稱優於一般 Validation Best。因資料仍屬原先已探索的 UCI20 來源且門檻是在之前結果後設計，**這是新 Seeds 的探索性外測，不是完全獨立新領域的確認性檢定**。原 G4「Meta Selector 在跨未知資料集穩定勝出」仍 **NOT PASS**。

### 對 G4 方法論的影響
研究重點從「資料型態直接決定六策略」收斂為：**資料在 Train/Validation 顯示強烈 Client Label Skew＋原始規則多類別 Conflict＋足夠的有標籤衝突驗證案例時，路由有機會優於固定方法**。不能把 Test label/Conflict 當部署選擇器輸入；也不能拿任意幾個極端 Client 例子直接推論普適因果。

- [1,080筆模型與路由結果](../data/G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv)
- [三分布方法均值](../data/G4_ROUTER_UCI20_NEW_SEEDS_SUMMARY.csv)
- [20個來源分群Bootstrap與對ValidationBest的配對](../data/G4_ROUTER_UCI20_DATASET_BOOTSTRAP.csv)
- [120組內驗證路由接受記錄](../data/G4_ROUTER_UCI20_GATE_DECISIONS.csv)
- [G4 source manifest](../data/G4_ROUTER_UCI20_MANIFEST.json)
- [原始20來源新Seeds全部通過的Actions](https://github.com/Jimmy0307/LEM2/actions/runs/43621645619)
- [獨立重用原始Artifacts核對與修正統計的Actions](https://github.com/Jimmy0307/LEM2/actions/runs/43622293509)

## 2. Coverage／Conflict 聯合控制：有效 Coverage 成立，但不能保證 BA 或原始衝突下降

**研究設計**：UCI20×Seeds 1,7,42×Centralized C0／Federated C3＝**120** 組固定規則系統，每組比較：
1. 原始 Classical LEM2、原始 No-Match 用訓練多數類 fallback；
2. Train-only「刪一個前件條件」候選補充規則，要求支持≥5、純度≥90%，直接全部加入；
3. 同樣 Train 候選，但只加入通過 Inner Validation Coverage／Conflict／Accuracy／BA 多目標限制的補充規則（原始規則優先，只有原始 No-Match 才啟用 Supplement）。

原始Exact Coverage不變；實驗的**有效Coverage = 原始有規則命中，或原始No-Match但補充規則命中**。Active Conflict 是真正在推論啟用的那一層規則是否同時提出不同決策；Shadow Conflict 是忽略優先權、將兩類規則全部放在一起時的潛在衝突。**No-Match仍以預設類別預測，不是拒絕/Abstention**。

### 集中式（20來源×3Seeds 平均）

| 指標 | 原始 LEM2 | 全部補充規則 | 驗證守門補充規則 |
|---|---:|---:|---:|
| 有效 Coverage | 43.167% | **57.303%** | **56.340%** |
| 正確類別在候選中 | 35.411% | **48.158%** | **47.373%** |
| Active Conflict | 2.136% | 2.307% | 2.204% |
| Shadow Conflict | 2.136% | 3.369% | 2.641% |
| Balanced Accuracy | 59.808% | **61.642%** | **61.390%** |

集中式驗證守門相對原始：有效 Coverage **+13.173 pp**（跨20來源Bootstrap 95% CI [+4.806,+23.132]），BA **+1.582 pp**（[+0.643,+2.663]），Active Conflict **+0.068 pp**（[+0.005,+0.174]）。**不能說衝突沒有增加**。

### 聯邦式 C3（相同20來源與Seeds）

| 指標 | 原始 LEM2 | 全部補充規則 | 驗證守門補充規則 |
|---|---:|---:|---:|
| 有效 Coverage | 65.439% | 67.869% | **67.830%** |
| 正確類別在候選中 | 56.652% | 58.873% | **58.854%** |
| Active Conflict | **16.394%** | 16.399% | **16.394%** |
| Shadow Conflict | 16.394% | 16.983% | **16.408%** |
| Balanced Accuracy | **63.976%** | 63.961% | 63.961% |

聯邦驗證守門：有效 Coverage **+2.391 pp**（[+0.163,+5.451]）；**Active Conflict 相同但BA微降 −0.015 pp**（CI [−0.055,+0.012]）。這說明解決「規則無命中」不一定等於解決「有正確候選但最終投票選錯」；高衝突 Client 仍是另一層問題。

> 研究中使用的補充規則是本倉庫的 Train-only 一條條件刪除啟發式，**不是重現 Inuiguchi & Washimi（2015）的 MLEM2 Supplementary Rules**。該文已有先行研究，不能主張首創「增加補充規則」：[原文 DOI](https://doi.org/10.20965/jaciii.2015.p0747)。

- [360筆外測配對](../data/G2_JOINT_COVERAGE_CONFLICT_3SEED_RESULTS.csv)
- [逐規則採用與拒絕事件](../data/G2_JOINT_COVERAGE_CONFLICT_3SEED_EVENTS.csv)
- [分架構／版本彙總](../data/G2_JOINT_COVERAGE_CONFLICT_3SEED_SUMMARY.csv)
- [20來源分群Bootstrap](../data/G2_JOINT_COVERAGE_CONFLICT_3SEED_CLUSTER_BOOTSTRAP.csv)
- [G2 manifest](../data/G2_JOINT_COVERAGE_CONFLICT_3SEED_MANIFEST.json)
- [原始20來源三Seeds完整運算 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43621841892)

## 3. G8 約簡加速：精確快取核對通過；貪婪近似不是最小約簡且可能損失 Test

### 3A. 約簡階段

**技術**：
- `roughset/reduct_fast.py` 的分割快取依特徵的編碼欄位遞增產生 `IND(A)` 群組，純群組計數求出**完全精確的整數 POS**；`exact_cached` 遍歷全部最小 cardinality reduct 候選，其枚舉最壞仍呈組合性。
- `greedy_pos` 按選入一個特徵後的 POS 大小貪婪增添，最後做逆向刪除；終止條件為 `POS_selected = POS_full`。**這是啟發式 reduct，不保證 minimum cardinality，也不保證Test泛化**。
- `teacher_demo/test_reduct_fast.py` 核對多種隨機資料、含缺值與矛盾決策/XOR的全子集 POS 等價、精確最小 Reduct 結果／候選數一致。

**真實資料**：Adult、Connect-4、MNIST、Spambase，共 **82** 個適用的 Rows × Features 設定（600／1600／3200／6400 Rows，4／6／8／12／16／24 Features，部分原來源不支援）；其中**36** 個 4／6／8 Features 設定有原始最小精確搜尋與快取精確搜尋的逐一配對，全部在**最小基數、候選數和選出特徵**上等價；82個 Greedy 全部 Train POS 保持正確。

例：Connect-4：
- 600×8：原精確 **0.309秒**、快取精確 **0.068秒**、Greedy **0.018秒**；
- 6400×24：Greedy **4.646秒**，並保留相同的 **Train POS**（*未執行原精確對照與完整LEM2模型*）。

不同來源與設定下快取不保證總是更快。MNIST 取上游原始順序的前24欄，部分為無資訊常數，使 POS=0 或空 reduct：**這不是MNIST全784特徵有好結果的證據**。

### 3B. 完整 LEM2：訓練POS相同不保證 Test Performance 相同

新增 **Adult／Connect-4／Spambase ×600／1600 Rows×8／12／16 Features（來源可用者）＝16組配對，32個真實完整規則模型**；兩邊在**完全相同Train/Test、同一Train-only離散化**下，比較全部已選原始特徵與Greedy POS保留特徵，均使用Global Strength分類。

- **14／16** 的外部Test Balanced Accuracy完全相同；
- Adult，600 Rows×12 Features：Greedy 相較全部原特徵 **BA +1.099pp**，但 Test Coverage **−0.833pp**；
- Connect-4，600 Rows×16 Features：Greedy **BA −3.719pp**，Test Coverage **+0.833pp**；
- 16組平均 BA 增益 **−0.164pp**，只是小樣描述值。
- 規則歸納／支持計算整體速度沒有穩定大幅優勢（多數候選 reduct 與原完整特徵幾乎相同）。

**結論**：不能因為高維 Greedy 的「數秒內算出相同Train POS」就宣稱它比正式精確最小Reduct更好。此輪的Full Feature基準也**不是精確最小Reduct**，因此不能將此比較偷換成「貪婪 vs 精確最小」的 Test accuracy 效果。

- [82組真實來源CPU約簡性能](../data/G8_OPTIMIZED_REDUCT_REAL_CPU.csv)
- [約簡正域、特徵限制與測試Manifest](../data/G8_OPTIMIZED_REDUCT_MANIFEST.json)
- [32個完整LEM2 Train/Test模型](../data/G8_GREEDY_FULL_LEM2_TEST_QUALITY.csv)
- [16組相同Train/Test的配對BA／Accuracy／Coverage／規則數／耗時](../data/G8_GREEDY_FULL_LEM2_TEST_PAIRED.csv)
- [完整LEM2外測Manifest](../data/G8_GREEDY_FULL_LEM2_TEST_MANIFEST.json)
- [完整約簡實測 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43621213749)
- [完整規則學習和Test品質 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43622531133)

**先行研究邊界**：Greedy QuickReduct 與正域保留型特徵約簡早已有文獻，[Liu et al. (2014)](https://doi.org/10.1016/j.ins.2014.02.093) 及 [Adaptive Quick Reduct (2021)](https://www.mdpi.com/1999-4893/14/2/58) 展示相關設計原理。我們這一版是工程可行性與對照，不能稱演算法首創。

## 4. 真正能回答「何時有效」的判斷

| 狀況 | 目前有證據的建議 | 不成立的推論 |
|---|---|---|
| **IID、極少原始衝突** | Global Strength 是高競爭力固定基準；路由改善不穩 | 不能保證所有IID一定是GS |
| **Non-IID α=.1、高原始規則衝突** | 有標籤Inner Validation的受控決策選擇，比固定SV有顯著探索性增益 | 不能說未見資料集Meta選擇器已成功 |
| **原始No-Match很高、集中式規則覆蓋不足** | 純度／支持守門的Train補充規則能顯著提高有效Coverage與BA | 不能說原始LEM2 Exact Coverage改變；Active Conflict略增 |
| **聯邦原本Coverage已高、Conflict高** | 補充規則主要降低No-Match，不必然提升BA；應另研究選錯候選類別 | 不能宣稱「Coverage提高即解決Conflict」 |
| **中等高維，允許近似特徵約簡** | POS快取可保持精確Reduct；貪婪可更快取出Train POS不減的特徵 | 不能宣稱貪婪即精確最小、更快的完整LEM2或Test不下降 |
| **未經驗證的高維與企業級** | 限定G8實驗可行性，維持現有精確基準 | 不可宣稱24+特徵、超10萬列、GPU、700GB或大量Client無痛擴展 |

## 5. G4–G8 驗收狀態

| Gate | 本輪完成 | 還未通過 |
|---|---|---|
| **G4** | 新Seeds20公開資料 ×IID及非IID；受控衝突路由對強固定法在α=.5/.1有改善 | 對VALIDATION_BEST的全面勝出、跨真正獨立未見領域Meta Selector的統計優越性 |
| **G5** | Label Skew 的三分布試驗進一步擴充 | Quantity/Feature/Temporal Drift、Client數量變化 |
| **G6** | 20來源Bootstrap並保留上游109 PMLB的家族配對統計 | 新方法的跨家族真正獨立學術確認性比較與多重測試設計 |
| **G7** | 固定規則、Conflict分類與POS等價性測試；先行研究核對 | 新穎算法的形式化保證、真正超越既有方法的消融與反例 |
| **G8** | 82組約簡CPU、36組精確對照、16組完整LEM2外部測試 | 全高維精確替代、全量大型資料性能、Train/Test穩健性、GPU／多Client實驗 |

### 下一個必要但尚未完成的研究驗證

若要把這次的研究原型寫成原創新演算法：
1. 在**訓練前固定的全新來源**上預先宣告Risk Router與補充規則參數，不再對新Seed表現調整門檻；至少比較固定六法、ValidationBest與正式外部元學習法。
2. 對四類失敗分別建模：NoMatch、正確候選缺失、Conflict多決策、候選存在但決策解析錯誤；分別提供 Train/Validation 可觀測訊號與獨立Test證據。
3. 對高維資料作真正的源特徵分布／重要性訓練期分析，不再機械地取前8／24欄；比較精確基準、Greedy、QuickReduct、可行的近似與快取法，固定相同Test及資源限制。
4. 做最終論文方法的形式化演算法、時間／空間複雜度、保證界限、統計效果、消融研究，而非單靠「跑完很多資料集」。

**本輪已完成三條對照的程式開發、實際執行、來源稽核、結果留底與可互動網頁。但原訂完整G4–G8學術及企業部署停止條件仍不得標成全部PASS。**
