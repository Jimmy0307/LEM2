# 演算法架構：聯邦 Rough Set／LEM2 管線

每一步標示三種身分，不可混用：

- **【理論】**：既有文獻的方法，本研究沒有發明。
- **【工程】**：本研究的程式實作或模擬方式，不構成方法學貢獻。
- **【候選】**：本研究評估的研究候選方法。通過預註冊驗證不代表它是新演算法或一般最佳。

```
Data ─► Client Partition ─► Discretization ─► Reduct ─► Local LEM2
     ─► Federated Rule Aggregation (UNION) ─► TRUE-Rule Handling ─► Prediction (6 policies / selector)
     ─► Evaluation (nested split, dataset-level paired statistics)
```

## 1. Data【工程】
- 來源：UCI20（探索性，Gate 0–4）、合成資料（Gate 3）、OpenML 51 份（確認性，Gate 5，`experiments/redesign_20261116/confirmatory_registry.py`）。
- 預註冊的機械規則：取前 6 個特徵，最多 1,800 列，數值缺值 >5% 的來源排除（E1–E6b）。這是絕對準確率偏低（BA 約 44–50%）的主因。
- 切分（`fedrs/experiment.py: nested_split`）：外層 80/20 分層切出 Test（seed）；內層把 Development 再 80/20 切出 Validation（seed+1000）。Train : Validation : Test = 64 : 16 : 20。**Test 只用於最後評估，不參與任何選擇。**

## 2. Client Partition【工程】
- `fedrs/partition.py: original_partition`：沿用原研究的分割器。3 個 Client；IID（分層）或 Dirichlet(α) 標籤偏斜，α ∈ {0.5, 0.1}。
- Control C（`constrained_partition`，只在 Gate 1 診斷使用）：要求每個 Client ≥20 列、≥2 類、每個出現的類 ≥3 列，最多重抽 500 次。它會改變資料分配，因此不能當成規則層處理的效果。

## 3. Discretization
| 方法 | 身分 | 說明 |
|---|---|---|
| EQUAL_WIDTH_3（EW3） | 【理論】原始基線 | 每個連續特徵在全域範圍上切成 3 個等寬區間（Low／Medium／High） |
| EW5、等頻、MDLP（Fayyad–Irani） | 【理論】 | 對照組；MDLP_HIST 是在 32 格共享網格的直方圖上執行 |
| RS_DISCERNIBILITY_CENTRAL（R1） | 【理論】Nguyen–Skowron MD 啟發式 | 集中式參考，貪婪地選擇能分辨最多「不同決策物件對」的切點 |
| **FED_MD_HIST（M2 的離散化）** | 【候選】把 R1 搬到聯邦設定 | 候選切點限制在 32 格共享網格；每一步選擇使「無法分辨的不同決策物件對數」W 最小的切點；每個特徵最多 6 個區間。W 只需要「每格類別計數的跨 Client 總和」與每個 Client 一個純量，**原則上**可以用加總型聚合計算 |
| FED_MD_XC（M3） | 【候選】已被否定 | 把 Client 內部的物件對權重降為 μ=0.25，優先處理跨 Client 衝突。探索性與確認性資料都沒有比 M2 好 |
| FCP_HIST、LOCO_SELECT | 【候選】負面結果 | 衝突懲罰項沒有帶來增益（Gate 4） |

**工程限制**：目前的程式在單一行程內把 Client 資料合併後計算 W（`fedrs/conflict_cuts.py: fit_fed_md`），也就是**模擬**聯邦計算，沒有實作通訊協定、安全聚合或差分隱私。樸素上界是每個 Client 約 7.7×10⁶ 個數字（Gate 5，α=0.1 平均）。

## 4. Reduct【理論】
- `roughset/pipeline.py: select_minimum_reduct`（原始程式，未改）：每個 Client 在本地決策表上找最小基數的正域約簡 R_c，使 |POS_{R_c}(d)| = |POS_C(d)|。
- 允許空約簡。若 Client 只有單一類別，空集合就已達到完整正域，因此最小約簡 = ∅（退化命題，報告 §0.1）。
- 窮舉搜尋，這也是預註冊只取前 6 個特徵的原因。
- VPRS β-約簡（`fedrs/induce.py`）只在 Gate 3 雜訊實驗中使用。

