# 20 個新公開資料集：Training Coverage 增強之實測與研究邊界

**審核狀態：ALL_20_ONE_SEED_PASS。** 總計 UCI 不重複公開來源 **20/20 成功**，單一 Seed 42、Classical 正域約簡＋LEM2、集中式及 Federated C3、每配置 NONE＋六策略：**280 列**；Train-only 補充規則兩架構 A/B：**40 列**。未改動原有三資料集 8,820 筆 42 Seeds 主矩陣。

## 1. 研究範圍

- 公開來源及授權：20 份 UCI ML Repository 來源；保留官方連結、公開資料集特徵契約、原始／實際使用筆數、分層子集檔及 SHA-256。授權來源聲明為 CC BY 4.0，衍生子集需標示出處。
- 六策略比較：First Match、Simple、Standard、Global Strength、Population Standard、Population Global；**同資料集／Client 數／Seed 的六策略共享相同規則集合**。
- 先導只使用 Seed **42**，資料由 UCI 抓取後依標籤固定分層抽樣，最多 **6 個特徵**，80/20 stratified train/test，訓練／離散化與約簡完全不看測試標籤。
- 原來源大小可達 **Covertype 581,012 筆**、Adult Income 48,842 筆、Bank Marketing 45,211 筆，但模型實際輸入均是來源的固定子集。**不屬於 581k 原始全量的運算效能檢驗**。
- 研究目標：一筆物件有至少一條規則前件命中即算 rule-set match coverage，與最後是否預測正確、正確標籤是否在候選決策中、真正拒判機制等區分。
- 補充規則是作者定義的**簡化單一前件刪除**，最多使用原規則前 240 條產生候選；Train purity≥90%、Min Support≥5、最多保留 80 條，僅對原規則 No Match 物件產生最終判斷。**不是 Inuiguchi–Washimi 原典補充規則，也不是 VC-DomLEM**。

## 2. 二十個來源的結果（兩學習架構等權平均）

**以下是單一 Seed 42 的描述性數字**，每個資料集集中式、Federated C3 各執行一次。欄位依序為原來源／模型子集、Training 與 Test 原始 Exact Coverage／補充後 Coverage，後兩欄則是相對 Global Strength 原預測的變動（pp）。

