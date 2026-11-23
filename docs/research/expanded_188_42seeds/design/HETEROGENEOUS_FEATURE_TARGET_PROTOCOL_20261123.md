# LEM2 異質聯邦研究設計：特徵擴張、目標不一致與企業真實資料分割
**狀態：新增研究假說及預註冊草案，未執行新實驗；不得將此文件的情境結果歸入 188×42 seeds 現有數字。**  
研究基準：2026-11-23 11:42:29 (Asia/Taipei) 期中快照，179/188 完整資料集。本文是新增的研究設計，不修改 baseline 或原始證據。

## 1. 已驗證的 baseline 與外推界線
- `experiments/full_scale_20261118/model.py`: 同一 `Source.frame` 先執行 64/16/20 split，`dev` 再分配給三個 client；`source.features`、`source.target` 對各 client 均為同一份 contract。
- `experiments/full_scale_20261118/sources.py`: PMLB、UCI 原則取前六項（部分 UCI 由 config 指定），OpenML 的準備器 `experiments/redesign_20261116/confirmatory_registry.py` 先排除識別或 ignore 欄位，再取最多六項。不能把六特徵效果和資料 Rows 效果混為因果。
- `fedrs/experiment.py::fit_model`：所有 client 套用同一 `features`、`target`，對全體資料離散化，逐 client 做 reduct / LEM2，再規則去重 union。它**不是**對不同 Schema / target 的原生支援。
- `roughset/reduct.py::find_exact_minimum_cardinality_reducts`：從大小 0 開始枚舉特徵子集，最壞候選數隨特徵數呈指數成長；不能直接在全部高維資料集無上限開放 features。
- `fedrs/discretize.py::fit_equal_width` 取得各 client 數值特徵全域範圍；目前是離線協定模型，不等同保證企業間沒有資料洩漏的分散式實作。

## 2. 真實情境要以三個正交維度定義

定義 `X_c` 為 client c 的特徵集合，`Y_c` 為決策語意／標籤空間，`I_c` 為實體身份集合。對每一對 client，必須記錄：
- `feature_overlap = |X_A∩X_B| / |X_A∪X_B|`（特徵語意一致才算；名稱相同但單位／定義不同不算）。
- `target_relation ∈ {EXACT, ALIAS_EQUIVALENT, COARSE_GRAIN_MAPPING, PARTIAL_OVERLAP, INCOMPATIBLE}`，由外部標籤規格與獨立人工／元資料對齊確定；**不能用測試標籤反向產生映射**。
- `entity_overlap ∈ {DISJOINT, PARTIAL, ALIGNED}`，是否有共同實體、能否以合法安全協定對齊。
- `feature_availability_at_inference` 需獨立記錄；訓練時有欄位不代表部署時同樣可用。

| 情境 | Target | Feature | 實體 | 合理 baseline 與比較單位 |
|---|---|---|---|---|
| H1 同構 HFL | EXACT | 100% 共用 | disjoint rows | 原 188×42，同一目標 Accuracy/BA/Coverage/Conflict |
| H2 Feature-heterogeneous HFL | EXACT | 25–75% 或 0% overlap | disjoint rows | 本地專業模型＋驗證集融合；共同 feature only；有條件的 rules union |
| H3 VFL | EXACT 或標籤僅由持有方提供 | 不同或部分重疊 | same/overlapping entities | 先取得合法的 entity-alignment，推理協調；不能直接 union raw rule antecedents |
| H4 Label harmonization | ALIAS_EQUIVALENT / COARSE_GRAIN_MAPPING / PARTIAL_OVERLAP | 任意 | disjoint/partial | 論域映射、對齊成本、映射損失；共同粒度 task 的 Accuracy/BA + 原 task 的保留績效 |
| H5 Multi-task / transfer | INCOMPATIBLE | 任意 | 任意 | 無共同分類 accuracy；target-specific metrics、negative transfer、共享規則片段的品質與費用 |

**重點**：標籤文字不同不等於目標不同；標籤文字相同也不等於目標同義。H5 的規則不能直接投票為同一 Decision。

## 3. 六特徵擴張與目標異質性分開做消融

研究問題：
- RQ-A：在 X 完全共同時，feature budget 改變是否使 Accuracy、Coverage、Conflict、NoMatch、TRUE rules 出現非單調轉折？
- RQ-B：固定 feature budget、相同 target，降低 X overlap 是否使聯邦規則整合失效？有無可行的 rule compatibility/decision-level fallback？
- RQ-C：Label relation 從 EXACT → ALIAS → COARSE_GRAIN → PARTIAL → INCOMPATIBLE 時，何時「共同模型」不再有定義？是否應停止 aggregation 改用 multi-task？
- RQ-D：當 X overlap 很低但 entity overlap 很高時，是否可以用 VFL 的合法對齊與分散式推理比 HFL rule union 更有效？
- RQ-E：train sample size × effective feature dimensionality × client/class minimum support 是否比單一 Rows 更能定位衝突 regime？

**分階段固定其他變數避免爆炸：**

P0｜基準特徵數擴張（無 feature heterogeneity）：選 6–10 個原始特徵 ≥12、大小與類別數多樣且不含同源重複的資料集，固定 identical 64/16/20 split，特徵數 `k∈{6,8,12,16}`（來源不夠時省略），每 dataset 多個 seeds。Feature selection 僅使用 development fold；至少比較 ORIGINAL_FIRST_K、TRAIN_ONLY_FILTERED_RANKED_K、RANDOM_K；在可計算與計算成本守門下用 exact reduct，不能偷換 greedy 定義。

