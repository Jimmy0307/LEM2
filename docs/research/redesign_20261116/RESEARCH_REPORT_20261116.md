# 聯邦 Rough Set 規則退化與衝突：研究方法重建報告

**分支**：`research/federated-rule-degeneracy-redesign-20261116`（起點 87e31c4；未改動原研究分支、已發布 CSV、42 Seeds 基線；未合併 `main`）
**日期**：2026-11-16
**證據等級**：Gate 0–4 全部為**探索性**（UCI20 已探索來源；Seeds 11、23 為歷史重複使用、101–108 為新增探索 Seeds）。Gate 5 為**預先註冊**的確認性驗證（51 份依預先凍結家族／別名規則排除歷史來源的 OpenML 資料，Seeds 1001–1010）。

**封版狀態**：見 [`RESEARCH_FINAL_STATUS.md`](RESEARCH_FINAL_STATUS.md)；終版稽核的所有文字更正記在 [`FINALIZATION_REVISIONS_20261116.md`](FINALIZATION_REVISIONS_20261116.md)。

---

## 0. 研究問題重構

> 當決策表被分割到不同 Client 後，為什麼局部確定性（local certainty）不能保證全域確定性？如何在保留局部資訊與聯邦限制下控制規則衝突與分類品質？

拆成四個機制分別驗證，不預設單一因果：
1. **Client 類別碎片化 → 退化規則**（Gate 1）
2. **連續特徵離散化 → 局部正域變化**（Gate 2）
3. **局部確定規則合併 → 全域衝突**（Gate 1、3、4）
4. **六種策略的解析能力**（Gate 1、3）

### 0.1 形式定義
決策表 \(S=(U, C\cup\{d\})\)，Client 分割 \(U=\bigsqcup_{c=1}^{m}U_c\)。對屬性集 \(B\)，\(\mathrm{IND}(B)\) 的等價類為 \([x]_B\)。

- Client \(c\) 的正域：\(\mathrm{POS}^c_B(d)=\{x\in U_c: [x]^c_B\subseteq [x]^c_d\}\)。
- 局部最小約簡：最小基數 \(R_c\subseteq C\) 使 \(|\mathrm{POS}^c_{R_c}|=|\mathrm{POS}^c_C|\)，允許 \(R_c=\emptyset\)。
- **退化命題**：若 \(U_c\) 只含單一決策 \(k\)，則 \(\mathrm{IND}(\emptyset)\) 只有一個等價類 \(U_c\subseteq[x]_d\)，因此 \(\mathrm{POS}^c_\emptyset=U_c=\mathrm{POS}^c_C\)，最小約簡為 \(\emptyset\)，LEM2 唯一的確定規則是 \(\mathrm{TRUE}\to k\)（`roughset/pipeline.py: induce_lem2_on_reduct`）。這條規則在 \(U_c\) 上 confidence = 1，但在全域上的 confidence 等於類別先驗 \(P(d=k)\)，且匹配**每一個**物件。
- 規則 \(r\) 的聯邦全域可信度：\(\mathrm{conf}_G(r)=\sum_c|\mathrm{Supp}_c(r)|/\sum_c|\mathrm{Match}_c(r)|\)。局部確定（\(\mathrm{conf}_c=1\)）不保證 \(\mathrm{conf}_G=1\)；這正是本研究的核心落差。
- 預測時每一列的候選決策集合 \(D(x)=\{\mathrm{dec}(r): r\text{ 匹配 } x\}\)：\(|D|=0\) 無命中、\(|D|=1\) 單一候選、\(|D|\ge2\) **Conflict**。

### 0.2 規則層變體（同一組規則，只改合併／預測層）
- **A_ALL_RULES**：原始 UNION。
- **B_DROP_TRUE（Control B）**：排除空前件規則。
- **B2_TRUE_AS_FALLBACK**：TRUE 規則只在沒有任何非空規則命中時才參與（把它解釋為「該 Client 的類別先驗」，局部適用範圍限於無證據區域）。
- **Control C**：限制 Client 建立（≥20 列、≥2 類、每個出現的類 ≥3 列，Dirichlet 決定性重抽 ≤500 次）。**改變資料分配**，另行解讀。

---

## 1. Gate 0：原始審查重現 — PASS

- 指定審查文件 `claude/independent_review_20261116.md` 與 `lem2_review_scripts_20261116.tar.gz` 在儲存庫、全部遠端分支歷史與本機皆**不存在**。診斷全部重新實作；不宣稱已使用審查腳本驗證。
- 新引擎 `fedrs/`：約簡與 LEM2 直接呼叫原始 `roughset` 函式（研究對象不變），僅把規則比對與六策略改成向量化（原始逐列 `iterrows` 一個模型需 36–43 秒）。
- `tests/test_fedrs_parity.py`（Iris／Covertype α=0.1 含 TRUE 規則／German Credit）：等寬三區間離散表、全域規則（鍵與順序）、六策略 Validation 與 Test 預測、歷史發布 `G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv` 的 Router Test BA／Coverage／Conflict **逐位相同**。
- `tests/test_fedrs_units.py`：15 項單元測試（離散器、VPRS β=1 ≡ Classical、單類別 → TRUE 規則、規則變體、平手規則、Control C 決定性、雜訊、P4 原型）。

## 2. Gate 1：退化規則 — 完成

設計：UCI20 × 10 Seeds × {IID, α=0.5, α=0.1} × {ORIGINAL, CONTROL_C}，等寬三區間，3 Clients；共 1,200 模型，成功 1,176；24 個失敗全是 Control C 不可行（Covertype IID：稀有類無法讓每個 Client ≥3 列；Letter：26 類），保留於 `REDESIGN_G1_DEGENERACY_FAILURES.csv`，未替換。

