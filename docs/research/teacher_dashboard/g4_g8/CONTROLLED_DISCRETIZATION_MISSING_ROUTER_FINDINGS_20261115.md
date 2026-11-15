# 連續型資料是否需要額外離散化？——A/B/C 三因子控制消融實驗

**驗證日**：2026-11-15  
**研究分支**：`research/report-ready-dashboard-20261109`（沒有更動 `main` 與已封存42 Seeds基準）  
**實測來源**：UCI 20份可重現的Prepared資料，總表161筆仍保留原研究批次，不可當161個獨立來源合併推論。  
**原始歸納**：Classical positive-region minimum-cardinality reduct + LEM2、Federated C3（三個Client）、原始六種衝突解析策略。  
**固定重複配置**：Seeds **11、23**，Non-IID Dirichlet α=0.5 / α=0.1，64% Development / 16% Inner Validation / 20% Outer Test；同一Seed/Client配置內單獨更動一種因素，原始三分箱重建和前一批G4 1080筆來源驗證完全一致。

> **結果判定**：計算、資料來源SHA與固定Split完整性均PASS；「更高Test BA」並不等於「降低Conflict」「低成本」或「已建立普適自動離散化演算法」。本頁列出正、負結果並保留每一配置，不以Test挑選部署模型。

## 一、為何三區間等寬法可能不適合某些連續特徵？

現有`roughset/preprocessing.py`從Development/Client Training的每個連續特徵取最小與最大，**預設等寬三區間**，交給Classical Rough Set/LEM2歸納。此做法不依決策類別最佳化切點，亦不能保證各區間樣本數適當。

兩類失敗機制可能並存：
- **欠離散化**：真實可分的數值範圍被合併到同一個符號，可能增加不同類別的不可辨識性、降低規則候選品質。
- **過度離散化**：切得太細導致規則數／規則合併重疊／Client間衝突升高，可能造成運算成本和泛化不穩。

**Missing Data、No Rule Match、Conflict、正確候選在命中規則中與否、分類正確率**分別是不同概念，不能只看Coverage或規則數推論分類好壞。

### A 線：連續值分箱單因子干預

計算共 **420** 個真實來源模型：17份含入模連續特徵（14份全連續、3份混合），每份於2 Seeds×2 Client 分布下比較6種方法；3份全類別資料只保留原三區間對照。每個模型實際測原始六策略、Validation Best、Conflict Bucket Router，總 **3,360** 筆來源鎖定的解析效果。

| 方法 | 主要差異 | 是否使用Test值建立邊界 |
|---|---|---|
| **Equal Width 2** | 等寬2個區間 | 否 |
| **Equal Width 3** | 原始封存基準 | 否 |
| **Equal Width 5** | 等寬5個區間 | 否 |
| **Equal Frequency 3** | Development上以3等頻分箱；大量重複值可能合併切點 | 否 |
| **Equal Frequency 5** | Development上以5等頻分箱；大量重複值可能合併切點 | 否 |
| **Robust Width 3** | 以Development第1–99百分位截尾後切3等寬區間 | 否 |

**重大Federated界限**：等頻和穩健截尾在本研究模擬流程中使用Development階段的**跨Client彙總數值**；目前未實作安全分位數聚合、隱私保護或Client端通訊協定。因此其效果不能直接宣稱適合隱私隔離的真實聯邦部署；仍需額外Federated Protocol和隱私證明。

### A線固定方法：14份「實際選入全連續」資料，衝突路由器不變

| Client Label Skew | 分箱方法 | Train/Val/Test Exact Coverage (%) | Test Conflict (%) | Test Balanced Accuracy (%) | 平均規則數 | 結構建置秒數 |
|---|---|---|---:|---:|---:|---:|
| α=.5 | **等寬3（原始）** | 78.29 / 77.95 / 78.00 | 27.47 | **63.06** | 30.1 | 1.82 |
| α=.5 | 等寬2 | 66.86 / 67.77 / 67.87 | 19.21 | 53.66 | 9.9 | 0.79 |
| α=.5 | 等寬5 | 88.62 / 88.65 / 88.50 | 35.90 | **66.17** | 65.3 | 3.48 |
| α=.5 | 等頻3 | 93.66 / 93.46 / 93.45 | 41.39 | 63.86 | 62.0 | 3.35 |
| α=.5 | 等頻5 | 96.41 / 96.46 / 96.33 | **48.82** | 65.68 | **119.9** | **6.07** |
| α=.5 | 穩健3 | 88.91 / 89.45 / 89.06 | 36.42 | 65.15 | 38.8 | 2.24 |
| α=.1 | **等寬3（原始）** | 96.41 / 96.46 / 96.42 | 62.34 | **56.12** | 25.7 | 1.73 |
| α=.1 | 等寬2 | 93.46 / 93.67 / 93.78 | 53.45 | 52.76 | 6.9 | 0.62 |
| α=.1 | 等寬5 | 99.72 / 99.78 / 99.58 | 73.09 | 57.35 | 55.1 | 3.38 |
| α=.1 | 等頻3 | 98.44 / 98.41 / 98.59 | 75.98 | 57.88 | 42.5 | 2.66 |
| α=.1 | 等頻5 | 99.25 / 99.43 / 99.34 | **78.44** | **59.18** | 87.8 | **5.11** |
| α=.1 | 穩健3 | 97.69 / 97.70 / 97.75 | 68.73 | 58.64 | 30.9 | 2.00 |

