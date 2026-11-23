"""Summarise conflict_diag.csv: where conflict comes from, and how each policy
does on conflicting rows versus random choice and the oracle.
Dataset-level: pool rows over seeds within a dataset, then average datasets."""
import sys
from pathlib import Path

import pandas as pd

d = pd.read_csv(sys.argv[1])
out = Path(sys.argv[2])
d = d[d.variant.notna()]
POL = ['FIRST_MATCH', 'SIMPLE_VOTING', 'STANDARD_VOTING', 'GLOBAL_STRENGTH', 'POPULATION_STANDARD', 'POPULATION_GLOBAL']
SC = ['CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01']
cnt = ['test_rows', 'nohit', 'single', 'multi', 'multi_with_true_rule', 'multi_truth_in', 'multi_random_expected',
       'single_truth_in'] + [f'multi_correct_{p}' for p in POL] + [f'nohit_correct_{p}' for p in POL]
g = d.groupby(['variant', 'scenario', 'dataset'])
ds = g[cnt].sum()
ds = ds.join(g[['rules', 'true_rules', 'single_class_clients', 'empty_reduct_clients', 'multi_mean_candidates', 'n_classes']].mean())
ds = ds.reset_index()
ds['conflict_pct'] = 100 * ds.multi / ds.test_rows
ds['nohit_pct'] = 100 * ds.nohit / ds.test_rows
ds['true_share_of_conflict'] = 100 * ds.multi_with_true_rule / ds.multi.where(ds.multi > 0)
ds['oracle_on_conflict'] = 100 * ds.multi_truth_in / ds.multi.where(ds.multi > 0)
ds['random_on_conflict'] = 100 * ds.multi_random_expected / ds.multi.where(ds.multi > 0)
for p in POL:
    ds[f'{p}_on_conflict'] = 100 * ds[f'multi_correct_{p}'] / ds.multi.where(ds.multi > 0)
ds['single_precision'] = 100 * ds.single_truth_in / ds.single.where(ds.single > 0)
cols = (['conflict_pct', 'nohit_pct', 'true_share_of_conflict', 'rules', 'true_rules', 'single_class_clients',
         'empty_reduct_clients', 'multi_mean_candidates', 'single_precision', 'oracle_on_conflict', 'random_on_conflict']
        + [f'{p}_on_conflict' for p in POL])
summ = ds.groupby(['variant', 'scenario'])[cols].mean().reindex(SC, level=1).reset_index()
summ['datasets'] = ds.groupby(['variant', 'scenario']).dataset.nunique().reindex(
    pd.MultiIndex.from_frame(summ[['variant', 'scenario']])).to_numpy()
summ.to_csv(out / 'conflict_summary.csv', index=False)
ds.to_csv(out / 'conflict_by_dataset.csv', index=False)
pd.set_option('display.width', 300)
print(summ.round(2).T.to_string())
