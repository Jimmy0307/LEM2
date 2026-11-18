# G4–G8 核心缺口補強｜第一輪實際執行結果（2026-11-18）

**狀態：工程與探索性回溯分析 PASS；正式新確認性研究、規則補充的全新干預及真實高維完整外測仍未完成。** 不能將本檔當作已通過的全新學術驗證或新演算法論文。

- 研究來源：`research/federated-rule-degeneracy-redesign-20261116` @ `006dbe8`（PR #6，未合併）
- 本輪分支：`research/g4-g8-closure-20261118`
- [GitHub Actions 首輪（21測試通過，原始G5回溯及高維工程Smoke PASS）](https://github.com/Jimmy0307/LEM2/actions/runs/44258223134)
- [7個回溯表與Manifest的Artifact](https://github.com/Jimmy0307/LEM2/actions/runs/44258223134/artifacts/14407325610)，有30日保留期限；原數據不因此變更。
- 執行協定：[EXECUTION_PROTOCOL.md](./EXECUTION_PROTOCOL.md)

## 1. 老師要求：六策略／Non-IID／自適應

**重要更正**：先前「六個固定方法的跨資料集平均差小」不等於「對單一資料使用Validation挑策略沒有任何效益」。回溯51個來源×10 Seeds固定任務，先對同一來源的10 Seeds平均，再對51來源等權；沒有新增資料，也沒有做新顯著性檢定。

### ValidationBest − 歷史固定法之 Test BA（pp；探索性）

| 分布 | EW3 + B2 | FED_MD + B2 | 固定方法 |
|---|---:|---:|---|
| IID | −0.0321 | −0.1458 | GS |
| α=0.5 | +0.5852 | +2.0133 | SimpleVoting |
| α=0.1 | +0.5329 | +1.4845 | SimpleVoting |

**判讀**：Non-IID下存在值得獨立再驗證的模型選擇效益，且其幅度可能隨離散化方法不同而改變；不能因此宣稱新的Meta-Router或正式預註冊比較成功。與「六固定法的平均排名差距」不同，以上是逐配置以Validation選法後的真實Test平均差值，前提是Validation有真實標籤。

### 每配置六策略最高與最低 Test BA 差距，再按來源平均（pp；Test Oracle，不可部署）

| 分布／分箱 | 原始A | B2 | B_DROP_TRUE |
|---|---:|---:|---:|
| IID／EW3 | 1.9246 | 1.9246 | 1.9246 |
| IID／FED_MD | 4.4319 | 4.4319 | 4.4319 |
| α=.5／EW3 | 2.8019 | 2.4660 | 2.4490 |
| α=.5／FED_MD | 5.7069 | 5.1996 | 5.1979 |
| α=.1／EW3 | 3.5693 | 1.8976 | 1.6793 |
| α=.1／FED_MD | 6.7281 | 3.5955 | 3.3499 |

**判讀**：在α=.1下，B2明顯壓低六策略可產生的結果離散幅度，但FED_MD+B2每配置仍有約3.60pp最高−最低差異。這不是「可以從Test挑最佳法」的效益估計，也不是新顯著性證據。它與報告中的「六方法**整體平均**最多差0.4pp」是不同統計量，不應混用。

## 2. 老師要求：提升 Coverage、降低 NoMatch／Rejection

已交付可執行的 **互斥五類診斷** `fedrs/closure_diagnostics.py`：NO_MATCH、TRUE_ONLY、CANDIDATE_MISS、CONFLICT_RESOLVABLE、SINGLE_CORRECT。這個分類不會假裝「命中TRUE」就是具體的分類規則，也不會把NoMatch叫做已執行的Rejection。

### 已發布 Gate5 Test 的重算（α=.1，51來源等權、探索性回溯）

| 分箱＋規則後處理 | Rule Coverage | Conflict | True-in-Candidates |
|---|---:|---:|---:|
| EW3 + 原始 UNION | 82.50% | 46.24% | 65.37% |
| EW3 + B2 | 82.50% | 30.76% | 58.80% |
| EW3 + 刪除 TRUE | 40.07% | 11.07% | 26.01% |
| FED_MD + UNION | 88.60% | 63.57% | 76.44% |
| FED_MD + B2 | 88.60% | 39.22% | 66.64% |
| FED_MD + 刪除 TRUE | 63.03% | 23.39% | 44.92% |

**非常重要**：表中 Coverage 依變體定義為「至少一條規則命中」；A/B2可以把TRUE作為候選，因此不是 `strict_nonempty_coverage`。當TRUE被刪除，其下降才揭示嚴格非空規則命中占比。B2降低Conflict但也會降低Candidate Correct，不宜將後者視為負面數據而遮蔽。

以前20來源的補充規則控制消融早已觀察到：集中式有效Coverage約+13.17pp、BA+1.58pp；聯邦有效Coverage約+2.39pp、BA−0.015pp。這支持「Coverage提升不必然帶來聯邦BA增益」，但**不是此輪新實驗**。

**仍需的真正補強**：新來源受控S0基線、S1明確Abstain、S2 Train-only補充、S3 Validation-only守門、S4 FED_MD+B2干預；主要終點須事先固定All-Test BA、minority recall、candidate coverage與selective risk，並與固定原始規則同切分比較。不應繼續只調投票公式。

## 3. 老師要求：G7形式化與G8高維

- 形式結果：單類Client空約簡→TRUE，屬已知經典結構；全域Support只知道Local資料與Remote匹配上界時，conf界為 `[s/(m+u),(s+u)/(m+u)]`，已有可執行單元測試；這不是BA保證或學術首創。
- **B2反例 PASS**：對 `TRUE→P` 與 `x→N`，若True=P，原A在預設P平手情況可對而B2錯；若True=N，反向成立。不能主張無條件B2支配A。
- Dirichlet公式測試 PASS，但僅適用 `p_c ~ Dirichlet(α)`且Client內標籤iid的生成機制；原始類別分配機制不同，公式**未**獲准解釋當前α=.1的68.6%純Client配置。
- **合成工程規模Smoke**：240筆；5、8特徵Greedy與Exact cached確實同最小約簡；12／24特徵Greedy均達完整Train POS，但**沒有**同維Exact最佳性、規則歸納、外部Test BA及大規模效能證據。
- 真實G8現有82組POS／CPU、36組低維exact配對、16組完整LEM2配對，不等於20+特徵的同條件全流程外測。

### 本輪CI

| 項目 | 實際 |
|---|---|
| 新單元／命題反例與補充規則測試 | **24 passed** |
| G5源資料51×10回溯對照 | **PASS** |
| B2/A六策略與Coverage分析 | **PASS** |
| 合成5/8/12/24約簡Smoke | **PASS**
| 合成3/5/10 Client補充規則干預 | **18/18 PASS，但ΔBA全部0pp（負面結果）** |
| 原G5數據／預註冊未改寫 | **PASS** |
| 真實高維全LEM2模型與更多Clients | **尚未執行** |
| 真正新的確認性試驗與投稿新穎性 | **尚未通過** |

## 3.1 新增 Client × 補充規則控制實驗：18組合成測試（負面結果）

另以固定新合成資料生成器跑 **2 Seeds×3 分布×3／5／10 Client＝18個設定**；每個設定使用完全一致的 Development／Validation／Test與EW3規則，受控比較原B2與「只用Development Client類別計數篩選的單前件放寬Supplement」。預設最低Train support=5、purity≥0.90，補充規則不覆蓋原有非空規則的預測。此處統計是新合成資料的**探索性實驗**，不是新增真實外部來源的確認性證據。

- **18／18任務成功，0失敗；沒有出現Test BA改善，全部平均 ΔBA=0pp。** 
- 本次合成資料的原始嚴格非空規則 Coverage 已經很高（IID全部100%、多數Non-IID 100%、α=.1且3 Client為95.24%），所以可救的未命中空間有限。
- α=.1、10 Clients的兩個 Seeds 平均已有 **7個單類別Client**；α=.1、3 Clients平均1個；再次顯示純類別Client與分割規模有關，但兩個Seeds不能推論一般機率。
- 這個負面結果只能證明實作在指定合成環境沒有觀察到Supplement效益，**不能**推論在真實來源必然無效，更不能宣稱規則補充已完成學術驗證。
- 聚合Client類別計數只是模擬交換資訊，仍**沒有Secure Aggregation或DP**；「Client-local計數」不代表隱私安全。
- 此次生成器的來源分布、任務難度與NoMatch比例過於簡單。下一輪應改在有明顯Original NoMatch的**真實來源**做固定的同分割干預，並將高Coverage來源作negative control。

[最新24測試PASS及18組Supplement實驗CI](https://github.com/Jimmy0307/LEM2/actions/runs/44258932143)；[全部10個輸出檔Artifact（30日保留）](https://github.com/Jimmy0307/LEM2/actions/runs/44258932143/artifacts/14407805826)。

## 3.2 新增20份真實UCI來源的同切分補充規則控制：120／120成功（探索性）

> **此處是新的程式實驗，但來源20份及Seeds11/23已在歷史G4研究中用過。不是新的獨立確認性驗證。**

使用 GitHub 已提交的20份準備後UCI資料、原本64/16/20切分、固定C3、IID／Non-IID α=.5／.1、Seeds11/23。每個配置先固定Development Client分配、EW3離散化、Reduct、LEM2、UNION規則，再比較同一模型的 B2＋歷史固定投票與 **只使用Development來源類別計數**篩選的補充規則（單前件放寬、Train support≥5、Train purity≥.90）。只在**沒有非空原規則命中**的資料使用補充；原有非空規則命中的預測保持不變。Test標籤只用於評估、不參與生成、篩選或路由。

**研究結果：20來源 ×2 Seeds ×3分布 = 120組，120成功／0失敗。**

| 分布 | 配對配置 | 原始嚴格非空Coverage | 補充後嚴格Coverage | Coverage增益 | Δ Test BA（pp） | BA改善／下降／不變 |
|---|---:|---:|---:|---:|---:|---:|
| IID | 40 | 62.565% | 65.843% | **+3.278pp** | **+0.26457** | 3／0／37 |
| Non-IID α=.5 | 40 | 74.892% | 75.490% | **+0.598pp** | **+0.00962** | 1／0／39 |
| Non-IID α=.1 | 40 | 60.522% | 65.995% | **+5.473pp** | **+0.59670** | 4／0／36 |
| 合計 | **120** | — | — | — | — | **8／0／112** |

**研究意義**：補充規則確實提高了嚴格的「非空前件規則」命中率，但多數配置的Test BA不變；增加可被規則處理的樣本不等同增加正確決策。先前在α=.1純 `TRUE→d` 規則造成的表面高Coverage與本次 `strict_nonempty_coverage`不同，不能直接混用。即使某個資料分布平均ΔBA>0，也不等於實務上必然受益或統計顯著；本輪沒有對120組相依配置做資料集級Wilcoxon、Holm或新預註冊檢定，不能稱為確證。

**重要方法限制**：補充規則會查看**各Client的Development標籤**及相關計數，用於模擬跨Client聚合；**未實作secure aggregation、DP或可部署的消息協定**。高Coverage來源可能形成天然天花板；2 Seeds與歷史20來源有來源與實驗重複使用限制。缺少正確Candidate的部分需要額外比較，而不只是提高命中。

**產物**：[雲端工作流程（120/120 PASS；24測試PASS）](https://github.com/Jimmy0307/LEM2/actions/runs/44260272861)；[13檔實驗、錯誤紀錄與Manifest（30日Artifact）](https://github.com/Jimmy0307/LEM2/actions/runs/44260272861/artifacts/14407083738)。執行來源 `experiments/g4_g8_closure_20261118/uci_supplement_controlled.py`；重要原始已發表G5 CSV與預註冊**沒有改動**。

**尚待驗證才能稱老師要求「全部完成」**：真正未見、非同源來源；事前固定主要統計端點與多重檢定；增加Client數、持有完整高維特徵的LEM2 Train／Test配對；Selective Prediction在拒答與分類品質間的完整Selective-risk/coverage曲線；對少數類Recall以及原始Correct Candidate的因果分解；理論與隱私保證。

## 4. 現階段研究判斷與下一步

**G4：PARTIAL** — 六策略與自適應的「表現差異能否區分TRUE效應」現在有完整重算表；資料仍舊是已探索過的51份來源，尚不能做新確認性結論。

**G5–G6：PARTIAL** — 錯誤分類工具與非空／TRUE規則量化已建立；已完成20份真實UCI ×2 Seeds×3分布的120組 Train-only補充規則干預，Coverage上升、平均BA改善小但非零。此批來源已被使用過，缺新獨立確認、更多Client與少數類的正式外測、拒答風險分析及隱私協定。

**G7：PARTIAL** — 可檢驗的數學界與B2反例已寫入測試；新定理、先行研究排除及教授審閱未完成。

**G8：PARTIAL** — 合成24特徵POS可行性通過；高維真實Full LEM2、5–20 Client、高維外測及實際通訊仍未驗證。

**推薦下一輪最小可行學術里程碑**：先以新的預註冊協定、不同來源家族檢驗「B2＋Train-only補充」相對M2的各種錯誤模式與是否改進Minority Recall；同時另起理論工作證明有用的聯邦規則可信度界限。若沒有新穎性，不再包裝成新演算法。
