# 逐頁來源對照

所有引用以使用者提供備份為依據；本次未重新取得或全文驗證外部論文。不是將檔名中的 verified 當成此次獨立文獻查核。

檔案路徑：鎖定事實與 prompt 位於 `03_CLAUDE_MEETING_HANDOFF/`；來源核對版 MD/DOCX 位於 `01_WORKSPACE_ALL_FILES/`。兩種核對版均已閱讀。


## 01｜研究問題

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§1, 5, 7–8

- 支持內容：研究問題與目前證據範圍

- 圖意：研究主線是 C → 規則結構 → 衝突工作量 → 策略 → 表現。


## 02｜合併規則之後，同一個案可能收到不同答案

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§2–3；prediction_policies_voting_sources_verified_20261021.md §2

- 支持內容：既有 federated baseline 與 inference overlap

- 圖意：UNION 建立全域規則集；不同決策的重疊需在推論時處理。

- 文獻：Woźniak, Sousa, & Śnieżyński (2026). Rule-Based Federated Learning for Healthcare. DOI: 10.1007/978-3-032-29921-5_38. FIRST_MATCH / Federated LEM2 baseline；正式稿仍需原 PDF 方法頁碼。

- 文獻：Lindgren (2004). Methods for Rule Conflict Resolution. DOI: 10.1007/978-3-540-30115-8_26. Overlapping rules 對同一 example 給出不同 decisions。


## 03｜全系統流程：先固定結構，再比較預測策略

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§1–5；既有 federated 流程圖片（只作視覺背景）

- 支持內容：train-only pipeline、C、UNION、policy 的分層

- 圖意：資料、規則學習、UNION、決策與評量是不同層次。

- 文獻：Woźniak, Sousa, & Śnieżyński (2026). Rule-Based Federated Learning for Healthcare. DOI: 10.1007/978-3-032-29921-5_38. FIRST_MATCH / Federated LEM2 baseline；正式稿仍需原 PDF 方法頁碼。


## 04｜UNION 聚合保留規則身分，與決策層分開

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §2；來源核對版 §§4–5

- 支持內容：完整規則身分與聚合／決策層

- 圖意：完全相同的 antecedent 仍可能保留不同 decision；UNION 不會自動消除衝突。

- 文獻：Woźniak, Sousa, & Śnieżyński (2026). Rule-Based Federated Learning for Healthcare. DOI: 10.1007/978-3-032-29921-5_38. FIRST_MATCH / Federated LEM2 baseline；正式稿仍需原 PDF 方法頁碼。


## 05｜主要衝突定義：同一 x 命中多個 decisions

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §3

- 支持內容：inference conflict 主定義；exact supplementary audit

- 圖意：Inference conflict 包含非完全相同條件的規則重疊。

- 文獻：Lindgren (2004). Methods for Rule Conflict Resolution. DOI: 10.1007/978-3-540-30115-8_26. Overlapping rules 對同一 example 給出不同 decisions。

- 文獻：Lindgren & Boström (2002). Classification with Intersecting Rules. DOI: 10.1007/3-540-36169-3_31.


## 06｜C 改變資料碎片化，衝突工作量可能隨之改變

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§1, 7

- 支持內容：client fragmentation 假設鏈；不宣稱單調性

- 圖意：這是一條待重複實驗檢驗的機制鏈，不是單調性定理。


## 07｜四種 Prediction Policies：四種證據使用方式

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §4；來源核對版 §§1, 6

- 支持內容：四個正式名稱、核心證據、既有方法與 adaptation

- 圖意：共同名稱是預測策略；四種機制皆有既有方法來源。

- 文獻：Woźniak, Sousa, & Śnieżyński (2026). Rule-Based Federated Learning for Healthcare. DOI: 10.1007/978-3-032-29921-5_38. FIRST_MATCH / Federated LEM2 baseline；正式稿仍需原 PDF 方法頁碼。

- 文獻：Lazo-Cortés et al. (2020). Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers. DOI: 10.1007/978-3-030-49076-8_7. Simple/Standard Voting 原理；非本研究 federated support 定義。

- 文獻：RSES 2.2 User's Guide (2005), Warsaw University. Simple: one matching rule, one vote；Standard: supporting-object weighting。

- 文獻：Bazan et al. (2000). Rough Set Algorithms in Classification Problem, Eq. (23). DOI: 10.1007/978-3-7908-1840-6_3. Unique class-consistent coverage / class size；federated context 為 adaptation。


## 08｜FIRST_MATCH：第一條命中規則決定預測

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §4.1；來源核對版 §2

- 支持內容：FIRST_MATCH 公式與順序敏感；例子為說明用途

- 圖意：FIRST_MATCH 的 order sensitivity 是需要量化的機制。

- 文獻：Woźniak, Sousa, & Śnieżyński (2026). Rule-Based Federated Learning for Healthcare. DOI: 10.1007/978-3-032-29921-5_38. FIRST_MATCH / Federated LEM2 baseline；正式稿仍需原 PDF 方法頁碼。


## 09｜SIMPLE_VOTING：每一條 matching rule 一票

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §4.2；來源核對版 §3

- 支持內容：Simple Voting 公式；五條規則為示意，不是實測資料

- 圖意：Simple Voting 只比較 matching-rule count；示例假設五條規則都命中 x。

- 文獻：Lazo-Cortés et al. (2020). Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers. DOI: 10.1007/978-3-030-49076-8_7. Simple/Standard Voting 原理；非本研究 federated support 定義。

