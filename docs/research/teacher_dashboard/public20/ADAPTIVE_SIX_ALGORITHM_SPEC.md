# 六種 LEM2 決策選擇 → 可泛化演算法：正式驗證規格與研究成熟度稽核

**研究日期：2026-11-14。** 此規格的主要目標不是挑最高的單次測試分數，而是驗證：**對未知的資料集，只用可在部署前取得的訓練／內部驗證特徵，選擇哪個決策解析策略能穩定改善 Balanced Accuracy 或 Macro-F1。**

## 1. 先釐清：「六種方法是不是演算法？」

六種程序**已經是可計算、可終止的決策解析演算法**，只是目前它們共用一套 Classical 正域約簡＋LEM2 歸納出的規則；它們不是六個獨立的規則學習器，更不等於已證明創新的六種新演算法。一般的「根據資料特徵選演算法」是 Rice (1976) 早已提出的 algorithm selection problem，後來也有 Meta-learning 和 CASH/AutoML 系列，不能將「學習選一個方法」本身當成 2026 年新穎性。

我們真正可能形成研究貢獻的方向是：
- LEM2 原始／Federated 規則專屬的 **資料—規則—衝突適用性表示**；
- 以**正確候選覆蓋率、衝突風險與稀有類別召回**為條件的決策策略選擇；
- 不需要重新歸納六次規則，直接共用凍結規則集合的**低成本解析器切換**；
- 在沒有充足的標籤驗證資料時提供可稽核的**不切換與退場條件**。

這些目前仍是研究假設，必須和固定策略、內部驗證選法、資料集留一 Meta-learning 比較。

## 2. 形式化

對資料集 D，固定訓練集 T、內部驗證集 V、未見測試集 E，學習器產生規則集合：

\[
R=\mathrm{LEM2}(\mathrm{Reduct}(T)).
\]

六種解析器 \(p\in\mathcal{P}\) 對**同一個**規則集合 R 輸出 \(\widehat y_p(x\mid R)\)。定義訓練／驗證的特徵：

\[
z = \left[\phi(T), \psi(R,V)\right]
\]

其中 \(\phi\) 僅含 Train 的資料形態、類別熵、最小類別比例、特徵基數、Client Label JS divergence／Client Quantity CV；\(\psi\) 包含**內部驗證集**的規則數、平均條件數、無匹配比例、候選正確率、Conflict Rate 等。

本輪跨資料集選擇器（\(f\)）：

\[
\widehat p=f(z;\{(z_i, u_i(p,V_i)): i\neq D\}),\qquad
\mathrm{Score}_{\mathrm{test}}=u_D(\widehat p,E).
\]

**不得讓目標資料集 D 的任何 Seed 進入 Meta 訓練，也不得使用 E 的 label、Conflict、Accuracy 或 Winner 去訓練選擇器。**

主要指標：
- 測試 Balanced Accuracy（BA）；
- 測試 Macro-F1、Accuracy 與少數類別 Recall（需要完整類別標籤），避免只有整體 Accuracy；
- 對照最佳固定方法與診斷 Oracle 的 Selection Regret（pp）：
\[
\mathrm{Regret}=100\left(\max_{p\in\mathcal P}u(p,E)-u(\widehat p,E)\right).
\]
Oracle 僅為**事後理想上限**，永遠不可執行或當作研究方法。

## 3. 第一輪嚴格可重現評估設計

- **公開來源**：先前稽核通過的 20 份 UCI 固定子集，有出處、資料 SHA-256、原始筆數、選取特徵與類別分布。特徵最多 6 個；原始大資料只抽樣至 1800 以下，不宣稱全量擴展性。
- **內外資料切分**：每資料集 Seeds **1、7、42**，Outer Holdout 20%；剩下 80% 再以同 Seed 衍生的內層切分，**64% 開發集 + 16% 內層驗證集 + 20% Test**。為了避免第二次擬合導致變數漂移，選法完成後不重訓規則，保留同一個固定規則系統。
- **對照架構**：Centralized + Federated C3，皆用原 Classical positive-region minimum-cardinality reduct + LEM2，聯邦 STRATIFIED IID。**未加入 non-IID**，因此本次不能單靠這批實驗證明偏斜場景的策略適用性。
- **六策略**：First Match、Simple Voting、Standard Voting、Global Strength、Population Standard、Population Global。原規則一致；只有最終 Winner Resolver 改變。
- **比較**：固定六策略（6）、內部驗證最佳（1）、其他 19 資料集最佳固定（1）、其他 19 資料集訓練的固定 K=5 最近鄰 Meta-selector（1）、測試集 Oracle **純診斷**（1）。每方法除了 Test BA，也保留 Macro-F1、Accuracy。
- **Meta-learning 的假設與限制**：K=5、距離特徵、等權資料集等參數**預先固定**，不是用 Test 反向調參；特徵的均值／標準差只從其他 19 資料集估計。相同資料集的 3 Seed 先平均為一個來源，不能把它們當成三個獨立的資料領域。
- **統計**：按原始 20 個資料集計算分群／等權平均與配對差，提供只以**資料集為 cluster** 的描述性 95% bootstrap 區間，僅為探索性不確定度，不取代正式跨資料集統計比較。

預期固定矩陣：\(20\times3\times2=120\) 組固定規則集合；每組 6 種解析器，合計 \(720\) 筆真正的外部 Test 解析結果；再配對全部 10 種研究性比較方法與 3 種目標。

