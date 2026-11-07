# LEM2 1–42 Seeds｜實驗變因定義與對照契約

> 執行證據：[GitHub Actions run 42409836379](https://github.com/Jimmy0307/LEM2/actions/runs/42409836379)｜完整數據：`tables/SEED_SWEEP_8820.csv`（8,820 rows，42 seeds × 210）。此文件不包含 DRSA 或 LERS 的實測值。

## 本輪六個真正改變的因素（自變因）

| ID | 因素 | 基準／水準 | 改動含義 | 影響範圍 |
|---|---|---|---|---|
| D01 | dataset | Balance Scale / Car Evaluation / Hayes-Roth | 改變決策表、條件屬性與類別分布 | Reduct → Rules → Evaluation |
| D02 | evaluation.seed | **1–42，全部已執行** | 同一原始表，對每個決策類別使用新亂數重切 Train/Test；Federated 另重切 Clients | Split / Local rules |
| D03 | split_mode | FULL_DATA / HOLDOUT_80_20 | 全資料建模與回代評估 vs 依類別分層 80% 建模、20% 未見評估 | Train、Eval、Rule Set |
| D04 | system | CENTRALIZED / FEDERATED | 一次對 Train 算 reduct + LEM2 vs 各 Client 計算再 UNION | Rule source |
| D05 | client_count | 0（僅集中式）、2/3/4/5（聯邦式） | 固定 Train，改變分到幾個 Client 以及各自的局部規則 | Client partition/Rule union |
| D06 | selection_policy | NONE、FIRST_MATCH、SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH、POPULATION_STANDARD、POPULATION_GLOBAL | **同一 Rule Set 不重訓**，NONE 是只做完整 Matching 診斷；其餘六個方法輸出唯一預測 | Rule Matching / Winner selection |

- 對照計算：固定 dataset、seed、split、system、C 等，**只改一個因素**，令 `Δ = Metric(B) - Metric(A)`。
- 如比較 FULL_DATA vs HOLDOUT_80_20，評估集合不同，**不可把 Accuracy 差異直接解讀成泛化性能的純因果影響**。
- `NONE` 的 Accuracy、BA、Macro-F1 是「未定義」，不可填 0。
- 使用資料的七個 Level 是「NONE + 六策略」，不是七種 Rough Set 演算法。

## 固定控制參數（本輪沒有變更，不能聲稱已做效果掃描）

| ID | 因素 | 固定值 | 定義／限制 |
|---|---|---|---|
| C01 | test_ratio | 0.20 | 每類決策使用 `round(n_class × 0.2)`，至少保留 1 筆 Train/Test |
| C02 | 80/20 stratified split | STRATIFIED | 先依決策類別分組，用同一 NumPy RNG(seed) 依組順序洗牌 |
| C03 | Federated partition | STRATIFIED | Train 各類別重新洗牌後，按照 `i % C` 逐個分配至各 Client |
| C04 | reduct.enabled | true | 先計算 Classical reduct，再輸入 LEM2 |
| C05 | reduct.method | MINIMUM_CARDINALITY | 找保存 `|POS_P(d)| = |POS_C(d)|` 的最小基數條件子集 |
| C06 | reduct.selection | LEXICOGRAPHIC_FIRST | 若有多個最小候選 reduct，取字典序第一個 |
| C07 | preprocessing.auto_discretize | true | 只以 Train 擬合共享前處理；不是用 Test 擬合 |
| C08 | preprocessing.n_bins | 3 | 如需要連續屬性離散化，使用三箱；三個 UCI 特徵列為類別 |
| C09 | unique_numeric_threshold | 10 | 特徵型別檢測閾值；資料 profile 強制類別 |
| C10 | Rule UNION dedup | 完整前件＋決策去重 | 保留第一個相同 key 規則，記錄所有 producer provenance |
| C11 | global support context | all client Train supports | STD／GS／PS／PG 需額外統計交換，不是單純交換規則 |
| C12 | No-match fallback | Train majority class | 六策略在無規則命中時仍可能輸出預測，NONE 不輸出 |
| C13 | Conflict | `|Cand_R(x)|>1` | 完整 Rule Matching 的跨決策候選衝突，**不是 DRSA boundary** |
| C14 | Evaluation scope | FULL=resubstitution | Full Data 與 Holdout 指標統計口徑不同 |
| C15 | Order audit | 1（主矩陣） | FIRST_MATCH 對規則列表次序敏感，尚未窮舉所有 Client 排列 |
| C16 | Aggregation | equal-weight datasets / C | 總平均不是物件層 micro-average；應並報逐資料集 |

## 待擴充因素（**8,820 列不包含這些結果**）

1. P01：`DIRICHLET_LABEL_SKEW` 下的 non-IID partition，α=0.5/0.1。現有 config 中 alpha=0.5，但因 partition=STRATIFIED，**它未在本輪生效**。
2. P02：Client 的 C! 種規則合併順序／FIRST_MATCH 排序敏感性。
3. P03：DRSA reduct：需 dominance cones、class union、保存準則與最小性實作。
4. P04：文獻原典的 LERS classifier（不等同本 repo 的 STANDARD_VOTING）。
5. P05：改變 test_ratio，例如 0.1/0.2/0.3；本輪只固定 0.2。

## 42-Seed 可重現性與實測發現

- 一次 Seed 210 列，其中 NONE 30、六策略 180；1–42 合計 **8,820 列 = 1,260 NONE + 7,560 policy**。
- Seed 1–6 新執行與舊 7-Seed 穩健性結果的數值完全一致；Seed 42 已通過既有 210 列 frozen baseline 的重現檢查。
- 80/20，三資料集等權平均，Conflict Rate：Centralized **10.57%**；Federated C=2 **27.75%**、C=3 **46.07%**、C=4 **59.72%**、C=5 **68.67%**。
- Federated 80/20（C2–C5 等權），GLOBAL_STRENGTH：Accuracy **80.94%**、Balanced Accuracy **69.25%**、Macro-F1 **67.26%**。
- 配對 C=2→C=5：Conflict +**40.92** 百分點、Coverage +**5.00** 百分點；GLOBAL_STRENGTH Accuracy −**3.19** 百分點。它是本設計的描述性效果，不是對一切聯邦學習的一般定理。
- GLOBAL_STRENGTH 相對 STANDARD_VOTING（配對）：BA +**5.16** 百分點、Accuracy +**0.40** 百分點。
- 42 Seeds 重複使用相同資料集；**不要把 42×3×C×policy 視為全獨立的推論樣本**。應使用 paired contrasts、逐資料集敏感性分析及適合的階層／配對設計。

## 程式對照

- `roughset/splitting.py`：per-class 80/20 split
- `roughset/federated.py`：per-class client partition、UNION
- `roughset/reduct.py`：Classical reduct，POS preservation
- `roughset/pipeline.py`：Local reduct/LEM2 → global UNION → support context
- `roughset/evaluation.py`：完整 Matching 診斷與六策略
- `teacher_demo/full_factorial_matrix.py`：210-row experiment design
- `teacher_demo/seed_sweep_runner.py`：42 Seed 個別重跑與 Seed 42 frozen baseline 檢查
