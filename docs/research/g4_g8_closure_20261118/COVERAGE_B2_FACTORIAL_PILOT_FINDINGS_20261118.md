# Track B｜B2 × Train-only 補充規則之受控探索：現有結果與負面發現（2026-11-18）

**實驗性質：Exploratory pilot；非新來源確認性研究。** 所有原始 Gate 5 確認性實驗、預註冊及舊版 CSV 都未更動。此試驗在既有 UCI Prepared 資料上比較 `A_ALL_RULES` vs `B2_TRUE_AS_FALLBACK`，各自再比較 `NO_SUPPLEMENTS`、`ALL_TRAIN_SUPPLEMENTS`、`VALIDATION_GATED_SUPPLEMENTS`，依相同 seed／split／規則集控制；Supplement 由 *pooled Development* 產生，**是集中式上界型診斷，不是有隱私保證的聯邦方法**。

## 可核查的實際執行

- 已成功的 GitHub Actions：<https://github.com/Jimmy0307/LEM2/actions/runs/44267950050>；提交 `636c9ba6fda3200c67ad8db6d7bd65bc2c03930e`。
- Adult Seed203 Non-IID α=.1 EW3，`SINGLE_LITERAL` 候選結果（6臂+Gate Events+Manifest SHA）：<https://github.com/Jimmy0307/LEM2/actions/runs/44267950050/artifacts/14410299037>。
- Adult 原 `RULE_RELAX`（0個候選）對照：<https://github.com/Jimmy0307/LEM2/actions/runs/44267950050/artifacts/14410443967>。
- Iris 原 `RULE_RELAX`（0個候選）對照：<https://github.com/Jimmy0307/LEM2/actions/runs/44267950050/artifacts/14411102310>。
- 51份OpenML相同規則下政策事後分層：<https://github.com/Jimmy0307/LEM2/actions/runs/44267950050/artifacts/14410293934>。
- 執行程式：`experiments/g4_g8_closure_20261118/coverage_b2_factorial_pilot.py`。以上CI artifacts 暫留14天；重要數據在此文件留底，以免只剩過期連結。

## Adult Seed203：TRUE-only與非空證據必須分開（Test，單位%或pp）

本次 `SINGLE_LITERAL` 的 pooled-Development 候選數為 **28**。無補充規則下，原 UNION 的 `TRUE→d` 造成所有測試列都有某個規則命中，故「Effective Coverage 100%」**不是全部列都有非空規則證據**。

| Rule Variant／Supplement | Nonempty evidence coverage | Effective coverage | Original TRUE-only coverage | Active conflict | Test BA | 少數類 Recall | ΔBA（對自身無補充） |
|---|---:|---:|---:|---:|---:|---:|---:|
| A／無補充 | 95.56 | 100.00 | 4.44 | 100.00 | 50.00 | 0.00 | 0 |
| A／全部候選 | 95.56 | 100.00 | 4.44 | 100.00 | 50.00 | 0.00 | 0 |
| A／Validation Gate | 95.56 | 100.00 | 4.44 | 100.00 | 50.00 | 0.00 | 0 |
| B2／無補充 | 95.56 | 100.00 | 4.44 | 5.28 | 51.16 | 2.33 | 0 |
| B2／全部候選 | **98.06** | 100.00 | 4.44 | **2.78** | 51.16 | 2.33 | **0** |
| B2／Validation Gate | **97.22** | 100.00 | 4.44 | **3.61** | 51.16 | 2.33 | **0** |

上表增量：B2 + 全部 Supplement 將 **Nonempty evidence coverage 增加2.50pp**；B2 + Validation Gate 增加 **1.67pp**，而兩者在這筆單一來源／Seed上 Test BA 均沒有改善。這是 **COVERAGE_ONLY／NO_ADDITIONAL_BA**，不能標記 Track B「分類品質成功」。A 中 TRUE 規則已匹配所有列，按照原始規則優先的契約，Supplement 不能生效，故 A 三臂相同。

B2 單獨相對原 UNION：Test BA +1.1628pp、Active Conflict大幅下降，但這是 **一份資料、一次 Seed 的探索性單例**；不可用它推論穩定平均效應，更不可解讀為過去51份確認性Gate5的H2結果。

## 零候選反例與可學到的事

- Iris Seed203、Non-IID α=.1、EW3，`RULE_RELAX` 0個候選；即使6個Arm全數完成也只驗證流程，不可宣稱補充方法有效。
- Adult Seed203，同一RULE_RELAX亦0個候選；`SINGLE_LITERAL` 則有28個。兩種候選生成器不是同一演算法，必須明確記錄方法與候選分母，不可只挑有利的生成器替換報表。
- 所有結果來源為**pooled Development**，不符合嚴格資料孤島的聯邦隱私要求。真實聯邦化還需要各Client局部生成、可追溯來源、跨Client衝突檢查、交換成本與資料洩漏分析。
- 目前沒有完成跨20份來源的配對效果量／家族層級信賴區間，也沒有8／12／16／24特徵的跨Client完整模型實驗。

## 下一輪嚴格停止條件

1. 凍結 `{EW3,FED_MD}×{A,B2}×{NoSupp,AllSupp,ValGated}` 對照，確保各因子只變動一層，並標明為探索性來源。
2. 先做UCI20同Seed多來源，再做足夠來源級的Test BA、Minority Recall、Confidence Interval和完整失敗紀錄。
3. 如補充規則只能增加 nonempty coverage、但沒有BA正向證據，必須明確終止「Coverage代表分類效益」假說，而不是再調門檻尋找正面樣本。
4. 強基準、真正高維 End-to-End 與全新來源的 Confirmatory 必須有單獨預先註冊；不能改寫既有51份結果。

**狀態**：`EXPLORATORY_PIPELINE_AND_FACTORIAL_SMOKE_PASS`，`TRACK_B_CLASSIFICATION_BENEFIT_NOT_ESTABLISHED`；Track A與Track C仍是 `PARTIAL`。
