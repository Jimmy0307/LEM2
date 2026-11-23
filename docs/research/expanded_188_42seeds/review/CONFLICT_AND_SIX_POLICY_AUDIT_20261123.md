# LEM2 六種 Rule Resolution Policies 的排名、有效性與 Conflict 機制
**資料來源：** 2026-11-23 11:43 期中快照，179/188 完整資料集，每資料集 42 Seed、四情境、兩種 Rule Variants；跨資料集等權。**固定研究條件：** NESTED_64_16_20、最多六 Features、聯邦三 Clients。

## 先更正術語
六種 **Selection Policies** 並非六條 LEM2 Rules，更不是六 Features。每個 source × seed × scenario 先學一組 Rule Set，再用六種方式把匹配到的規則轉成一個分類結果。因此同一 rule_variant 下六種方法的 **Coverage、Candidate Coverage、Conflict、Rule Count 完全相同**，只有最終 Accuracy / BA 不同。

| Selection Policy | 實際實作 | 主要風險 |
|---|---|---|
| FIRST_MATCH | 取最先命中的規則，沿 Client union／Local LEM2 規則順序 | 先後順序非品質分數，容易有順序偏誤 |
| SIMPLE_VOTING | 每類別獲得的命中規則條數 | 很多相似規則可能重複投票 |
| STANDARD_VOTING | 依每條命中規則在 pooled Development 的正確前件＆決策支持度加權 | 受支持度／類別不平衡影響；只需規則支持度聚合而非每次重算支持集聯集 |
| GLOBAL_STRENGTH | 各類別命中規則的 support set union / Dev 類別數 | 跨客戶端 rowwise support 成本高，若隱私部署需另設協定 |
| POPULATION_STANDARD | 各類別命中規則 support set 聯集筆數 | 易受類別人數影響；大樣本高規則運算昂貴 |
| POPULATION_GLOBAL | 全域比例（support union/class size）再乘 support union / rule support 總和 | 計算昂貴，原始 A 版在重度 non-IID 常最差 |

## 1. 六種策略的**絕對 Accuracy**（179完整來源等權平均，非事後 Test winner）

| Policy | Centralized（A=B2） | Fed IID（A=B2） | α=.5 A | α=.5 B2 | α=.1 A | α=.1 B2 |
|---|---:|---:|---:|---:|---:|---:|
| `STANDARD_VOTING` | 60.15% | 62.45% | 59.02% | 59.89% | 53.41% | 54.94% |
| `POPULATION_STANDARD` | 60.15% | 62.41% | 58.61% | 59.74% | 52.44% | 54.87% |
| `SIMPLE_VOTING` | 60.00% | 62.06% | 59.72% | 59.85% | 54.52% | 54.51% |
| `GLOBAL_STRENGTH` | 60.10% | 62.23% | 57.19% | 58.80% | 49.58% | 54.07% |
| `POPULATION_GLOBAL` | 60.10% | 62.11% | 56.38% | 58.37% | 46.28% | 53.83% |
| `FIRST_MATCH` | 60.00% | 61.48% | 57.41% | 58.18% | 47.59% | 50.66% |

同一來源相同 Policy 的 Centralized vs Federated 才是配對設計。雖然這些 Policy 同步在 Test 評估，**並沒有事先用 Validation 選優勝 Policy**；此表只是固定 Policy 的獨立 Accuracy，不等於使用 Test 先挑出最佳策略再當部署效能。

### 每情境組平均第一／第二名
| 分布 | Variant | 最高策略（Accuracy） | 第二名（Accuracy） | 差距 |
|---|---|---|---|---:|
| CENTRALIZED | A_ALL_RULES | POPULATION_STANDARD (60.146%) | STANDARD_VOTING (60.145%) | 0.001 pp |
| CENTRALIZED | B2_TRUE_AS_FALLBACK | POPULATION_STANDARD (60.146%) | STANDARD_VOTING (60.145%) | 0.001 pp |
| FED_IID | A_ALL_RULES | STANDARD_VOTING (62.447%) | POPULATION_STANDARD (62.409%) | 0.038 pp |
| FED_IID | B2_TRUE_AS_FALLBACK | STANDARD_VOTING (62.447%) | POPULATION_STANDARD (62.409%) | 0.038 pp |
| FED_A05 | A_ALL_RULES | SIMPLE_VOTING (59.718%) | STANDARD_VOTING (59.024%) | 0.694 pp |
| FED_A05 | B2_TRUE_AS_FALLBACK | STANDARD_VOTING (59.892%) | SIMPLE_VOTING (59.850%) | 0.042 pp |
| FED_A01 | A_ALL_RULES | SIMPLE_VOTING (54.522%) | STANDARD_VOTING (53.415%) | 1.107 pp |
| FED_A01 | B2_TRUE_AS_FALLBACK | STANDARD_VOTING (54.938%) | POPULATION_STANDARD (54.869%) | 0.069 pp |

