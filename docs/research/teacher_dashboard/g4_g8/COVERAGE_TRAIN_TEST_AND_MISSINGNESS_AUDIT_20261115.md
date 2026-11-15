# G4／LEM2：Train–Validation–Test Coverage、資料缺失值、連續／類別型態之實證核對

**核對日**：2026-11-15
**凍結規則基準**：Classical Positive-Region Reduct + LEM2；Federated C3；UCI公開資料20份；Seeds 11、23；IID、Dirichlet α=.5、α=.1。
**重建範圍**：120 組完全重新歸納規則；與原 G4 原始紀錄的 Validation Coverage、Validation Conflict、Test Coverage、Test Conflict、Test Candidate Correct 逐配置相同（容忍數值四捨五入）；[執行來源校驗成功](https://github.com/Jimmy0307/LEM2/actions/runs/43678358638)。
**20資料集並非161來源都使用同一演算法設定**。161來源只做現有來源欄位稽核；原始UCI raw檔Missingness仍未逐一重掃，不能宣稱所有161筆沒有缺值或已完成同一處理流程。

## 1. 四個「Missing」絕對不能混用

| 名稱 | 數學／資料定義 | 實務現象 |
|---|---|---|
| Missing Data | CSV特徵欄沒有值、`?` 或其他可能代表缺值的標記 | 可使特徵辨識、離散化、規則前件受到影響，但要確認來源的資料字典 |
| No Match | 某個物件無法命中任何固定LEM2規則前件 | **不是資料缺失值**；物件可有全部特徵，但規則沒有覆蓋其組合 |
| Missing Client Class | Dirichlet Label Skew讓個別Client可能沒有某個決策類別的樣本 | 來源資料可完全沒有空值，但Client訓練規則仍有偏斜 |
| Conflict | 某筆物件命中至少兩種不同決策的規則 | 可與Coverage同時上升；六策略只負責衝突時決策，不直接改變原始命中集合 |

G4 最終仍會對 No Match 使用Development訓練多數類 Fallback，**不是 Reject／Abstain**。若要主張「資料缺失造成失敗」，必須控制其他條件做Missing值處理消融，不能從原始場景的資料名稱推斷。

## 2. 目前真正的 Train／Validation／Test 實驗關係

- 原始20個Prepared資料池，每份N先以種子固定20% Test；剩下80%再取80% Development、20% Validation；即 **64%／16%／20%**。
- 所有離散化邊界、約簡、LEM2規則及多數類Fallback只由Development學得。
- Validation只對固定規則評估，用於選六策略及決策路由參數。
- Test在所有選擇完成後測試一次。三組 Coverage **對相同 `R_development` 計算，不可用三組各自重新訓練過的規則**。
- 本輪 Test 的真實Decision只用於事後評估Accuracy／Correct Candidate及統計報表，**不參與策略選擇**。

\[
\operatorname{ExactCoverage}(S;R_{\mathrm{dev}})
=\frac{1}{|S|}\sum_{x\in S}\mathbf{1}\big[\exists r\in R_{\mathrm{dev}}:\operatorname{Ante}(r)\text{ 命中 }x\big].
\]

*精確Coverage是規則命中率，不是分類Accuracy。* 多條互相矛盾的規則也算命中；No Match則在缺乏命中時使用固定Fallback。

### 120組模型、各資料來源與Seed等權平均

| 分布 | Development（Train）Coverage | Validation Coverage | Test Coverage | Test Conflict | Test 正確類別候選率 |
|---|---:|---:|---:|---:|---:|
| IID | **62.928%** | 63.229% | 62.565% | 15.752% | 54.004% |
| Non-IID α=.5 | **80.916%** | 80.390% | 80.899% | 30.330% | 66.586% |
| Non-IID α=.1 | **97.462%** | 97.260% | 97.248% | **67.005%** | 82.541% |

同一資料、Seed與Train/Val/Test分割，改動的是Federated Client partition α與由此學出的不同規則，**Prepared缺值數量在三條分布路線中沒有改變**。因此 α=.1「高Coverage／高Conflict」不能歸因於同一資料在α=.1突然出現更多缺值。

在20來源平均，Train−Test Coverage 差距：IID **+0.363pp**、α=.5 **+0.017pp**、α=.1 **+0.214pp**。沒有發現對應 α=.5 策略下滑的總體大幅 Train–Test Coverage 崩落；但個別來源仍可能有較大的落差，應查看120行逐配置。

## 3. 特徵型態「資料集標籤」vs 真正選入模型的特徵

第一輪依 Registry 的 `feature_mode` 分類，誤把 `grid_stability` 計入混合型；此資料集的六個實驗特徵全為連續（tau1～tau4、p2、p3），Registry `EXPLICIT_MIXED` 是載入器設定而非該輪真正的特徵結構。

**更正後：14份全連續，3份全類別，3份混合**。依 `n_numeric_continuous`、`n_declared_categorical` 的實際入模選欄核對，並保留原Registry型態供追溯。

| 真正輸入型態 | 來源數 | α=.5 Router−ValidationBest BA | α=.1 Router−ValidationBest BA | α=.5 Test Coverage | α=.1 Test Coverage |
|---|---:|---:|---:|---:|---:|
| 全連續 | **14** | **−0.711 pp** | **−0.369 pp** | 77.996% | 96.421% |
| 全類別 | **3** | **+0.058 pp** | **−0.092 pp** | 78.538% | 98.352% |
| 混合 | **3** | **−0.589 pp** | **+1.849 pp** | 96.806% | 100.000% |
| **全20來源** | **20** | **−0.578 pp** | **+0.005 pp** | 80.899% | 97.248% |

**注意**：連續型特徵在本研究進入LEM2前由Development學得離散化區間（常用3 bins），最終規則並不是直接對原始浮點值做相等判定。若要說「連續型數值導致路由落後」，必須比較相同資料、相同Seed、不同Train-only binning設定的控制消融；此表只有資料家族間的探索性相關。

混合型只剩3份，受到 **Bank Marketing α=.1 +5.548pp** 的影響極大；連續型同時存在 **MAGIC α=.1 +9.822pp** 與 **Wine −7.222pp、Covertype −5.337pp** 的對立案例。不能用平均數直接制定「哪一型就選哪一策略」的因果規則。

## 4. 真正的缺值標記掃描結果：不是161原始來源的Raw Missingness

逐份掃描20個**研究實際使用的Prepared CSV**內所有特徵欄，區分空字串／NA／?／其他明示缺值標記，以及字面 `unknown` 類別：

| Prepared來源 | 實際使用Rows | 特徵欄位數 | 明示缺值／?標記格數 | 特徵格數中的標記比例 | 觀測欄位 |
|---|---:|---:|---:|---:|---|
| Adult Income | 1,800 | 6 | **224** | **2.074%** | workclass 112、occupation 112 |
| Bank Marketing | 1,800 | 6 | **88** | **0.815%** | education 79、job 9 |
| 其餘18份來源 | 各自來源大小 | 3–6 | **0** | **0.000%** | 在已選特徵與Prepared CSV未檢出定義內標記 |

這是讀取後的已處理來源檔掃描。Adult與Bank的標記可能是 `?` 等字元；這些在模型裡可能當作離散類別而不是空值直接丟棄。其他18份原始資料可能有缺值但被排除的欄位、前處理或抽樣遮蔽，**不能用本表否認上游缺失**。Mushroom 原始來源文字註記「missing」，但本輪六個Prepared特徵沒有檢出明示缺值標記，正是例子。

缺值標記存在與否**無法解釋單純改變 α 時同一份資料的 Coverage／Conflict變化**，因為Prepared值在α=.5與α=.1相同。另看兩份有標記來源：
- Adult α=.5 Router−ValidationBest **−1.059 pp**；α=.1 **0 pp**；
- Bank Marketing α=.5 **−0.887 pp**；α=.1 **+5.548 pp**。

因此目前尚未找到「Missing Data越多，Router一定越差」的穩定方向；缺值本身的因果影響尚需獨立介入測試。

## 5. α=.5 比ValidationBest差0.58pp，更直接的機制線索：路由Guard未允許切換

兩種方法**使用相同規則集合**，Test Coverage及原始Conflict在二者之間不會改變；差別是**如何根據Inner Validation選擇解析方法**：

- Validation Best：直接對整個Validation挑六方法之一，套用所有Test已命中情形。
- Conflict Bucket Router：先固定IID=GlobalStrength、NonIID=SimpleVoting；只針對「多種Decision同時命中」的衝突子群，至少10筆Validation衝突案例、至少2筆淨正確改善、Validation BA增加至少0.2pp、Accuracy loss限制≤0.5pp且最多2組接受切換。

| 分布 | 固定規則配置數 | Router未切換 | Router有切換 | ValidationBest選了非預設策略 | Router未切換而ValidationBest非預設 | Router−ValidationBest BA |
|---|---:|---:|---:|---:|---:|---:|
| IID | 40 | 35 | 5 | 29 | 25 | +0.352 pp |
| Non-IID α=.5 | 40 | **31** | **9** | **23** | **14** | **−0.578 pp** |
| Non-IID α=.1 | 40 | **27** | **13** | **15** | **2** | **+0.005 pp** |

在 α=.5 下，31/40的配置Router完全沒有切換；其中14組ValidationBest已選了不同於預設SimpleVoting的策略。相同40組中Router有切換的9組也不保證勝過ValidationBest。這是**比全資料集Missingness更直接且可核對的決策機制差異**。

在 α=.1 下，Router未切換的27組平均差−0.307pp，有切換的13組平均差+0.653pp，正負效應互相抵銷，造成總均值僅+0.005pp。個別極端正負大於平均：
- MAGIC Gamma連續型+9.822pp；
- Bank Marketing混合型+5.548pp；
- Wine連續型−7.222pp；
- Covertype連續型−5.337pp。

**重要限制**：這是由不同選法的已觀察決策結果與原程式Guard約束構成的**機制線索**，而非對Missingness、離散化或Guard門檻做受控消融後的因果證明。

## 6. 161筆全部來源的稽核邊界

| 研究批次 | 登錄 | 成功 | 有原始Rows | 有使用Rows | 有Raw來源SHA | 有Prepared SHA | 本輪做同一套G4測試 |
|---|---:|---:|---:|---:|---:|---:|---|
| PMLB117 | 117 | 109 | 117 | 109 | 109 | 109 | 否 |
| UCI20 | 20 | 20 | 20 | 20 | 0 | 20 | **是** |
| UCI12 | 12 | 12 | 12 | 12 | 0 | 12 | 否 |
| 極端7 | 7 | 7 | 7 | 7 | 0 | 7 | 否 |
| 電商／設備2 | 2 | 2 | 2 | 2 | 0 | 2 | 否 |
| 原始基線3 | 3 | 3 | 3 | 3 | 0 | 0 | 否 |

注意：
- 各批次的G4／G5／G8 Seeds、架構、原始特徵與實驗抽樣規格不同，不能直接合成一個161來源同條件選法效果。
- **PMLB** 原始表按固定 upstream commit＋SHA 已完成可重現來源核對，但本輪沒有重新分析每份原始 raw 缺值。
- **UCI20** 完成的是Prepared輸入掃描，不代表每份raw下載檔原生Missingness已知。
- **所有研究資料筆數**指跨批次登錄，包含同源／重複，並非161個互不相關的企業領域。

## 7. 下一步要對「原因」做真正的干預驗證

若要支持「連續性」或「缺失值」具有因果影響，至少用**相同來源與同Seed/Client分布**預先固定並比較：

1. 連續數值：固定規則歸納協定，Train-only binning使用2、3、5、10 bins或等頻策略；獨立Test檢驗Coverage、Conflict、BA與ValidationBest差距。
2. 缺失標記：先依官方資料字典確認 `?`、`unknown` 真正語義，只使用**Train擬合**的缺失類別保留／眾數補值／Missing指標（數值用Train中位數）；不對無缺值來源創造額外缺值。
3. Client Label Skew：同一Data、Seed但更換α；將Client類別缺失率、JS divergence、rule overlap、正確候選率納入中介與互動分析。
4. Router Guard：固定原始規則與Test，做保留原預設／放寬最小衝突樣本與切換次數／ValidationBest全域改選的消融；Test只用於事後指標，不能回頭調門檻。
5. 在不同資料家族與未見來源外測，對所有假設先訂門檻與多重檢定修正。

**不執行以上控制介入，不能正式回答「是Missing Data還是連續性造成」；本報告已經把能否定的不當因果推論與更直接的Router機制線索分開。**

## 機器可查核附件

- [20來源Prepared缺值標記／原始與實際特徵剖面](../data/G4_20_SOURCES_PREPARED_MISSINGNESS_PROFILE.csv)
- [120組同一固定規則Development／Validation／Test／Conflict／Candidate資料](../data/G4_TRAIN_VAL_TEST_COVERAGE_120_CONFIGS.csv)
- [60組資料來源×分布的策略與Coverage連結](../data/G4_TRAIN_TEST_TYPE_AND_SELECTOR_60_DATASET_SCENARIOS.csv)
- [真實14／3／3入模特徵型態分群表](../data/G4_SELECTOR_BY_FEATURE_TYPE_9_GROUPS.csv)
- [G4對ValidationBest路由切換機制40配對／分布](../data/G4_ROUTER_VS_VALIDATION_SWITCH_MECHANISM_20261115.csv)
- [161筆來源證據完整性表](../data/ALL_161_SOURCE_DATA_QUALITY_CENSUS.csv)
- [20資料來源樣本偏斜／Coverage／Conflict探索Spearman置換檢定](../data/G4_SELECTOR_EXPLORATORY_ASSOCIATIONS.csv)
- [全部來源／同規則／Split驗證Manifest](../data/G4_COVERAGE_TYPE_MISSINGNESS_MANIFEST.json)
- [原始實驗的1,080筆六策略與新Router逐配置](../data/G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv)
- [重用120組實驗Artifact的核對流程PASS](https://github.com/Jimmy0307/LEM2/actions/runs/43678358638)
