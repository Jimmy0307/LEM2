# 教授報告索引｜188 資料集 × 42 seeds × 19 原始欄位

**凍結快照：2026-11-23 11:42:29（台灣時間），模型 30,078/31,584，179/188 資料集完整。**
以下均為從已發布真實 checkpoint 和 metadata 產生的結果；仍屬期中分析，不能宣稱 188 個來源全部完成。

## 優先打開哪個檔案？

| 需求 | 檔案 | 資料量與用途 |
|---|---|---|
| **每個資料集的 Rows、特徵、標籤類別數、四情境各策略最高 Accuracy、Coverage/Conflict** | [MASTER_188_DATASET_SCENARIO_VARIANT_42SEED.csv](./MASTER_188_DATASET_SCENARIO_VARIANT_42SEED.csv) | **1,504 列 × 41 欄**，188 datasets ×4 scenarios ×2 variants；完成 1,432 列、部分 10 列、無結果 62 列。主檔推薦 Excel 篩選用 |
| **188 資料集元資料** | [DATASET_CATALOG_188.csv](./full42_generated/DATASET_CATALOG_188.csv) | 188 列；原始/使用 Rows、features、類別數、特徵型態、來源 |
| **42 seeds 每個情境的最佳 Accuracy 與 Coverage** | [DATASET_SCENARIO_BEST_42SEED.csv](./full42_generated/DATASET_SCENARIO_BEST_42SEED.csv) | 1,442 列；同分保留全部策略、BA、Test Coverage、Candidate Coverage、Conflict、Rule count |
| **六種決策策略的真實 42-seed 平均績效** | [DATASET_POLICY_METRICS_42SEED.csv](./full42_generated/DATASET_POLICY_METRICS_42SEED.csv) | **8,652 列**；逐 dataset×scenario×variant×policy 的 Accuracy、BA、Coverage、衝突、規則數與 seeds 數 |
| **個別資料集跨四情境哪個策略 Accuracy 最高** | [DATASET_OVERALL_WINNER_42SEED.csv](./full42_generated/DATASET_OVERALL_WINNER_42SEED.csv) | 181 有結果（179 完整、2 部分），另 7 筆無結果 |
| **真正的 19 欄完整逐模型原始實驗數值** | [FULL42_19COL_A_ALL_RULES.csv.gz](./full42_generated/FULL42_19COL_A_ALL_RULES.csv.gz)／[FULL42_19COL_B2_TRUE_AS_FALLBACK.csv.gz](./full42_generated/FULL42_19COL_B2_TRUE_AS_FALLBACK.csv.gz) | 每個版本 **180,468 列 ×19 欄**，合計 360,936 列；zip/gzip 解壓後以 Excel、Python 開啟 |
| **來源/執行驗收憑證** | [BUILD_RECEIPT.json](./full42_generated/BUILD_RECEIPT.json) | GitHub Actions 一次性產生並通過 19 欄、每版本列數、snapshot、188 任務等斷言 |

### 重要閱讀限制

- **原始 Rows** 不等於 **實際使用 Rows**；**n_classes（標籤類別數）** 不等於原始文字標籤名稱。現有 REGISTRY 不保存全部類別的實際值，必須回到原始來源或各 source metadata 驗證；報告不會猜測。
- **「最高 Accuracy」** 是在同一資料集、同一實驗情境及同一規則版本下，先平均已完成的 seeds，再比較六種策略的 Accuracy；並保留同分的所有策略。沒有完整 42 seeds 的組合會標示 PARTIAL 或 NO_OBSERVED_RESULT。
- **Coverage**、Candidate Coverage 與 Conflict 在同模型下不因六種決策策略不同而改變；它們衡量的不是相同概念，不能把測試覆蓋率提升直接解釋成分類績效改善。
- **歷史 5-seed** 分析的數字在本資料夾另外保留，請勿與新版 42-seed 方法獲勝次數混合。

## 179 個完整資料集的簡單描述性比較（A_ALL_RULES）

以下數字是「**每資料集先取六策略中最高的 42-seed 平均 Accuracy，再對 179 個資料集平均**」，故不代表單一固定決策策略的準確率，也不作為新方法效能顯著性的檢定。

| 情境 | Mean best Accuracy (%) | Mean Test Coverage (%) | Mean Candidate Coverage (%) | Mean Conflict (%) |
|---|---:|---:|---:|---:|
| CENTRALIZED | 60.18 | 27.56 | 23.01 | 1.26 |
| FED_IID | 62.60 | 46.75 | 39.06 | 13.08 |
| FED_A05 | 60.15 | 64.63 | 51.78 | 27.20 |
| FED_A01 | 55.24 | 86.54 | 68.50 | 55.48 |