| 資料集／官方來源 | 原始 → 實驗筆數 | 原 Train | 補充 Train | 原 Test | 補充 Test | Accuracy Δ | Balanced Accuracy Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| [adult_income](https://archive.ics.uci.edu/dataset/2) | 48,842 → 1,800 | 87.12% | 90.90% | 86.53% | 89.86% | +0.14 pp | +0.29 pp |
| [bank_marketing](https://archive.ics.uci.edu/dataset/222) | 45,211 → 1,800 | 47.15% | 82.67% | 50.42% | 83.75% | +0.00 pp | +0.00 pp |
| [banknote](https://archive.ics.uci.edu/dataset/267) | 1,372 → 1,372 | 57.42% | 65.94% | 56.75% | 65.33% | +4.20 pp | +4.79 pp |
| [breast_diagnostic](https://archive.ics.uci.edu/dataset/17) | 569 → 569 | 70.61% | 97.59% | 71.68% | 97.35% | -1.33 pp | -0.08 pp |
| [covertype](https://archive.ics.uci.edu/dataset/31) | 581,012 → 1,800 | 28.28% | 29.33% | 33.52% | 34.35% | +0.00 pp | +0.00 pp |
| [dry_bean](https://archive.ics.uci.edu/dataset/602) | 13,611 → 1,600 | 19.40% | 24.79% | 19.28% | 24.45% | +4.86 pp | +4.87 pp |
| [eeg_eye_state](https://archive.ics.uci.edu/dataset/264) | 14,980 → 1,800 | 11.32% | 14.58% | 8.89% | 11.25% | +0.97 pp | +1.08 pp |
| [german_credit](https://archive.ics.uci.edu/dataset/144) | 1,000 → 1,000 | 74.06% | 83.19% | 71.00% | 79.75% | +0.00 pp | +0.00 pp |
| [grid_stability](https://archive.ics.uci.edu/dataset/471) | 10,000 → 1,800 | 78.47% | 85.31% | 84.03% | 90.28% | +1.11 pp | +1.62 pp |
| [haberman](https://archive.ics.uci.edu/dataset/43) | 306 → 306 | 24.69% | 24.69% | 29.51% | 29.51% | +0.00 pp | +0.00 pp |
| [htru2](https://archive.ics.uci.edu/dataset/372) | 17,898 → 1,800 | 23.78% | 100.00% | 24.17% | 100.00% | +0.28 pp | +1.52 pp |
| [iris](https://archive.ics.uci.edu/dataset/53) | 150 → 150 | 97.08% | 100.00% | 100.00% | 100.00% | +0.00 pp | +0.00 pp |
| [letter](https://archive.ics.uci.edu/dataset/59) | 20,000 → 900 | 93.73% | 93.73% | 84.62% | 84.62% | +0.00 pp | +0.00 pp |
| [magic_gamma](https://archive.ics.uci.edu/dataset/159) | 19,020 → 1,800 | 7.81% | 11.56% | 8.47% | 12.08% | +1.94 pp | +3.29 pp |
| [mushroom](https://archive.ics.uci.edu/dataset/73) | 8,124 → 1,600 | 98.95% | 100.00% | 99.06% | 100.00% | +0.00 pp | +0.00 pp |
| [phishing](https://archive.ics.uci.edu/dataset/327) | 11,055 → 1,600 | 17.93% | 17.93% | 18.44% | 18.44% | +0.00 pp | +0.00 pp |
| [rice](https://archive.ics.uci.edu/dataset/545) | 3,810 → 1,600 | 55.63% | 72.73% | 57.50% | 74.06% | +2.03 pp | +2.46 pp |
| [sonar](https://archive.ics.uci.edu/dataset/151) | 208 → 208 | 26.65% | 26.65% | 21.95% | 21.95% | +0.00 pp | +0.00 pp |
| [spambase](https://archive.ics.uci.edu/dataset/94) | 4,601 → 1,800 | 1.81% | 1.81% | 1.67% | 1.67% | +0.00 pp | +0.00 pp |
| [wine](https://archive.ics.uci.edu/dataset/109) | 178 → 178 | 87.32% | 89.44% | 88.89% | 88.89% | +0.00 pp | +0.00 pp |

各資料集權重一致（不按筆數加權）後：
- **15/20** 資料集的 Train Match Coverage 提高；**13/20** 的 Test Match Coverage 提高。
- **8/20** Accuracy 提高、**1/20** 下降、**11/20** 無變化。Balanced Accuracy 的正／負／無變化筆數亦為 8／1／11。
- Train Coverage 平均變化 **+10.18 pp**；Test Coverage **+9.56 pp**；Accuracy **+0.71 pp**。這只是 20 個資料集單 Seed 和兩架構等權的探索性敘述，不是估計母體平均效果或統計顯著性。

## 3. 最值得解釋的機制案例

### HTRU2：Coverage 幾乎全部救回，但 Accuracy 增益非常有限

Train 23.78% → 100%；Test 24.17% → 100%；Accuracy +0.28 pp，BA +1.52 pp。這可能是補充規則大多仍選原本多數類別，或者少數正類辨識不足。需核對逐筆新增命中物件、與原本 fallback 是否同決策、真正的 positive recall。

### Bank Marketing：Test Coverage +33.33 pp，但 Accuracy 完全不變

Train 47.15% → 82.67%；Test 50.42% → 83.75%；Accuracy +0.00 pp。單靠「規則可以命中」無法證明增加決策效益，應在逐筆 audit 區分沒有改變類別 vs. 原先 fallback 及新規則同答。

### Breast Diagnostic：Test Coverage 增加卻使 Accuracy 下降

Train 70.61% → 97.59%；Test 71.68% → 97.35%；Accuracy **−1.33 pp**，BA **−0.08 pp**。提高 Training Coverage 不是無成本，更不能取代泛化驗證；醫療研究資料不可以作臨床部署推薦。

### Banknote、Dry Bean 與 Rice：值得再驗證的增益候選

- Banknote：Test Coverage +8.58 pp；Accuracy +4.20 pp；BA +4.79 pp。
- Dry Bean：Test Coverage +5.17 pp；Accuracy +4.86 pp；BA +4.87 pp。
- Rice：Test Coverage +16.56 pp；Accuracy +2.03 pp；BA +2.46 pp。

### Phishing、Spambase、Sonar、Haberman：純度門檻無法有效擴充

此固定純度與一條件刪除方式沒有帶來 Coverage 提升；有可能是規則前件太短、單條件放寬後 purity 低於 90%、原樣本太稀疏或候選限制所致。需要記錄 proposal rejection reasons 才能驗證，不能猜成唯一原因。

## 4. 對教授的可檢驗假設

1. **H1 覆蓋不足並不等於選擇策略差**：當 Test No Match 極高時，六種策略無法從不存在的匹配候選中選答案；Train-only 補充規則是候選機制的改善，而非 Winner 排序改善。
2. **H2 訓練覆蓋改善應以未見資料驗證**：用同一份模型同時量 Train/Test Match Coverage、候選涵蓋率、BA、Accuracy、False Positive、稀有類別召回。
3. **H3 規則擴充有代價**：補充規則純度、支持數與規則長度可能影響 Test 類別誤判；不能只追求 Coverage=100%。
4. **H4 資料生成情境造成方法異質性**：離散、連續、混合、多分類、類別不平衡、時間序列、來源大樣本，需要使用資料集階層的效應統計；單 Seed 不足以證明一般性。
5. **H5 演算法擴展性需要獨立驗證**：超過十萬列來源的固定抽樣測試，只代表能取得來源並執行小樣，不證明 exact reduct 在 581k 全量可解；需另測 sample-size ladder、時間、記憶體、停止條件與近似約簡。

## 5. 文獻根據與學術邊界

- [Inuiguchi & Washimi (2015)](https://doi.org/10.20965/jaciii.2015.p0747)：對 MLEM2 補充規則與完全無匹配物件的分類改進（本研究只做簡化 heuristic）。
- [Cohen (1995), RIPPER](https://doi.org/10.1016/B978-1-55860-377-6.50023-2)：規則覆蓋、效率與雜訊資料；本批未將完整 RIPPER 當比較法。
- [VC-DomLEM (2011)](https://doi.org/10.1016/j.ins.2010.10.030)：可變一致性與循序覆蓋的規則歸納，與本研究目前的 Classical 不是同一演算法。
- [Ziarko (1993), Variable Precision Rough Sets](https://doi.org/10.1016/0022-0000(93)90048-2)：在不精確資訊下放寬粗糙近似的一致性設定，供後續方法線使用。
- [El-Yaniv & Wiener (2010)](https://jmlr.org/papers/v11/el-yaniv10a.html)：正式拒判的 Risk–Coverage 權衡。**目前 No Match 依然採 Train Majority fallback，不等於真正的拒判事件。**

## 6. 下載、來源與證據

- [20 個來源逐條註明的 Manifest](../data/PUBLIC20_MANIFEST.json)。
- [20 份來源抽樣資料 CSV](../../public_datasets_20/)；[授權說明](../../public_datasets_20/README.md)。
- [280 列正式分類結果](../data/PUBLIC20_BASE_RESULTS.csv)；[240 列各策略整合指標](../data/PUBLIC20_POLICY_SUMMARY.csv)。
- [40 列補充規則 A/B](../data/PUBLIC20_SUPPLEMENT_RESULTS.csv)；[20 組配對平均](../data/PUBLIC20_SUPPLEMENT_SUMMARY.csv)。
- [六策略資料集內的 Winner 次數與平票](../data/PUBLIC20_POLICY_WINS.csv)。
- [GitHub Actions: 真正下載與運算](https://github.com/Jimmy0307/LEM2/actions/workflows/public-20-uci-coverage-benchmark.yml)；[20 來源最終驗證](https://github.com/Jimmy0307/LEM2/actions/workflows/public20-finalize-reuse-artifacts.yml)。

**停止條件**：20 源 20/20、每資料集 14 原規則輸出＋2 補充輸出、來源子集 SHA、Train/Test 及 no-match 分母合理，無效不得補零。下一輪以 42 Seeds、內部驗證選參及資料集層級分群比較，證明適用條件，而不直接把此單 Seed pilot 當方法優越性結果。
