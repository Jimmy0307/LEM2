# 188 × 42 LEM2 TIMEOUT 性能診斷（網站）
- 資料來源：使用者 2026-11-23 18:16 上傳的 per_source_observed.csv（181來源）、per_source_scaling.csv（48組），SHA256 見研究分支同目錄 `TIMEOUT_ANALYSIS_REVIEWED.md`。
- Gzip 內容是原始 CSV 的**逐位元可逆壓縮**；研究／網頁雙分支引用相同 Git blob。
- 此頁以瀏覽器 `DecompressionStream("gzip")` 讀原始資料並繪 SVG，散點使用成功模型最大 wall，不隱瞞右設限；CI full-size 成功者 median 與 TIMEOUT 分別繪圖。
- scaling CSV 未提供 1,800 Rows 的 wall seconds；只畫 10k 的耗時實測與未校正的 n^(2+g) 外推，沒有杜撰 1,800 耗時。
- 不重新訓練、不調整 TIMEOUT／排程器、不改變原 30,078 Success／179 complete 或原 Accuracy/BA/Coverage/Conflict。
- 研究解讀：GitHub `research/expanded-42seeds-20261120/docs/research/expanded_188_42seeds/timeout_analysis_20261123/TIMEOUT_ANALYSIS_REVIEWED.md`。
