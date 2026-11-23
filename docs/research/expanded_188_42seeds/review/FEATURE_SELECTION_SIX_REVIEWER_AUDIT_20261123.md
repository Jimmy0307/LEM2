# LEM2 188 資料集｜六特徵限制、特徵選取與三 Client 方法學稽核
**Snapshot：2026-11-23 11:42:29（台灣時間）｜本檔只做來源、方法與結果盤點，不修改已凍結實驗。** 42-seed 完整資料集 179／188；未完成 9 筆也納入來源規格分母。證據出自程式與實驗 registry，不推定未實驗的多特徵績效。

## 1｜主要審稿者問題：188 datasets 到底使用幾個特徵？

全部 188 筆來源：
- **162** 筆原始特徵 **>6**，實際輸入 **6**（86.17%）。
- **9** 筆原始特徵 **=6**，實際輸入 **6**（4.79%）。
- **17** 筆原始特徵 **<6**，實際保留 **2–5**（9.04%）。
- **171/188（90.96%）** 模型輸入六特徵；**0 筆模型使用超過六個輸入特徵**。
- **74／188** 特徵保留率小於 **25%**，**31／188** 小於 10%。
- 在 **179** 筆 42-seed 完整資料集中：**162** 筆使用六個輸入特徵、**17** 筆少於六個；其餘九個未完成來源都是六個輸入特徵。
- 這裡的 feature count 是 **送入 exact reduct 之前的候選特徵數**，**不是**最終 reduct size、規則條件長度、也不是每個 client 平均分到的 feature 數。

### 依資料來源群組（欄位依序：原始維度高於六／等於六／少於六；實際使用六／少於六）
| Cohort | 研究任務數 | 42 seeds 完整 | 原始 >6 | 原始 =6 | 原始 <6 | 使用 6 | 使用 <6 | 預先手選欄位 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| COMMERCE2 | 2 | 2 | 1 | 1 | 0 | 2 | 0 | 2 |
| EXT7 | 7 | 7 | 7 | 0 | 0 | 7 | 0 | 0 |
| NEXT12 | 12 | 12 | 10 | 1 | 1 | 11 | 1 | 2 |
| O3 | 3 | 3 | 0 | 1 | 2 | 1 | 2 | 0 |
| OML51 | 51 | 43 | 49 | 1 | 1 | 50 | 1 | 0 |
| PMLB | 93 | 93 | 78 | 5 | 10 | 83 | 10 | 0 |
| UCI20 | 20 | 19 | 17 | 0 | 3 | 17 | 3 | 4 |
| **合計** | **188** | **179** | **162** | **9** | **17** | **171** | **17** | **8** |

### 原始特徵高、只取六個的代表性風險
| Dataset | 原始特徵 | 使用特徵 | 保留率 |
|---|---:|---:|---:|
| Bioresponse (`OML51:openml_4134`) | 1776 | 6 | 0.338% |
| christine (`OML51:openml_41142`) | 1636 | 6 | 0.367% |
| Internet-Advertisements (`OML51:openml_40978`) | 1558 | 6 | 0.385% |
| GAMETES_Epistasis_2_Way_1000atts_0.4H_EDM_1_EDM_1_1 (`PMLB:GAMETES_Epistasis_2_Way_1000atts_0.4H_EDM_1_EDM_1_1`) | 1000 | 6 | 0.600% |
| gina (`OML51:openml_41158`) | 970 | 6 | 0.619% |
| cnae-9 (`OML51:openml_1468`) | 856 | 6 | 0.701% |
| fabert (`OML51:openml_41164`) | 800 | 6 | 0.750% |
| Fashion-MNIST (`OML51:openml_40996`) | 784 | 6 | 0.765% |
| mnist (`PMLB:mnist`) | 784 | 6 | 0.765% |
| har (`OML51:openml_1478`) | 561 | 6 | 1.070% |
| madelon (`OML51:openml_1485`) | 500 | 6 | 1.200% |
| philippine (`OML51:openml_41145`) | 308 | 6 | 1.948% |

**解釋**：例如 MNIST / Fashion-MNIST 原本 784 維，僅留 6 維；這是 six-feature feature-subset benchmark，**不是**全 784 維的分類成績。各資料集原始特徵計數依各自 loader/registry 定義，識別欄位及來源欄位型態可能不同；本表不可視為各來源完全等價的可用預測欄位總數。

### 全部實際少於六個特徵的資料集（非「另外刪到六個以下」）
| Dataset | 原始特徵 | 實際模型輸入 |
|---|---:|---:|
| `NEXT12:blood_donation` | 4 | 4 |
| `O3:Balance Scale` | 4 | 4 |
| `O3:Hayes-Roth` | 4 | 4 |
| `OML51:openml_40983` | 5 | 5 |
| `PMLB:analcatdata_dmft` | 4 | 4 |
| `PMLB:analcatdata_germangss` | 5 | 5 |
| `PMLB:analcatdata_lawsuit` | 4 | 4 |
| `PMLB:banana` | 2 | 2 |
| `PMLB:bupa` | 5 | 5 |
| `PMLB:irish` | 5 | 5 |
| `PMLB:new_thyroid` | 5 | 5 |
| `PMLB:phoneme` | 5 | 5 |
| `PMLB:prnn_synth` | 2 | 2 |
| `PMLB:tae` | 5 | 5 |
| `UCI20:banknote` | 4 | 4 |
| `UCI20:haberman` | 3 | 3 |
| `UCI20:iris` | 4 | 4 |