### 2.1 退化普遍性（`G1_DEGENERACY_PREVALENCE.csv`）
| 分布 | 含 TRUE 規則的配置 | 單類別 Client（/3） | 空約簡 Client | 全域規則數 |
|---|---:|---:|---:|---:|
| IID | 0% | 0.00 | 0.04 | 88.7 |
| α=0.5 | 21% | 0.23 | 0.27 | 72.9 |
| α=0.1 | **80%** | **1.33** | 1.34 | 51.5 |

### 2.2 Coverage／Conflict 分解（Outer Test，A_ALL_RULES）
| 分布 | Exact Coverage | **只靠 TRUE 規則命中** | Conflict | 排除 TRUE 後 Conflict | **TRUE 造成的 Conflict** | 正確候選只因 TRUE 才出現 |
|---|---:|---:|---:|---:|---:|---:|
| IID | 62.4% | 0 | 15.4% | 15.4% | 0 | 0 |
| α=0.5 | 79.9% | 5.6 pp | 30.1% | 23.6% | 6.5 pp | 4.3 pp |
| α=0.1 | 97.1% | **35.4 pp** | 61.5% | 18.6% | **42.9 pp** | 34.3 pp |

Development／Validation 分解幾乎相同（α=0.1：35.1／35.1 pp），所以這是規則結構性質，不是 Test 偶然。**過去 Non-IID 「Coverage 比 IID 高」的現象，主要是 TRUE 規則造成的。**

### 2.3 Balanced Accuracy（資料集為單位，Wilcoxon，Holm 於整張表）
| 分布・方法 | B vs A | B2 vs A |
|---|---|---|
| α=0.1 Simple Voting | +2.38 pp [0.48, 4.89] | **+2.72 pp [0.96, 5.13]**，Holm p=0.022 |
| α=0.1 Global Strength | +10.95 pp，Holm p=0.011 | **+11.30 pp [5.93, 17.24]**，Holm p=0.007 |
| α=0.1 Validation Best | +2.51 pp | **+2.85 pp [1.27, 4.89]**，Holm p=0.015 |
| α=0.1 原 Router | +1.85 pp | +2.21 pp，Holm p=0.034 |
| α=0.5 Validation Best | +0.27 pp（n.s.） | +0.47 pp（n.s. after Holm） |
| IID | 0（無 TRUE 規則） | 0 |

排除 TRUE 規則**不是**單純刪除：B 會讓 α=0.1 Coverage 從 97.1% 掉到 61.8%；B2 保留 Coverage（97.1%）同時把 Conflict 從 61.5% 降到 37.2%，BA 也最好。

### 2.4 六策略優劣是否改變？（`G1_POLICY_SPREAD_FRIEDMAN.csv`）
| 分布 | A：六策略最大差 | A：Friedman p | B2：最大差 | B2：Friedman p |
|---|---:|---:|---:|---:|
| α=0.1 | 9.02 pp（Simple Voting 最佳） | 0.0001 | 1.10 pp | **0.85** |
| α=0.5 | 3.74 pp | 0.16 | 0.85 pp | 0.12 |
| IID | 1.34 pp | 0.0003 | 1.34 pp | 0.0003 |

**原本 Non-IID 下「Simple Voting 最好、Global Strength 最差」的排序，大部分是各策略對 TRUE 規則的反應差異**（Global Strength 給 TRUE→d 規則極大的支持度分數）。處理掉 TRUE 規則後，α=0.1 六策略已無可偵測差異。IID 下仍有小但顯著的差異（Global Strength 最好，1.3 pp）。

### 2.5 α=0.5 與 α=0.1 的差異是否還存在？（`G1_ALPHA_GAP.csv`，Validation Best）
α=0.1 相對 IID：A 為 −6.62 pp [−10.21, −3.42]；B2 為 −3.77 pp [−6.22, −1.57]。**差距縮小約 43%，但仍顯著存在**。α=0.5 相對 IID 在 B2 下已不顯著（−0.13 pp）。

### 2.6 Control C（不同資料分配）
α=0.1 下 Control C 相對原始分割 +6.36 pp（Validation Best，p=0.0001），但同時：TRUE 規則降為 0、label skew TV 從 0.42 降到 0.33、平均需要 55 次重抽。這是「**換一個較不偏斜的聯邦**」的效果，不能當成規則處理演算法。

## 3. Gate 2：連續特徵離散化 — 完成

固定協定：17 份含連續特徵的 UCI 來源 × 10 Seeds × 3 分布 × 11 方法 = 5,610 模型，0 失敗；同一切分、同一 Client 分割、同一 Classical 約簡 + LEM2、A／B／B2 都在同一組規則上評估。

方法：等寬3/5、等頻3/5、穩健截尾3、MDLP（集中參考）、MDLP_HIST（Client 32 格類別直方圖加總）、ChiMerge（集中參考）、Rough Set 辨識切點 MD heuristic（Nguyen & Skowron，集中參考）、以及兩個**區間數配對對照**（EW／EF 使用與 MDLP_HIST 每特徵相同的區間數），用來分開「切點位置」與「區間數」。

