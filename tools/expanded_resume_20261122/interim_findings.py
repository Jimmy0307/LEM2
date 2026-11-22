"""Interim (partial) analysis of the 188 x 42-seed run for progress reporting.

Unit of analysis = dataset (registry task): seed-level paired differences are
first averaged within each dataset, then compared across datasets, because the
188 registry tasks are not independent domains and seeds are not independent
datasets.  Primary set = datasets whose 168 models all completed (42 seeds x 4
scenarios); sensitivity set = every dataset with at least one matched pair.

Usage: python interim_findings.py <audit_dir> <out_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

EPS = 1e-9
SCEN = ['FED_IID', 'FED_A05', 'FED_A01']
SCEN_LABEL = {'FED_IID': 'Fed IID', 'FED_A05': 'Fed Dirichlet a=0.5', 'FED_A01': 'Fed Dirichlet a=0.1'}
VARIANTS = ['A_ALL_RULES', 'B2_TRUE_AS_FALLBACK']
METRICS = {'accuracy_pct': 'Accuracy', 'balanced_accuracy_pct': 'Balanced accuracy'}


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (len(p) - rank) * p[idx])
        adj[idx] = min(1.0, running)
    return adj


def wilcoxon_p(x):
    x = np.asarray(x, float)
    if np.all(np.abs(x) < EPS) or len(x) < 6:
        return np.nan
    return float(wilcoxon(x, zero_method='wilcox', alternative='two-sided').pvalue)


def delta_table(paired, datasets):
    """Dataset-level mean fed-minus-central deltas, summarised across datasets."""
    sub = paired[paired.dataset.isin(datasets)]
    rows, per_dataset = [], []
    for (sc, var, pol), g in sub.groupby(['scenario_fed', 'rule_variant', 'selection_policy']):
        dm = g.groupby('dataset')[[f'{m}_delta_fed_minus_central' for m in METRICS]].mean()
        dm['seeds'] = g.groupby('dataset').seed.nunique()
        for d, r in dm.iterrows():
            per_dataset.append({'dataset': d, 'scenario_fed': sc, 'rule_variant': var,
                                'selection_policy': pol, **r.to_dict()})
        row = {'scenario_fed': sc, 'rule_variant': var, 'selection_policy': pol, 'n_datasets': len(dm)}
        for m in METRICS:
            x = dm[f'{m}_delta_fed_minus_central']
            row.update({f'{m}_mean': x.mean(), f'{m}_median': x.median(),
                        f'{m}_q25': x.quantile(.25), f'{m}_q75': x.quantile(.75),
                        f'{m}_fed_worse': int((x < -EPS).sum()), f'{m}_tie': int((x.abs() <= EPS).sum()),
                        f'{m}_fed_better': int((x > EPS).sum()), f'{m}_wilcoxon_p': wilcoxon_p(x)})
        rows.append(row)
    out = pd.DataFrame(rows)
    for m in METRICS:
        out[f'{m}_wilcoxon_p_holm'] = holm(out[f'{m}_wilcoxon_p'].fillna(1.0))
    return out, pd.DataFrame(per_dataset)


def structural_table(paired, datasets):
    """Coverage / conflict / rule-count deltas (policy independent: use one policy)."""
    sub = paired[paired.dataset.isin(datasets) & (paired.selection_policy == 'FIRST_MATCH')]
    cols = ['test_coverage_pct_delta_fed_minus_central', 'conflict_rate_pct_delta_fed_minus_central',
            'rule_count_delta_fed_minus_central', 'test_coverage_pct_central', 'test_coverage_pct_fed',
            'conflict_rate_pct_central', 'conflict_rate_pct_fed', 'rule_count_central', 'rule_count_fed']
    dm = sub.groupby(['scenario_fed', 'rule_variant', 'dataset'])[cols].mean()
    return dm.groupby(['scenario_fed', 'rule_variant']).agg(['mean', 'median']).reset_index()


def policy_table(results, datasets):
    sub = results[results.dataset.isin(datasets)]
    dm = sub.groupby(['scenario', 'rule_variant', 'selection_policy', 'dataset']).accuracy_pct.mean().reset_index()
    dm['rank'] = dm.groupby(['scenario', 'rule_variant', 'dataset']).accuracy_pct.rank(ascending=False, method='average')
    spread = dm.groupby(['scenario', 'rule_variant', 'dataset']).accuracy_pct.agg(lambda s: s.max() - s.min())
    tab = dm.groupby(['scenario', 'rule_variant', 'selection_policy']).agg(
        mean_accuracy=('accuracy_pct', 'mean'), mean_rank=('rank', 'mean')).reset_index()
    return tab, spread.groupby(['scenario', 'rule_variant']).agg(['mean', 'median', 'max']).reset_index()


def variant_table(results, datasets):
    sub = results[results.dataset.isin(datasets)]
    piv = sub.pivot_table(index=['dataset', 'seed', 'scenario', 'selection_policy'], columns='rule_variant',
                          values='accuracy_pct')
    piv['b2_minus_a'] = piv['B2_TRUE_AS_FALLBACK'] - piv['A_ALL_RULES']
    dm = piv.groupby(['scenario', 'selection_policy', 'dataset']).b2_minus_a.mean()
    return dm.groupby(['scenario', 'selection_policy']).agg(
        mean='mean', median='median', n_datasets='count',
        b2_better=lambda s: int((s > EPS).sum()), tie=lambda s: int((s.abs() <= EPS).sum()),
        b2_worse=lambda s: int((s < -EPS).sum())).reset_index()


def fmt(x, nd=2):
    return '—' if pd.isna(x) else f'{x:.{nd}f}'


def pfmt(p):
    return '—' if pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')


def headline_md(tab, metric, variant):
    lines = ['| 情境 | 決策策略 | 資料集數 | 平均差 | 中位數 | Fed 較差 / 持平 / 較好 | Wilcoxon p (Holm) |',
             '|---|---|---:|---:|---:|---|---:|']
    t = tab[tab.rule_variant == variant]
    for sc in SCEN:
        for _, r in t[t.scenario_fed == sc].sort_values('selection_policy').iterrows():
            lines.append(f"| {SCEN_LABEL[sc]} | {r.selection_policy} | {r.n_datasets} | {fmt(r[f'{metric}_mean'])} | "
                         f"{fmt(r[f'{metric}_median'])} | {r[f'{metric}_fed_worse']} / {r[f'{metric}_tie']} / "
                         f"{r[f'{metric}_fed_better']} | {pfmt(r[f'{metric}_wilcoxon_p_holm'])} |")
    return '\n'.join(lines)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    status = json.loads((src / 'STATUS.json').read_text())
    comp = pd.read_csv(src / 'COMPLETENESS.csv')
    reg = pd.read_csv(src / 'SOURCE_REGISTRY.csv')
    reg = reg[reg.status == 'PENDING']
    results = pd.read_csv(src / 'RESULTS.csv')
    paired = pd.read_csv(src / 'PAIRED_COMPARISONS.csv')
    failures = pd.read_csv(src / 'FAILURES.csv') if (src / 'FAILURES.csv').stat().st_size > 1 else pd.DataFrame()

    complete = sorted(comp[comp.status == 'COMPLETE'].dataset)
    any_pairs = sorted(paired.dataset.unique())
    prim, prim_ds = delta_table(paired, complete)
    sens, _ = delta_table(paired, any_pairs)
    struct = structural_table(paired, complete)
    pol, spread = policy_table(results, complete)
    var = variant_table(results, complete)
    prim.to_csv(out / 'interim_fed_minus_central_complete_datasets.csv', index=False)
    prim_ds.to_csv(out / 'interim_dataset_level_deltas_complete_datasets.csv', index=False)
    sens.to_csv(out / 'interim_fed_minus_central_all_paired_datasets.csv', index=False)
    struct.to_csv(out / 'interim_structure_coverage_conflict_rules.csv', index=False)
    pol.to_csv(out / 'interim_policy_accuracy_and_rank.csv', index=False)
    var.to_csv(out / 'interim_b2_minus_a.csv', index=False)

    rows = reg.set_index('dataset').original_rows
    done_rows, all_rows = rows.reindex(complete), rows
    pending = comp[comp.status != 'COMPLETE'].merge(reg[['dataset', 'original_rows']], on='dataset')
    big_pending = pending.sort_values('original_rows', ascending=False).head(12)
    fail_summary = (failures.groupby(['dataset', 'status']).size().reset_index(name='n')
                    if not failures.empty else pd.DataFrame(columns=['dataset', 'status', 'n']))

    bins = [0, 500, 5_000, 50_000, float('inf')]
    labels = ['< 500', '500 – 5,000', '5,000 – 50,000', '≥ 50,000']
    all_bin = pd.cut(all_rows, bins, labels=labels, right=False).value_counts().reindex(labels)
    done_bin = pd.cut(done_rows, bins, labels=labels, right=False).value_counts().reindex(labels)
    size_lines = '\n'.join(f'| {lab} | {int(all_bin[lab])} | {int(done_bin[lab])} | '
                           f'{100 * done_bin[lab] / all_bin[lab]:.0f}% |' for lab in labels)
    a = prim[prim.rule_variant == 'A_ALL_RULES']
    bullets = []
    for sc in SCEN:
        s = a[a.scenario_fed == sc]
        bullets.append(f"- **{SCEN_LABEL[sc]}**（A_ALL_RULES）：六種決策策略的資料集層級平均準確率差（Fed − 集中式）介於 "
                       f"{fmt(s.accuracy_pct_mean.min())} 至 {fmt(s.accuracy_pct_mean.max())} 個百分點；"
                       f"中位數介於 {fmt(s.accuracy_pct_median.min())} 至 {fmt(s.accuracy_pct_median.max())}；"
                       f"Fed 較差的資料集數 {s.accuracy_pct_fed_worse.min()}–{s.accuracy_pct_fed_worse.max()} / {int(s.n_datasets.max())}。")
    sa = struct[struct.rule_variant == 'A_ALL_RULES']
    cov_lines = []
    for sc in SCEN:
        r = sa[sa.scenario_fed == sc]
        if len(r):
            r = r.iloc[0]
            cov_lines.append(
                f"| {SCEN_LABEL[sc]} | {fmt(r[('test_coverage_pct_central', 'mean')])} → {fmt(r[('test_coverage_pct_fed', 'mean')])} "
                f"| {fmt(r[('conflict_rate_pct_central', 'mean')])} → {fmt(r[('conflict_rate_pct_fed', 'mean')])} "
                f"| {fmt(r[('rule_count_central', 'mean')], 1)} → {fmt(r[('rule_count_fed', 'mean')], 1)} |")
    pol_a = pol[pol.rule_variant == 'A_ALL_RULES'].pivot(index='selection_policy', columns='scenario', values='mean_rank')
    pol_lines = ['| 決策策略 | ' + ' | '.join(pol_a.columns) + ' |', '|---|' + '---:|' * len(pol_a.columns)]
    for p_, r in pol_a.iterrows():
        pol_lines.append(f'| {p_} | ' + ' | '.join(fmt(v) for v in r) + ' |')
    sp_a = spread[spread.rule_variant == 'A_ALL_RULES']
    var_lines = ['| 情境 | 決策策略 | B2−A 平均 | 中位數 | B2 較好 / 持平 / 較差 |', '|---|---|---:|---:|---|']
    for _, r in var.iterrows():
        var_lines.append(f'| {r.scenario} | {r.selection_policy} | {fmt(r["mean"])} | {fmt(r["median"])} | '
                         f'{r.b2_better} / {r.tie} / {r.b2_worse} |')

    md = f"""# 期中結果（INTERIM）— 188 資料集 × 42 seeds 擴充實驗