跨四情境看每個 dataset 的 Accuracy 最佳情境，**有 179 個完整資料集**，有些情境會同分，因此單純「出現於最佳」的次數為 CENTRALIZED 47、FED_IID 106、FED_A05 27、FED_A01 14，合計可能超過 179。若對同分情境分配分數，則分別為 41、100、25.5、12.5。

原始表格以下沿用舊版資料來源與讀法。

---

# LEM2 dataset × label-count × policy catalog (2026-11-23 11:42:29 UTC+8)
**Snapshot-locked, not final.** Sources are published GitHub research artifacts. No synthetic values.
**188** registry tasks, **179** 42-seed complete; remaining 9 partial/failed. Do not conflate the archival 5-seed winners with newest 42-seed accuracy.

| File | Rows | Meaning |
|---|---:|---|
| DATASET_CATALOG_188.csv | 188 | Every eligible source: cohort, original/used rows, feature count, feature names, class count, minority share, sources, 42-seed completeness |
| BEST_POLICY_5SEED_BY_DATASET_SCENARIO.csv | 727 | Legacy 5-seed absolute winner Accuracy and BA per dataset × scenario; ties included; 25 scenario records missing |
| ALL_POLICY_5SEED_BY_DATASET_SCENARIO.csv | 4,362 | Legacy 5-seed absolute mean Accuracy and BA per dataset × scenario × all six methods |
| PAIRED_DELTA_42SEED_BY_DATASET_POLICY.csv | 6,444 | Current 42-seed paired Fed-minus-central Accuracy/BA differences for 179 completed datasets ×3 fed scenarios×2 variants×6 policies |
| 19_COLUMN_CONTRACT.md | — | Actual 19-col definition and source links, including full legacy 19-column CSV and current gzip full metric record artifact |

## Critical reading rules
1. **Label counts are not label identities.** `n_classes` is supported by `REGISTRY.csv`; actual class-value names are absent from that aggregate, so `actual_class_labels` is explicitly marked NOT_PUBLISHED_IN_AGGREGATE. Inspect dataset-specific SOURCE.json or original data to verify labels. No labels invented.
2. **Absolute winner is from legacy 5 seeds only.** The 42-seed `PAIRED_DELTA` cannot identify the 42-seed *absolute* best method without the 42-seed `RESULTS.csv.gz` itself. Those latest 42-seed compressed raw rows and per-model checkpoints are available in the repository, but were not extracted into this catalog.
3. Coverage, candidate coverage and conflicts at **dataset × method** granularity are not in legacy `DATASET_BEST.csv`. They must be computed from the existing `FULL_SCALE_19COL.csv` (5 seeds) or `interim/RESULTS.csv.gz` (42 seeds). Missing fields in the 5-seed policy catalog are explicitly marked, never filled with group averages.
4. Old full scale may have partial 5-seed scenario records. Each 5-seed entry carries `n_seeds_5seed`; compare only within matched protocols.
5. 42-seed study is INCOMPLETE (30,078/31,584 success models and 98 logged timeouts). Freeze all charts to `20261123T114229`.

## Original evidence
- [Complete original 19-column 5-seed CSV](https://github.com/Jimmy0307/LEM2/blob/a928b067f9d976cb26899e314f2b2604dfbb9c1b/docs/research/full_scale_20261118/FULL_SCALE_19COL.csv)
- [Original B2 19-column 5-seed CSV](https://github.com/Jimmy0307/LEM2/blob/a928b067f9d976cb26899e314f2b2604dfbb9c1b/docs/research/full_scale_20261118/FULL_SCALE_19COL_B2.csv)
- [42-seed raw result gzip](https://github.com/Jimmy0307/LEM2/blob/a928b067f9d976cb26899e314f2b2604dfbb9c1b/docs/research/expanded_188_42seeds/interim/RESULTS.csv.gz)
- [Legacy dataset best by method](https://github.com/Jimmy0307/LEM2/blob/a928b067f9d976cb26899e314f2b2604dfbb9c1b/docs/research/full_scale_20261118/DATASET_BEST.csv)
- [Original full-scale registry metadata](https://github.com/Jimmy0307/LEM2/blob/a928b067f9d976cb26899e314f2b2604dfbb9c1b/docs/research/full_scale_20261118/REGISTRY.csv)
- [42-seed paired dataset-level deltas](https://github.com/Jimmy0307/LEM2/blob/a928b067f9d976cb26899e314f2b2604dfbb9c1b/docs/research/expanded_188_42seeds/interim/interim_dataset_level_deltas_complete_datasets.csv)