### 3.1 相對等寬三區間（B2，Validation Best，Δ Test BA pp；IID / α=0.5 / α=0.1）
| 方法 | 是否聯邦可行 | Δ BA | 平均有效區間 | 規則數（α=0.1） | Dev 正域 |
|---|---|---|---:|---:|---:|
| RS 辨識切點（集中） | 否 | **+8.27 / +6.32 / +5.22** | 4.97 | 98.7 | 0.90 |
| ChiMerge（集中） | 否 | +6.71 / +5.10 / +4.95 | 5.20 | 57.6 | 0.65 |
| 等寬5 | 是 | +4.23 / +3.59 / +2.26 | 5.00 | 54.2 | 0.54 |
| 等頻5（集中分位數） | 否 | +4.21 / +3.43 / +2.69 | 4.68 | 86.0 | 0.78 |
| MDLP（集中） | 否 | +2.04 / +2.44 / +2.00（n.s.） | 2.57 | 26.0 | 0.41 |
| MDLP_HIST | 直方圖 | +1.21 / +2.26 / +1.26（n.s.） | 2.45 | 26.1 | 0.37 |

（完整數值、CI、表內 Holm 與全族 Holm（`holm_p_family`）：`G2G4_PAIRED_VS_EW3.csv`；成本：`G2G4_METHOD_SUMMARY.csv`。全族校正下，RS 辨識切點三個分布都顯著；ChiMerge 在 IID 與 α=0.1 顯著；等寬5、等頻5、MDLP 都不顯著。）

### 3.2 位置 vs 區間數（`G2_POSITION_VS_COUNT.csv`）
- **相同區間數**下，監督式位置（MDLP_HIST）比等寬位置高 +3.04 pp（IID，CI [0.36, 5.53]）、+2.20 pp（α=0.5）、+1.29 pp（α=0.1，CI 跨 0）。
- 區間數 3→5（等寬）：+4.23 pp（IID）、+3.59 pp（α=0.5）、+2.26 pp（α=0.1）。
- 區間數相近（≈5）時，RS 辨識切點位置仍比等寬5 高 +4.04／+2.73／+2.96 pp（全部 p≤0.003）。
- **MDLP 對 LEM2 系統性欠離散化**：MDLP 的停止準則為決策樹的單變量資訊增益設計，平均只留 2.5 區間，正域僅 0.37–0.41，Rough Set 規則歸納需要的可辨識性不足。

### 3.3 更細必然增加衝突嗎？——否（反例）
`G2_COUNTEREXAMPLES_FINER_VS_CONFLICT.csv`：在 510 組配對配置中，等寬5 比等寬3 的 Conflict（B，Test）**降低**的佔 15.7%、相同 13.9%、升高 70.4%；FED_MD 對等寬3 降低 11.4%。例如 Iris α=0.1 seed 11：66.7% → 43.3%。因此只能說「在本資料上通常增加」，**不能宣稱必然**。

### 3.4 成本（α=0.1，單模型平均，秒）
分箱建置 0.008（等寬）～2.4（RS 集中）～2.9（FED_MD）～10.4（LOCO）；約簡 0.68–1.03；LEM2 0.10–0.32；三個資料切分的比對 0.013–0.053。現在**分箱、約簡、歸納、比對時間分開記錄**，不再混稱「分箱成本」。峰值記憶體在另一次只跑 Seed 11 的 tracemalloc 量測中記錄（避免追蹤影響計時）：分箱＋歸納＋支持度建置的平均峰值為 0.6～1.1 MB，最大值 2.7 MB（`G2_PEAK_MEMORY_SEED11.csv`；561 個任務，0 失敗）。這只是 Python 物件配置量，不是處理程序 RSS，也不代表大規模部署需求。

## 4. Gate 3：雜訊與六策略 — 完成

### 4.1 標籤雜訊（只翻轉 Development 標籤）
真實：UCI20 × Seeds {11,101} × 3 分布 × 6 雜訊率 × {EW3, EW5} × {Classical, VPRS β=0.8, β=0.6} = 4,320 模型；合成（已知門檻、混合型特徵、平衡／70:20:10 偏斜）：1,620 模型；0 失敗。

- **合成資料證實經典正域崩潰**：平衡資料 Development 正域 0.81（0%）→ 0.19（5%）→ 0.02（15%）；Classical BA（IID, MDLP_HIST）0.98 → 0.89 → 0.61；VPRS β=0.8 維持 0.98–0.99。
- **真實 UCI20（EW3, Validation Best + B2）**：IID 15% 雜訊 Classical 0.575、VPRS β=0.8 0.620；α=0.1 15% 雜訊 0.492 vs 0.564。但 **0% 雜訊、α=0.1 下 VPRS β=0.8 反而較差**（0.577 vs 0.598）。
- **雜訊容忍與聯邦衝突的關係**：VPRS 放寬局部確定性後，規則覆蓋範圍擴大、跨 Client 重疊增加，Conflict 上升（α=0.5、0% 雜訊：Classical 21.1% → β=0.8 29.3% → β=0.6 35.4%）。可解釋的機制是：**局部容忍雜訊 = 接受局部不確定規則 = 擴大與其他 Client 規則重疊的區域**。這是取捨，不是單調改進；β 應被視為需在 Validation 上選擇的超參數，且 VPRS 不解決單類別 Client 退化（單類別 Client 的 β-正域在空集合上仍為全集，仍產生 TRUE→d）。

### 4.2 六策略的五類分解（固定規則，`G3_POLICY_FIVE_WAY_DECOMPOSITION.csv`，α=0.1 Test）
| 規則層 | 無命中 | 單一候選 | 多候選且正確解析 | 正確類存在但解析錯 | 多候選但正確類不在 | 單一候選但錯 |
|---|---:|---:|---:|---:|---:|---:|
| A（Simple Voting） | 2.9% | 35.7% | 36.9% | 20.2% | 4.3% | 12.9% |
| A（Global Strength） | 2.9% | 35.7% | 28.9% | **28.3%** | 4.3% | 12.9% |
| B2（Simple Voting） | 2.9% | 59.9% | 20.8% | 12.2% | 4.3% | 19.0% |
| B2（Global Strength） | 2.9% | 59.9% | 20.5% | 12.4% | 4.3% | 19.0% |