> **狀態：INCOMPLETE，非最終結果。** 產生時間：{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（UTC+8）。
> 本文件只供進度報告；最終結論須待 STATUS.json 為 COMPLETE。數字會隨後續補跑改變。

## 1. 完成度
- 模型：**{status['complete_models']:,} / {status['expected_models']:,}**（{100*status['complete_models']/status['expected_models']:.1f}%）；結果列 {status['complete_rows']:,} / {status['expected_rows']:,}
- 完整完成的資料集（168/168 模型成功）：**{len(complete)} / 188**；有任何配對結果的資料集：{len(any_pairs)}
- 已記錄失敗：{len(failures)} 筆（全部狀態：{', '.join(f"{k}={v}" for k, v in failures.status.value_counts().items()) if not failures.empty else '無'}）

### 樣本偏誤（重要）
排程依預估運算量由重到輕排序、並受記憶體限制，因此已完成集合**不是隨機子集**：最大的資料集尚未完成，許多小型資料集也仍在佇列中。
- 已完成資料集原始列數中位數 **{int(done_rows.median()):,}**；全部 188 個為 {int(all_rows.median()):,}

| 原始列數 | 全部 | 已完整完成 | 完成比例 |
|---|---:|---:|---:|
{size_lines}

- 最大的未完成資料集（CI 上單一模型常達 2,700 秒上限）：
{chr(10).join(f"  - {r.dataset}（{int(r.original_rows):,} 列，已成功 {r.complete_models}/168）" for _, r in big_pending.iterrows())}

因此以下結論**只代表目前已完成的 {len(complete)} 個資料集**，不能推論到全部 188 個任務。

## 2. 主要比較：聯邦（C=3）− 集中式，準確率（百分點）
分析單位＝資料集：先在每個資料集內對 42 個 seeds 的配對差（同 seed、同規則版本、同決策策略、同來源 SHA）取平均，再跨資料集彙總。檢定為 Wilcoxon signed-rank（雙尾），36 個條件以 Holm 校正。負值＝聯邦較差。

{chr(10).join(bullets)}

### 2a. A_ALL_RULES（完整資料集，n={len(complete)}）
{headline_md(prim, 'accuracy_pct', 'A_ALL_RULES')}

### 2b. B2_TRUE_AS_FALLBACK（完整資料集）
{headline_md(prim, 'accuracy_pct', 'B2_TRUE_AS_FALLBACK')}

平衡準確率（balanced accuracy）的同型表格見 `interim_fed_minus_central_complete_datasets.csv`；
納入所有有配對資料集（含未跑完者，以現有 seeds 平均）的敏感度分析見 `interim_fed_minus_central_all_paired_datasets.csv`。

## 3. 結構面：覆蓋率、衝突率、規則數（A_ALL_RULES，資料集平均：集中式 → 聯邦）
| 情境 | 測試覆蓋率 % | 衝突率 % | 規則數 |
|---|---|---|---|
{chr(10).join(cov_lines)}

## 4. 六種決策策略（A_ALL_RULES）
資料集內排名（1＝準確率最高，同分取平均）跨資料集平均：

{chr(10).join(pol_lines)}

同一模型下六種策略的準確率最大差距（資料集平均）：
{chr(10).join(f"- {r['scenario']}：平均 {fmt(r['mean'])}、中位數 {fmt(r['median'])}、最大 {fmt(r['max'])} 百分點" for _, r in sp_a.iterrows())}

（依程式內建檢查，策略間差距必然不超過該模型的衝突率。）

## 5. 規則版本：B2_TRUE_AS_FALLBACK − A_ALL_RULES（準確率，完整資料集）
{chr(10).join(var_lines)}

## 6. 已記錄失敗
{chr(10).join(f"- {r.dataset}：{r.status} × {r.n}" for _, r in fail_summary.iterrows()) or '- 無'}

TIMEOUT 為協定規定的單一模型 2,700 秒上限；這些資料集在原 full_scale CI 執行中同樣大多逾時。失敗保留在分母中（MISSING.csv / FAILURES.csv）。

## 7. 判讀限制
1. 期中、非隨機缺漏：大型資料集尚未完成，且其中部分資料集的集中式模型系統性逾時，最終配對可能大量缺漏。
2. 188 個是 registry 任務，不是 188 個獨立領域；Wilcoxon 檢定把資料集視為交換單位，僅作描述性參考。
3. 與原三資料集 factorial 實驗屬不同協定，不可合併。
4. 本期中結果取自 checkpoint 快照當下（見 SNAPSHOT_STAMP 與 INTERIM_README.md）。
"""
    (out / 'INTERIM_FINDINGS.md').write_text(md, encoding='utf-8')
    print(json.dumps({'complete_datasets': len(complete), 'paired_datasets': len(any_pairs),
                      'complete_models': status['complete_models']}))


if __name__ == '__main__':
    main()
