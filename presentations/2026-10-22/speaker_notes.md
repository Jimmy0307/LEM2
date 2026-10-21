# Federated LEM2｜逐頁會議講稿

預計總長約 10–15 分鐘。每頁約 30–60 秒，討論可另加時間。

備份日期：2026-10-22（Asia/Taipei）。下列講稿亦已嵌入 PPTX 的 speaker notes。


## 01｜Federated LEM2：研究問題

今天想討論的不是重新發明 LEM2，而是 Federated LEM2 裡一個實際的推論問題。當資料分給更多 clients，每個 client 產生的規則可能改變；把規則合併以後，同一個測試個案也可能同時收到不同類別的建議。我們把這件事拆成規則結構、衝突工作量、預測策略與分類表現四個層次。接下來會先釐清流程與衝突定義，再比較四種策略，最後用備份中的三個 frozen UCI 資料集說明目前能支持的結論。

**這張圖要證明什麼：** 研究主線是 C → 規則結構 → 衝突工作量 → 策略 → 表現。

**來源：** 來源：鎖定研究事實 §§1, 5, 7–8；備份日期 2026-10-22


## 02｜合併規則之後，同一個案可能收到不同答案

原始的 federated LEM2 基準，是各 client 先產生 local rules，再由 server 做 UNION，推論時採用 FIRST_MATCH。這裡用一個小例子：第一條規則說 A 等於一就判 Yes，第二條說 A 等於一而且 B 等於二就判 No。UNION 會把兩條都留下來，所以測試個案同時符合兩條時，仍然要決定最後採哪個答案。我們關心的是，在完全相同的規則證據下，不同預測策略會怎麼改變結果；不是預設投票一定比較好。

**這張圖要證明什麼：** UNION 建立全域規則集；不同決策的重疊需在推論時處理。

**來源：** 來源：鎖定研究事實 §§2–5；Woźniak et al. (2026)；Lindgren (2004)


## 03｜全系統流程：先固定結構，再比較預測策略

這張圖從左上開始看。資料先切成 training 與 test，training 再依 C 分配給 clients。各 client 在 training 範圍內做必要的前處理、Rough Set、reduct 與 LEM2，不能讓 test rows 參與學習。server 接著做 UNION，形成同一份 global rule set，再先辨識 conflict cases。最後四種 prediction policies 使用相同的結構產物做預測與評量。圖上的 C 是外層實驗因素，UNION 是聚合，真正對 competing rules 做決策的是最下方的 policy layer。

**這張圖要證明什麼：** 資料、規則學習、UNION、決策與評量是不同層次。

**來源：** 來源：鎖定研究事實 §§1–5；主流程採 train-only preprocessing / reduct


## 04｜UNION 聚合保留規則身分，與決策層分開

這裡把 aggregation 與 prediction 再分清楚。global rule set 是所有 local rule sets 的聯集，但做去重時，規則身分必須包含 antecedent 加上 decision。因此，即使兩條規則的條件完全一樣，只要預測類別不同，就是兩條不同規則，不能把其中一條當成重複資料刪掉。聚合層只負責建立規則集合；到了 test object 進來、找到 matching rules 以後，才輪到 prediction policy 決定答案。這個分層也是後面公平比較四種策略的基礎。

**這張圖要證明什麼：** 完全相同的 antecedent 仍可能保留不同 decision；UNION 不會自動消除衝突。

**來源：** 來源：鎖定研究事實 §2；來源核對版 §§4–5


## 05｜主要衝突定義：同一 x 命中多個 decisions

我們的主要 conflict 定義，是同一個測試個案命中的規則裡，出現超過一種 decision。沒有規則命中時，用既定 default class；只有一種 decision 時，做一般規則式預測；出現不同 decisions 時，就是 inference conflict，交給選定的 policy。這不等於 exact conflict。右下角兩條規則的條件不完全相同，所以 exact audit 抓不到，但 A 等於一、B 等於二的個案會同時命中兩條。這就是為什麼主分析要用 prediction-time conflict，而 exact conflict 只作補充結構稽核。

**這張圖要證明什麼：** Inference conflict 包含非完全相同條件的規則重疊。

**來源：** 來源：鎖定研究事實 §3；Lindgren (2004)；Lindgren & Boström (2002)


## 06｜C 改變資料碎片化，衝突工作量可能隨之改變

C 是外層實驗因素，不是第五種演算法。當 client 數量改變，每個 client 看到的資料量和類別組成也可能改變，接著影響 local reduct、規則長度與規則集合，再影響 global rules 的重疊情況。這是一條合理的研究機制鏈，但不能直接當成數學定理。鎖定文件提到 frozen datasets 的 C 等於五端點高於 C 等於二；備份沒有附這段的逐點原始數值，所以這頁不另造趨勢圖，也不宣稱每個中間的 C 都嚴格增加。

**這張圖要證明什麼：** 這是一條待重複實驗檢驗的機制鏈，不是單調性定理。