在 B2 之下，**任何解析器理論上最多只能再救回約 12% 的列**（「正確類存在但解析錯」），而六策略之間的差異只有約 0.2–1 pp。誤差的大宗轉移到「單一候選但錯」（19%）——也就是**規則本身錯**，不是解析器錯。依任務規定，在固定規則下解析器沒有可證明的獨立貢獻，因此**暫停六策略自適應選擇的研究**。

## 5. Gate 4：衝突感知切點原型 — 完成（含負面結果）

候選框架（不是既定定義）：
\[
\min_P\; \lambda_1 L_{\mathrm{decision}}(P)+\lambda_2 C_{\mathrm{global}}(P)+\lambda_3 K_{\mathrm{rules}}(P)+\lambda_4 T_{\mathrm{compute}}(P)
\]

### 5.1 三個設計（`fedrs/conflict_cuts.py`）
**設計 1 — FCP_HIST（一輪、直方圖）**
\(J_f(P)=H(D\mid I_P)/\log_2K+\lambda_2\hat C_f(P)+\lambda_3|P|\)，其中 \(\hat C_f(P)=\frac1N\sum_I\sum_c n_c(I)\,\mathbf 1[\text{c 在 I 局部純且另一 Client 在 I 局部純但類別不同}]\)。需要**每個 Client 的**直方圖（不能只傳加總），與單純安全加總不相容。

**設計 2 — LOCO_SELECT（規則回饋）**
對候選切點集合池 {EW3, EW5, EF_HIST3/5, MDLP_HIST, FCP_HIST, FED_MD_HIST}，每個 Client 用**其他 Client 的規則**預測自己的 Development 資料，回傳混淆矩陣與衝突／無命中計數；\(J=(1-\mathrm{BA_{LOCO}})+0.25\,\mathrm{Conf_{LOCO}}+0.05\log_2(1+|R|)/\log_2(1+N)\)。不使用 Validation 或 Test。

**設計 3 — FED_MD（Nguyen–Skowron MD heuristic 聯邦化）**
令 \(W(P)\) 為 \(P\) 與類別屬性無法分辨、但決策不同的物件對數（以合併的 Development 資料計）。
\[
W(P)=\underbrace{\sum_c W_c(P)}_{W_{\mathrm{within}}}+W_{\mathrm{cross}}(P),
\]
\(W\) 只需「每個格子各類別計數」的**跨 Client 加總**，\(W_{\mathrm{within}}\) 只需每個 Client 一個純量，所以 \(W_{\mathrm{cross}}\) 也可由加總型量計算。貪婪加入使 \(W_{\mathrm{cross}}+\mu W_{\mathrm{within}}\) 最小的共享網格切點；\(\mu=1\)（FED_MD_HIST）等於集中式 MD heuristic 限制在網格候選上；\(\mu=0.25\)（FED_MD_XC）優先消除跨 Client 不可辨識對——也就是讓局部確定規則在全域矛盾的那些物件對。

### 5.2 偽程式碼（FED_MD）
```
input: clients U_1..U_m (Development only), continuous F, categorical A, grid G=32, mu, max_intervals=6
server: collect global min/max per f -> shared grid edges; candidate cuts = interior grid points
cells <- joint code of categorical A                      # all rows start in their categorical cell
repeat:
  for each feature f with < max_intervals-1 cuts, each candidate c not chosen:
     each client c': send per-(cell x side(c) x class) counts  and  W_c'(trial)     # sums only
     server: W_total = sum over cells of (n^2 - sum_k n_k^2)/2 ; W_within = sum_c' W_c'
             score = (W_total - W_within) + mu * W_within
  pick (f,c) with minimal score (ties: feature order, cut value)
  if score does not decrease: stop
  add c to P_f ; cells <- refined cells
output: cut sets P_f
```

### 5.3 複雜度與通訊
- 時間：每輪評估 \(|F|(G-1)\) 個候選，每個候選對 \(n\) 筆做一次計數 → \(O(R\,|F|\,G\,n\log n)\)，\(R\le 5|F|\) 輪；實測 α=0.1 平均 2.9 秒（集中 MD 2.4 秒）。
- 空間：\(O(n+\text{cells}\cdot K)\)。
- 通訊（樸素協定上界）：每輪每候選回傳 cells×2×K 個整數；實測平均約 8.5×10⁶ 個數字／Client（`binning_communication_numbers_per_client`）。**這是本設計最大的實務缺點**；只傳「每個候選的 \(W\) 與 \(W_c\) 純量」可把通訊降到每候選 2 個數字，但伺服器就需要由 Client 端計算交叉項，需另行設計安全加總協定——尚未實作。
- 隱私：格子層級的列聯計數會暴露給聚合端；**沒有**安全聚合或差分隱私保證。
- LOCO_SELECT：每候選需完整規則交換，7 個候選平均 10.4 秒。

### 5.4 結果（17 份 UCI 連續來源 × 10 Seeds × 3 分布，B2，Validation Best，Δ vs EW3 pp；IID / α=0.5 / α=0.1）
| 方法 | Δ BA | 全族 Holm p（IID / α=0.5 / α=0.1） |
|---|---|---|
| RS 辨識切點（集中參考） | +8.27 / +6.32 / +5.22 | 0.001 / 0.027 / 0.033 |
| **FED_MD_HIST** | **+7.51 / +5.56 / +4.83** | 0.012 / 0.027 / **0.119（n.s.）** |
| FED_MD_XC（μ=0.25） | +7.61 / +5.80 / +4.74 | 0.002 / 0.009 / 0.279 |
| LOCO_SELECT | +6.22 / +4.80 / +3.71 | 0.279 / 0.225 / 0.476 |
| LOCO_SELECT **去掉衝突項** | **+7.99 / +5.72 / +4.30** | 0.009 / 0.054 / 0.209 |
| FCP_HIST | +2.81 / +3.23 / +2.66 | 1.0 / 1.0 / 1.0 |
| FCP_HIST 去掉衝突項 | +2.88 / +3.23 / +3.33 | 1.0 / 1.0 / 1.0 |

