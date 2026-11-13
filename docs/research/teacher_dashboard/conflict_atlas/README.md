# 公開資料集逐 row／逐 column 與 Coverage × Conflict 實驗圖譜

- 已驗證：20 個新資料集，20 個相同 Seed 的 C0/C3 配對；實際已發布子集 22 份，欄位 125 筆，類別統計 80 筆。
- 核心定義：Coverage=P(至少一條規則命中)；Conflict=P(命中規則指向兩種以上類別)；無衝突覆蓋=Coverage−Conflict。
- 實驗僅 Seed 42，80/20；不是 42 Seeds。資料表原始 rows 與 prepared rows 不可混用。
- 本次還保留兩個前期電商／工業資料的 profile；不把它們重新計入「新增 20 資料集」。

## 20 配對資料集：Coverage vs Conflict（百分點）

| 資料集 | 原始→實際 rows | C0 Coverage | C3 Coverage | C0 Conflict | C3 Conflict | Δ 無衝突覆蓋 |
|---|---:|---:|---:|---:|---:|---:|
| [adult_income](https://archive.ics.uci.edu/dataset/2) | 48,842→1,800 | 73.61% | 99.44% | 2.22% | 30.56% | -2.50 pp |
| [bank_marketing](https://archive.ics.uci.edu/dataset/222) | 45,211→1,800 | 25.83% | 75.00% | 0.28% | 7.50% | +41.94 pp |
| [banknote](https://archive.ics.uci.edu/dataset/267) | 1,372→1,372 | 47.08% | 66.42% | 0.00% | 0.00% | +19.34 pp |
| [breast_diagnostic](https://archive.ics.uci.edu/dataset/17) | 569→569 | 51.33% | 92.04% | 0.00% | 7.08% | +33.63 pp |
| [covertype](https://archive.ics.uci.edu/dataset/31) | 581,012→1,800 | 18.28% | 48.75% | 1.66% | 18.28% | +13.85 pp |
| [dry_bean](https://archive.ics.uci.edu/dataset/602) | 13,611→1,600 | 13.17% | 25.39% | 0.00% | 0.00% | +12.23 pp |
| [eeg_eye_state](https://archive.ics.uci.edu/dataset/264) | 14,980→1,800 | 4.17% | 13.61% | 0.00% | 1.67% | +7.78 pp |
| [german_credit](https://archive.ics.uci.edu/dataset/144) | 1,000→1,000 | 55.50% | 86.50% | 1.50% | 35.50% | -3.00 pp |
| [grid_stability](https://archive.ics.uci.edu/dataset/471) | 10,000→1,800 | 68.61% | 99.44% | 1.67% | 49.44% | -16.94 pp |
| [haberman](https://archive.ics.uci.edu/dataset/43) | 306→306 | 4.92% | 54.10% | 0.00% | 0.00% | +49.18 pp |
| [htru2](https://archive.ics.uci.edu/dataset/372) | 17,898→1,800 | 14.17% | 34.17% | 0.00% | 1.39% | +18.61 pp |
| [iris](https://archive.ics.uci.edu/dataset/53) | 150→150 | 100.00% | 100.00% | 0.00% | 0.00% | +0.00 pp |
| [letter](https://archive.ics.uci.edu/dataset/59) | 20,000→900 | 74.18% | 95.05% | 15.38% | 75.27% | -39.01 pp |
| [magic_gamma](https://archive.ics.uci.edu/dataset/159) | 19,020→1,800 | 8.06% | 8.89% | 0.00% | 0.28% | +0.56 pp |
| [mushroom](https://archive.ics.uci.edu/dataset/73) | 8,124→1,600 | 98.12% | 100.00% | 0.00% | 1.25% | +0.62 pp |
| [phishing](https://archive.ics.uci.edu/dataset/327) | 11,055→1,600 | 15.94% | 20.94% | 0.00% | 3.75% | +1.25 pp |
| [rice](https://archive.ics.uci.edu/dataset/545) | 3,810→1,600 | 46.25% | 68.75% | 0.00% | 0.62% | +21.88 pp |
| [sonar](https://archive.ics.uci.edu/dataset/151) | 208→208 | 14.63% | 29.27% | 0.00% | 4.88% | +9.76 pp |
| [spambase](https://archive.ics.uci.edu/dataset/94) | 4,601→1,800 | 0.83% | 2.50% | 0.00% | 0.56% | +1.11 pp |
| [wine](https://archive.ics.uci.edu/dataset/109) | 178→178 | 77.78% | 100.00% | 2.78% | 47.22% | -22.22 pp |

## 實驗資料下載
- [逐資料集 row 數／類別數與欄位型態](DATASET_ROW_COUNTS_AND_TYPES.csv)
- [每個決策類別的 rows 與比例](DATASET_CLASS_COUNTS.csv)
- [每個因子的欄位型態、缺值、基數、分位數](DATASET_COLUMN_TYPES_AND_STATS.csv)
- [20 配對 Coverage×Conflict 全量資訊](PUBLIC20_COVERAGE_CONFLICT_PAIRS.csv)
- [依特徵型態分組](PUBLIC20_BY_FEATURE_TYPE.csv)
- [依類別數分組](PUBLIC20_BY_CLASS_COUNT.csv)
- [以無衝突覆蓋變化排序](PUBLIC20_CONFLICT_TRADEOFF_RANKED.csv)
- [資料來源與公式稽核](MANIFEST.json)

## 解讀限制
C0 與 C3 是不同的學習規則集合，不能直接宣稱新增規則造成衝突。對衝突的因果檢驗需使用固定 R 的逐條加入／移除實驗，並以 train/validation 選規則，最後 test 僅評估。
無衝突覆蓋率也不能視為正確覆蓋率，因為單一錯誤候選同樣算在內。