### 逐資料集可追溯總表
[FEATURE_SELECTION_AUDIT_188.csv](./FEATURE_SELECTION_AUDIT_188.csv)（188 列，每筆包括原始/使用 Rows、原始/使用 Features、保留率、原始被選欄名、source、Class 數、選特徵規則與 42-seed 完成狀態；**不公開 SHA256**）。

## 2｜究竟為什麼取六個、又怎麼挑六個？

**其目的為控制 exact classical reduct 及 LEM2 的計算負擔，並維持與先前 feasibility protocol 的一致性；不是任何文獻證明「六個最佳」。**

精確最小 reduct 搜尋 `roughset/reduct.py::find_exact_minimum_cardinality_reducts` 依子集大小由 0 開始逐層枚舉，直到找到 positive region 與全部輸入特徵相同的最小基數子集。可檢查的子集空間為 `2^k`（k=6: 64, k=12: 4096, k=20: 1,048,576）；實際候選枚舉可能提早停止，實際執行成本還依 Rows、分組密度和資料型態而變。

**實際挑法依來源不同，而非統計上挑最有用的六個：**

1. **PMLB（93）**：先排除特定識別欄（如 `id/index/*_id`），再取原始剩餘 predictors 的**前六欄**。模型內部為 `f0`–`f5`，原始名稱另存 `original_feature_names`。沒有用 Target 或測試集做特徵重要度排序。
2. **OpenML（51）**：按 OpenML **欄位順序**，排除 target、ignore、row identifier 以及整數且幾乎每列唯一（≥95%）的疑似 ID 欄位，再取前六欄。完整檔案擷取全資料列，不代表使用全部 feature；原始 `source_name` 仍可追溯。
3. **UCI 類（44=UCI20 20 + NEXT12 12 + EXT7 7 + COMMERCE2 2 + O3 3）**：多數由 UCI 原始次序**前 min(6, 設定 max_features) 欄**，但有 **8 筆** 事先手選欄位：`UCI20:bank_marketing`, `UCI20:adult_income`, `UCI20:german_credit`, `UCI20:grid_stability`, `NEXT12:heart_disease`, `NEXT12:student_performance`, `COMMERCE2:online_shoppers`, `COMMERCE2:ai4i_maintenance`。這些是由研究設定預先定義，不是 learned feature ranking。
4. 特徵預處理：連續變數使用共用 `EQUAL_WIDTH_3` 離散化；Rule / Reduct 在各 client 的訓練資料上局部歸納。部分來源對 Target 做了二元化及罕見類別移除，需另表追蹤，不可誤當所有來源 Target 天然等價。
5. **注意**：「前六欄」並非有保證的最佳組合，有些高維影像或序列資料前六欄未必承載主要分類訊號；先驗人工挑選有業務/避免 leakage 意圖，但與 first-k 不同，可能造成不同 Cohort 的 selection bias。現有模型不包含 feature-ranking 消融。

## 3｜六個 Features VS 三個 Clients：是不是硬體或數學必須？

**不是 `6 features / 3 clients = 每人 2 features`**，也不是有學理證明六個對三個最佳。現行協定是同一份 dataset 先以 64/16/20 Dev/Val/Test 切分，將**同一個 feature schema 和同一個 target** 的 Dev rows 分配到三個 clients（HFL）：

```text
Original Data: N rows × k≤6 features + 1 target
             ├── Development 64% N ──┬── Client A: different rows × SAME k features
             │                        ├── Client B: different rows × SAME k features
             │                        └── Client C: different rows × SAME k features
             ├── Validation 16% N
             └── Test 20% N
```

- 三個 client IID 近似平均每方 `0.64N/3 ≈ 0.213N` 筆 Development 資料，**不是**分兩個 feature 給每個 client。
- `FED_IID` 實施 stratified partition；`FED_A05` 和 `FED_A01` 是 label-skew Dirichlet α=0.5/0.1。三方各自用共同特徵與自己的局部資料找 reduct / LEM2 rules，伺服端 union/dedup。
- 原始 partition 不可行才會進入 constrained partition（min_rows=20、至少 2 類、每個出現類別 ≥3 筆；最多 500 attempts）。**是否觸發此 fallback 必須逐模型留在 partition_status 中核對**。它改變實現的資料分配，不應說每輪都以純粹 Dirichlet 採樣成功。
- `EQUAL_WIDTH_3` 只在數值特徵設定三個 bin；對六個純連續特徵，組合空間上限為 `3^6=729` 種離散條件組合，對十二個純連續特徵為 `3^12=531,441`。這是理論組合數，並非一定都觀測到；混合類別欄位的 cardinality 更不同。
- Features 太少：不同類別可能落在同條件組合，產生不可辨識、低 precision、衝突或無有用 reduct 的問題；**但不能保證一定產生反曲線**。
- Features 太多：每 Client 可用訓練筆數/離散條件組合可能過低，引發過度分割、uncovered/no-match、泛化失效，以及 exact reduct 計算/記憶體成本升高；**也不能保證一定會提高 Accuracy 或錯誤率**。
- 目前所有 clients 在同一 dataset 都收到相同 k 欄位。真實企業的 Feature-heterogeneous FL（不同 schema）、Target-heterogeneous FL 未在這一套 188×42 主實驗評估；不得推論跨企業不同 Schema 的直接 union 成功率。