全族 Holm：同一規則層 × 解析方法內，全部 20 個方法 × 3 個分布（60 個檢定）一起校正（`holm_p_family`）。在這個較嚴格的校正下，FED_MD 於 α=0.1 的優勢**沒有達到顯著**；這也是 Gate 5 必須獨立確認的原因。

### 5.5 消融結論（如實的負面結果）
1. **直接懲罰衝突沒有幫助**：LOCO 去掉衝突項反而更好；FCP 有無衝突項沒有差別；FED_MD 強調跨 Client 對（XC）與 μ=1 沒有可區分差異。
2. 有效的是**保存全域可辨識性**：FED_MD 與集中式 RS 辨識切點只差約 0.4–0.8 pp，且它們的 Conflict 反而較高（α=0.1 B2：43.4% vs EW3 36.9%），但單一候選精確率較高（72.6% vs 65.9%）——**衝突率本身不是好的最佳化目標**；「讓候選集合含正確類、且單一候選更準」才是。
3. 相對 MDLP、ChiMerge、Classical LEM2：MDLP 是單變量資訊增益停止準則，對 LEM2 欠離散化；ChiMerge 是單變量 χ² 合併；FED_MD 是多變量、以 Rough Set 不可辨識對為目標，且可用加總計數聯邦化。Classical LEM2 本身未修改。

---

## 6. Gate 5：預先註冊確認性驗證

協定見 `PREREGISTRATION_CONFIRMATORY_20261116.md`（commit 89fd52b，早於任何完整確認性結果）與 `PREREGISTRATION_AMENDMENTS_20261116.md`（審查後、結果產生前的實作修正）。51 份 OpenML 來源（37 個家族）× Seeds 1001–1010 × 3 分布 × 7 方法 = **10,710 個任務，0 失敗**。

### 6.1 主要假設（Validation Best，Outer Test BA，資料集為單位）
| 假設 | 分布 | n | 基線 M0 | 候選 | Δ（pp） | 中位差 | 95% CI | 勝/平/負 | Holm p | rank-biserial | 判定 |
|---|---|---:|---:|---:|---:|---:|---|---|---:|---:|---|
| H1：M2 vs M0 | IID | 51 | 44.12 | 50.21 | **+6.09** | +1.63 | [3.91, 8.50] | 36/8/7 | <0.0001 | 0.84 | **PASS** |
| H1：M2 vs M0 | α=0.5 | 51 | 44.25 | 49.85 | **+5.60** | +2.13 | [3.64, 7.75] | 37/5/9 | <0.0001 | 0.82 | **PASS** |
| H1：M2 vs M0 | α=0.1 | 51 | 43.22 | 47.55 | **+4.33** | +1.75 | [2.91, 5.83] | 43/2/6 | <0.0001 | 0.89 | **PASS** |
| H2：M1 vs M0 | α=0.1 | 51 | 43.22 | 43.75 | **+0.53** | +0.24 | [0.17, 0.96] | 32/10/9 | 0.0007 | 0.61 | **PASS** |

家族層級敏感度（37 個家族，家族內先平均）：H1 三個分布仍全部通過（+6.67／+5.99／+5.11 pp，Holm p ≤ 0.0001）。

### 6.2 次要結果（描述性，不做優越性宣稱）
- **M3（跨 Client 加權）沒有比 M2 好**：IID −0.17、α=0.5 −0.25（未校正 p=0.013，反而較差）、α=0.1 −0.07 pp。→ 「特別懲罰跨 Client 衝突」的想法在新資料上也沒有得到支持。
- **M2 vs 集中式 RS 辨識切點 R1（方向更正）**：以下一律報告 **M2 − R1**：IID **−1.77 pp**（原表 R1−M2 = +1.77 pp；未校正雙尾 Wilcoxon p=0.0106），α=0.5 **−0.76 pp**（p=0.759），α=0.1 **−0.97 pp**（p=0.209）。三種分布的 R1 平均 BA 均較高；其中 IID 有未校正配對檢定證據。α=0.1 的平均差 bootstrap 95% CI 為 [−2.03, −0.08] pp（不含 0），但 Wilcoxon p=0.209，兩種方法結論不一致，只能說「平均方向偏向 R1，秩檢定未確認」；α=0.5 兩者都未排除 0（終版稽核補充，見 `FINALIZATION_REVISIONS_20261116.md`）。不得把「未達顯著」解讀為非劣性、等效或 FED_MD 較優。R1 為集中式參考，不能與真正聯邦部署直接畫上等號。
- **M2 vs MDLP_HIST（R2）與等寬5（R3）**：M2 在三個分布都高 1.8–4.9 pp（全部 p ≤ 0.0002）。所以增益不只是「區間變多」。
- **非 Rough Set 對照 CART**：
  - 集中式 CART（C1，非聯邦參考）在三個分布都比 M2 高 **4.6–7.2 pp**。
  - **聯邦 CART 投票（C2；方向更正）**：以下一律報告 **M2 − C2**：IID **−3.27 pp**（C2−M2 = +3.27 pp，95% CI [＋1.64,＋5.14] pp，未校正 p=0.00015）、α=0.5 **−2.08 pp**（C2−M2 = +2.08 pp，95% CI [＋0.84,＋3.46] pp，p=0.0031）；在 α=0.1 **+0.84 pp**（原表 C2−M2 = −0.84 pp，其95% CI [−1.72,+0.02] pp，p=0.098）。也就是 C2 在 IID／α=0.5 具有較高且可檢出的配對表現，α=0.1 則 M2 略高但未達顯著；這些都屬預註冊次要描述性比較，不可主張一般優越性。
