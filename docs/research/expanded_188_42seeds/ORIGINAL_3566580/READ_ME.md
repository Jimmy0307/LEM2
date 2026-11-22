# 188 筆資料集 × 42 seeds 補跑檢查點

**狀態：尚未完成。此檔為執行中的檢查點，不是最終研究結果。**

{
  "datasets": 188,
  "complete_datasets": 8,
  "expected_models": 31584,
  "complete_models": 1559,
  "expected_rows": 379008,
  "complete_rows": 18708,
  "missing_models": 30025,
  "status": "INCOMPLETE"
}

設定：seed 1–42；集中式、聯邦 C=3 IID、Dirichlet α=0.5／0.1；六種決策策略；A／B2 兩種規則版本；64/16/20 切分。沿用既有 full_scale_20261118 完整列數與選欄設定。

COMPLETENESS.csv 是逐資料集完成率，MISSING.csv 是所有缺跑模型。RESULTS.csv 是已完成的實測結果；PAIRED_COMPARISONS.csv 是相同資料集、seed、策略、規則版本與來源 SHA 的成對比較。PAIRED_SUMMARY.csv 可能不足 42 seeds，須查 count，不可當作全量結論。

每個資料集需要 168 次訓練與 2,016 筆結果才算完成。預期共 31,584 次訓練、379,008 筆結果；24 筆同源重複來源已明列排除。

程式本地提交 3566580；28 項相關測試通過。程式分支 research/expanded-42seeds-20261120。此包不包含原始第三方資料。