- 文獻：RSES 2.2 User's Guide (2005), Warsaw University. Simple: one matching rule, one vote；Standard: supporting-object weighting。


## 10｜STANDARD 與 GLOBAL：重複加總，或先去重

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§4.3–4.4；來源核對版 §§4–5；prompt §E

- 支持內容：3+3=6 與 unique union=4/N_A；均為同類、命中 x 的示例

- 圖意：Standard 以 rule support 加總；Global 對物件去重，再除以 training class size。

- 文獻：Lazo-Cortés et al. (2020). Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers. DOI: 10.1007/978-3-030-49076-8_7. Simple/Standard Voting 原理；非本研究 federated support 定義。

- 文獻：RSES 2.2 User's Guide (2005), Warsaw University. Simple: one matching rule, one vote；Standard: supporting-object weighting。

- 文獻：Bazan et al. (2000). Rough Set Algorithms in Classification Problem, Eq. (23). DOI: 10.1007/978-3-7908-1840-6_3. Unique class-consistent coverage / class size；federated context 為 adaptation。


## 11｜公平比較：固定 artifact，分開衡量機制與表現

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§5–6

- 支持內容：frozen artifact、公平比較、既有評量、後續檢定

- 圖意：先固定比較條件，再把分類品質、衝突工作量與順序變動分開評量。

- 文獻：Brodersen et al. (2010). The Balanced Accuracy and Its Posterior Distribution. DOI: 10.1109/ICPR.2010.764.

- 文獻：Sokolova & Lapalme (2009). A systematic analysis of performance measures for classification tasks. DOI: 10.1016/j.ipm.2009.03.002.

- 文獻：Gal (2016). Uncertainty in Deep Learning, §3.3.1 Eq. (3.19). Variation Ratio。

- 文獻：Demšar (2006). Statistical Comparisons of Classifiers over Multiple Data Sets. JMLR 7:1–30. Friedman / Wilcoxon framework。


## 12｜Frozen UCI3：不同資料與 C，對應不同優勢策略

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §8（全部 48 個 BA 數值）

- 支持內容：同一色階、每列最高值含並列；不新增統計推論

- 圖意：在這三個 frozen datasets 與四個 C 設定中，沒有 universal winner。

- 檢核：附 `frozen_uci3_balanced_accuracy.csv`，以程式解析鎖定檔後逐值比較；色階固定 BA 0.45–0.85，橘框為每列最大值含並列。

- 範圍：數值無 seeds/splits/uncertainty 的完整 metadata，不推論顯著性，也不視為新重跑結果。


## 13｜目前貢獻：共同證據上的系統性比較

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §§5, 7, 9

- 支持內容：貢獻定位與結論邊界；Policy* 為概念表達

- 圖意：貢獻定位在研究設計與機制比較，結論隨資料與設定而定。

- 文獻：Woźniak, Sousa, & Śnieżyński (2026). Rule-Based Federated Learning for Healthcare. DOI: 10.1007/978-3-032-29921-5_38. FIRST_MATCH / Federated LEM2 baseline；正式稿仍需原 PDF 方法頁碼。

- 文獻：Lazo-Cortés et al. (2020). Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers. DOI: 10.1007/978-3-030-49076-8_7. Simple/Standard Voting 原理；非本研究 federated support 定義。

- 文獻：Bazan et al. (2000). Rough Set Algorithms in Classification Problem, Eq. (23). DOI: 10.1007/978-3-7908-1840-6_3. Unique class-consistent coverage / class size；federated context 為 adaptation。


## 14｜可重現性：研究快照與本機驗證各自標示

- 檔案／章節：02_REPOSITORY_SNAPSHOT_METADATA/repository_state.json；CLAUDE_LOCKED_RESEARCH_FACTS.md §10；本次環境設定執行記錄

- 支持內容：備份 research CI 105 與本次 main 100 分開；未驗證目前 PR 狀態

- 圖意：105 tests 屬備份研究分支；100 tests 屬本次 main，兩者不是同一份驗證。


## 15｜下一步：把機制證據推進到統計證據

- 檔案／章節：CLAUDE_LOCKED_RESEARCH_FACTS.md §6；MEETING_TALK_TRACK_10_TO_15_MIN.md 收尾

- 支持內容：待決議研究問題、dataset scope、statistics scope

- 圖意：需要共同決定研究問題、資料範圍與重複實驗的統計設計。

- 文獻：Demšar (2006). Statistical Comparisons of Classifiers over Multiple Data Sets. JMLR 7:1–30. Friedman / Wilcoxon framework。


## 獨立圖檔對應

- Federated_LEM2_System_Flow.svg / .png：第 3 頁；流程圖重畫，避免沿用舊海報中的其他 aggregation 選項。

- Federated_LEM2_Conflict_Flow.svg / .png：第 5 頁；主 conflict 與 supplementary audit 分層。

- Standard_vs_Global_Strength.svg / .png：第 10 頁；依 prompt §E 的 support-object 小例子製圖。


## 稽核與未執行工作

- 原始 ZIP 校驗通過；所有新輸出另存 /workspace/lem2-presentation。

- 不操作 GitHub branch、PR、merge、push；不改研究程式、資料或原始 prompt。

- 不執行 housing 分支腳本；該資料與輸出不屬本次 UCI3 簡報結果。

- 研究快照本次未重新 checkout 或執行；UCI 數字屬提供的 frozen evidence。

- 第 14 頁 current main 100 passed 只引用本對話前一階段的實際驗證結果。