- **TRUE 規則在新資料上再現**（EW3, A, Test）：α=0.1 有 68.6% 配置含 TRUE 規則；Coverage 82.5% 中 42.4 pp 只靠 TRUE 規則；Conflict 46.2% 中 35.2 pp 由 TRUE 規則造成。B2 把 α=0.1 Conflict 從 46.2% 降到 30.8%。
- **B2 對準確率的效果在新資料上明顯較小**：Validation Best +0.53 pp、Simple Voting +0.70 pp（探索性 UCI20 為 +2.85／+2.72 pp）。結構效果大、準確率效果小。
- **六策略差異**：在 51 份新資料上，A 下最大差 0.46–1.22 pp，B2 下 0.38–0.73 pp。Friedman p 仍可能 < 0.05（樣本大），但差距都在 1.3 pp 以內，實務意義很小。
- **成本**（α=0.1，單模型平均）：FED_MD 分箱 3.0 秒（等寬 0.009 秒）；規則數 145.9 vs 69.9；約簡 1.05 vs 0.96 秒；LEM2 0.55 vs 0.31 秒；樸素通訊上界約 7.7×10⁶ 個數字／Client。

### 6.2.1 方向一致的外部基準比較（合併前資料解讀修訂，未改原始數據）

下表固定方向為 **M2 − 比較方法**，正值代表 FED_MD_HIST + B2 平均較高；負值代表比較方法較高。來源：`data/G5_ARM_MEANS.csv` 及 `data/G5_SECONDARY_DESCRIPTIVE.csv`（原始 `mean_diff` 一律定義為 treatment − baseline，於 M2 作 baseline 時必須取負號）。單位為 **百分點（pp）**，與 H1／H2 的預註冊主檢定分開。

| 對照 | IID：M2−對照 | α=0.5：M2−對照 | α=0.1：M2−對照 | 結論 |
|---|---:|---:|---:|---|
| R1 集中式 RS 辨識切點 | −1.77 | −0.76 | −0.97 | R1 在三組平均均較高；IID 的 Wilcoxon 與 bootstrap CI 都支持；α=0.1 只有 bootstrap CI 不含 0（Wilcoxon p=0.21） |
| C1 集中式 CART | −4.55 | −4.91 | −7.22 | M2 均較差；C1 使用集中式 Development，不是聯邦對照 |
| C2 聯邦 CART 投票 | **−3.27** | **−2.08** | **+0.84** | IID／α=0.5 有配對差異證據；α=0.1 差異不顯著 |

**審計規則**：不可將「沒有顯著差異」寫成「一樣好」「不輸」或「已證明非劣」。原始 G5 表格和預先註冊文件完全不更動，這次是結論方向更正，未重新執行模型或選取超參數。

### 6.3 絕對水準的警告
所有方法的絕對 BA 都偏低（M2 約 47.6–50.2%，CART 54.8%）。原因是預先註冊的「前 6 個特徵、最多 1,800 列」規則：很多來源的前 6 欄資訊量很低（例如像素邊角、匿名欄位）。這個結果只表示「在相同的受限特徵條件下的相對比較」，**不代表這些方法在完整資料上的能力**。另有 6 份資料只有類別特徵，離散化對它們沒有作用（M2 與 M1 相同）。

### 6.4 結論的範圍
在本預註冊協定與這 51 份來源上：**FED_MD_HIST + B2 相對原始 EW3 + A 的提升已通過確認性驗證**；只修正規則層（B2）的提升也通過，但效果很小（約 0.5 pp）。這**不**表示它是一般最佳演算法：它仍輸給集中式 CART；相對聯邦 CART（C2），IID／α=0.5 平均較低（M2−C2 = −3.27／−2.08 pp），α=0.1 平均高 +0.84 pp 但未達顯著；通訊量高，且沒有隱私保證。（終版稽核更正此句，原句只描述 α=0.1。）


---

## 7. 七個問題的回答

### Q1. 我們之前究竟錯在哪裡？
**主要是實驗設計與結果解釋，不是 LEM2 本身寫錯。**
- 演算法層：Classical 約簡 + LEM2 的行為完全符合定義；單類別 Client 產生 TRUE→d 是正確的數學結果，不是 bug。問題在於 **UNION 把只在局部成立的確定性直接當成全域知識**。
- 實驗設計層：沒有記錄逐 Client 的類別組成、空約簡與空前件規則，因此看不到 Non-IID 下 Coverage／Conflict 的主要來源；歷史 Seeds 11／23 的 Test 被反覆使用。
- 解釋層：把「Non-IID Coverage 較高」「六策略在 Non-IID 下差異大」解讀為策略或資料特性的差別，但實際上大部分是各策略對 TRUE 規則的不同反應（§2.4）。離散化被當成次要因素，但它對準確率的影響其實比解析策略大一個數量級（§3、§6）。