**發現**：
1. 更細的分箱常可改善Test BA：α=.5等寬5比等寬3約 **+3.11pp**；α=.1等頻5約 **+3.06pp**。這是**現有資料的跨來源描述均值**，非外部一般化保證。
2. 更多bins不保證高效：α=.5等頻5由平均 **30.1條規則增加至119.9條**，結構建置時間由 **1.82秒增加至6.07秒**；Test Conflict同時從 **27.47%升至48.82%**。
3. Coverage上升不等於Conflict下降；α=.1本來Test Coverage已96.42%，等頻5升至99.34%，但Conflict從62.34%升至**78.44%**。
4. 等寬2的分類明顯變差，顯示**過粗分箱導致資訊流失**也是值得測量的風險；但本研究未直接提供每個區間的因果可辨識性證明。

### 真正可實施的選法：只讓Inner Validation選擇分箱，再測Outer Test

每份來源、Seed、Client配置，用**六種分箱的Validation路由Balanced Accuracy**選出一個（平手優先原始等寬3），再用封存Test驗證；不使用Test挑分箱方法。

| 入模型態／Label Skew | 資料來源數 | 選到非原始分箱的配置比例 | Test BA相對等寬3 | Test Coverage變化 | Test Conflict變化 |
|---|---:|---:|---:|---:|---:|
| **全連續、α=.5** | 14 | 82.14% | **+6.310 pp** | **+15.749 pp** | **+11.439 pp** |
| **全連續、α=.1** | 14 | 78.57% | **+6.374 pp** | +1.821 pp | **+12.873 pp** |
| **混合、α=.5** | 3 | 83.33% | +0.981 pp | +3.056 pp | +2.231 pp |
| **混合、α=.1** | 3 | 16.67% | **−1.239 pp** | 0 pp | +0.324 pp |
| **全類別（兩種α）** | 3 | 0% | 0 pp | 0 pp | 0 pp |

全連續14來源先按兩個Seeds平均後做**資料集分群探索性Bootstrap**：
- α=.5 BA **+6.310pp**，95%區間 **[+2.794,+10.415]pp**；10來源改善、2來源變差、2相同。
- α=.1 BA **+6.374pp**，95%區間 **[+2.301,+10.984]pp**；9來源改善、5來源變差、0相同。

**不能宣稱全部資料會改善**。混合資料 α=.1甚至有負效應；全連續的Breast Diagnostic α=.5、Iris α=.1等資料也可能因Validation對小樣本的偶然性而退步。

**統計與實作界限**：
- 只有2 Seeds，使用的是已探索的20份來源；分群Bootstrap是探索性，不是已事先註冊的確認檢定。
- 同一Validation既用來學路由切換，又用來選擇分箱模式，可能有二次選擇過擬合；需要額外的內層切分、交叉驗證或獨立來源確認。
- 分箱方法的CPU時間僅為此研究小規模特徵與規則處理；**不等於**保有數千Client與700GB部署能力。
- 如果在新資料集先看Test排名再決定要用哪個分箱，那是Test Oracle，不能當成可部署演算法。

## 二、B線：Missing Data不是當前主要改善槓桿

研究只針對實際已選特徵含明示標記的兩個Prepared來源（**Adult 224格、Bank Marketing 88格**）；其它18份Prepared檔無標記不代表原始UCI完全無缺值。

3個方案在同一原始Train／Validation／Test和Client划分下執行：**保留標記作獨立類別**、**只用Development學習每欄眾數補值**、**保留標記另加二元Missing Indicator特徵**。2來源×2Seed×2α×3方法＝**24** 組模型、192筆解析結果。

| 來源與分布 | 原始保留標記 Test BA | Development眾數補值 BA | 保留類別+Indicator BA |
|---|---:|---:|---:|
| Adult α=.5 | **67.041%** | **65.952%**（−1.089pp） | **67.041%** |
| Adult α=.1 | **59.852%** | **59.669%**（−0.182pp） | **59.852%** |
| Bank Marketing α=.5 | **50.865%** | **50.303%**（−0.562pp） | **50.865%** |
| Bank Marketing α=.1 | **56.705%** | **56.076%**（−0.629pp） | **56.705%** |

**解讀**：本輪只有2個受測來源、各兩Seeds，沒有見到眾數補值穩定改善G4路由；額外指示特徵與原本保留缺值標記完全相同，因為前者本來就能由保留標記決定，屬資訊上冗餘的欄位。這不是「Missing永遠不重要」的證明，更不能從Prepared值猜測所有上游Raw缺值。

