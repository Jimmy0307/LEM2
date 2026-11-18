# G4–G8 核心缺口補強｜第一輪實際執行結果（2026-11-18）

**狀態：工程與探索性回溯分析 PASS；正式新確認性研究、規則補充的全新干預及真實高維完整外測仍未完成。** 不能將本檔當作已通過的全新學術驗證或新演算法論文。

- 研究來源：`research/federated-rule-degeneracy-redesign-20261116` @ `006dbe8`（PR #6，未合併）
- 本輪分支：`research/g4-g8-closure-20261118`
- [GitHub Actions 雲端執行（21測試通過，原始G5回溯及高維工程Smoke PASS）](https://github.com/Jimmy0307/LEM2/actions/runs/44258223134)
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
| 新單元／命題反例測試 | **21 passed** |
| G5源資料51×10回溯對照 | **PASS** |
| B2/A六策略與Coverage分析 | **PASS** |
| 合成5/8/12/24約簡Smoke | **PASS** |
| 原G5數據／預註冊未改寫 | **PASS** |
| 真實高維全LEM2模型與更多Clients | **尚未執行** |
| 真正新的確認性試驗與投稿新穎性 | **尚未通過** |

## 4. 現階段研究判斷與下一步

**G4：PARTIAL** — 六策略與自適應的「表現差異能否區分TRUE效應」現在有完整重算表；資料仍舊是已探索過的51份來源，尚不能做新確認性結論。

**G5–G6：PARTIAL** — 錯誤分類工具與非空規則/TRUE規則量化已建立；正式新的補充規則干預未執行，聯邦BA是否能提升仍未知。

**G7：PARTIAL** — 可檢驗的數學界與B2反例已寫入測試；新定理、先行研究排除及教授審閱未完成。

**G8：PARTIAL** — 合成24特徵POS可行性通過；高維真實Full LEM2、5–20 Client、高維外測及實際通訊仍未驗證。

**推薦下一輪最小可行學術里程碑**：先以新的預註冊協定、不同來源家族檢驗「B2＋Train-only補充」相對M2的各種錯誤模式與是否改進Minority Recall；同時另起理論工作證明有用的聯邦規則可信度界限。若沒有新穎性，不再包裝成新演算法。
