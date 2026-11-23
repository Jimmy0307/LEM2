# LEM2「能階／反曲線」假說：證據分級與研究判讀

> **探索性；非物理相變的證明，也非事先註冊的臨界點檢定。**  
> 42-seed primary snapshot 2026-11-23 11:42:29（Asia/Taipei），179/188 完整資料集；規則版本 A_ALL_RULES，固定 STANDARD_VOTING。所有表格沒有公開 SHA256 等內部驗證欄位。

## 1. 我們是否看到資料量增大、衝突反而下降？

**有跨資料集規模關聯，但不是因果證據。** 對 `FED_A01 − CENTRALIZED` 的 Conflict Rate：

| 原始資料集 Rows | 完整資料集 n | ΔConflict pp | 聯邦自身 Conflict % | ΔAccuracy pp | 聯邦 Conflict ≥50% 的資料集數 |
|---|---:|---:|---:|---:|---:|
| <500 | 43 | +75.86 | 78.37 | −8.98 | 42 |
| 500–4,999 | 84 | +55.07 | 56.36 | −6.63 | 53 |
| 5,000–49,999 | 39 | +42.21 | 42.42 | −5.24 | 17 |
| ≥50,000 | 13 | +13.22 | 13.23 | −4.44 | 1 |

Spearman（Rows vs Conflict Δ）= **−0.704**（179 dataset-level samples）。控制 cohort、feature type、n_classes、minority share、feature retention 後，對 `log10(original_rows)` 的線性係數約 **每增加 10 倍 Rows，Conflict Δ 下降 14.52 pp**；dataset-bootstrap 95% interval 約 **[−18.52, −10.79]**。這是描述性／敏感度結果，區間未處理所有同源家族依賴，不能將係數解釋為增加資料量造成的效果。

**不是實際運算降載的證明。** Conflict *rate* 下降時，Test rows 的絕對數量可能增加；規則數及規則匹配計算成本、wall-clock、VRAM/CPU 都是不同指標。本輪無法用這條線直接聲稱服務成本下降。

## 2. 有沒有可報告的轉折閾值（Change Point）？

比較調整協變項的線性模型與「一個轉折點」的 piecewise-linear（hinge）模型。轉折點僅在訓練 folds 搜尋，5-fold CV ×3 repeats 於 held-out datasets 計算 RMSE。

| 場景 | 探索候選 Rows cut | 候選 cut bootstrap IQR | 線性 RMSE (pp) | Hinge RMSE (pp) | 勝出證據 |
|---|---:|---|---:|---:|---|
| FED_IID | 約 3,751 | 1,324–3,770 | 13.94 | 13.70 | 幅度較小 |
| FED_A05 | 約 **3,751** | 1,458–3,771 | 16.26 | 15.28 | **值得追查**，但仍是探索性的  |
| FED_A01 | 約 7,200 | 1,664–8,237 | 14.95 | 14.93 | **不足以主張有尖銳轉折** |

- α=0.5 的分段模型有約 0.98 pp RMSE 減少（約 6%），但 cut 是 data-driven、隨 resample 浮動，不能說「3,751 Rows 是確定門檻」。
- α=0.1 的 cut 雖然最佳樣本內約 7,200 Rows，**out-of-sample RMSE 只改善約 0.02 pp**。這更支持**平滑規模效應（scale dependence）**，而不是已證實的臨界能階。
- 50,000+ Rows 僅有 13 個完整資料集，其他大型 OpenML 仍有 TIMEOUT／未完成，推論易有樣本選擇偏差。

## 3. 同一來源逐層加大資料，會不會有真正的反曲線？

已有舊的 [SCALE_LADDER.csv](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/docs/research/full_scale_20261118/SCALE_LADDER.csv)，以 seed 1001 在約 1,800、10,000、FULL Rows 比較。這些子集**不保證嚴格 nested**，也未固定完全相同 Test rows；因此適合探索訊號，不足以確立因果的非單調性。

使用 **每相鄰區間超過 1.0 pp** 才算明確向上／向下；共有 22 個 A01 配置三點俱全：

| α=0.1 指標 | 持續下降 | 持續上升 | 先升後降（peak） | 先降後升（valley） | 平臺／單段變化 |
|---|---:|---:|---:|---:|---:|
| Conflict Rate | 9 | 2 | **4** | **1** | 6 |
| Accuracy | 1 | 3 | **2** | **6** | 10 |
| Coverage | 3 | 0 | 2 | 2 | 15 |

