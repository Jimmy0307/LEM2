# 聯邦 Rough Set 規則退化與衝突：研究方法重建報告

**分支**：`research/federated-rule-degeneracy-redesign-20261116`（起點 87e31c4；未改動原研究分支、已發布 CSV、42 Seeds 基線；未合併 `main`）
**日期**：2026-11-16
**證據等級**：Gate 0–4 全部為**探索性**（UCI20 已探索來源；Seeds 11、23 為歷史重複使用、101–108 為新增探索 Seeds）。Gate 5 為**預先註冊**的確認性驗證（51 份未使用 OpenML 來源，Seeds 1001–1010）。

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

（完整數值、CI、Holm p：`G2G4_PAIRED_VS_EW3.csv`；成本：`G2G4_METHOD_SUMMARY.csv`。）

### 3.2 位置 vs 區間數（`G2_POSITION_VS_COUNT.csv`）
- **相同區間數**下，監督式位置（MDLP_HIST）比等寬位置高 +3.04 pp（IID，CI [0.36, 5.53]）、+2.20 pp（α=0.5）、+1.29 pp（α=0.1，CI 跨 0）。
- 區間數 3→5（等寬）：+4.23 pp（IID）、+3.59 pp（α=0.5）、+2.26 pp（α=0.1）。
- 區間數相近（≈5）時，RS 辨識切點位置仍比等寬5 高 +4.04／+2.73／+2.96 pp（全部 p≤0.003）。
- **MDLP 對 LEM2 系統性欠離散化**：MDLP 的停止準則為決策樹的單變量資訊增益設計，平均只留 2.5 區間，正域僅 0.37–0.41，Rough Set 規則歸納需要的可辨識性不足。

### 3.3 更細必然增加衝突嗎？——否（反例）
`G2_COUNTEREXAMPLES_FINER_VS_CONFLICT.csv`：在 510 組配對配置中，等寬5 比等寬3 的 Conflict（B，Test）**降低**的佔 15.7%、相同 13.9%、升高 70.4%；FED_MD 對等寬3 降低 11.4%。例如 Iris α=0.1 seed 11：66.7% → 43.3%。因此只能說「在本資料上通常增加」，**不能宣稱必然**。

### 3.4 成本（α=0.1，單模型平均，秒）
分箱建置 0.008（等寬）～2.4（RS 集中）～2.9（FED_MD）～10.4（LOCO）；約簡 0.68–1.03；LEM2 0.10–0.32；三個資料切分的比對 0.013–0.053。現在**分箱、約簡、歸納、比對時間分開記錄**，不再混稱「分箱成本」。峰值記憶體另以 tracemalloc 量測（見 §8）。

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
| 方法 | Δ BA | Holm p（α=0.1） |
|---|---|---:|
| RS 辨識切點（集中參考） | +8.27 / +6.32 / +5.22 | 0.001 |
| **FED_MD_HIST** | **+7.51 / +5.56 / +4.83** | 0.003 |
| FED_MD_XC（μ=0.25） | +7.61 / +5.80 / +4.74 | 0.007 |
| LOCO_SELECT | +6.22 / +4.80 / +3.71 | 0.016 |
| LOCO_SELECT **去掉衝突項** | **+7.99 / +5.72 / +4.30** | 0.005 |
| FCP_HIST | +2.81 / +3.23 / +2.66 | 0.29（n.s.） |
| FCP_HIST 去掉衝突項 | +2.88 / +3.23 / +3.33 | 0.10（n.s.） |

### 5.5 消融結論（如實的負面結果）
1. **直接懲罰衝突沒有幫助**：LOCO 去掉衝突項反而更好；FCP 有無衝突項沒有差別；FED_MD 強調跨 Client 對（XC）與 μ=1 沒有可區分差異。
2. 有效的是**保存全域可辨識性**：FED_MD 與集中式 RS 辨識切點只差約 0.4–0.8 pp，且它們的 Conflict 反而較高（α=0.1 B2：43.4% vs EW3 36.9%），但單一候選精確率較高（72.6% vs 65.9%）——**衝突率本身不是好的最佳化目標**；「讓候選集合含正確類、且單一候選更準」才是。
3. 相對 MDLP、ChiMerge、Classical LEM2：MDLP 是單變量資訊增益停止準則，對 LEM2 欠離散化；ChiMerge 是單變量 χ² 合併；FED_MD 是多變量、以 Rough Set 不可辨識對為目標，且可用加總計數聯邦化。Classical LEM2 本身未修改。

---

## 6. Gate 5：預先註冊確認性驗證

（見 §6 結果段，由 `analyze_g5.py` 依預註冊產生。）

GATE5_RESULTS_PLACEHOLDER

---

## 7. 七個問題的回答

GATE7_ANSWERS_PLACEHOLDER

---

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