研究原始碼：
- `teacher_demo/adaptive_six_policy_runner.py`
- `teacher_demo/adaptive_six_policy_aggregate.py`
- `teacher_demo/test_adaptive_six_policy_selection.py`
- `.github/workflows/adaptive-six-policy-20-eval.yml`

## 4. 演算法成熟度：有證據的 G0–G8 Gate，而不是猜「已完成百分之幾」

| Gate | 定義與客觀停止條件 | 目前狀態 |
|---|---|---|
| **G0 方法語意與計算定義** | 六種投票公式、支持物件、預設類別、無匹配、平手的完整定義 | 已有實作／早先實驗 |
| **G1 固定規則集合可比性** | 每個配置六方法共享 Reduct／LEM2 規則，且 Coverage/Conflict 結構不因解析策略改變 | 先前基線已通過 |
| **G2 外部公開資料管線** | 20 個真正公開來源、有 SHA、來源連結、固定切分與 provenance | 已驗證 20/20 |
| **G3 自適應策略不洩漏 Test** | Inner Validation 決定策略；留一整個資料集防重複 Seed 洩漏；單元測試通過 | 本輪已實作，實驗執行中 |
| **G4 未見資料優於固定方法** | 留一資料集 BA／Macro-F1 等權平均，至少不輸最佳固定策略，並公開失敗案例和 95% CI | 本輪需以實驗決定，不能預先宣稱 |
| **G5 分布移轉穩健性** | ≥42 Seeds、Client α=.1/.5、數量／特徵偏斜、時間切分、零或高衝突、稀有類別 | 未達 |
| **G6 交叉資料集完整統計** | ≥20 互異資料領域為獨立單位，效應、置信區間、paired test、Friedman 與多重檢定，預註冊主要目標 | 未達；本輪先導描述性 |
| **G7 演算法設計／新穎性** | 形式化偽代碼、理論性質／反例、與現有 Algorithm Selection/Meta-Learning/Rule Pruning 的清楚差異和消融驗證 | 未達；Meta kNN 本身並非全新 |
| **G8 可實際導入的大樣本效能** | 比較參數、訓練／推論時間、記憶體與 Client 數量；驗證超過小型固定子集的可擴展性 | 未達；目前存在 Exact Reduct 組合搜尋限制 |

### 「差多少」的技術結論

如果目標是**能執行的研究 PoC**：G0–G3 為必要基礎，G4 能決定是否有相對固定策略的真正效益。這不是論文已接受或創新已確立。

如果目標是**有機會發表的新的算法主張**：至少還欠 G4、G5、G6、G7；若論文主張支援大型 Federated 資料，還必須完成 G8。這不是依工時估算的百分比，而是依可複驗實證和學術新穎性分解的驗收 Gate。

## 5. 實驗最容易踩到的錯誤

1. **多數類別 Accuracy 假高**。若少數類別 Recall 幾乎 0，不能把高 Accuracy 當選擇器成功。
2. **零衝突策略全平手**。不得強塞「某策略最好」的標籤；可考慮預設最低成本的固定解析器。
3. **將 Test 的 Conflict/Candidate Coverage 當作訓練特徵**。即使無目標標籤，也已接觸目標測試分布，不適合聲稱完全未見。
4. **同資料集的三 Seed 同時出現在 Meta Train/Test**。必須排除整份資料集，不只排除 Seed 42。
5. **用測試最佳策略當 Meta 標籤**。必須只使用其他資料集的驗證表現；Oracle 只用於 Regret 上限。
6. **與 8,820 基線直接比較分數**。本次規則只用 64% Development，舊基線用 80%，兩者訓練條件不同。
7. **把六策略稱為六個規則學習方法**。它們其實共享相同歸納結果，是六個決策解析器，方法層級應清楚標示。

## 6. 相關文獻及新穎性邊界

- Rice, J. R. (1976). [The Algorithm Selection Problem](https://doi.org/10.1016/S0065-2458(08)60520-3)：以資料／問題特徵選擇演算法的正式框架。
- Thornton, C., Hutter, F., Hoos, H., & Leyton-Brown, K. (2013). [Auto-WEKA: Combined Selection and Hyperparameter Optimization of Classification Algorithms](https://www.cs.ubc.ca/~kevinlb/papers/2013-KDD-AutoWeka.pdf)：算法選擇與參數搜尋已是成熟研究領域。
- Cawley, G. C. & Talbot, N. L. C. (2010). [On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation](https://jmlr.org/papers/v11/cawley10a.html)：選擇器自身可能過擬合內部驗證，不能用同一內驗證估計泛化。
- Demšar, J. (2006). [Statistical Comparisons of Classifiers over Multiple Data Sets](https://jmlr.org/papers/v7/demsar06a.html)：跨資料集配對比較，Friedman、Wilcoxon 及後續檢定；Seed 間重複觀測不能冒充不同資料集。
- Dagan, I. et al. (2024). [Automated algorithm selection using meta-learning and pre-trained deep convolution neural networks](https://doi.org/10.1016/j.inffus.2023.102210)：跨資料集推薦本身已有多種基準及設計。

**原則**：結果負面也要保留；若僅固定 Simple Voting 或 Global Strength 已優於 Meta Selector，就應回到特徵設計、驗證樣本不足或策略差異太小等問題，而不能換 Test 導向的算法宣稱成功。
