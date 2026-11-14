# 六種 LEM2 決策策略的資料適用性：資料型態、偏斜、衝突與目標的條件式分析

**研究結論（2026-11-14）：沒有證據可以直接斷言「連續型適合某策略、離散型適合另一策略」。**
不過，在**三個原始資料集 × 42 Seeds × Federated C2–C5** 上，資料分布偏斜程度確實伴隨六種策略的平均表現與勝出順位改變。20 個其他公開 UCI 資料集目前只有 **1 Seed**，主要用來定位假設，不用來宣稱一般性最優法。

## 1. 原始三資料集，完整 42 Seeds，等架構公平比較

C2、C3、C4、C5 相同三資料集、相同 Seeds（1–42），對 IID、non-IID Dirichlet α=0.5、non-IID α=0.1 分別進行比較。每一分布共 **3×42×4＝504 組六策略競賽**。所有競賽先固定規則集合，六策略只改決策選擇，不改原規則的 Coverage 或 Conflict。平均分數不是 504 個獨立資料集。

### Balanced Accuracy（%，各配置等權平均）

| 策略 | IID（C2–C5） | non-IID α=0.5 | non-IID α=0.1 |
|---|---:|---:|---:|
| FIRST_MATCH | 61.28 | 54.74 | 43.95 |
| SIMPLE_VOTING | 59.63 | 55.63 | **49.22** |
| STANDARD_VOTING | 64.09 | 53.37 | 41.41 |
| GLOBAL_STRENGTH | **69.25** | **56.97** | 37.93 |
| POPULATION_STANDARD | 63.65 | 52.26 | 39.53 |
| POPULATION_GLOBAL | 68.51 | 55.85 | 35.09 |

### Accuracy（%，同上）

| 策略 | IID | non-IID α=0.5 | non-IID α=0.1 |
|---|---:|---:|---:|
| FIRST_MATCH | 75.80 | 66.11 | 48.35 |
| SIMPLE_VOTING | 75.49 | **70.33** | **62.34** |
| STANDARD_VOTING | 80.54 | 69.93 | 57.38 |
| GLOBAL_STRENGTH | **80.94** | 67.44 | 43.85 |
| POPULATION_STANDARD | 80.11 | 68.80 | 55.29 |
| POPULATION_GLOBAL | 79.94 | 66.08 | 39.10 |

### Balanced Accuracy：平票分攤後的獲勝比例（%）

| 策略 | IID | non-IID α=0.5 | non-IID α=0.1 |
|---|---:|---:|---:|
| FIRST_MATCH | 見可機讀 CSV | 21.6 | 24.9 |
| SIMPLE_VOTING | 見可機讀 CSV | 25.7 | **48.9** |
| STANDARD_VOTING | 見可機讀 CSV | 11.9 | 10.0 |
| GLOBAL_STRENGTH | **35.3** | 22.5 | 5.5 |
| POPULATION_STANDARD | 見可機讀 CSV | 見可機讀 CSV | 見可機讀 CSV |
| POPULATION_GLOBAL | **24.6** | 見可機讀 CSV | 見可機讀 CSV |

**正式數字請以 [54 行同架構、同分母 CSV](../data/POLICY_SUITABILITY_42_DISTRIBUTIONS.csv) 為準。** IID 獲勝次數本輪已重新從 8,820 原始 frozen 矩陣只篩 C2–C5 計算，不再混入 Centralized C0。全部指標均保留平票分攤權重。

在最極端 α=0.1 情境，六策略的**同一規則集合**有平均 Test Coverage 約 99.66%，Conflict 約 86.42%，但 Balanced Accuracy 只有 35–49%。這表示分類策略是顯著待研究的調整維度，不能單憑高 Coverage 決定好壞。

## 2. 20 個新資料集：資料形態與勝出比例（Seed 42，探索性）

資料型態是**本研究所選六個特徵的編碼／離散化方式**，不是整份來源的所有特徵都具有該性質。

