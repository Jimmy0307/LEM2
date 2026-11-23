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
