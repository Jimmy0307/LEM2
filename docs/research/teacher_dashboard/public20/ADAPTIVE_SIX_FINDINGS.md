# 六種 LEM2 決策策略自適應選擇：跨資料集 20×3 Seeds 的可重現驗證結果

**研究執行日**：2026-11-14  
**證據完整性**：`VALIDATED_20_DOMAINS_3_SEEDS_6_POLICIES`，原始來源與雜湊通過、120 組凍結規則系統、720 筆獨立政策結果、3,600 筆策略決策對照。  
**重要負面結論**：本輪 **LODO Meta KNN 未優於固定 Global Strength**，同資料集的內層驗證最優法也未勝過固定 Global Strength。不能提前宣稱自適應演算法有效。

## 1. 正式問題與實驗方式

六種既有策略共用 **Classical positive-region reduct + LEM2** 規則集合；每個方法只改變多規則命中後的決策解析，**不是六個獨立的規則學習模型**。

- 20 份**確實下載與驗證**的 UCI 開放資料，使用已保留雜湊的固定研究子集；每份使用 Seed **1、7、42**。
- 每個 Seed 做 80/20 外層 holdout，剩餘 80% 再分為 **64% induction＋16% inner validation**，外層 20% 為完全未見測試。
- 架構：集中式 C0、聯邦 C3，均分層 IID；共 **20×3×2=120** 組固定規則。每組測六種選法，得 **720** 份 Test 策略輸出。
- 主指標 **Balanced Accuracy**，另檢查 Macro-F1 和 Accuracy。
- 三個可實施選法：**固定六策略**；**同資料集內層驗證最優**；**LODO Global Validation**（用其他 19 份資料在驗證集的平均成績選同一固定策略）；**LODO Meta KNN=5**（其他 19 份資料的訓練特徵／內層驗證規則結構，學習鄰近資料領域的六策略效益）。
- 對照 **Test Oracle**：事後拿外層 Test 的六個真實分數選最大，僅表示不可達到的研究理想上限，**永遠不會部署**。
- Meta 參數與距離特徵預先固定，沒有用 Test 調整。對目標資料集 D，其他 Seeds 和集中／聯邦結果也全部排除在 Meta Train 之外。只用目標 D 的 Train＋Inner Validation 特徵作為預測輸入，不用 D 的 Test Label/Conflict/Winner。

## 2. 最重要的實驗數字

### Balanced Accuracy（主指標，%）

| 比較方法 | 20 資料集 × 3 Seeds × 2 架構等權 Test 平均 | 距離 Test Oracle（pp） | 相對固定 Global Strength（pp） |
|---|---:|---:|---:|
| 固定 FIRST_MATCH | 61.110 | 1.032 | −0.782 |
| 固定 SIMPLE_VOTING | 61.132 | 1.010 | −0.760 |
| 固定 STANDARD_VOTING | 61.318 | 0.824 | −0.574 |
| **固定 GLOBAL_STRENGTH** | **61.892** | **0.250** | **0.000** |
| 固定 POPULATION_STANDARD | 61.339 | 0.803 | −0.553 |
| 固定 POPULATION_GLOBAL | 61.731 | 0.410 | −0.161 |
| LOCAL_VALIDATION_BEST | 61.627 | 0.515 | **−0.265** |
| LODO_GLOBAL_VAL | **61.892** | **0.250** | **0.000** |
| LODO_META_KNN_5 | 61.744 | 0.398 | **−0.148** |
| TEST_ORACLE_DIAGNOSTIC | 62.142 | 0.000 | +0.250（**不可執行**） |

### Macro-F1（%）

| 方法 | Test 平均 |
|---|---:|
| 固定 GLOBAL_STRENGTH | **59.552** |
| LOCAL_VALIDATION_BEST | 59.199 |
| LODO_META_KNN_5 | 59.364 |
| TEST_ORACLE_DIAGNOSTIC | 59.908（不可執行） |

### Accuracy（%）

| 方法 | Test 平均 |
|---|---:|
| 固定 GLOBAL_STRENGTH | 70.328 |
| LOCAL_VALIDATION_BEST | 70.326 |
| LODO_META_KNN_5 | **70.330** |
| TEST_ORACLE_DIAGNOSTIC | 70.736（不可執行） |

Accuracy 的 Meta 與 Global 差距只有約 **+0.003 pp**，不足以稱為實質提升。

