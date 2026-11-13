# 另外 12 個公開資料集（與前 20 個來源不重複）

狀態：**PARTIAL_SOURCES_UNAVAILABLE**；成功 0/12、失敗 12/12。不可將失敗當成零或成功結果。
第一輪 Seed=42，Classical LEM2 C0/C3，各資料集共 14 列分類／結構結果、2 列 Train-only 補充規則。

| Dataset | UCI ID | 類型與研究特性 | Source rows | Prepared rows | 資料狀態 |
|---|---:|---|---:|---:|---|
| [Ionosphere Radar Return](https://archive.ics.uci.edu/dataset/52) | 52 | 351 cases, 34 raw continuous features, binary radar validity | — | — | FAIL_NOT_IMPUTED |
| [Yeast Protein Localization](https://archive.ics.uci.edu/dataset/110) | 110 | Ten-class protein localization, class imbalance and rare classes | — | — | FAIL_NOT_IMPUTED |
| [Image Segmentation](https://archive.ics.uci.edu/dataset/50) | 50 | Seven regional image labels from 3x3 image regions; potential shared-image leakage | — | — | FAIL_NOT_IMPUTED |
| [Statlog Vehicle Silhouettes](https://archive.ics.uci.edu/dataset/149) | 149 | Four classes and 18 extracted shape attributes; orientation shift sensitivity | — | — | FAIL_NOT_IMPUTED |
| [Wheat Seeds](https://archive.ics.uci.edu/dataset/236) | 236 | 210 rows, three equally sized wheat kernel types and seven continuous measurements | — | — | FAIL_NOT_IMPUTED |
| [Raisin Morphology](https://archive.ics.uci.edu/dataset/850) | 850 | 900 rows, two balanced visual grain varieties and continuous shape features | — | — | FAIL_NOT_IMPUTED |
| [Wine Quality (binary>=6 protocol)](https://archive.ics.uci.edu/dataset/186) | 186 | Originally ordered wine quality labels; explicit secondary BINARY >=6 target task | — | — | FAIL_NOT_IMPUTED |
| [QSAR Biodegradation](https://archive.ics.uci.edu/dataset/254) | 254 | 1055 chemical records, 41 descriptors in source and two biodegradation classes | — | — | FAIL_NOT_IMPUTED |
| [Vertebral Column](https://archive.ics.uci.edu/dataset/212) | 212 | 310 rows, six continuous biomechanics variables, possible two-vs-three target variant | — | — | FAIL_NOT_IMPUTED |
| [Higher-Ed Dropout and Academic Success](https://archive.ics.uci.edu/dataset/697) | 697 | 4424 records, three classes, 36 source predictors; pre-enrollment coded attributes only | — | — | FAIL_NOT_IMPUTED |
| [Blood Transfusion Service Center](https://archive.ics.uci.edu/dataset/176) | 176 | Taiwan donor retention 748 records, RFM/T numeric and 24% positive | — | — | FAIL_NOT_IMPUTED |
| [Fertility](https://archive.ics.uci.edu/dataset/244) | 244 | 100 volunteers, rare binary outcome and small sample instability | — | — | FAIL_NOT_IMPUTED |

### 注意
- 這批 12 份資料是新增來源，不計入前 20 份的 Seed 42 實驗結論。
- 新資料仍為固定欄位與抽樣，不能宣稱原始全量或原始全部特徵已執行。
- Wine Quality 的任務被明確轉成 >=6 二元分類；原本是有序品質標籤。
- Image Segmentation 來源圖像可能重複產生關聯區塊，隨機切分有群組洩漏風險。
- 若有任何來源失敗，記錄其實際原因，待修復後才加入比較。