P1｜Same Y / Different X：固定 feature budget，例如 `k=8/12`；指定 client feature overlap 100% / 50% / 0%。不重抽 target、不更換外層 test。先做有共用 anchor feature 的情境；no-overlap 要先定義推理可用欄位與融合協議（不是任意補缺失為 0），baseline 包含 LOCAL_ONLY、SHARED_FEATURE_ONLY、VALIDATION_SELECTED_ENSEMBLE、SCHEMA_AWARE_RULE_ROUTING、IF_COMPATIBLE_UNION。

P2｜Target ontology：固定 X overlap；製造 (a) label alias (b) 類別合併映射 (c) 部分類別缺失 (d) truly unrelated target。映射所需 class taxonomy 只能來自 developer annotation / source metadata / train-set ontology，不可利用 test truth。共同 target 只在有合法可解釋 mapping 下評估；不同 target 改採 target-specific/transfer metrics。

P3｜縱向聯邦與真實組織：相同 entity 分持不同行/欄的場景需有效的主鍵對齊與權限控制；PSI/secure join 的實際權限、安全與 membership disclosure 需獨立評估。沒有 entity overlap 也沒有共用 feature 時，可能沒有足夠可識別性，結果應為 NOT_IDENTIFIABLE / NOT_SUPPORTED 而不是硬算全域 Accuracy。

## 4. 機制不應把「無欄位」視為規則匹配

對任意 rule r、推理查詢 q：
- 若 q 缺少 r 所需前件特徵，`evaluability(r,q)=UNAVAILABLE_FEATURE`；不能把未觀測條件視為 true（否則 coverage 假性膨脹）。
- 若前件可評估但條件不符，`NO_MATCH`。
- 若前件可評估且符合，`MATCH`。
- 若不同 client 使用相同名稱、但單位、類別語義、equal-width bin edges 不同，規則 **不可**以字面相同判為可合併；需 schema/units/bin definition canonicalization。
- Label 不可對齊，rule 的 consequent 絕對不可合併成同一投票空間。
- UNION 的 dedup / provenance 必須帶 `feature_schema_version`, `target_ontology_version`, `binning_contract`, `source_client`, `inference_availability`；不可把不可比較的規則當同義規則去重。

## 5. 測量：Accuracy 不夠

**主要效能**（同一 target 才可比較）：Accuracy、Balanced Accuracy、Macro F1、class-wise recall、NoMatch、Test Coverage、Candidate Coverage、Conflict、abstention、標籤映射後的保留率。
**機制**：reduct size、TRUE-rule rate、rule length、exact antecedent collision、unavailable-feature rate、各 client class min support、client overlap、prediction disagreement、跨 Client 所用規則比例。
**運算成本**：reduct candidates、training wall time、peak RSS/VRAM、推理延遲、timeout、communication cost、secure alignment cost。
**可部署性**：完全不需要對齊者／需 PSI 者／只可局部專業模型／無法合法整合者；不得以連通性或缺資料隨意補足。
**公平比較**：同一 source、同一 seed、相同外層 Test、同樣的可用欄位／前處理契約；分組先 dataset 後 cross-source；同源系列使用 family-block sensitivity。不可用 Test set 事後選最佳 policy 回報為 deployable best。

## 6. 前期觀測與可證／不可證區分

- 已有 188×42：高 non-IID 時 test coverage 與 conflict 同時上升；有異質目標/特徵研究設計的需求，但**不能**由此推論不同 Feature/Target 情況也會相同。
- 已有研究的 6 features cap 使「特徵數與 Rows 的交互作用」尚未識別；六特徵限制造成反曲線是需要驗證的假說，而非定理。
- 當增加 features，in-sample 依賴度可能非下降，但 out-of-sample accuracy / coverage 並不保證改善；exact reduct 搜尋與規則比對成本可能快速增加。
- 某些行為的「斷層」來自 `empty_reduct`、`TRUE→class`、特徵覆蓋缺口或標籤無共同語意，這些不是同一種 transition，必須分別定義。

## 7. 正式提案的停止條件

P0: 每個 k 的 exact job 不超資源與時間門檻；任何提前中止有明確 TIMEOUT / NOT_COMPUTABLE，不能混作模型表現。
P1: 相同 X overlap 的三種策略需要相同 test 可評估 feature 集合；若 model 無法取得必要 feature，改使用 abstention 或 specialist output，而非偷看原始 Test fields。
P2: 不存在可證實 label mapping 則停止宣稱共同 Accuracy，改用各 task 保留與 negative transfer。
P3: 無合法 entity alignment / privacy contract 停止 VFL 建模；不使用未授權跨機構 join。
P4: 不發生 source leakage / family leakage，否則任何推論不宣告 PASS。

## 研究參考

- Q. Yang et al., *Federated Machine Learning: Concept and Applications*, ACM TIST (2019), [paper](https://hufudb.com/static/paper/2019/TIST2019_Federated%20Machine%20Learning_Concept%20and%20Applications_PDF.pdf).
- *A Survey on Heterogeneous Federated Learning*, arXiv:2210.04505, [preprint](https://arxiv.org/abs/2210.04505).
- *A comprehensive survey of federated transfer learning: challenges, methods and applications*, [article](https://journal.hep.com.cn/fcs/EN/10.1007/s11704-024-40065-x).
- 現行方法定義：`experiments/full_scale_20261118/{sources,model}.py`, `experiments/redesign_20261116/confirmatory_registry.py`, `fedrs/{experiment,induce,discretize}.py`, `roughset/reduct.py`.

## 狀態

**PROTOCOL_ONLY / NO_NEW_MODEL_RUN / HYPOTHESES_NOT_CONFIRMED.** 下一階段優先執行 P0→P1 小樣設計；先界定可對齊 target 與 inference-time feature availability，再評估 H3/H4/H5，不直接把所有因素笛卡兒相乘跑完。