## 3. 不確定度：20 份來源才是主要獨立單位

這次將同資料集 Seeds 與集中／聯邦配置先平均，再以原本的 **20 個不同 UCI 資料來源**作 cluster bootstrap（1,000 次，固定抽樣 Seed）：

| 候選 | 相對固定 Global Strength 的平均 Balanced Accuracy 差（pp） | 探索性 95% bootstrap 區間（pp） | 跨 20 來源改善／退步／相同 |
|---|---:|---|---|
| LOCAL_VALIDATION_BEST | −0.265 | [−0.492, −0.085] | 5／9／6 |
| LODO_META_KNN_5 | **−0.148** | **[−0.286, −0.038]** | **2／7／11** |
| LODO_GLOBAL_VAL | 0.000 | [0.000, 0.000] | 0／0／20 |

這是**探索性分群區間**，不是預註冊的統計確認或對所有領域母體的保證。20 個來源是固定抽樣的小樣與最多六特徵，特徵分類、樣本數、標籤分布相互混雜。

## 4. 為什麼 Meta 選擇器沒有贏？有兩個結構性限制

### A. 這批 IID 資料的理論可選空間極小

固定 Global Strength 的 BA **61.892%**，即使使用事後 Test Oracle 也只有 **62.142%**，整體改善上限僅 **0.250 pp**。因此此批資料不像先前極端 Non-IID 42 Seeds 那樣能拉開解析器差異。

120 組固定規則中：
- 42 組在內部 Validation 上 **沒有任何 Conflict**；
- 50 組有 Conflict，但低於 10%；
- 19 組 Conflict 介於 10%–40%；
- **只有 9 組**達到 40% 以上。

有些 Validation 0% Conflict 的配置在外層 Test 仍會發現衝突，因此不能說 42 組所有未見物件絕對相同，但大部分配置確實缺乏明顯策略競爭。

### B. Meta 特徵無法彌補非常有限的跨域樣本

LODO Meta KNN 使用其他 **19 個**資料集的 Train 特徵與內層 Validation 規則指標。即使每份做三個 Seed，**跨領域樣本仍只有 19 個**，相近度度量尚未有足夠證據預測規則策略效益。此外，此輪 C3 是 STRATIFIED IID，Client label skew 特徵很接近，無法充分驗證先前觀察到的 Dirichlet α=.1 策略反轉機制。

### 分架構測試 BA（%）

| 架構 | 固定 Global Strength | Meta KNN | 內部驗證選法 | Test Oracle |
|---|---:|---:|---:|---:|
| 集中式 C0 | 59.808 | 59.808 | 59.753 | 59.871 |
| 聯邦 C3 | **63.976** | 63.680 | 63.501 | 64.413 |

集中式幾乎沒有可以透過 Meta 選法賺取的收益；聯邦 C3 上策略差異較多，但目前 Meta KNN 還不如固定 Global Strength。

### 個別 UCI 的對比

- EEG Eye State：Meta 相對固定 Global Strength **+0.150 pp**（三 Seeds／兩架構平均）。
- MAGIC Gamma Telescope：Meta **+0.036 pp**。
- Sonar：Meta **−0.937 pp**。
- Haberman：Meta **−0.821 pp**。
- Adult Income：Meta **−0.454 pp**。
- Letter Recognition：Meta **−0.183 pp**。

上述均為 Seed 1、7、42 的初步數據，不足以對特定領域直接推薦 Meta 選擇器。

## 5. 與先前 42 Seeds Non-IID 結果如何共同解釋？

先前三份原始 UCI 資料在完整 42 Seeds 的 STRATIFIED IID、Dirichlet α=.5、α=.1 聯邦實驗中，發現**策略排名會因為 Client Label Skew 反轉**：

- IID，Global Strength 平均 BA **69.25%**，Simple Voting **59.63%**。
- α=.1，Simple Voting 平均 BA **49.22%**，Global Strength **37.93%**。

但那是**固定規則系統上的不同候選策略的最終 Test 表現**，不是已完成 Train-only 自動選擇器的正確決策證據。不能把 α=.1 的 Test 成績拿來直接制定「看到某個測試指標就選 Simple Voting」的產品規則。