## 三、C線：Router的Guard參數會影響分類，但單改Guard不夠

固定**原始等寬3**的規則與預測候選，不重新歸納；只在Validation更改規則衝突的局部策略切換門檻。

| 門檻 | NonIID α=.5 Test BA | 相對ValidationBest（pp） | NonIID α=.1 Test BA | 相對ValidationBest（pp） |
|---|---:|---:|---:|---:|
| 固定SV完全不換 | 60.265% | −1.261 | 53.320% | −2.309 |
| **原始G4** | **60.948%** | **−0.578** | **55.633%** | **+0.005** |
| **放寬Guard** | **60.989%** | −0.536 | **56.437%** | **+0.809** |
| 加嚴Guard | 60.929% | −0.596 | 54.644% | −0.984 |

**解讀**：
- α=.1放寬Guard對原始G4改善約 **+0.804pp**，比ValidationBest高0.809pp。
- α=.5放寬Guard只比原始G4 **+0.041pp**，仍低於ValidationBest **0.536pp**。
- 這說明過嚴門檻有影響，但**不能用單純放寬全部門檻完全解決α=.5選法落後**。需要把特徵處理和Conflict條件納入更完整的選擇框架，並建立獨立外測。

## 四、對演算法方向的決策

### 不是直接改「一律五分箱」，而是建立受控的離散化選擇層

建議保持原 **Classical reduct + LEM2 + 六策略**不變，前面加入可配置的**Continuous Discretization Candidate Generator**：

1. **Data profiling**：Development-only範圍、有效唯一值、重複值、類別數、極端值、Client分布。
2. **候選分箱**：等寬3（永遠保留的Baseline）、等寬5、等頻3/5、穩健3；不要使用Test統計量。
3. **Inner Validation評估**：不只有BA，同時記錄 **Exact Coverage、Conflict、規則數、耗時、正確候選率**。
4. **Risk budget**：只接受符合BA改善下限、Conflict額外增量、規則數和資源預算的選法；若證據不足回退等寬3。**此項多目標Risk Gate尚未完成預註冊與外測，不要宣稱已獲證明**。
5. **Policy router**：在最終選定的固定規則集合上執行Conflict-aware六策略解析，與B線缺值處理分離；再次只用Validation選參數。
6. **Test once**：封存選法後只做最後一次未見Test評估，並保留所有原始資料、SHA、配置、Seed及CI receipts。

如果論文要主張新演算法，可能是**資料分布、離散化切分、規則衝突與策略選擇的共同最佳化**；但單純等頻或類別熵切點是已有研究，必須做嚴謹的公平比較和形式化機制說明。

### 已有先行研究（不可當原創）

- Fayyad, U. M., & Irani, K. B. (1993). *Multi-Interval Discretization of Continuous-Valued Attributes for Classification Learning*. IJCAI, pp.1022–1028. [正式會議頁](https://ijcai.org/proceedings/1993/141) — 以分類熵與最小描述長度原則選擇連續特徵切點。本輪**未實作MDLP**。
- Kerber, R. (1992). *ChiMerge: Discretization of Numeric Attributes*. AAAI. [正式會議頁](https://new.aaai.org/Library/AAAI/1992/aaai92-019.php) — 已有依類別統計訊號進行離散化的思路。本輪**未實作ChiMerge**。

後續若要進一步研究，可增加Train-only監督式MDLP、ChiMerge，或Rough Set正域／衝突成本感知切點，而不是只延伸固定等寬與等頻分箱。

## 五、全部資料、統計與重跑紀錄

- [來源完整性與全局狀態](../data/CONTROLLED_CONTINUOUS_MISSING_ROUTER_MANIFEST.json)
- [A 3,360筆原始六策略＋ValidationBest＋Router分箱測試](../data/CONTROL_A_ALL_DISCRETIZATIONS.csv)
- [A 固定同Seed／Client分布的每方法配對差值](../data/CONTROL_A_PAIRED_TO_EQUAL_WIDTH_3.csv)
- [A 分組Train／Validation／Test Coverage及模型資源耗時](../data/CONTROL_A_BINNING_OUTCOMES_GROUPED.csv)
- [A 80組Inner Validation選分箱後的獨立Test結果](../data/CONTROL_A_VALIDATION_SELECTED_TREATMENT.csv)
- [A 14／17／20資料來源分群Bootstrap](../data/CONTROL_A_PROSPECTIVE_DATASET_BOOTSTRAP.csv)
- [B 192筆Missing處理、原始與替代模式](../data/CONTROL_B_MISSING_TREATMENTS.csv)
- [C 320個Guard對照及來源Seed](../data/CONTROL_C_ROUTER_GUARDS.csv)
- [A/C全部20來源實際運算PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43718630891)
- [B兩資料來源實際運算PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43718834462)
- [A/B/C從原始Artifacts核對並發布PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43719970031)

**本輪完成的是受控分箱與解析策略消融，未包含無條件部署、原始全維資料、隱私保護分位數通訊、正式MDLP／ChiMerge、形式化新算法創新性證明。**
