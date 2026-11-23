"""Row-level conflict diagnostic on a sample of completed sources (read only).

Re-fits models exactly as experiments.full_scale_20261118.model.run_model does
(same split, partition, feature typing, fit_model, match/variant/resolve), but
keeps per-row candidate information so we can measure, on conflicting test rows:
  * how often each of the six policies picks the true class,
  * the random-among-candidates baseline and the oracle (truth among candidates),
  * how much conflict involves empty-antecedent (TRUE -> d) rules,
  * client degeneracy (single-class clients, empty reducts).
Every policy's overall accuracy is checked against the official RESULTS rows.

Usage: python conflict_diagnostic.py <repo> <interim_dir> <out_csv> [max_rows] [seeds] [workers]
"""
import gzip
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

REPO = sys.argv[1]
sys.path.insert(0, REPO)
ROOTS = [Path('/home/user/lem2_runs/expanded_188_42seeds/checkpoints'), Path('/home/user/lem2_runs/source_prefetch/checkpoints')]
SCENARIOS = ('CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01')
VARIANTS = ('A_ALL_RULES', 'B2_TRUE_AS_FALLBACK')


def load_source(dataset):
    for root in ROOTS:
        p = root / dataset.replace(':', '__') / 'source.pkl'
        if p.exists():
            with p.open('rb') as fh:
                return pickle.load(fh)
    raise FileNotFoundError(dataset)


def one_model(source, dataset, seed, scenario):
    from fedrs.experiment import fit_model, nested_split
    from fedrs.partition import constrained_partition, original_partition
    from fedrs.predict import POLICIES, _decision_masks, match_matrix, resolve_scalable, variant_matrix
    from roughset.preprocessing import detect_feature_types
    from experiments.full_scale_20261118.model import REGIMES
    dev, val, test = nested_split(source.frame, source.target, seed)
    if scenario == 'CENTRALIZED':
        clients = {'central': dev}
    else:
        regime, _ = REGIMES[scenario]
        try:
            clients = original_partition(dev, source.target, 3, seed, regime)
        except ValueError:
            clients, _, _ = constrained_partition(dev, source.target, 3, seed, regime)
    continuous, categorical = (detect_feature_types(dev, source.features, unique_numeric_threshold=10)
                               if source.dynamic_types else (source.continuous, source.categorical))
    fm = fit_model(source.features, continuous, categorical, source.target, clients, dev, val, test,
                   'EQUAL_WIDTH_3', 'CLASSICAL', 1.0)
    M = match_matrix(fm.frames['test'], fm.rules)
    truth = fm.frames['test'][source.target].astype(str).to_numpy()
    ctx = fm.ctx
    lookup = {c: i for i, c in enumerate(ctx.classes)}
    tidx = np.asarray([lookup.get(v, -1) for v in truth])
    base = dict(dataset=dataset, seed=seed, scenario=scenario, test_rows=len(truth), rules=ctx.n_rules,
                true_rules=int(ctx.is_empty.sum()),
                single_class_clients=int(sum(m.n_classes == 1 for m in fm.local.values())),
                empty_reduct_clients=int(sum(len(m.reduct) == 0 for m in fm.local.values())),
                n_classes=len(set(truth)))
    out = []
    for variant in VARIANTS:
        mv = variant_matrix(M, ctx, variant)
        present = _decision_masks(mv, ctx) if ctx.n_rules else np.zeros((len(truth), 0), bool)
        ncand = present.sum(axis=1)
        tin = np.zeros(len(truth), bool)
        ok = tidx >= 0
        tin[ok] = present[np.flatnonzero(ok), tidx[ok]]
        multi, single, nohit = ncand >= 2, ncand == 1, ncand == 0
        true_fired = mv[:, ctx.is_empty].any(axis=1) if ctx.is_empty.any() else np.zeros(len(truth), bool)
        row = dict(base, variant=variant, nohit=int(nohit.sum()), single=int(single.sum()), multi=int(multi.sum()),
                   multi_with_true_rule=int((multi & true_fired).sum()),
                   multi_truth_in=int((multi & tin).sum()),
                   multi_random_expected=float((tin[multi] / ncand[multi]).sum()) if multi.any() else 0.0,
                   multi_mean_candidates=float(ncand[multi].mean()) if multi.any() else 0.0,
                   single_truth_in=int((single & tin).sum()))
        for p in POLICIES:
            pred = resolve_scalable(mv, ctx, p)
            correct = pred == truth
            row[f'acc_{p}'] = float(100 * correct.mean())
            row[f'multi_correct_{p}'] = int(correct[multi].sum())
            row[f'nohit_correct_{p}'] = int(correct[nohit].sum())
        out.append(row)
    return out


def run_dataset(dataset, seeds):
    source = load_source(dataset)
    rows = []
    for seed in seeds:
        for sc in SCENARIOS:
            try:
                rows.extend(one_model(source, dataset, seed, sc))
            except Exception as exc:  # recorded, never hidden
                rows.append(dict(dataset=dataset, seed=seed, scenario=sc, error=f'{type(exc).__name__}: {exc}'[:300]))
    return rows


def main():
    interim, out_csv = Path(sys.argv[2]), Path(sys.argv[3])
    max_rows = int(sys.argv[4]) if len(sys.argv) > 4 else 10000
    seeds = [int(s) for s in (sys.argv[5] if len(sys.argv) > 5 else '1,2,3').split(',')]
    workers = int(sys.argv[6]) if len(sys.argv) > 6 else 3
    comp = pd.read_csv(interim / 'COMPLETENESS.csv')
    reg = pd.read_csv(interim / 'SOURCE_REGISTRY.csv')
    sample = comp[comp.status == 'COMPLETE'].merge(reg[['dataset', 'original_rows']], on='dataset')
    sample = sorted(sample[sample.original_rows <= max_rows].dataset)
    print(json.dumps({'datasets': len(sample), 'seeds': seeds}), flush=True)
    rows = []
    with ProcessPoolExecutor(workers) as pool:
        futs = {pool.submit(run_dataset, d, seeds): d for d in sample}
        for i, f in enumerate(as_completed(futs), 1):
            rows.extend(f.result())
            if i % 10 == 0:
                print(f'{i}/{len(sample)} datasets', flush=True)
    diag = pd.DataFrame(rows)
    # Faithfulness check against the official results.
    res = pd.read_csv(interim / 'RESULTS.csv.gz', usecols=['dataset', 'seed', 'scenario', 'rule_variant',
                                                             'selection_policy', 'accuracy_pct'])
    res = res[res.dataset.isin(sample) & res.seed.isin(seeds)]
    off = res.pivot_table(index=['dataset', 'seed', 'scenario', 'rule_variant'], columns='selection_policy',
                          values='accuracy_pct').reset_index().rename(columns={'rule_variant': 'variant'})
    m = diag.dropna(subset=['variant']).merge(off, on=['dataset', 'seed', 'scenario', 'variant'], how='left')
    pols = [c[4:] for c in diag.columns if c.startswith('acc_')]
    worst = max(float((m[f'acc_{p}'] - m[p]).abs().max()) for p in pols)
    diag['faithful_max_abs_diff_pct'] = worst
    diag.to_csv(out_csv, index=False)
    print(json.dumps({'models': int(diag.variant.notna().sum() / 2), 'errors': int(diag.get('error', pd.Series()).notna().sum()),
                      'max_abs_accuracy_diff_vs_official': worst}), flush=True)


if __name__ == '__main__':
    main()