### Q2. TRUE→d 對 Coverage、Conflict、Accuracy 的影響？
| 指標（α=0.1, Test, EW3） | 探索性 UCI20 | 確認性 OpenML51 |
|---|---:|---:|
| 含 TRUE 規則的配置 | 80% | 68.6% |
| Coverage 中只靠 TRUE 規則 | 35.4 pp（共 97.1%） | 42.4 pp（共 82.5%） |
| TRUE 規則造成的 Conflict | 42.9 pp（共 61.5%） | 35.2 pp（共 46.2%） |
| B2 對 Validation Best BA | +2.85 pp [1.27, 4.89] | **+0.53 pp [0.17, 0.96]**（預註冊 H2 通過） |
| B2 對 Global Strength BA | +11.30 pp | +2.08 pp [1.29, 3.01]（描述性） |
IID 下為 0（沒有單類別 Client）。結論：**TRUE 規則對 Coverage／Conflict 是一階效應；對最終準確率在新資料上是小而確定的效應**；對個別策略（尤其 Global Strength 類）影響很大。合理的處理不是直接刪除（B 會讓 Coverage 掉 35 pp），而是 **B2：把 TRUE→d 限定在「無任何具體規則命中」的區域，當作該 Client 的類別先驗**。

### Q3. 連續型資料是否需要特殊處理？什麼最有效？
需要，而且**離散化是本研究所有因素中影響最大的一個**。最有效的是**以 Rough Set 全域可辨識性為目標的多變量切點**（Nguyen–Skowron MD heuristic）及其聯邦版本 FED_MD_HIST：探索性 +4.8～+8.3 pp；確認性 M2 vs M1（同為 B2，只差離散化）+3.8～+6.1 pp。MDLP 對 LEM2 欠離散化；單純加區間（等寬5）有幫助但明顯較少（確認性 M2 比等寬5 高 2.5–4.7 pp）；在相同區間數下，切點位置本身也有影響（探索性 +1.3～+3.0 pp）。

### Q4. Classical Rough Set、LEM2 與六策略各自的實際貢獻？
以確認性 α=0.1 為例（Validation Best）：
- **離散化（EW3 → FED_MD，規則層固定 B2）**：+3.80 pp ——最大。
- **聯邦合併層（A → B2，離散化固定 EW3）**：+0.53 pp。
- **六策略之間**：在 B2 下最大差 0.38 pp；在固定規則下，任何解析器理論上最多只能救回「正確類存在但被解錯」的列（探索性 B2 約 12%），而六策略實際只差 1 pp 以內。
- **Classical Rough Set／LEM2 本身**：在相同受限特徵條件下，集中式 CART 比 M2 高 4.6–7.2 pp；聯邦 CART 投票在 IID／α=0.5 **平均優於 M2 +3.27／+2.08 pp**（C2−M2），α=0.1 則 **M2 平均高 +0.84 pp**（M2−C2；未達顯著）。因此本研究不能主張聯邦 Rough Set 相對聯邦 CART 有普遍優勢。
- **雜訊下**：Classical 正域對標籤雜訊非常敏感（合成資料 15% 雜訊時正域 0.81 → 0.02）；VPRS 可以容忍，但會增加跨 Client 衝突。

### Q5. 新方法是否優於既有基準？在什麼條件下？
- **相對原始基線（EW3 + A）**：是，已通過預註冊確認性驗證（51 份新來源、三種分布，+4.3～+6.1 pp）。
- **相對其他離散化（MDLP_HIST、等寬5）**：描述性上一致較好（全部 p ≤ 0.0002，但屬次要分析）。
- **相對集中式辨識切點參考**：R1 在三種分布的平均 BA 都較 M2 高（**R1−M2：IID +1.77、α=0.5 +0.76、α=0.1 +0.97 pp**）；IID 配對比較有未校正證據；α=0.1 僅 bootstrap CI 不含 0、Wilcoxon 未達顯著；α=0.5 未達顯著。未進行非劣性或等效檢定，故不得稱「不輸」。
- **相對 CART**：M2 在三種分布均落後集中式 CART；IID／α=0.5 亦落後聯邦 CART（C2）；只有 α=0.1 M2 平均領先 C2 +0.84 pp，但95% CI跨0、未達顯著。不可宣稱全面優於聯邦 CART。
- 「衝突感知」設計（FCP、LOCO 衝突項、FED_MD_XC 跨 Client 加權）在探索性與確認性資料上**都沒有帶來增益**——這是負面結果。真正有效的元素是「全域可辨識性」，而它是既有方法的聯邦化，**不能宣稱為新演算法**。
- 成立條件：前 6 特徵、≤1,800 列、3 Clients、Dirichlet α∈{0.5, 0.1} 或 IID、含連續特徵的資料（6 份純類別資料沒有差別）。

### Q6. 距離可投稿的新演算法還差哪些可驗證條件？
1. **新穎性**：FED_MD 本質上是 Nguyen–Skowron MD heuristic 的聯邦化；需要與 Wozniak et al.（2026）、Flores et al.（2026）及聯邦決策樹直方圖方法正面比較，並找出真正的新貢獻（目前最有可能的是「單類別 Client 退化的形式化 + B2 的局部適用範圍語意」，但 H2 的準確率效果只有 0.5 pp）。
2. **通訊與隱私**：目前樸素協定約 7.7×10⁶ 個數字／Client，且暴露格子層級計數。需要設計只傳純量的安全加總協定、量化通訊，並（若主張隱私）提供正式保證。
3. **理論**：證明或否證 FED_MD 在何種條件下保留全域正域，並給出近似保證（最佳切點問題為 NP-hard，見 Nguyen 1998）。
4. **規模**：解除「前 6 特徵、1,800 列」限制（需要非窮舉的約簡），測試更多 Client 數（5–50）、Client 數掃描與真實跨機構資料。
5. **更強的對照**：聯邦決策樹／梯度提升（FedTree 類）、聯邦規則學習（RIPPER 類），以及使用完整特徵的 CART。
6. **雜訊**：VPRS 與 FED_MD 的組合、β 的 Validation 選擇規則，需要另一次預註冊驗證。
7. **第二次確認**：本次確認性驗證的設計是由同一研究者在同一天完成；需要不同資料來源（例如另一個 benchmark suite）或獨立團隊重現。