| 特徵型態（資料集數） | 競賽配置數 | Balanced Accuracy 平票分攤後比例最高 | 平手配置數 |
|---|---:|---|---:|
| 純連續（13） | 26 | SIMPLE_VOTING **25.4%**；FIRST_MATCH 18.3% | **21／26** |
| 純類別／離散（3） | 6 | STANDARD_VOTING **29.2%**；GLOBAL_STRENGTH 20.8% | **5／6** |
| 混合（4） | 8 | GLOBAL_STRENGTH **37.5%**；FIRST_MATCH / SIMPLE_VOTING 各 21.9% | **3／8** |

**這三列不能當成資料型態對策略的因果或普遍適用性定律。** 六策略大量平手，且每資料集只有一次 Holdout、只有最多六個特徵。特徵類型和類別數、規則 Coverage、Conflict、原始來源也混雜。20 份資料的 class proportion 源自整份*預先抽取的公開子集*，只能用於本研究的事後診斷，正式策略選擇器必須改成只用 Train profile。

同類資料也可能有不同 winner：例如純離散類別的 Mushroom（幾乎無衝突）和 Letter Recognition（多分類高衝突），演算法競爭場景完全不同。

## 3. 不是照「資料種類」一對一選；而是六種策略的機制與條件假設

| 決策策略 | 實作使用的訊息 | 可優先試驗的條件（非普遍勝出聲明） | 風險 |
|---|---|---|---|
| FIRST_MATCH | 按規則順序選第一條命中規則 | 無衝突／極低衝突；要求行為簡單、可稽核的固定順序 | 規則順序敏感，複雜重疊時較容易任意 |
| SIMPLE_VOTING | 每條命中規則各投 1 票 | **極端 Client label skew**：42 Seeds α=0.1 表現最好；也可作基線 | 規則很多的 Client／重複規則，可能被過度代表 |
| STANDARD_VOTING | 每條命中規則以前件在 Train 匹配到的筆數加權 | 資料來源較同質、每條規則支持數可比較，且重視 Accuracy | 大 Client、重複支持與高頻類別可能主導 |
| GLOBAL_STRENGTH | 各類別匹配規則之正確支持物件「聯集數／該類別 Train 筆數」 | **IID 或輕／中度偏斜；以 Balanced Accuracy 為目標**：42 Seeds 有支持 | 當 Client 類別分布極端偏斜，類別比例支持的可比性需重驗 |
| POPULATION_STANDARD | 命中規則中每類決策的「去重後正確支持物件數」 | 多條規則反覆涵蓋同一批 Train 物件，想降低重複計數；Balance Scale IID 有初步勝出證據 | 未正規化類別規模；可能偏向樣本多的類 |
| POPULATION_GLOBAL | Global Strength × 去重支持比例 `U/T` | 類別規模不平衡且支持重複情況明顯、分布仍相對穩定 | 在極端 α=0.1 平均表現最差之一；懲罰可能過大 |

這是「優先候選方法」矩陣，不是已經驗證的決策樹。在沒有衝突時，六策略選擇結果相同；這時應先優化 Coverage／正確候選，不必僅為提高 Accuracy 而反覆切換投票法。當候選集合不含正確類別時，任何 Winner Selection 都無法直接恢復缺失的類別。

### 方法差異的程式真實定義

以匹配到某決策 d 的規則集合為例，令 `S(r)` 是規則 r 的 Train **正確支持**物件集合、`N_d` 是 Train 類別 d 的大小：
- `SIMPLE`：每條命中規則 +1（沒有依支持權重）
- `STANDARD`：規則前件 Train 匹配筆數加總（不限定類別為該規則決策）
- `GLOBAL_STRENGTH`：`U_d / N_d`，其中 `U_d = |union S(r)|`
- `POPULATION_STANDARD`：`U_d`
- `POPULATION_GLOBAL`：`(U_d/N_d) × (U_d/T_d)`，`T_d = sum |S(r)|`
- `FIRST_MATCH`：取順序中的第一條命中規則

這些定義直接來自本 repository 的 `roughset/evaluation.py`，不是一般文獻中同名模型可以直接替換。

## 4. 「偏鋒」應至少拆解成五個獨立維度