**下一輪優先順序因此應調整**：先在 20 份公開資料建立 Dirichlet α=.1／.5 的真正標籤偏斜，使 Client label divergence 成為有差異的訓練特徵，再在 Inner Validation 研究是否能正確預測「GS → Simple」的策略反轉，並用 Outer Test 檢驗選擇 Regret。

## 6. 六策略變成有學術說服力的新演算法，還缺什麼？

六個方法已是定義明確的 Winner Resolution 程序，但都共用 LEM2 歸納結果；**不能直接聲稱六個新的 Induction Algorithm**。

依[ G0–G8 演算法成熟度規格](./ADAPTIVE_SIX_ALGORITHM_SPEC.md)：

| Gate | 狀態 | 意義 |
|---|---|---|
| G0–G2：公式、共用規則、公開資料與實驗再現 | 已具備 | 已能重現六策略和 20 來源結果 |
| G3：只用 Train/Validation、LODO 防洩漏 | **已通過** | 具備可執行的算法選擇器 PoC |
| G4：實證勝過最佳固定法 | **本批未通過** | Meta 在 BA 上 −0.148 pp；沒有新方法效益證據 |
| G5：非 IID／時間／特徵／數量偏斜穩健性 | **未完成** | 這是最有希望也是必要的區別場景 |
| G6：跨來源統計、超參數敏感度、正式多次實驗 | **未完成** | 三 Seeds、20 資料來源太有限，Bootstrap 僅探索 |
| G7：理論與新穎性、與既有 Meta-learning 基準/消融 | **未完成** | Rice (1976) 已有演算法選擇框架；KNN 本身不是新演算法 |
| G8：大型資料、CPU/GPU 計算與部署成本 | **未完成** | 目前最多六特徵與約 1,800 筆抽樣，不能宣稱大型資料能力 |

**現在能叫做：**「Classical/Federated LEM2 上的 Leak-free Adaptive Policy Selection PoC」。  
**還不能叫做：**「在多領域上已驗證優越的新型粗糙集演算法」。

如果要形成真正的新論文方法，研究焦點不應只有 KNN 選法，而需結合**規則候選覆蓋、原始規則衝突、Client 資料偏斜、計算預算與可驗證的拒判／退場條件**，並證明此特化架構真的比既有固定法與一般 Meta-learning 選法強。

## 7. 正式來源、驗證與文獻

- [完整可重現 Manifest](../data/ADAPTIVE_SIX_20_MANIFEST.json)
- [720 筆原六策略 Inner/Outer 數據](../data/ADAPTIVE_SIX_20_ALL_POLICIES.csv)
- [3,600 筆選擇決策＋後悔值](../data/ADAPTIVE_SIX_20_SELECTORS.csv)
- [三目標、十種方法彙總](../data/ADAPTIVE_SIX_20_SUMMARY.csv)
- [20 來源分群 Bootstrap 95% 區間](../data/ADAPTIVE_SIX_20_DATASET_BOOTSTRAP.csv)
- [原始 60 任務實際運算與來源 artifacts](https://github.com/Jimmy0307/LEM2/actions/runs/43571344581)：20 worker 成功；首次 aggregate 僅資料檢查程式錯誤（DataFrame.between），隨後修復。
- [重用來源 artifacts 完成的最終可重現 PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43571781178)
- [Rice (1976) Algorithm Selection Problem](https://doi.org/10.1016/S0065-2458(08)60520-3)
- [Cawley & Talbot (2010) Model Selection Bias](https://jmlr.org/papers/v11/cawley10a.html)
- [Demšar (2006) Multi-Dataset Classifier Comparisons](https://jmlr.org/papers/v7/demsar06a.html)
- [Dagan et al. (2024) Automated Algorithm Selection via Meta-learning](https://doi.org/10.1016/j.inffus.2023.102210)

### 最終研究決策

**對目前 IID 公開資料：固定 Global Strength 仍為預設的效益／成本基準。** 不應為 +0.003 pp Accuracy 或 −0.148 pp Balanced Accuracy 的 Meta 選法增加額外工程複雜度。

**對極端 Non-IID：值得繼續，但尚未驗證自適應機制。** 下一個關鍵實驗要讓訓練資料中的 Client 偏斜程度、規則支持重疊與驗證集衝突共同決定是否切換策略；如果仍不能穩定超過固定 Global Strength 與 Simple Voting，就應把研究貢獻回到「資料條件診斷與策略適用性邊界」，而不是硬稱新演算法。
