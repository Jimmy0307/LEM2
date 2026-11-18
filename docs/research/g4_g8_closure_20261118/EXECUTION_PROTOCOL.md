# G4–G8 補強研究執行協定｜2026-11-18

> **這份文件是後續新研究的預先分析計畫／執行規格，不是已完成確認性研究的預註冊證明。**
> 本工作包以 PR #6 最終研究 Head `006dbe8` 建立獨立分支，不改原始基準 `87e31c4`、Gate 5 預註冊、51份數據與 PR #6。

## I. 研究範圍與不可跨越的證據邊界

本輪補強老師的三項重點，而不是繼續灌資料集數：

1. **G4 六策略／Non-IID 自適應**：確定過去所見的「選策略效益」有多少被單類別 Client 的 `TRUE→d` 規則混淆。
2. **G5–G6 Coverage／No Match**：區分沒命中規則、只靠 TRUE 命中、正確候選缺失、可解析的多候選衝突；比較規則層的受控補充與拒答取捨。
3. **G7–G8 理論／高維**：確認可證性與反例，辨認 exact minimum reduct 的組合性代價，分離工程加速與分類泛化。

階段標籤固定：HISTORICAL / EXPLORATORY_POSTHOC / NEW_EXPLORATORY / FUTURE_CONFIRMATORY。**任何 2026-11-16 既有來源、Seeds 或模型在本工作包中再被分析，必須標為 EXPLORATORY_POSTHOC**。當來源有 ada/gina/sylvine 的同源疑慮，保留原始結果並單列敏感度。

## II. Gate 4A：六策略在同規則、同分割下的真正增量

**比較單位**：每 dataset×seed×regime×discretizer。令最原始 A=`A_ALL_RULES`、B=`B_DROP_TRUE`、B2=`B2_TRUE_AS_FALLBACK`；每個條件保留全部同一套 Local LEM2 和 UNION 規則、切分及 Train/Val/Test，唯一差異是推論層 TRUE 規則處理與解析法。

- 六固定策略：FIRST_MATCH、SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH、POPULATION_STANDARD、POPULATION_GLOBAL。
- 自適應：VALIDATION_BEST（只用Inner Val挑六法）、原 G4 `CONFLICT_BUCKET_ROUTER_V1`；固定比較法依歷史設定 IID=GS，α=.5/.1=SimpleVoting。不得由 Test 事後挑「最佳固定法」當可部署對照。
- 分層：IID、α=.5、α=.1；含／不含單類別 Client；純類別／純連續／混合來源；`TRUE_ONLY` 比例；Client 類別組成。
- 同時報告 Test BA、MacroF1、Exact nonempty Coverage、真實類別在候選集合比例、Test policy spread、router switch rate、決策變化率；最後一項「Test 六法最好−最差」只作 **oracle** 描述性診斷。
- 先按 Dataset 內跨10 Seeds平均、再按 Dataset 或事先明確的來源家族等權聚合。不能把10 Seeds當510份獨立資料。主要研究方法若後續確認性研究，應事前固定 endpoint、最小實務效應1pp、校正族與來源獨立性。
- 新程式 `analyze_retrospective.py` 能直接從凍結G5原始CSV產生探索性表，無需把本機420MB OpenML快取搬到公司電腦。

**通過條件**：所有來源／Seeds成對；六法完整；選擇不得接觸Test；B2與A的差異分解成立；沒有資料缺漏被靜默排除。**停止條件**：來源家族重疊足以動搖推論時先做敏感度，不得宣稱優勢。若新獨立研究所見六法差異均小於預設實務門檻且推論不確定，停止昂貴自適應路由研究。

## III. Gate 5–6：Coverage、真正NoMatch及拒答的分解

現有 `fedrs/closure_diagnostics.py` 對 Test 每列建構**互斥且窮盡**的五類：

| 類型 | 定義 | 可改進的研究層 |
|---|---|---|
| NO_MATCH | 無非空規則，也無TRUE規則 | 原始規則誘導、補充規則或 fallback |
| TRUE_ONLY | 沒有非空規則，但匹配TRUE | 區分虛高Coverage與真正分類訊號 |
| CANDIDATE_MISS | 有非空規則，卻沒提出真實Decision | 規則品質、離散化、類別不平衡 |
| CONFLICT_RESOLVABLE | 有非空規則、真實類別在候選且≥2不同決策 | 再談投票／解析器 |
| SINGLE_CORRECT | 有非空規則且唯一候選正確 | 不需額外解析 |

因此原始 **nonempty Coverage** ≠ 含TRUE的 effective Coverage ≠ 正確候選率 ≠ 最終Accuracy ≠ 實際Abstention。原程式沒有主動拒答，NoMatch仍會多數類Fallback；報告不准把 `1−Coverage` 直接叫做已發生的 Reject。

**干預對照（後續新實驗，尚未聲稱完成）**：

- S0：原始確定性規則、A / B2、固定六法。
- S1：保持S0規則不變、拒答 `NO_MATCH` 或 `NO_NONEMPTY` 的 selective prediction；報告 **coverage–selective-risk**，但不得稱為減少 NoMatch。
- S2：Train-only 單前件放寬式 Supplement（對應現有 `teacher_demo/supplementary_rule_coverage_pilot.py`），最低支持數5、Train純度0.90／0.95；Supplement與原規則分開記錄，禁止稱其為原典LEM2 Exact Coverage。
- S3：Validation-only 補充規則守門（延續 `teacher_demo/conflict_aware_coverage_pilot.py` 已凍結版），不得依Test調整門檻。
- S4：同設定的 B2＋FED_MD 組合；**改動離散化就是改動規則**，因此要另設配對，不可將收益歸因於單一方法。