| 因素 | 合理評量方式 | 現有證據狀態 |
|---|---|---|
| 類別偏斜（Label Imbalance） | Train 的最大類比例、Normalized Entropy、稀有類別最低支持數 | 20 份單 Seed 研究可事後描述，未做獨立因果操控 |
| Client 標籤分布偏斜（Label Skew） | Client label histogram 與 global Train 的 JS divergence、Client 缺類別比例 | 已有三資料集×42 Seeds 的 Dirichlet α=0.5／0.1 配對模擬；有策略排名反轉 |
| Client 數量不平衡（Quantity Skew） | 各 Client 列數 CV、Gini、最大／最小筆數比 | 本 Atlas 未直接操控；不能混同 α 產生的 label skew |
| 條件／特徵偏斜（Feature Skew） | 各欄 PSI／JS、分位數位移、未知類別比例 | 尚未完成跨 Client 對照 |
| 時間與概念漂移（Temporal / Concept Drift） | 時間順序外測、分期條件分布、conditional label drift | 尚未完成；本批都是隨機分層切分 |

另需保留訓練資料矛盾比例、特徵值組合稀疏度、維度、規則平均條件數、平均命中規則數、規則支持重複度等結構性因素。

## 5. 正式研究設計：Train Profile → Rule Profile → Policy Selector

真正要找「適用性」需建立在 **未見 Test 之前可觀測的資料特徵**：

1. **Train Profile**：特徵型態、類別數、Entropy、Minority Share、規模、特徵基數與 Client label／feature／quantity skew。
2. **Rule Profile**：用 Train 開發出的固定規則，於*內層驗證集*統計 Exact Coverage、Conflict、Candidate Coverage、重複支持、每個類別的正確候選比例與規則順序敏感度。
3. **Objective**：優先指定 Balanced Accuracy 或 Macro-F1；再依錯誤成本與算力選擇。Accuracy、Minority Recall、Latency 必須單獨報告。
4. **Selection**：只使用 Train + Inner Validation 比較六策略；凍結後在 Outer Test 評估。元選擇器若跨資料集訓練，需要 leave-one-dataset-out 或 leave-domain-out 驗證，與固定策略基線及理想 Oracle 作比較。
5. **Holdout Guardrails**：若六策略差異低於預先固定容忍值或只有有限 Conflict，優先維持簡單一致且可稽核的策略。不得輸入 Test conflict／accuracy 作為模型的選擇特徵。

可用的形式化任務：
[
widehat p=f(X_{\rm train}, X_{\rm rule,validation}, \text{objective}),\quad
p\in\{\text{FIRST},\text{SIMPLE},\text{STANDARD},\text{GS},\text{PS},\text{PG}\}
]
目標是最小化外部 Test 的 **selection regret**，而不是回頭把 Test 最佳策略標成一個可部署的「智慧選擇器」。

## 6. 學術依據與下一輪邊界

Ho & Basu (2002), [Complexity measures of supervised classification problems](https://doi.org/10.1109/34.990132) 指出分類問題的複雜度涉及類別重疊、邊界形態與樣本稀疏，為用資料特徵界定演算法能力範圍的研究基礎。Cano (2013), [Analysis of data complexity measures for classification](https://doi.org/10.1016/j.eswa.2013.02.025) 特別研究資料複雜度量與分類器表現的關係。本專案的六方法適用性矩陣**尚未據此證明新演算法選擇器具有優越性**。

- [20 個資料集 × 2 架構 × 6 策略 × 3 目標的 720 列勝次與形態表](../data/POLICY_SUITABILITY_20_MATCHUPS.csv)
- [20 個資料集依型態／偏斜／衝突／類別數統整的平票分攤報表](../data/POLICY_SUITABILITY_20_GROUPS.csv)
- [原三資料集 42 Seeds 三種分布的 54 列可比較表](../data/POLICY_SUITABILITY_42_DISTRIBUTIONS.csv)
- [資料契約及禁止過度解讀的研究限制](../data/POLICY_SUITABILITY_MANIFEST.json)
- [程式與正式檢核](https://github.com/Jimmy0307/LEM2/actions/workflows/policy-suitability-atlas.yml)

**總結**：目前最有把握的關係是「Client 的 Label Skew 程度 × 選擇策略 × 評估目標」；只有 1 Seed 的「連續／離散／混合型資料 × 最佳六策略」尚不能發展成一對一的硬規則。真正有學術價值的下一步，是用 Train-only meta-features 預測策略，並在獨立資料集上驗證選擇是否比固定 Global Strength 或 Simple Voting 更好。
