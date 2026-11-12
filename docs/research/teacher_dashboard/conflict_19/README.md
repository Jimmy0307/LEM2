# 19 張 Conflict Rate (%) 正式資料表

方法：Classical Rough Set 正域約簡 + LEM2；聯邦式為本地歸納後合併。
只讀取 NONE 結構診斷；不把六策略重複計算成六份 Conflict。Conflict Rate (%) = 衝突物件數 / 全部評估物件數 × 100；pp = 兩個百分率直接相減。跨 Seed 的 Mean 與 pooled ratio 可能不同；每表同時保留分母與兩種均值。

| # | CSV | 列數 | 內容 |
|---:|---|---:|---|
| 01 | [01_IID_ALL_CONFIGS.csv](01_IID_ALL_CONFIGS.csv) | 1260 | All Classical IID rule-set configurations; policy-independent conflict |
| 02 | [02_IID_BALANCE.csv](02_IID_BALANCE.csv) | 420 | IID Balance Scale by Seed, split, topology |
| 03 | [03_IID_CAR.csv](03_IID_CAR.csv) | 420 | IID Car Evaluation by Seed, split, topology |
| 04 | [04_IID_HAYES.csv](04_IID_HAYES.csv) | 420 | IID Hayes-Roth by Seed, split, topology |
| 05 | [05_IID_C0.csv](05_IID_C0.csv) | 252 | IID configuration C0 (C0 = Centralized) |
| 06 | [06_IID_C2.csv](06_IID_C2.csv) | 252 | IID configuration C2 (C0 = Centralized) |
| 07 | [07_IID_C3.csv](07_IID_C3.csv) | 252 | IID configuration C3 (C0 = Centralized) |
| 08 | [08_IID_C4.csv](08_IID_C4.csv) | 252 | IID configuration C4 (C0 = Centralized) |
| 09 | [09_IID_C5.csv](09_IID_C5.csv) | 252 | IID configuration C5 (C0 = Centralized) |
| 10 | [10_IID_IN_SAMPLE.csv](10_IID_IN_SAMPLE.csv) | 630 | IID FULL_DATA; never conflate Full Data with holdout |
| 11 | [11_IID_HOLDOUT.csv](11_IID_HOLDOUT.csv) | 630 | IID HOLDOUT_80_20; never conflate Full Data with holdout |
| 12 | [12_NONIID_ALPHA_01.csv](12_NONIID_ALPHA_01.csv) | 504 | Dirichlet label skew alpha=0.1 (complete 42 Seeds) |
| 13 | [13_NONIID_ALPHA_05.csv](13_NONIID_ALPHA_05.csv) | 504 | Dirichlet label skew alpha=0.5 (complete 42 Seeds) |
| 14 | [14_IID_SEEDPREFIX_01.csv](14_IID_SEEDPREFIX_01.csv) | 15 | First 1 seeds; same three datasets; SD is resampling sensitivity |
| 15 | [15_IID_SEEDPREFIX_07.csv](15_IID_SEEDPREFIX_07.csv) | 15 | First 7 seeds; same three datasets; SD is resampling sensitivity |
| 16 | [16_IID_SEEDPREFIX_21.csv](16_IID_SEEDPREFIX_21.csv) | 15 | First 21 seeds; same three datasets; SD is resampling sensitivity |
| 17 | [17_IID_SEEDPREFIX_42.csv](17_IID_SEEDPREFIX_42.csv) | 15 | First 42 seeds; same three datasets; SD is resampling sensitivity |
| 18 | [18_PAIRED_IID_VS_NONIID_01.csv](18_PAIRED_IID_VS_NONIID_01.csv) | 504 | Exact same seed/dataset/C paired percent-point contrast; alpha=0.1 |
| 19 | [19_PAIRED_IID_VS_NONIID_05.csv](19_PAIRED_IID_VS_NONIID_05.csv) | 504 | Exact same seed/dataset/C paired percent-point contrast; alpha=0.5 |

主矩陣 42 Seeds + IID/non-IID；本報表不代表新增外部 UCI 實驗已完成。