**條件式結論：**
- **若必須用 A_ALL_RULES：**Fed α=.5、α=.1 平均 Accuracy 最高皆為 `SIMPLE_VOTING`；Centralized 的 `POPULATION_STANDARD` 與 `STANDARD_VOTING` 差 <0.001 pp，Fed IID 為 `STANDARD_VOTING`。
- **若允許 B2_TRUE_AS_FALLBACK：**Fed IID、α=.5、α=.1 的最高平均 Accuracy 都是 `STANDARD_VOTING`；在後兩種分布下第二名僅差 0.042、0.069 pp，未做六策略間成對顯著性／等效性檢定，不能宣稱本策略統計上一定更好。
- **平均排名與平均 Accuracy 不完全相同。**平均排名越小越好。B2 下 STANDARD 的 IID/α=.5/α=.1 平均名次分別 2.536/2.165/2.299，且均為第一名。
- **Balanced Accuracy 可能偏好不同策略。**依初期報表的 Centralized BA（兩位小數）＋聯邦－集中式 BA 配對差反推，Fed α=.1 B2 的 `GLOBAL_STRENGTH` BA 約46.73%，`STANDARD_VOTING`約46.45%；這些是以四捨五入的基準數推得的近似值，不應當作原始全精度 BA 來源。前者更耗運算，應另外做成本與 BA 的 Pareto 對照。

## 2. 高 Conflict 從哪來？

精確程式定義：`fedrs.predict.candidate_profile` 建立每筆 Test 的候選決策集合，`n_candidate_decisions>=2` 就算 Conflict；分母是**整個 Test Set**，不是只計算「有命中」的樣本。無論裁決策略最後有沒有預測對，這個布林條件都已在投票前確定。換言之 **Conflict Rate ≠ Misclassification Rate，六種投票法也不會改變 Conflict Rate**。

| 結構指標 | Centralized | Fed IID | Fed α=.5 A | Fed α=.1 A | Fed α=.1 B2 |
|---|---:|---:|---:|---:|---:|
| Test Coverage | 27.56% | 46.75% | 64.63% | 86.54% | 86.54% |
| Candidate Coverage | 23.01% | 39.06% | 51.78% | 68.50% | 61.42% |
| Conflict (Test 分母) | 1.26% | 13.08% | 27.20% | 55.48% | 33.93% |
| No Match | 72.44% | 53.25% | 35.37% | 13.46% | 13.46% |

- Fed α=.1 A：被規則覆蓋的 Test 中約 **64.1%** 發生 Conflict（55.48 / 86.54）；但也有 **79.2%** 的覆蓋樣本，其真實類別至少在候選集合之中（68.50 / 86.54）。Conflict 並非全部「有害」。
- Fed α=.1 A→B2：Conflict **−21.55pp**，即原本 Test 衝突的約 **38.8%** 在 suppress TRUE co-match 後消失；但 Candidate Coverage 同時 **−7.08pp**。B2 保留原來的 No-Match 備援，所以 Test Coverage 沒變；不能說它無損地消除衝突。
- **TRUE 規則的直接來源：**各 Client 先尋找 exact minimal reduct，若某 Client 有空約簡（例如只有單一決策類別），`roughset.pipeline.induce_lem2_on_reduct` 可產生沒有條件的 `TRUE → class`。其前件匹配任何 Test 物件；多個 Client 的異類 TRUE／一般規則合併會增加同樣本多決策命中機會。一般 LEM2 的非 TRUE 規則也可能在跨 Client 異質資料後互相重疊。
- **B2 的機制：**有任何具條件規則命中時，暫時遮掉所有 TRUE 規則；若沒有具條件規則，仍保留 TRUE 規則。可縮減部分衝突，不能消除所有跨 Client 規則重疊。
- 不是單純因「六 Features」而起：原始 ≤6 的 25 完整資料集在 α=.1 A 有平均 Conflict 71.36%，而原始 >6 只用六 Features 的 154 筆平均 52.90%；兩組來源本質不同，這只能否定單一原因說法，不能以其差距推論截六 Features 的因果影響。

