# 確認性驗證預先註冊（Gate 5）— 凍結於執行前

**凍結時間**：2026-11-16（本檔案以 git commit 固定；確認性結果檔晚於此 commit 產生）
**狀態**：在任何確認性來源上執行任何模型之前撰寫。以下設定不得依確認性結果修改；若必須修改，須另立版本並標記為探索性。

## 1. 資料
- 來源：`data/CONFIRMATORY_SOURCE_REGISTRY.csv` 中 `status = ELIGIBLE_PREPARED` 的 51 份 OpenML 資料（37 個來源家族），規則 E1–E6b 機械化套用；排除與失敗（含 `albert` HTTP 500、兩份數值缺值 >5%）全數保留，不替換。
- 本研究過去使用的 161 份來源家族全部排除（E1 對照表見 `confirmatory_registry.py`）。
- 同家族（`nasa_mdp` 6 份、`automl_challenge` 12 份）保留但標記；主分析以資料集為單位，敏感度分析以家族為單位（家族內先平均）。
- 已知限制（凍結前已知）：前 6 個特徵規則為機械式，可能取到無意義欄位（例如 Diabetes130US 的 `patient_nbr`、像素邊角）；E6b 可能誤刪整數型非識別碼欄位（steel-plates V3/V4/V8）。

## 2. 協定
- Seeds：**1001–1010**（10 個，從未用於本研究）。
- 切分：外層 80/20 Test（seed）、內層 80/20 Validation（seed+1000），分層。
- 聯邦：3 Clients；IID（分層）、Dirichlet α=0.5、α=0.1（原始分割器，不使用 Control C）。
- 歸納：Classical 最小基數正域約簡 + LEM2（原始程式）；UNION。
- 解析：六策略；Validation Best（Inner Validation BA，平手依原 POLICY_ORDER）；原 G4 Conflict Bucket Router。

## 3. 比較方法（全部凍結）
| 代號 | 離散化 | 規則層 | 角色 |
|---|---|---|---|
| M0 | EQUAL_WIDTH_3 | A_ALL_RULES | 原始基線 |
| M1 | EQUAL_WIDTH_3 | B2_TRUE_AS_FALLBACK | 僅規則層修正 |
| **M2** | **FED_MD_HIST**（μ=1，32格，≤6區間） | **B2_TRUE_AS_FALLBACK** | **主要候選** |
| M3 | FED_MD_XC（μ=0.25） | B2 | 跨Client加權消融 |
| R1 | RS_DISCERNIBILITY_CENTRAL | B2 | 集中式參考（非聯邦） |
| R2 | MDLP_HIST | B2 | 既有監督式（直方圖） |
| R3 | EQUAL_WIDTH_5 | B2 | 區間數對照 |
| C1 | CART_CENTRAL（深度由 Validation 選） | — | 集中式非 Rough Set 參考 |
| C2 | CART_FED_VOTE（每 Client 一棵樹，機率平均） | — | 聯邦非 Rough Set 對照 |

所有方法 A/B/B2 規則變體都會輸出，但假設檢定只使用上表指定組合。

## 4. 主要終點與假設
- 主要終點：Outer Test Balanced Accuracy，解析方法為 **VALIDATION_BEST**。
- 統計單位：資料集（10 seeds 先平均）。檢定：雙尾 Wilcoxon signed-rank；Holm 校正於 H1 三個 regime 一族、H2 一族；95% CI：10,000 次資料集 bootstrap。效果量：平均差、中位差、rank-biserial、勝/平/負。
- **H1**（主要）：M2 − M0 > 0，分別於 NONIID_01、NONIID_05、IID（Holm, m=3）。
- **H2**：M1 − M0 > 0 於 NONIID_01（m=1）。
- 判定：某假設「通過」需 Holm p < 0.05、平均差 > 0、且 bootstrap CI 下界 > 0。

## 5. 次要（描述性，不做優越性宣稱）
M3 vs M2；M2 vs R1/R2/R3；M2 vs C1/C2；SIMPLE_VOTING 與 Router 下的同樣比較；Coverage／Conflict／TRUE 規則分解；B2 下六策略 Friedman；家族層級敏感度；失敗率。

## 6. 成功條件與限制
- 只有 H1 於兩個非 IID regime 都通過，才可說「在本預註冊協定與這 51 份來源上，M2 優於原始基線」。不可推論為一般最佳演算法、隱私安全或可部署。
- 任何失敗配置計入失敗率並列出；不重跑換 seed。
- 任何未預先列出的分析一律標示為探索性。