### Q7. 完整成果與下一階段 Roadmap 在哪裡？
- 研究分支：`research/federated-rule-degeneracy-redesign-20261116`
- 本報告：`docs/research/redesign_20261116/RESEARCH_REPORT_20261116.md`
- 預註冊／修訂紀錄：`PREREGISTRATION_CONFIRMATORY_20261116.md`、`PREREGISTRATION_AMENDMENTS_20261116.md`
- 文獻與新穎性：`LITERATURE_AND_NOVELTY_20261116.md`
- 原始結果、Manifest、失敗紀錄：`docs/research/redesign_20261116/data/`
- 網站：`docs/research/teacher_dashboard/redesign/`（首頁導覽列「規則退化重建（11-16）」）
- 程式：`fedrs/`、`experiments/redesign_20261116/`；測試：`tests/test_fedrs_parity.py`、`tests/test_fedrs_units.py`；CI：`.github/workflows/redesign-fedrs-tests.yml`

**Roadmap**（依優先順序）：
1. R1（2 週）：FED_MD 純量化通訊協定 + 通訊實測；Client 數 3→5→10→20 掃描。
2. R2（2 週）：與 FedTree 類聯邦樹、Wozniak et al. 的聯邦 LEM2 設定、Flores et al. 的聯邦離散化做同條件比較。
3. R3（3 週）：非窮舉約簡（貪婪正域保留，已有 G8 原型）以解除 6 特徵限制，重跑確認性設計於完整特徵。
4. R4（2 週）：B2 的理論化（TRUE→d 作為局部先驗的語意、與 VPRS／機率近似的關係），並設計第二次預註冊驗證。
5. R5：若 R1–R4 仍顯示穩定增益，再撰寫投稿；否則把本研究定位為「聯邦 Rough Set 的失效模式分析與評估方法論」論文。


---

## 7.1 研究治理：來源家族獨立性證據的邊界

Gate 5 的 51 份資料來自 OpenML 預先篩選來源，**不是**「已經逐筆比對所有歷史原始樣本、證明51份與歷史161筆在資料來源層級完全獨立」。目前 E1 主要使用手工家族別名表、名稱與預先凍結的篩選規則；正式對外主張應為「在本研究既有來源名稱／人工別名排除規則下的新資料」，而不是絕對無同源。已整理可疑近似名稱及必要的人工來源檢核於 `SOURCE_INDEPENDENCE_REVIEW_20261116.md`。其中 `Fashion-MNIST` 與 `MNIST`、棋盤／分割等名稱部分重合目前**不能直接認定重複**，也不能僅憑名稱排除；若後續取得上游可比資料及來源鏈，需重新確認。

**終版稽核補充（post-hoc，2026-11-16）**：文獻與 OpenML metadata 顯示 `ada`（41156）很可能是 UCI Adult 的 ALvsPK 版本，`gina`（41158）很可能是 MNIST 子集；兩者的歷史對應來源都在 161 筆清單中，但 E1 名稱／別名規則沒有攔下。預註冊分析不改；排除這 2 份（或再加上未驗證的 `sylvine`）後，H1 三個分布與 H2 仍全部通過，效果略大（H1 +4.49～+6.51 pp）。見 `SOURCE_INDEPENDENCE_REVIEW_20261116.md` 終版補充與 `data/G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv`。

## 8. 限制

1. Gate 0–4 的 UCI20 來源已被本研究多次探索，結果僅為探索性。
2. 每份資料只用前 6 個特徵、最多 1,800 列（精確最小約簡可行性的限制）；不代表高維或完整規模表現。
3. 只有 3 個 Client；Dirichlet α 只有 0.5、0.1；沒有 Client 數掃描與真實跨機構資料。
4. 所有「HIST／FED」方法只是計數彙總；**沒有**安全聚合、差分隱私或通訊實測。FED_MD 的樸素通訊量很高。
5. 標籤雜訊只模擬均勻翻轉；未測類別相依雜訊與特徵雜訊。
6. B2 把 TRUE 規則當成「無證據時的類別先驗」；這是預測層的規則，不是新的歸納演算法。
7. 確認性驗證的機械式特徵規則可能選到無意義欄位（例如識別碼型欄位、像素邊角），E6b 也可能誤刪整數型非識別碼欄位；這些都在凍結前已知並記錄。
8. 一次 14 個任務的流程冒煙測試在凍結前執行（只涵蓋 1 份資料、1 個 Seed），已揭露；未因其結果修改任何設定。

## 9. 可重現性
- 程式：`fedrs/`、`experiments/redesign_20261116/`；測試：`tests/test_fedrs_parity.py`、`tests/test_fedrs_units.py`。
- 每張原始表都有 dataset、`source_sha256`、`split_id`、seed、regime、partition、discretizer、induction；每個實驗都有 `*_MANIFEST.json`（git commit、環境、成功／失敗數）與 `*_FAILURES.csv`。
- 新實驗輸出檔名一律以 `REDESIGN_`、`G1_`…`G5_`、`CONFIRMATORY_` 開頭，不與歷史基線共用檔名。
- 確認性原始資料只快取於 `data_cache/`（不提交、不再散布）；登錄表保存 OpenML MD5、raw 與 prepared SHA-256。
