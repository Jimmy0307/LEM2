# 內容鎖定摘要

本簡報依使用者指定，執行備份中的 `CLAUDE_PPT_AND_FLOWCHART_PROMPT.md`，以 `CLAUDE_LOCKED_RESEARCH_FACTS.md` 作為研究內容基準；未改動原始研究檔案。15 頁、16:9、繁體中文，每頁均附 speaker notes 與圖意說明。

| 鎖定項目 | 簡報採用內容 |
|---|---|
| 共同名稱 | Prediction Policies（預測策略）；FIRST_MATCH 不是 voting |
| 四種策略 | FIRST_MATCH / SIMPLE_VOTING / STANDARD_VOTING / GLOBAL_STRENGTH |
| Client count | C = 2, 3, 4, 5，是外層實驗變數 |
| Aggregation | 固定為 UNION；完整規則身分包含 antecedent + decision |
| Main conflict | Inference / prediction-time conflict：同一 x 命中的規則 decisions 超過一種 |
| Exact conflict | 相同 antecedent、不同 decision；僅 supplementary structural audit |
| Standard | Matching-rule support sum；本研究採跨 clients、decision-consistent pooled support |
| Global Strength | Matching-rule unique support-object union / pooled training class size |
| 來源與 adaptation | 既有方法原理與本研究 federated adaptation 分開標示 |
| 比較條件 | 相同 split、partition、reduct、rules、UNION、pre-resolution conflicts、default class |
| 結論範圍 | Frozen UCI3 觀察；不宣稱 universal best、voting 必勝或四種策略為本研究首創 |
| 統計推論 | 未新增 p-value、顯著性、誤差棒；多 seeds/splits 與檢定列為下一步 |

## 素材差異與處理

1. **既有海報的 aggregation 選項較多。** 原圖包含 intersection 與 quorum/majority 作為其他聚合選項；本次鎖定研究設定只使用 UNION。新流程圖只呈現固定 UNION，不將其他選項當成本次比較因素。
2. **Legacy diagnostics 與主指標。** 文獻核對稿提到 OSR，既有海報亦含 legacy diagnostic 用語。簡報依鎖定文件將 established metrics 作為主要評量，順序分歧使用 Variation Ratio；未將 OSR/CRA/CCR/H_rule 包裝為主要 publication metrics。
3. **測試數屬不同版本。** 備份的 research snapshot CI 是 Python 3.12、105 tests passed；本次既有 main 環境是 Python 3.13.5、100 tests passed。第 14 頁明確分開，不將兩者視為同次執行。
4. **Repository / PR 狀態是歷史快照。** Research head `b12730d0a777dbfbcf562e238e54dbf34e386091` 與 PR #5 Draft/Open/Not merged 都標示為備份記錄；未宣稱即時查詢 GitHub 狀態。
5. **UCI3 數值是轉錄。** 第 12 頁的 48 個 BA 數值直接來自鎖定事實 §8。此次沒有重新訓練；備份中的 `rough_set_outputs.zip` 是 housing 的另一條資料流程，不混入 UCI3 結果。
6. **缺少 conflict 逐點原始表。** 鎖定文件記錄 C5 endpoint 高於 C2，但未附逐點數據。因此第 6 頁只畫機制假設鏈，不臆造單調曲線或 conflict 數值。
7. **文獻核對邊界。** 使用附檔的 MD 與 DOCX 核對政策定義；本次沒有把來源論文重新全文驗證。FIRST_MATCH 正式稿方法敘述仍需回原 PDF 補頁碼。
8. **公平比較與 C 的角色。** 對同一 dataset × split × C 的各 policies 固定結構產物；不同 C 是不同實驗條件，並未宣稱不同 C 共享相同 partition 或 global rules。

備份中的 SHA256SUMS 已逐檔核對通過。圖片已檢視；MD/DOCX 已閱讀；housing 與其腳本只作備份背景，不在本次 PPT 製作範圍內執行。