## 4｜目前可回答／不能回答的研究問題

**能回答**：在「固定最多六個輸入特徵、三 Clients、共用 Target、共用 discretization、四種資料分布／六策略／兩規則版本」的嚴格限定下，179 個完成資料集的 Coverage、Candidate Coverage、Conflict、Accuracy/BA 及變化。

**不能回答**：在 `k=8/12/ALL` 時是否更準、哪個 k 最佳、只選前 k 與 supervised feature selection 的差別、2/5/10 clients 是否重現同樣曲線、真實 heterogeneous features 下是否可以直接共用 rule、不同目標是否有同義的 Accuracy。此類結論需要新增實驗。

### 必須回答的 Reviewer Questions

| Question | 誠實答法 |
|---|---|
| Why six? | 為可重現、可計算的精確 reduct baseline 而預先凍結的 feature cap；不是聲稱特徵選擇已最佳化。 |
| How chosen? | PMLB/OpenML 主要 first-six eligible columns；UCI 多數 first-six，8 個明訂人工選欄；沒有 train-based importance ranking。 |
| Can the results generalize to full dimensions? | **尚不能**；全量 Rows 並不等於全量 Features。 |
| Why exactly 3 clients? | 固定三 client 作標準 HFL topology 對照，並非 k=6 所需；client-count sweep 未包含在這一組主協定。 |
| Is k related to partition skew? | 可能透過 client class support、可分辨條件組合、local reduct 與 TRUE-rule 增加產生交互作用；尚未驗證因果。 |
| Does adding features increase errors? | 可能改善或惡化、也可能因 NP-hard cost timeout；不能在沒有配對 feature-budget 消融下判定。 |
| Did you test heterogeneous features/targets? | 沒有；此 188×42 是同 schema + 同 target 的水平分割實驗。另有異質研究設計，尚未跑出新模型。 |

## 5｜最低成本的優先驗證矩陣

**先做 feature-budget 消融，不直接把高維原始資料全部投入 exact reduct。**
- 固定 source × seed × test split × 3 clients × partition protocol，選 6–10 個彼此非同源且具有足夠原始特徵的代表來源。
- 特徵數 `k∈{2,4,6,8,12}`（原始不足則刪除不可行 cells）；對 high-dimensional original sources 另設 `k=16/ALL` 的 **resource-gated** feasibility 階段，絕不將 greedy approximate 與 exact LEM2 偷換為同一實驗。
- Feature selection 需要最少三條 baseline：`FIRST_K`（對照原始）、`RANDOM_K`（多次特徵抽樣，train-independent）、`TRAIN_ONLY_RANKED_K`（任何 supervised ranking 僅能 Dev 資料內部完成、不得接觸 Val/Test Truth）。
- 固定 `clients=3` 比較 `IID, α=.5, α=.1`；另選小樣比較 `clients∈{2,3,5}`，**不要**把特徵數與 Clients 數同時改、卻只在結果後用 Clients 解釋變化。
- 追加 `effective client-class support`、`occupied discretized cells`、`full POS`、`reduct size / candidate_count`、`TRUE rules`、`no-match`、`balanced accuracy`、`class recall`、`runtime/RSS`、`TIMEOUT`；所有完成／未完成有同等透明度。
- 先以同資料集、同 seed 的配對差異估計 `Δ(k)`，再以 dataset 為單位聚合。預先訂定失敗門檻與運算預算，且需對來源家族做 grouped sensitivity。

## Sources
- [來源元資料：REGISTRY.csv](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/docs/research/full_scale_20261118/REGISTRY.csv)
- [42-seed completeness](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/docs/research/expanded_188_42seeds/interim/COMPLETENESS.csv)
- [PMLB 與 UCI Source loader](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/experiments/full_scale_20261118/sources.py)
- [OpenML first-six E6](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/experiments/redesign_20261116/confirmatory_registry.py)
- [UCI predefined feature contracts](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/teacher_demo/public_20_registry.py)
- [UCI Next12 feature contracts](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/teacher_demo/public_next12_registry.py)
- [3-client split and exact model](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/experiments/full_scale_20261118/model.py)
- [Partition fallback constraints](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/fedrs/partition.py)
- [Exact minimum reduct implementation](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/roughset/reduct.py)

**Evidence status: REVIEWER_READY_FOR_METHODS_DISCUSSION; FEATURE_DIMENSION_CAUSAL_CLAIMS_NOT_ESTABLISHED.**