## 5. Local LEM2【理論】
- `roughset/pipeline.py: induce_lem2_on_reduct`（原始程式）：在 R_c 上由正域歸納確定規則。
- R_c = ∅ 時，唯一可能的規則是空前件規則 **TRUE → k**：在本地 confidence = 1，在全域上的 confidence 只等於類別先驗 P(d=k)，而且會匹配每一個物件。

## 6. Federated Rule Aggregation【理論＋工程】
- UNION（原始做法）：把所有 Client 的規則合併成全域規則集，相同前件、不同結論的規則同時保留。
- 核心落差：局部確定（conf_c = 1）不保證全域確定。全域可信度定義為 conf_G(r) = Σ_c |Supp_c(r)| / Σ_c |Match_c(r)|。

## 7. TRUE-Rule Handling（規則層變體）
| 變體 | 身分 | 行為 | 實證 |
|---|---|---|---|
| A_ALL_RULES | 原始 | TRUE 規則與一般規則一起參與 | α=0.1 時 Coverage 中約 35–42 pp 只靠 TRUE 規則命中 |
| B_DROP_TRUE | 對照 | 刪除 TRUE 規則 | Coverage 掉約 35 pp，不可取 |
| **B2_TRUE_AS_FALLBACK** | 【候選】 | 只有在沒有任何非空規則命中時才使用 TRUE 規則（視為該 Client 的類別先驗） | 確認性 H2：α=0.1 BA +0.53 pp（通過，但效果小） |

B2 目前是工程上的處理規則，沒有理論證明（見 Roadmap R4）。

## 8. Prediction【理論＋工程】
- `fedrs/predict.py`：向量化規則比對（`match_matrix`），結果與原始逐列實作逐位相同（`tests/test_fedrs_parity.py`）。
- 六種解析策略：FIRST_MATCH、SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH、POPULATION_STANDARD、POPULATION_GLOBAL；無命中時用多數類。
- 選擇器：VALIDATION_BEST（以 Inner Validation BA 選策略，平手依原 POLICY_ORDER）；原 G4 Conflict Bucket Router。
- 在 B2 下，六策略之間最大只差約 0.4 pp（確認性），所以策略選擇不是主要槓桿。

## 9. Evaluation【理論】
- 主要指標：Outer Test Balanced Accuracy。結構指標：Exact Coverage、Conflict rate、正確類別是否在候選集合中、TRUE 規則造成的 Coverage／Conflict 分解。
- 統計（Demšar 2006；Benavoli et al. 2016）：先在 (dataset, seed) 配對，seed 先平均，以資料集為統計單位；雙尾 Wilcoxon signed-rank；Holm 校正（H1 三個分布一族）；10,000 次資料集 bootstrap 95% CI；rank-biserial 效果量；家族層級敏感度分析。
- 外部比較（R1、C1 集中式 CART、C2 聯邦 CART 投票）是預註冊的**次要描述性**比較，p 值未校正，沒有非劣性或等效檢定。

## 10. 確認性比較方法（凍結於 `89fd52b`）
| 代號 | 離散化 | 規則層 | 身分 |
|---|---|---|---|
| M0 | EW3 | A | 原始基線 |
| M1 | EW3 | B2 | 只改規則層 |
| **M2** | FED_MD_HIST | B2 | 主要候選 |
| M3 | FED_MD_XC | B2 | 消融 |
| R1／R2／R3 | RS 集中式／MDLP_HIST／EW5 | B2 | 參考 |
| C1／C2 | CART 集中式／CART 聯邦投票 | — | 非 Rough Set 對照 |

## 程式對照
| 步驟 | 模組 |
|---|---|
| 切分、模型建立、評估 | `fedrs/experiment.py` |
| Client 分割 | `fedrs/partition.py` |
| 離散化（基線與參考） | `fedrs/discretize.py` |
| FED_MD、FCP、LOCO 原型 | `fedrs/conflict_cuts.py` |
| 約簡＋LEM2（呼叫原始程式） | `fedrs/induce.py` → `roughset/pipeline.py` |
| 規則變體、比對、六策略 | `fedrs/predict.py` |
| 統計 | `fedrs/stats.py`（獨立驗證：`experiments/redesign_20261116/verify_g5_independent.py`） |
| CART 對照 | `fedrs/baselines.py` |