- **OpenML #1486（nomao）**：Conflict **52.22 → 100.00 → 0.87%**；Accuracy **78.33 → 71.45 → 28.57%**（1,800 → 10,000 → 34,465 Rows）。此案例說明 Conflict 下降不保證 Accuracy 回升。
- **UCI bank_marketing**：Conflict **100.00 → 69.35 → 0.15%**；Accuracy **88.33 → 18.55 → 88.30%**（約 1,800 → 10,000 → 45,211 Rows）。Accuracy 表現為 valley。
- **PMLB sleep**：Conflict **24.93 → 33.05 → 7.87%**（1,800 → 10,000 → 105,908 Rows），為 Peak 型案例。

不同判定容忍度可能改變形狀計數：0.1 pp 門檻和 1.0 pp 門檻會導致分類不同，不能將單一分類當成客觀自然界線。

## 4. 不是只有 Rows；類別數可能造成不同的 regime

用固定 STANDARD_VOTING、A01−Centralized，比較完全配對資料集：

| 類別數 | n | Mean Accuracy Δ (pp) | Mean Conflict Δ (pp) |
|---|---:|---:|---:|
| 2 類 | 103 | −7.86 | +62.53 |
| 3–5 類 | 42 | −11.74 | +58.33 |
| ≥6 類 | 34 | **+2.88** | +23.98 |

這是值得研究的反例：**在 ≥6 類資料集，α=0.1 的 Accuracy 平均反而高於 Centralized**（注意是固定 STANDARD_VOTING 而非事後挑選方法）。但是同源資料集存在，例如 PMLB mfeat 同系列，且多類型資料集往往也有不同 Rows／特徵，因此不能斷言「增加類別數可以改善聯邦準確率」。

一個更有機制意義的組合變數是 **每類別有效訓練筆數（rows / classes）**，甚至是 **每個 client × class 的最少有效支持數**。目前原始 Rows/class 尚未充分代表聯邦客戶端不均分造成的支持問題；後者必須從逐 seed 客戶端輸出才能確認。

## 5. 研究假說與驗證順序

**H1：規模效應**。更多有效樣本可以降低 rule overlap / conflict vulnerability。已有跨來源關聯，待 nested-scale 驗證。

**H2：稀疏與空前件規則的相變**。當 client-class support 低於某些值，單類 client、empty reduct、TRUE→decision 可能突然變多，進而提高 coverage 與 conflicts。這是**假說**，不應因為 B2 有改善就直接認定成因。需量測 TRUE-rule count、empty reduct、client-class min support、規則重複／衝突來源。

**H3：非單調績效不是單一 Conflict 指標可以解釋**。需要 class-wise recall、confusion matrix、candidate correctness、no-match default rate、rule count 和投票 tie-break 共同診斷。

**H4：計算成本與預測衝突率不等價**。必須另外量測 CPU time、peak RSS/VRAM、規則比對次數、資料量與 timeout；不能從 Conflict Rate 下降推論運算成本下降。

### 建議可驗證的小規模實驗

固定 6–10 個代表性來源（包含 2 類／多類、小型／大型、純連續／離散、典型下降／peak／valley）；每來源至少 5 個 seeds；同一 seed 固定外層 Test、內層 Val 與已選特徵，訓練集以 class-stratified **nested prefixes** 逐層增加（僅跑對該來源可行的 Row budget：例如 500、1,800、5,000、10,000、25,000、FULL）；同時比較 IID／α=0.5／α=0.1、A／B2。

請保留 source-family held-out、bootstrap 及多次 seeds，並於確定候選 cut 後使用未參與 cut 選擇的新 seeds 或來源驗證，避免從同一批資料選出並證明門檻。

## 原始計算與重現

- [分組四級與分位數](./SIZE_REGIMES_179.csv)
- [Size quantile 連續趨勢](./SIZE_QUANTILES_179.csv)
- [控制變數／CV breakpoint](./EXPLORATORY_CHANGEPOINT_CV.csv)
- [單來源三階曲線](./WITHIN_SOURCE_SCALE_LADDER_1SEED.csv)
- [曲線形狀統計](./LADDER_SHAPE_COUNTS.csv)
- [Spearman 描述性關聯](./SPEARMAN_DESCRIPTIVE.csv)
- [計算腳本](../../../../../../tools/expanded_resume_20261122/analyze_conflict_regimes_20261123.py)

**研究判定：目前證實跨資料集的規模關聯與少量單來源非單調例子；尚未找到具穩定 out-of-sample 支持的 α=0.1 銳利臨界點。**
