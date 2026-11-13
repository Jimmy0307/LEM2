# 三條規則層級研究線：實驗證據與限制

來源：六份已發布公開資料子集；所有模型使用既有 Classical 約簡＋LEM2，Seed 42。獨立 C0/C3 規則集。
所有改動的決策都只參照 Train；最後 Test 只計算結果。這仍是單一 Seed 的探索性實驗。

## Track A｜Letter：26 類候選與衝突分解
- 逐類別樣本／命中／正確候選率：[資料表](TRACK_A_LETTER_PER_CLASS.csv)
- 逐測試物件是否真正命中正確決策：[資料表](TRACK_A_LETTER_OBJECT_CASES.csv)
- 逐條規則前件、訓練支持度、純度與測試命中：[資料表](TRACK_A_LETTER_INDUCED_RULES.csv)

## Track B｜Wine／Grid：Train-only Conflict-Aware Pruning
- [規則修剪前後的 Train/Test Coverage、Conflict、正確候選與 BA](TRACK_B_WINE_GRID_PRUNING.csv)
- 固定訓練集評分 = 正確候選率 − 0.70×衝突率 − 0.10×No Match 率；規則刪除以 Train 內的分布判斷，不以 Test 調參。
- 注意：現有規則是在整個 Train 上歸納，所以這不是獨立內部驗證；下一步需 Nested Train/Validation，不能用它宣稱泛化最佳。

## Track C｜Haberman／Banknote／Rice：逐條新增規則的邊際效益
- [每一條候選補充規則的邊際 Coverage／Conflict／Candidate 與 Train-only Gate 結果](TRACK_C_RULE_BY_RULE_MARGINAL.csv)
- [安全選入後 Train/Test 結果與回退分類影響](TRACK_C_SAFE_SUPPLEMENT_SUMMARY.csv)
- 保留 Structural Union 與 No-Match fallback-only 兩種處理的不同定義；不將它們混稱為相同 Coverage。

## 解讀前必讀
- 凍結基線：[`PUBLIC20_BASE_RESULTS.csv`](../data/PUBLIC20_BASE_RESULTS.csv)。
- 方法使用同一 Seed 42；尚無 42 Seeds 的統計有效性。
- 不保證 Conflict-Aware 剪枝一定優於原始 LEM2；負面或零效益一樣會儲存。
- 這些模型不是原典 MLEM2 補充規則或 VC-DomLEM。
- [本批可重現實驗 manifest](MANIFEST.json)。