每個干預應分開報告：Exact Coverage、Augmented Effective Coverage、Truth in Candidates、Conflict、Abstention、Conditional BA、All-Test BA、MacroF1、Minority Recall、規則數與成本。只有 Coverage 上升而 BA不升，結論是規則提供更多候選但未改善選擇；不准宣稱救回失敗樣本。對 20 UCI 來源既有 Gate5–6 是探索性資料，不是新確認性資料。

**停止條件**：如果Supplement造成新的Conflict或少數類 Recall 顯著惡化，不再以Coverage上升作為成功；如只靠 TRUE 提升覆蓋，標記 `COVERAGE_ARTIFACT` 而非 `TRUE_RULE_RECALL`。

## IV. Gate 7：可證明的命題及反例，不偷換演算法新穎性

1. **已驗明的空約簡條件**：非空單類別 Client (U_c) 中，`IND(∅)`唯一類別即 (U_c)，故POS為全集、空集是最小基數Reduct，LEM2可導出TRUE→d；這是經典粗糙集結構性結果，不是新定理。
2. **全域支持上下界（新形式化稽核）**：對固定規則 r，已知本地匹配 m、本地正確 s，外部匹配上界 u；在假設各來源不重複、全域前件語意一致時，全域 confidence (\in[s/(m+u),(s+u)/(m+u)])。若缺乏 u 或外部統計，沒有不依賴資料分布且有用的正向保證。此為計數邊界，不保證 Balanced Accuracy。
3. **B2 不能無條件勝過A**：反例：同時有TRUE→P與(x)→N，系統預設 P。若 Test (x,P)，A在SimpleVoting平手選P而B2選N；若Test (x,N)，反之。已用單元測試核對，因此不能無條件寫「降級TRUE必然改善」。
4. **對稱Dirichlet–multinomial生成模型**下 (p\sim Dirichlet(\alpha_1,...,\alpha_K))，Client內 n 個標籤 iid 取樣，純Client機率為 (Σ_k Γ(A)Γ(\alpha_k+n)/(\u0393(A+n)\u0393(\alpha_k)))（n≥1）。此式**不等於**目前 `roughset.federated.partition_clients` 的「按類別向Client分配 Dirichlet 比例」實驗機制。未重新推導前不能拿它解釋目前68.6%統計。

投稿前需獨立專家審核形式命題、資料生成假設及已知先行文獻；工程數學檢查≠全形式化證明≠新演算法首創。

## V. Gate 8：規模與NP-hard瓶頸的誠實驗證

**既有證據**：82個真實來源CPU約簡配置、36個低維確切等價配對、16個完整LEM2的Train/Test比較；最高6400列、24特徵的Greedy訓練POS驗證，**不是**同維精確 Reduct + 全LEM2 + Test 品質比對。

**新控制矩陣**（必須另行投入運算，不能從此次Smoke聲稱已完成）：

| 維度 | 保留完整條件 | 測試設定 |
|---|---|---|
| Client數量 | 固定Rows、Features、Seeds、單一外層Test；測量實際標籤偏斜 | 3／5／10／20 |
| 特徵數 | 同一資料固定切分、合理資料型態選欄、分箱與Label分佈 | 6／12／20／全特徵（受資源預算上限約束） |
| 約簡方法 | Exact minimum vs Exact cached（同語意）；Greedy POS 只能稱啟發式 | Exact只對可行維度執行，超過cap回報 `NOT_ESTIMABLE` |
| 成效 | 不只測POS，還測誘導的rules與完整TEST | BA、MacroF1、Coverage、Conflict、規則數、wall time、Peak RSS |
| 資源 | 單一Worker和預先固定的Timeout、memory budget | 超時＝CENSORED，不拿缺值補0，也不得宣稱高維求解成功 |

`experiments/g4_g8_closure_20261118/scaling_smoke.py` 僅在合成資料上做 5／8／12／24 特徵約簡POS測試與運算能力確認；目前**未**做高維真實完整LEM2外測。

**必要反例**：Greedy即使保持Train POS，也可能在Test BA下降；原始G8已有實測反例，不能用Train一致代替外部泛化。

## VI. 下一步與實驗開跑門檻

- **已可立即完成**：回溯51份已發布數據的G4/G5分層重新分析、程式測試、G7形式數值測試、合成規模Smoke；全部標為探索性或工程。
- **需正式新實驗**：受控 Train-only Supplement 的IID/NonIID × Dataset配對、更多Client、高維完整外測、真正FedTree對照、學術新穎性核對。
- **需新確認性驗證**：未看過的來源家族（嚴格排除前161＋51與同源變體）、先固定新Seeds/假設/樣本量/主要endpoint/ Holm家族、多樣本校正並附獨立審核，才能給真正的新確認性結論。

不能直接把上週部分完成三項改成全部PASS；應在每項有新實驗、分析及對照後按 `PASS / PARTIAL / BLOCKED / NOT VERIFIED` 正式驗收。