**來源：** 來源：鎖定研究事實 §§1, 7；不提供未附原始數據的 conflict 趨勢圖


## 07｜四種 Prediction Policies：四種證據使用方式

四種方法的共同名稱是 Prediction Policies。第一種 FIRST_MATCH 看順序，不是 voting。第二種 SIMPLE_VOTING 看 matching rule 的條數。第三種 STANDARD_VOTING 看 rule support 的加總。第四種 GLOBAL_STRENGTH 看 unique class coverage ratio。Simple Voting 是直接放進相同規則集作比較；Standard 的 federated weight，以及 Global Strength 的跨 client support context，則要明確標為本研究 adaptation。我們的貢獻是整合與系統性比較，不是宣稱發明這四種機制。

**這張圖要證明什麼：** 共同名稱是預測策略；四種機制皆有既有方法來源。

**來源：** 來源：來源核對版 §§1, 6；Woźniak 2026；Lazo-Cortés 2020；Bazan 2000


## 08｜FIRST_MATCH：第一條命中規則決定預測

FIRST_MATCH 的公式很直接：先把 global rules 排成固定順序，然後選最前面那條符合測試個案的規則。圖上兩種順序用的是同一組規則，同一個 x 都會命中兩條；Yes 的規則先出現，就判 Yes，No 的規則先出現，就判 No。因此它的結果可能受 client order 以及 global rule order 影響。我們保留這個來源基準，再另外做順序敏感度稽核。這一頁的例子是機制示意，不是額外的實驗結果；正式稿的來源細節仍要回原 PDF 核對頁碼。

**這張圖要證明什麼：** FIRST_MATCH 的 order sensitivity 是需要量化的機制。

**來源：** 來源：鎖定研究事實 §4.1；來源核對版 §2；Woźniak et al. (2026)


## 09｜SIMPLE_VOTING：每一條 matching rule 一票

Simple Voting 把每條命中的規則當成一票，再依 decision 累加。這裡假設五條規則都符合測試個案，三條建議 A，兩條建議 B，所以 A 得三票、B 得兩票，最後選 A。它不用看每條規則支援多少訓練樣本，也沒有對 class size 做正規化。這是既有文獻與 RSES Guide 的 one matching rule, one vote 原理。我們將它放進與其他策略相同的 frozen global rule artifact 裡比較；沒有先假定票數多就一定比較準，遇到同分則依固定實作處理。

**這張圖要證明什麼：** Simple Voting 只比較 matching-rule count；示例假設五條規則都命中 x。

**來源：** 來源：來源核對版 §3；Lazo-Cortés et al. (2020)；RSES 2.2 Guide (2005)


## 10｜STANDARD 與 GLOBAL：重複加總，或先去重

這是今天最容易混淆的一頁。假設兩條規則都命中測試個案，而且都預測 A。第一條 support 是 u1、u2、u3，第二條是 u2、u3、u4。Standard 把兩條規則的 support 大小直接相加，所以是三加三等於六，u2 與 u3 各貢獻了兩次。Global Strength 先做物件集合聯集，只剩四個不同物件，再除以 training class A 的大小 N_A。兩者分別採用 rule-level sum 與 unique object coverage；這個六和四除以 N_A 是不同策略的分數，不能直接跨策略比較大小。

**這張圖要證明什麼：** Standard 以 rule support 加總；Global 對物件去重，再除以 training class size。

**來源：** 來源：鎖定研究事實 §§4.3–4.4；來源核對版 §§4–5；Bazan et al. (2000), Eq. 23


## 11｜公平比較：固定 artifact，分開衡量機制與表現

比較四種策略之前，必須先固定所有結構條件，包括 train/test split、client partition、local reduct、local rules、UNION、解決前的 conflict cases 與 default class，只改 prediction policy。評量分三組：分類品質用 Balanced Accuracy、Macro-F1 與 Coverage；規則結構看數量、平均條件數和 antecedent Jaccard；衝突與順序則看 conflict set 的比例與分類品質，並用 Variation Ratio 描述不同 client orders 的類別分歧。這些都是既有指標；正式顯著性檢定要等多次 seed、split 的成對實驗完成。

**這張圖要證明什麼：** 先固定比較條件，再把分類品質、衝突工作量與順序變動分開評量。

**來源：** 來源：鎖定研究事實 §§5–6；Brodersen 2010；Sokolova 2009；Gal 2016；Demšar 2006


## 12｜Frozen UCI3：不同資料與 C，對應不同優勢策略

這張表的數字直接來自備份鎖定的 Frozen UCI3 Balanced Accuracy，並不是這次重新訓練的結果。所有面板都用同一個色階，橘框代表同一資料集、同一 C 裡的最高值，包含並列。Hayes-Roth 通常是 FIRST_MATCH 較好或並列；Car 的四個 C 都由 Global Strength 取得最高 BA；Balance 在 C 二到四由 Standard 較高，到 C 五才轉成 Global。這支持目前範圍內沒有 universal winner，但沒有多次實驗的不確定性估計，不能把表格中的差距直接當成統計顯著。

