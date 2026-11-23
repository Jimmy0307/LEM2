"""Build the 19-column master tables (same schema/validation as full_scale_20261118).

Outputs (from an interim package's RESULTS.csv.gz / TIMINGS.csv.gz):
  FULL_SCALE_19COL_42SEEDS.csv.gz      A_ALL_RULES, one row per model x policy (FULL19 schema)
  FULL_SCALE_19COL_42SEEDS_B2.csv.gz   B2_TRUE_AS_FALLBACK, same schema
  SUMMARY_19COL_A.csv / _B2.csv        same 19 columns aggregated per scenario x policy
                                       (complete datasets; dataset-level means, equal weight per dataset)
  PARTITION_STATUS.csv                 how the federated clients were obtained
  SUMMARY_19COL.md                     readable tables

Usage: python build_19col.py <repo> <interim_dir> <out_dir>
"""
import sys
from pathlib import Path

import pandas as pd

repo, interim, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(repo))
from experiments.full_scale_20261118.aggregate import check_19  # noqa: E402
from experiments.full_scale_20261118.shard import FULL19  # noqa: E402

out.mkdir(parents=True, exist_ok=True)
res = pd.read_csv(interim / 'RESULTS.csv.gz')
comp = pd.read_csv(interim / 'COMPLETENESS.csv')
complete = set(comp[comp.status == 'COMPLETE'].dataset)
SCEN_ORDER = {'CENTRALIZED': 0, 'FED_IID': 1, 'FED_A05': 2, 'FED_A01': 3}
POL_ORDER = ['FIRST_MATCH', 'SIMPLE_VOTING', 'STANDARD_VOTING', 'GLOBAL_STRENGTH', 'POPULATION_STANDARD', 'POPULATION_GLOBAL']
MEAN_COLS = ['rule_count', 'test_coverage_pct', 'candidate_coverage_pct', 'accuracy_pct', 'balanced_accuracy_pct',
             'conflict_rate_pct']
COUNT_COLS = ['train_rows', 'test_rows', 'no_match_count', 'covered_count', 'true_in_candidate_count']  # medians


def summary(df):
    d = df[df.dataset.isin(complete)]
    keys = ['scenario', 'distribution', 'dirichlet_alpha', 'split_mode', 'system', 'client_count', 'selection_policy']
    per_ds = d.groupby(keys + ['dataset'], dropna=False)[MEAN_COLS + COUNT_COLS].mean().reset_index()
    agg = per_ds.groupby(keys, dropna=False).agg(
        **{c: (c, 'mean') for c in MEAN_COLS}, **{c: (c, 'median') for c in COUNT_COLS},
        n_datasets=('dataset', 'nunique')).reset_index()
    agg['dataset'] = agg.n_datasets.map(lambda n: f'{n} complete datasets')
    agg['seed'] = '1-42'
    agg['_s'] = agg.scenario.map(SCEN_ORDER)
    agg['_p'] = agg.selection_policy.map(POL_ORDER.index)
    agg = agg.sort_values(['_s', '_p'])
    return agg[['scenario'] + FULL19]


def md_table(t):
    show = t.copy()
    for c in MEAN_COLS:
        show[c] = show[c].map(lambda v: f'{v:.2f}')
    for c in COUNT_COLS:
        show[c] = show[c].map(lambda v: f'{v:,.0f}')
    show['dirichlet_alpha'] = show['dirichlet_alpha'].map(lambda v: '' if pd.isna(v) else f'{v:g}')
    cols = list(show.columns)
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    lines += ['| ' + ' | '.join(str(v) for v in r) + ' |' for r in show.itertuples(index=False)]
    return '\n'.join(lines)


tables = {}
for variant, suffix in (('A_ALL_RULES', ''), ('B2_TRUE_AS_FALLBACK', '_B2')):
    v = res[res.rule_variant == variant].copy()
    full = v.sort_values(['dataset', 'seed', 'system', 'distribution', 'dirichlet_alpha', 'selection_policy'])[FULL19]
    check_19(full)  # identical validation to the full-scale lane
    full.to_csv(out / f'FULL_SCALE_19COL_42SEEDS{suffix}.csv.gz', index=False, compression='gzip')
    s = summary(v)
    s.to_csv(out / f'SUMMARY_19COL{suffix or "_A"}.csv', index=False)
    tables[variant] = (s, len(full))

tim = pd.read_csv(interim / 'TIMINGS.csv.gz')
fed = tim[tim.scenario != 'CENTRALIZED']
ps = fed.groupby(['scenario', 'partition_status']).size().unstack(fill_value=0)
ps.to_csv(out / 'PARTITION_STATUS.csv')
ps_md = '\n'.join(['| scenario | ' + ' | '.join(ps.columns) + ' |', '|---|' + '---:|' * len(ps.columns)]
                  + [f'| {i} | ' + ' | '.join(f'{v:,}' for v in r) + ' |' for i, r in ps.iterrows()])

(out / 'SUMMARY_19COL.md').write_text(f"""# 19 欄總表（188 資料集 × 42 seeds，期中）

逐筆總表（與 full_scale 的 FULL19 欄位、`check_19` 驗證完全相同）：
- `FULL_SCALE_19COL_42SEEDS.csv.gz`（A_ALL_RULES）：{tables['A_ALL_RULES'][1]:,} 列
- `FULL_SCALE_19COL_42SEEDS_B2.csv.gz`（B2_TRUE_AS_FALLBACK）：{tables['B2_TRUE_AS_FALLBACK'][1]:,} 列

每一列＝一個資料集 × 一個 seed × 一個情境 × 一種決策策略。情境由 system / distribution / dirichlet_alpha 三欄決定
（集中式：CENTRALIZED, IID, 空；Fed IID：FEDERATED, IID, 空；Fed α=0.5 / 0.1：FEDERATED, DIRICHLET_NONIID, 0.5 / 0.1）。
TIMEOUT 等未完成模型不在逐筆表內，列於 MISSING.csv / FAILURES.csv。

下方彙總表為同樣 19 欄、每列一個「情境 × 決策策略」：先在每個完整資料集內對 42 個 seeds 取平均，再跨資料集彙總——
百分比欄位與 rule_count 取資料集平均；計數欄位（train_rows、test_rows、no_match_count、covered_count、
true_in_candidate_count）取資料集中位數，避免被大型資料集主導。

## A_ALL_RULES
{md_table(tables['A_ALL_RULES'][0])}

## B2_TRUE_AS_FALLBACK
{md_table(tables['B2_TRUE_AS_FALLBACK'][0])}

## 聯邦客戶端的分配方式（partition_status，已完成模型）
{ps_md}
""", encoding='utf-8')
print(tables['A_ALL_RULES'][1], tables['B2_TRUE_AS_FALLBACK'][1])
print(ps.to_string())
