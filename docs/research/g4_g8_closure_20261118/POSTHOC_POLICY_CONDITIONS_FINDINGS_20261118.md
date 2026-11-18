# Gate 5 再分析｜TRUE規則條件下六策略與Router的實際價值（Post-hoc，2026-11-18）

> **資料治理聲明**：這不是全新資料或第二次確認性實驗。本次是依照 11/16 **已封存** `REDESIGN_G5_CONFIRMATORY_POLICIES.csv` 與 `CONFIG.csv` 所作的探索性／事後切層分析。未重訓、未調整預註冊、未覆寫原始CSV。存在同一資料集在TRUE／非TRUE兩種層中的情況，不可將下表來源個數相加成獨立樣本。也不得把 `has_true_rule` 當成隨機施加的因果處理。

## 執行與完整證據

- GitHub Actions：[44266567016](https://github.com/Jimmy0307/LEM2/actions/runs/44266567016)，Success。
- [暫存分析產物（原始CSV摘要、逐來源CSV、SHA Manifest；14天保留）](https://github.com/Jimmy0307/LEM2/actions/runs/44266567016/artifacts/14409773346)。
- 重算入口：`python -m experiments.g4_g8_closure_20261118.posthoc_policy_conditions --out <空白的新目錄>`，採Pandas來源級聚合；拒絕覆寫既有產出。
- Source/Seed/分布/規則：51份OpenML × 10 Seeds × IID/Non-IID α=.5/.1 × 2 variants（A、B2）＝**3,060**個配對方法配置。
- 六策略Spread：對每個固定規則配置，`100 × [max(TestBA 六策略)−min(TestBA 六策略)]`，再在同一 `dataset×regime×variant×TRUE-status` 內平均 Seeds，最後按資料集等權平均。
- 自適應增益：`100×(Router TestBA−ValidationBest TestBA)`，**負數表示 Router 較差**；不同配置的ValidationBest已在原實驗的16%內部驗證挑選，沒有用Test選參數。
- `TRUE-status` 由原本Client的 `true_rules>0` 事後分層，與Non-IID偏斜、Client純度高度共變，因此不作因果解釋。

## 主要發現（同資料、同Seed、同分箱及同規則集合）

| 分布 | 有TRUE規則？ | 來源數＊ | 配置數 | 原 UNION 六法Spread(pp) | B2 六法Spread(pp) | B2 Router−ValidationBest(pp) |
|---|---|---:|---:|---:|---:|---:|
| IID | 否 | 51 | 510 | 1.925 | 1.925 | −0.091 |
| α=0.5 | 否 | 51 | 425 | 2.661 | 2.661 | −0.446 |
| α=0.5 | 是 | 37 | 85 | **4.162** | **2.436** | **−0.935** |
| α=0.1 | 否 | 39 | 160 | 3.742 | 3.742 | −0.330 |
| α=0.1 | 是 | 43 | 350 | **3.898** | **1.565** | **−0.364** |

＊一個來源可能有部分Seeds含TRUE、部分Seeds沒有TRUE，因此同一分布下兩行的來源數不可相加。數值為依**來源級平均**，不是所有模型配置直接等權。原確認性報告使用不同彙總口徑，不能拿此表的Spread直接與原G5整體平均做同值核對。

**方法學結論**：

1. 在TRUE=0的配置，B2不能改變規則比對，因此六策略Spread及Router平均效果等於原UNION，這是規則選擇的恆等性，不是成功的模型改善。
2. 在TRUE=1的配置，B2明顯縮小六策略差距：α=.5從4.162→2.436pp；α=.1從3.898→1.565pp，與空前件規則造成原始解析差異的機制一致。
3. 各分布／TRUE分層中的Router−ValidationBest**平均都為負值**。這是對「只要高Conflict就該選自適應路由」的直接反證訊號。未做分層後的家族配對顯著性／非劣性檢定，不得因此聲稱Router在所有來源都較差。
4. 直接把「六法Spread變小」等同「模型分類更準」是錯的，因為該量度只表示六法彼此差距，不能取代Test BA、Candidate Correct或少數類Recall。
5. 本研究的下一個主要可操作問題應是 **B2後如何改良nonempty規則集合、正確候選生成與TRUE-only命中，而非只調投票權重**。

## 與三條研究缺口的整合

- **Track A｜自適應策略**：有充分理由維持 `PARTIAL/LOW PRIORITY`；除非在真正新來源以凍結Resolver/ValidationBest做前瞻對照，達到事前設定的效益門檻，否則不繼續做Router調參。
- **Track B｜Coverage／NoMatch**：以 `rule_trace.py` 分離 nonempty-hit、TRUE-only、effective-hit、fallback與active conflict，直接對有明顯錯誤候選的配置做Train-only規則增補對照。既有聯邦增補Coverage +2.391pp而Test BA −0.015pp，仍不能標SUCCESS。
- **Track C｜G8**：現有16組Full LEM2 paired Test中已出現Greedy TestBA −3.719pp的案例，POS等價不足。下一批須列出新增Client／高維Full-Pipeline／來源級非劣檢定，無法新增真實高維證據前一律 `PARTIAL`。

### 下一個提交的實驗證據

新的 Track B 實驗須預先鎖定 factorial `{EW3,FED_MD}×{A,B2}×{NoSupplement,TrainOnly,ValidationGated}`，並報Source-level的 TestBA、nonempty exact coverage、TRUE-only coverage、truth candidate rate、active/shadow conflict及minority recall。固定原始資料及Split、選法只看Development/Validation，未見Test不作調參。正式新來源確認研究需另外預註冊；歷史UCI20／OpenML51只算探索性。

**研究狀態**：`G4 POSTHOC SOURCE-LEVEL DIAGNOSTIC PASS`；`G4 GENERALIZED ADAPTIVE SUPERIORITY NOT ESTABLISHED`；`B COVERAGE QUALITY AND C HIGH-DIM END-TO-END REMAIN PARTIAL`。
