"""Which of the six policies is best? Dataset-level comparison on complete datasets.

For each scenario x variant x policy: mean accuracy / balanced accuracy (dataset
means over 42 seeds), mean within-dataset rank (1 = best), number of datasets
where the policy is (co-)best, and gain over FIRST_MATCH.  Also the size of the
policy effect: max-min spread per model, and the share of datasets whose best
policy beats the worst by > 1 pp.  Friedman test across policies per condition.

Usage: python policy_ranking.py <interim_dir> <out_dir>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon

interim, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
res = pd.read_csv(interim / 'RESULTS.csv.gz')
comp = pd.read_csv(interim / 'COMPLETENESS.csv')
res = res[res.dataset.isin(set(comp[comp.status == 'COMPLETE'].dataset))]
POL = ['FIRST_MATCH', 'SIMPLE_VOTING', 'STANDARD_VOTING', 'GLOBAL_STRENGTH', 'POPULATION_STANDARD', 'POPULATION_GLOBAL']
SC = ['CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01']
rows, effect = [], []
for var in ('A_ALL_RULES', 'B2_TRUE_AS_FALLBACK'):
    for sc in SC:
        d = res[(res.rule_variant == var) & (res.scenario == sc)]
        acc = d.pivot_table(index='dataset', columns='selection_policy', values='accuracy_pct')[POL]
        ba = d.pivot_table(index='dataset', columns='selection_policy', values='balanced_accuracy_pct')[POL]
        rank_acc = acc.rank(axis=1, ascending=False, method='average')
        rank_ba = ba.rank(axis=1, ascending=False, method='average')
        best = acc.eq(acc.max(axis=1), axis=0)
        fried = friedmanchisquare(*[acc[p] for p in POL]).pvalue if acc.nunique(axis=1).gt(1).any() else np.nan
        spread = acc.max(axis=1) - acc.min(axis=1)
        effect.append(dict(variant=var, scenario=sc, datasets=len(acc), mean_spread_pp=spread.mean(),
                           median_spread_pp=spread.median(), share_spread_gt_1pp=float((spread > 1).mean()),
                           friedman_p=fried))
        top = acc.mean().idxmax()
        for p in POL:
            diff = acc[p] - acc['FIRST_MATCH']
            p_vs_top = (wilcoxon(acc[p] - acc[top]).pvalue if p != top and (acc[p] - acc[top]).abs().gt(1e-9).sum() >= 6
                        else np.nan)
            rows.append(dict(variant=var, scenario=sc, policy=p, mean_acc=acc[p].mean(), mean_ba=ba[p].mean(),
                             mean_rank_acc=rank_acc[p].mean(), mean_rank_ba=rank_ba[p].mean(),
                             datasets_best=int(best[p].sum()), gain_vs_first_match=diff.mean(),
                             wilcoxon_p_vs_top=p_vs_top, top_policy=top))
tab, eff = pd.DataFrame(rows), pd.DataFrame(effect)
tab.to_csv(out / 'policy_ranking.csv', index=False)
eff.to_csv(out / 'policy_effect_size.csv', index=False)
pd.set_option('display.width', 250)
print(eff.round(3).to_string(index=False))
print(tab.drop(columns=['top_policy']).round(2).to_string(index=False))
