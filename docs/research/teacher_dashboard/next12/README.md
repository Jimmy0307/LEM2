# 另外 12 個公開資料集（與前 20 個來源不重複）

狀態：**PASS_ALL_12_SOURCES**；成功 12/12、失敗 0/12。不可將失敗當成零或成功結果。
第一輪 Seed=42，Classical LEM2 C0/C3，各資料集共 14 列分類／結構結果、2 列 Train-only 補充規則。

| Dataset | UCI ID | 類型與研究特性 | Source rows | Prepared rows | 資料狀態 |
|---|---:|---|---:|---:|---|
| [Ionosphere Radar Return](https://archive.ics.uci.edu/dataset/52) | 52 | 351 cases, 34 raw continuous features, binary radar validity | 351 | 351 | PASS_ONE_SEED |
| [Yeast Protein Localization](https://archive.ics.uci.edu/dataset/110) | 110 | Ten-class protein localization, class imbalance and rare classes | 1484 | 1200 | PASS_ONE_SEED |
| [Image Segmentation](https://archive.ics.uci.edu/dataset/50) | 50 | Seven regional image labels from 3x3 image regions; potential shared-image leakage | 210 | 210 | PASS_ONE_SEED |
| [Statlog Vehicle Silhouettes](https://archive.ics.uci.edu/dataset/149) | 149 | Four classes and 18 extracted shape attributes; orientation shift sensitivity | 846 | 845 | PASS_ONE_SEED |
| [Heart Disease Cleveland (binary)](https://archive.ics.uci.edu/dataset/45) | 45 | 303 records, continuous and categorical clinical measures; binary presence >0 | 303 | 303 | PASS_ONE_SEED |
| [Raisin Morphology](https://archive.ics.uci.edu/dataset/850) | 850 | 900 rows, two balanced visual grain varieties and continuous shape features | 900 | 900 | PASS_ONE_SEED |
| [Wine Quality (binary>=6 protocol)](https://archive.ics.uci.edu/dataset/186) | 186 | Originally ordered wine quality labels; explicit secondary BINARY >=6 target task | 6497 | 1600 | PASS_ONE_SEED |
| [Student Final-Grade (binary >=10)](https://archive.ics.uci.edu/dataset/320) | 320 | 649 source records, six PRE-grade features only; explicit G3 final score >=10 target | 649 | 649 | PASS_ONE_SEED |
| [Vertebral Column](https://archive.ics.uci.edu/dataset/212) | 212 | 310 rows, six continuous biomechanics variables, possible two-vs-three target variant | 310 | 310 | PASS_ONE_SEED |
| [Higher-Ed Dropout and Academic Success](https://archive.ics.uci.edu/dataset/697) | 697 | 4424 records, three classes, 36 source predictors; pre-enrollment coded attributes only | 4424 | 1800 | PASS_ONE_SEED |
| [Blood Transfusion Service Center](https://archive.ics.uci.edu/dataset/176) | 176 | Taiwan donor retention 748 records, RFM/T numeric and 24% positive | 748 | 748 | PASS_ONE_SEED |
| [Fertility](https://archive.ics.uci.edu/dataset/244) | 244 | 100 volunteers, rare binary outcome and small sample instability | 100 | 100 | PASS_ONE_SEED |

### 注意
- 這批 12 份資料是新增來源，不計入前 20 份的 Seed 42 實驗結論。
- 新資料仍為固定欄位與抽樣，不能宣稱原始全量或原始全部特徵已執行。
- Wine Quality 的任務被明確轉成 >=6 二元分類；原本是有序品質標籤。
- Image Segmentation 來源圖像可能重複產生關聯區塊，隨機切分有群組洩漏風險。
- 若有任何來源失敗，記錄其實際原因，待修復後才加入比較。