**這張圖要證明什麼：** 在這三個 frozen datasets 與四個 C 設定中，沒有 universal winner。

**來源：** 來源：鎖定研究事實 §8；48 個 BA 數值直接轉錄，非本次重新訓練；無誤差棒或顯著性結論


## 13｜目前貢獻：共同證據上的系統性比較

把前面的流程、定義和數據放在一起，我們目前的貢獻可以說成：將既有的 prediction 與 conflict mechanisms，整合到相同的 frozen Federated LEM2 結構產物，再系統性研究 client fragmentation 的影響。這裡 Policy 星號等於一個函數，是概念性的研究表達，不是說我們已經訓練好一個選策略的模型。比較適合的 policy 可能取決於資料、規則結構、衝突工作量以及 client 設定。這個說法保留目前 evidence 的範圍，也避免把結果包裝成普遍性優勝結論。

**這張圖要證明什麼：** 貢獻定位在研究設計與機制比較，結論隨資料與設定而定。

**來源：** 來源：鎖定研究事實 §§5–9；Policy* 為研究概念表達，並非已擬合的預測模型


## 14｜可重現性：研究快照與本機驗證各自標示

工程部分也要清楚標示證據是哪個版本。備份記錄的研究分支 snapshot head 是 b12730d 開頭，PR 五在當時是 draft、open、尚未合併；其 Linux CI 記錄為 Python 三點十二、compile 通過、105 個測試通過。這不是本次重新查詢 GitHub 的即時狀態。另外，前面環境設定驗證的是 frozen main，用 Python 三點十三點五跑過一百項測試。兩個結果不能混成同一次驗證。本次 UCI 連線受阻，所以簡報的 frozen 數據仍是轉錄；Linux CI 也不能代替 Windows 實機雙擊測試。

**這張圖要證明什麼：** 105 tests 屬備份研究分支；100 tests 屬本次 main，兩者不是同一份驗證。

**來源：** 來源：repository_state.json；鎖定事實 §10；本次環境驗證記錄（main 31b078bb…）


## 15｜下一步：把機制證據推進到統計證據

最後想請老師和組員決定三件事。第一，正式論文是否就以 client fragmentation 如何影響 conflict workload 與 policy performance 作為主線。第二，資料集要擴充到什麼範圍，才能涵蓋不同的類別不平衡以及規則重疊型態。第三，統計設計要先固定多個 seeds 和 splits，保留相同條件下的成對比較，再決定 Friedman 加 post-hoc 或 paired Wilcoxon 的適用方式。目前這份結果適合用來說明機制和形成研究假設，下一步才是把它推進到可支持正式統計推論的證據。

**這張圖要證明什麼：** 需要共同決定研究問題、資料範圍與重複實驗的統計設計。

**來源：** 來源：鎖定研究事實 §§6–7；會議講法收尾；Demšar (2006)


# 教授可能問的五個問題

## 1. 你們的 conflict 到底怎麼定義？

主要是 prediction-time conflict：同一 test object 命中規則的 decisions 超過一種。Exact conflict 指完全相同 antecedent、不同 decision，只是補充結構稽核，不能代表所有推論衝突。

## 2. UNION 為什麼不會自己把 conflict 消掉？

UNION 是聚合。完整規則身分包含 antecedent 與 decision，所以 X→A 與 X→B 是不同規則，都會保留。非完全相同的條件也可能重疊；需要在 test object 的 matching rules 上由 policy 做決策。

## 3. Standard Voting 跟 Global Strength 差在哪？

Standard 把 matching rules 的 pooled positive support 大小逐條加總，因此同一 object 可透過多條 rule 重複貢獻。Global 先把同類 matching rules 的 support object IDs 做聯集，再除以 pooled training class size。這兩種分數不能跨策略直接比大小。

## 4. 為什麼要改 FIRST_MATCH？Voting 一定比較好嗎？

我們沒有預設要淘汰 FIRST_MATCH，而是量化其 order sensitivity，再在相同 frozen artifact 上比較其他既有策略。Frozen UCI3 中 Hayes 常由 FIRST_MATCH 最佳或並列，沒有 evidence 支持 voting 一定更好。

## 5. Client 變多是不是一定 conflict 也更多？

不是。C 改變 fragmentation，可能改變規則與重疊，但不是單調性定理。鎖定文件記錄 frozen datasets 的 C5 endpoint 高於 C2；這不足以推論每個中間 C 嚴格增加，更不足以泛化到其他 datasets 或 seeds。


# 會議備註

平手處理與無匹配的 default class 需沿用同一 frozen implementation；本簡報沒有自行新增 tie-breaking 定義。引用以附檔為準；正式稿 FIRST_MATCH 的方法細節需回原 PDF 補 page-level citation。