### 從已有證據能／不能主張什麼
**能支持：**跨 Client 的 Label Skew + local reduct／LEM2 + rule UNION 後，A 版 Conflict 與 Coverage 在強 non-IID 中同步升高；B2 减少 TRUE 與具條件規則的共同命中衝突。 
**尚無直接診斷：**完整 179來源的 `empty_reduct_clients`、`true_rules`、`conflict_created_by_true`、`conflict_involving_true`、`conflict_rate_without_true`、`multi_truth_in_candidates` 的逐 Seed 分解。原程式 `fedrs.experiment.config_row/structure_rows` 其實已有這些欄位，但本批 `run_model` 只保存19欄 policy 結果、未跑完整診斷。不能將 21.55pp 全部當作「空約簡數量」或聲稱 61.2% 殘餘衝突全部來自非空規則。

## 3. 六策略到底有沒有用？
有**相對於彼此**的證據：α=.1 A 的 `SIMPLE_VOTING` 54.52%，`POPULATION_GLOBAL` 46.28%，同一 Rule Set 造成 **8.24pp** 的不同 Accuracy；其資料集層級「六策略最大 Accuracy 差」在 α=.1 A 平均10.73pp、中位7.91pp、最大47.77pp。然而沒有 **MAJORITY_ONLY** 與 **matched-only accuracy** 基線，不能聲稱 LEM2 Rules 整體比「永遠猜訓練資料多數類別」好多少；尤其 Centralized 平均只有 27.56% Test Coverage，其餘大多 fallback。
此外，在同一 source/seed/rules 下，六策略只在多個候選決策類別時可能產生不同結果：`model.py` 甚至檢查每個模型策略的最大 Accuracy 差距不得超過 Conflict Rate。這是數學上必然的限制，而不是需要更多策略才能解決的錯誤。

## 4. 建議怎麼選
**現有結果下的工程預設：`STANDARD_VOTING + B2_TRUE_AS_FALLBACK`。**理由：IID/α=.5/α=.1 下平均 Accuracy 和平均資料集排名表現穩健；STANDARD 可由已聚合的每條規則支持度計分，相比三種 support-union 策略可避免每種 Match Pattern 對 pooled Dev 做大矩陣計算（但目前原始程式仍對六策略共用大支持矩陣，未獨立 benchmark 單一策略實作）。**不代表統計上已證明它優於第二名或適用於所有來源**。若要求最簡、低額外聚合，`SIMPLE_VOTING + B2` 是重要 baseline；若優先 BA，可再看 `GLOBAL_STRENGTH+B2` 的成本／效能 Pareto，但其在高規則數資料有 TIMEOUT 風險。

## 5. 下一輪最有說服力的驗證
1. **先不重跑 31,584 配置：**現有同 Rule Set 的六策略資料直接加上逐資料集、逐 Seed、配對策略的 Accuracy/BA 差異、bootstrap CI 和 Holm-adjusted Wilcoxon，避免直接稱0.07pp差異顯著。
2. **MAJORITY_ONLY** 使用相同 Dev class proportions 作為「不用規則」基線；另報 matched-only accuracy、no-hit accuracy、coverage-conditioned accuracy、conflict-only accuracy。
3. 分三個重度 Non-IID 代表集、原始低維與截六維代表集，輸出 `true_rule_count`、`empty_reduct_clients`、`conflict_created_by_true`、`truth_in_candidates_only_via_true`；**只做診斷版，不更動 2,700s Frozen 主實驗**。
4. 用 Validation 在六策略中選方法（`VALIDATION_BEST`）、固定 Test 作獨立評估，再比較簡單固定 `STANDARD+B2` 策略是否相同或更好。
5. 把「Rule Discovery Quality」與「Rule Resolution Runtime／Memory」獨立，避免昂貴後處理掩蓋規則本身的可用程度。

## 來源
- [六方法平均 Accuracy 與平均排名（179 complete）](../interim/interim_policy_accuracy_and_rank.csv)
- [Coverage/Conflict 規則結構對照](../interim/interim_structure_coverage_conflict_rules.csv)
- [A→B2 同來源配對效果](../interim/interim_b2_minus_a.csv)
- [原始完整研究期中報告](../interim/INTERIM_FINDINGS.md)
- `fedrs/predict.py`：`candidate_profile`、`variant_matrix`、`resolve_scalable`；`fedrs/induce.py`、`fedrs/experiment.py`：Client rule union、TRUE rule/empty reduct 診斷
- [六 Features 與未完成來源研究限制](../review/FEATURE_SELECTION_SIX_REVIEWER_AUDIT_20261123.md)

**研究狀態：179 完整、9 未完整；以下排行不能宣稱全部188已完成，也不能當成已透過 Validation 選策略的部署實測。**
