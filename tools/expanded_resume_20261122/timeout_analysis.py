"""Why do some sources hit the 2,700 s per-model deadline, and at what size?

Mechanism (fedrs.predict.resolve_scalable): test rows are deduplicated by their
rule-match pattern, then the support-union policies compute, per pattern and
class, |union of training-support sets of matching rules| via a boolean
(patterns x rules) @ (rules x train rows) product.  Cost ~ U * R * N_train.
With many rules nearly every test row is a distinct pattern (U ~ test rows ~ n),
so cost ~ n * R(n) * n.  With R(n) ~ n^g, wall(n) ~ wall(10k) * (n/10k)^(2+g).

This script (1) measures where the time goes, (2) validates the per-source
scaling law against sources that finished at full size locally, (3) applies it
to the timing-out / pending sources, (4) reports a pooled fit as a secondary
rule of thumb.

Usage: python timeout_analysis.py <interim_dir> <ci_dir> <out_dir>
"""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DEADLINE = 2700.0
PHASES = ['binning_fit_seconds', 'binning_apply_seconds', 'reduct_seconds', 'lem2_seconds',
          'support_context_seconds', 'match_seconds', 'predict_seconds']
SCEN = ['FED_IID', 'FED_A01']  # scenarios present in the CI ladder


def load_local(interim):
    t = pd.read_csv(interim / 'TIMINGS.csv.gz')
    r = pd.read_csv(interim / 'RESULTS.csv.gz')
    r = r[(r.rule_variant == 'A_ALL_RULES') & (r.selection_policy == 'FIRST_MATCH')]
    m = t.merge(r[['dataset', 'seed', 'scenario', 'train_rows', 'test_rows', 'rule_count']],
                on=['dataset', 'seed', 'scenario'], how='inner')
    m['source'] = 'local 42-seed run'
    return m


def load_ladder(ci):
    t = pd.concat([pd.read_csv(f) for f in glob.glob(str(ci / 'fs_timings_*.csv'))])
    t = t[t.phase == 'SCALE_LADDER'].copy()
    t['scale'] = t['scale'].astype(str).str.replace('.0', '', regex=False)
    lad = pd.concat([pd.read_csv(f) for f in glob.glob(str(ci / 'fs_ladder_*.csv'))])
    lad = lad[(lad.rule_variant == 'A_ALL_RULES') & (lad.selection_policy == 'FIRST_MATCH')].copy()
    lad['scale'] = lad['scale'].astype(str)
    m = t.merge(lad[['dataset', 'scenario', 'scale', 'scale_used_rows', 'train_rows', 'test_rows', 'rule_count']],
                on=['dataset', 'scenario', 'scale'], how='inner').drop_duplicates(['dataset', 'scenario', 'scale'])
    m['source'] = 'CI scale ladder'
    return m


def load_ci_full(ci):
    """CI full-size models (same hardware as the ladder): median wall and TIMEOUT counts."""
    t = pd.concat([pd.read_csv(f) for f in glob.glob(str(ci / 'fs_timings_*.csv'))])
    t = t[t.phase.isna()].drop_duplicates(['dataset', 'seed', 'scenario'], keep='last')
    f = pd.read_csv(ci / 'fs_failures.csv')
    f = f[f.status == 'TIMEOUT']
    return (t.groupby(['dataset', 'scenario']).wall_seconds.median(),
            t.groupby(['dataset', 'scenario']).size(),
            f.groupby(['dataset', 'scenario']).size())


def scaling_table(ladder, local, rows_by_ds, fails, ci_full):
    """Per (source, scenario): rule growth g, wall at 10k, predicted wall at full size."""
    full_obs = local.groupby(['dataset', 'scenario']).wall_seconds.median()
    to = fails.groupby(['dataset', 'scenario']).size()
    ci_med, ci_n, ci_to = ci_full
    out = []
    for (ds, sc), g in ladder[ladder.scale.isin(['1800', '10000'])].groupby(['dataset', 'scenario']):
        g = g.set_index('scale')
        if not {'1800', '10000'} <= set(g.index):
            continue
        r18, r10 = g.loc['1800', 'rule_count'], g.loc['10000', 'rule_count']
        w10 = g.loc['10000', 'wall_seconds']
        if r18 <= 0 or r10 <= 0 or w10 <= 0:
            continue
        gr = max(np.log(r10 / r18) / np.log(10000 / 1800), 0.0)
        n_full = float(rows_by_ds.get(ds, np.nan))
        expo = 2 + gr
        pred_full = w10 * (n_full / 10000) ** expo
        n_star = 10000 * (DEADLINE / w10) ** (1 / expo)
        out.append(dict(dataset=ds, scenario=sc, full_rows=int(n_full), rules_1800=int(r18), rules_10000=int(r10),
                        rule_growth_g=round(gr, 2), exponent=round(expo, 2), wall_10000_s=round(w10, 1),
                        predicted_full_s=round(pred_full), observed_full_median_s=round(full_obs.get((ds, sc), np.nan), 1),
                        ci_full_median_s=round(ci_med.get((ds, sc), np.nan), 1), ci_full_done=int(ci_n.get((ds, sc), 0)),
                        ci_full_timeouts=int(ci_to.get((ds, sc), 0)),
                        timeouts_local=int(to.get((ds, sc), 0)), rows_reaching_2700s=int(n_star),
                        many_rules=bool(r10 >= 500), degenerate_ladder=bool(min(r18, r10) < 20)))
    return pd.DataFrame(out)


def pooled_fit(both, rmin=500):
    d = both[(both.rule_count >= rmin) & (both.wall_seconds > 0.5)]
    W = d.train_rows * d.test_rows * d.rule_count
    x, y = np.log10(W), np.log10(d.wall_seconds)
    slope, icpt = np.polyfit(x, y, 1)
    r2 = np.corrcoef(x, y)[0, 1] ** 2
    return slope, icpt, r2, len(d), 10 ** ((np.log10(DEADLINE) - icpt) / slope)


def main():
    interim, ci, out = map(Path, sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    local, ladder = load_local(interim), load_ladder(ci)
    both = pd.concat([local, ladder], ignore_index=True)
    both = both[both.rule_count > 0]
    fails = pd.read_csv(interim / 'FAILURES.csv')
    comp = pd.read_csv(interim / 'COMPLETENESS.csv')
    reg = pd.read_csv(interim / 'SOURCE_REGISTRY.csv')
    reg = reg[reg.status == 'PENDING'][['dataset', 'original_rows']]
    rows_by_ds = reg.set_index('dataset').original_rows

    share = local[PHASES].sum() / local.wall_seconds.sum()
    slow = local[local.wall_seconds > 60]
    share_slow = slow[PHASES].sum() / slow.wall_seconds.sum()

    sc = scaling_table(ladder, local, rows_by_ds, fails, load_ci_full(ci))
    sc.to_csv(out / 'per_source_scaling.csv', index=False)
    # Validation on the SAME hardware as the ladder: CI full-size models.
    val = sc[(sc.ci_full_done >= 2) & (sc.ci_full_median_s > 5) & ~sc.degenerate_ladder].copy()
    val['ratio_pred_over_obs'] = val.predicted_full_s / val.ci_full_median_s
    val['censored'] = val.ci_full_timeouts > 0  # completed-only median is biased low when some timed out
    slope, icpt, r2, n_fit, w_star = pooled_fit(both)

    per = local.groupby('dataset').agg(median_wall_s=('wall_seconds', 'median'), max_wall_s=('wall_seconds', 'max'),
                                       median_rules=('rule_count', 'median'), models=('wall_seconds', 'size')).reset_index()
    per = per.merge(reg, on='dataset', how='left')
    per = per.merge(fails.groupby('dataset').size().rename('timeouts'), on='dataset', how='left').fillna({'timeouts': 0})
    per.to_csv(out / 'per_source_observed.csv', index=False)
    pending = comp[comp.status != 'COMPLETE'].merge(reg, on='dataset')

    # Figure 1: rows alone do not predict time
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ok = per[per.timeouts == 0]
    ax.scatter(ok.original_rows, ok.max_wall_s, s=14, alpha=.6, label='completed sources (slowest model)')
    to = (fails.groupby('dataset').size().rename('timeouts').reset_index()
          .merge(reg, on='dataset', how='left').assign(max_wall_s=DEADLINE))
    ax.scatter(to.original_rows, [DEADLINE * 1.2] * len(to), marker='x', color='crimson', s=70, label='sources with TIMEOUT')
    for _, r in pd.concat([to, ok.nlargest(4, 'original_rows')]).iterrows():
        ax.annotate(r.dataset.split(':')[1], (r.original_rows, DEADLINE * 1.2 if r.timeouts else r.max_wall_s),
                    fontsize=7, xytext=(3, 4), textcoords='offset points')
    ax.axhline(DEADLINE, color='crimson', ls='--', lw=1, label='2,700 s deadline')
    ax.set(xscale='log', yscale='log', xlabel='source rows', ylabel='model wall time (s)',
           title='Rows alone do not predict the timeout')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / 'fig1_rows_vs_wall.png', dpi=150)

    # Figure 2: per-source scaling curves (FED_IID), observed points + law
    fig, ax = plt.subplots(figsize=(8, 5.5))
    show = sc[(sc.scenario == 'FED_IID') & sc.many_rules & ~sc.degenerate_ladder
              & ((sc.predicted_full_s > 300) | (sc.timeouts_local > 0))]
    show = show.sort_values('predicted_full_s', ascending=False).head(10)
    for _, r in show.iterrows():
        g = ladder[(ladder.dataset == r.dataset) & (ladder.scenario == 'FED_IID')]
        xs = g.scale_used_rows.astype(float).to_numpy()
        ys = g.wall_seconds.to_numpy()
        line, = ax.plot(xs, ys, 'o')
        n_grid = np.logspace(np.log10(10000), np.log10(r.full_rows), 30)
        ax.plot(n_grid, r.wall_10000_s * (n_grid / 10000) ** r.exponent, '--', color=line.get_color(), lw=1)
        ax.plot([1800, 10000], [g[g.scale == '1800'].wall_seconds.median(), r.wall_10000_s], '-', color=line.get_color(), lw=1)
        obs = local[(local.dataset == r.dataset) & (local.scenario == 'FED_IID')]
        if len(obs):
            ax.plot([r.full_rows], [obs.wall_seconds.median()], 's', color=line.get_color(), ms=7)
        if r.timeouts_local:
            ax.plot([r.full_rows], [DEADLINE * 1.15], 'x', color=line.get_color(), ms=9, mew=2)
        ax.annotate(r.dataset.split(':')[1], (r.full_rows, min(r.wall_10000_s * (r.full_rows / 10000) ** r.exponent, 5e5)),
                    fontsize=7, color=line.get_color(), xytext=(3, 0), textcoords='offset points')
    ax.axhline(DEADLINE, color='crimson', ls='--', lw=1.2)
    ax.text(2000, DEADLINE * 1.1, '2,700 s deadline', color='crimson', fontsize=8)
    ax.set(xscale='log', yscale='log', xlabel='rows used', ylabel='model wall time (s), Fed IID',
           title='Per-source scaling (Fed IID): o CI ladder, ■ local full size, × local TIMEOUT,\n'
                 '-- n^(2+g) law through the 10k point (uncalibrated; ~2x high, see §3)', ylim=(0.1, 1e6))
    fig.tight_layout()
    fig.savefig(out / 'fig2_per_source_scaling.png', dpi=150)

    phase_lines = '\n'.join(f'| {p.replace("_seconds", "")} | {100 * share[p]:.1f}% | {100 * share_slow[p]:.1f}% |' for p in PHASES)
    val_lines = '\n'.join(f'| {r.dataset} | {r.scenario} | {r.rules_10000:,} | {r.full_rows:,} | {r.exponent} | '
                          f'{r.predicted_full_s:,} | {r.ci_full_median_s:,}{" *" if r.censored else ""} | {r.ratio_pred_over_obs:.2f} |'
                          for _, r in val.sort_values(['many_rules', 'ci_full_median_s'], ascending=False).iterrows())
    vm, vf = val[val.many_rules & ~val.censored].ratio_pred_over_obs, val[~val.many_rules].ratio_pred_over_obs
    cal = float(vm.median())  # systematic over-prediction of the law in the many-rule regime
    sc['predicted_full_cal_s'] = sc.predicted_full_s / cal
    sc['rows_reaching_2700s_cal'] = (sc.rows_reaching_2700s * cal ** (1 / sc.exponent)).astype(int)
    sc.to_csv(out / 'per_source_scaling.csv', index=False)

    def secs(x):
        return '> 10⁶' if x > 1e6 else f'{x:,.0f}'

    hot = sc[sc.many_rules & ~sc.degenerate_ladder &
             ((sc.predicted_full_s > 1000) | (sc.timeouts_local > 0) | (sc.ci_full_timeouts > 0))]
    hot = hot.sort_values(['dataset', 'scenario'])
    hot_lines = '\n'.join(f'| {r.dataset} | {r.scenario} | {r.full_rows:,} | {r.rules_1800:,} → {r.rules_10000:,} | '
                          f'{r.wall_10000_s} | {secs(r.predicted_full_cal_s)} | **{r.rows_reaching_2700s_cal:,}** | '
                          f'{r.ci_full_timeouts}/{r.ci_full_timeouts + r.ci_full_done} | {r.timeouts_local} |'
                          for _, r in hot.iterrows())
    degenerate = sc[sc.degenerate_ladder]
    degen_note = '、'.join(f'{r.dataset.split(":")[1]} {r.scenario}（{r.rules_1800}→{r.rules_10000} 條）'
                           for _, r in degenerate.iterrows()) or '無'
    to_tab = (fails.groupby('dataset').agg(timeouts=('status', 'size'),
                                           scenarios=('scenario', lambda s: '、'.join(sorted(s.unique()))))
              .reset_index().merge(reg, on='dataset', how='left')
              .merge(per[['dataset', 'models', 'median_rules']], on='dataset', how='left'))

    iid = sc[sc.scenario == 'FED_IID'].set_index('dataset')
    pend_ds = list(pending.dataset)
    over = [d for d in pend_ds if d in iid.index and iid.loc[d, 'many_rules']
            and sc.loc[(sc.dataset == d) & (sc.scenario == 'FED_IID'), 'predicted_full_cal_s'].iloc[0] > DEADLINE]
    expect_to = '、'.join(d.split(':')[1] for d in over) or '無'
    expect_ok = '、'.join(d.split(':')[1] for d in pend_ds if d not in over) or '無'

    def nstar(ds):
        s = sc[(sc.dataset == ds) & (sc.scenario == 'FED_IID')]
        return f'{int(s.rows_reaching_2700s_cal.iloc[0]):,}' if len(s) else '—'
    fast_big = per[(per.original_rows > 100_000) & (per.timeouts == 0)].sort_values('original_rows', ascending=False)
    fast_lines = '\n'.join(f'| {r.dataset} | {int(r.original_rows):,} | {r.median_rules:.0f} | {r.max_wall_s:.0f} |'
                           for _, r in fast_big.iterrows())
    to_lines = '\n'.join(f'| {r.dataset} | {int(r.original_rows):,} | {int(r.timeouts)} | {r.scenarios} | '
                         f'{0 if pd.isna(r.models) else int(r.models)} | {"—" if pd.isna(r.median_rules) else f"{r.median_rules:.0f}"} |'
                         for _, r in to_tab.iterrows())
    exceptions = sc[sc.many_rules & ~sc.degenerate_ladder & (sc.predicted_full_cal_s < DEADLINE)
                    & (sc.ci_full_timeouts * 2 >= sc.ci_full_timeouts + sc.ci_full_done) & (sc.ci_full_timeouts > 0)]
    exc_note = '、'.join(f'{r.dataset.split(":")[1]} {r.scenario}（預估 {r.predicted_full_cal_s:,.0f} 秒，CI 逾時 '
                         f'{r.ci_full_timeouts}/{r.ci_full_timeouts + r.ci_full_done}）' for _, r in exceptions.iterrows()) or '無'
    ratio = vm
    rule_rows = '\n'.join(f'| {R:,} | 約 {int((w_star / (0.128 * R)) ** .5):,} 列 |' for R in (300, 1000, 3000, 10000))

    md = f"""# 逾時（TIMEOUT）分析：資料要多大才會跑超過 2,700 秒？

產生時間：{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（UTC+8）。資料：本機 42-seed 執行已完成的 {len(local):,} 個模型
（期中快照 {(interim / 'SNAPSHOT_STAMP').read_text().strip()}）＋ CI full-scale 縮放實驗（1,800 / 10,000 列，同一個 `run_model`）。
**所有 TIMEOUT 紀錄原樣保留**（FAILURES.csv / MISSING.csv），未刪除、未重跑。

## 先講答案
1. **沒有單一的「列數門檻」。** 58 萬列的 covertype、100 萬列的 openml_42769 單一模型約 1 分鐘內完成；
   4.5 萬列的 openml_41027 卻幾乎全部逾時。決定性因素是 **規則數 × 列數²**。
2. **時間幾乎全部花在「決策策略的衝突裁決」，不是 LEM2 歸納或約簡。** 在 wall > 60 秒的模型中，
   predict 階段占 {100 * share_slow['predict_seconds']:.0f}%，LEM2 占 {100 * share_slow['lem2_seconds']:.0f}%，約簡占 {100 * share_slow['reduct_seconds']:.1f}%。
3. **原因（程式機制）**：`fedrs.predict.resolve_scalable` 先依「命中哪些規則」把測試列去重成 U 種樣式，
   再對三種以支持集聯集計分的策略（GLOBAL_STRENGTH、POPULATION_STANDARD、POPULATION_GLOBAL）計算
   (樣式 × 規則) @ (規則 × 訓練列) 的布林矩陣乘積。成本 ≈ **U × 規則數 × 訓練列數**，每個模型做 3 策略 × 2 規則版本。
   規則少時 U 很小（所以百萬列也快）；規則上千時幾乎每一列都是不同樣式，U ≈ 測試列數，成本變成 **∝ n² × 規則數**。
4. 逾時的資料集，規則數還會隨資料量成長（規則數 ∝ n^g），所以耗時約 **∝ n^(2+g)**，比平方更快爆掉。
5. **門檻（各資料集自身縮放律外推並校正，Fed IID）**：openml_42732 約 {nstar('OML51:openml_42732')} 列、openml_1169 約 {nstar('OML51:openml_1169')} 列、
   openml_42733 約 {nstar('OML51:openml_42733')} 列、openml_41162 約 {nstar('OML51:openml_41162')} 列、openml_41027 約 {nstar('OML51:openml_41027')} 列
   就會超過 2,700 秒；也就是**規則上千條的資料集，大約 2.5–6 萬列就是極限**。這是數量級估計（耗時誤差約 2–3 倍，
   換算成列數約 ±30–40%），詳見第 3–4 節。
6. 規則只有數十～數百條的資料集耗時近乎線性成長，百萬列也不會逾時（第 5 節）。

## 1. 時間花在哪個階段（本機已完成模型）
| 階段 | 全部模型 | wall > 60 秒的模型 |
|---|---:|---:|
{phase_lines}

## 2. 已記錄的逾時
| 資料集 | 原始列數 | TIMEOUT 次數 | 發生情境 | 已完成模型 | 已完成模型的規則數中位數 |
|---|---:|---:|---|---:|---:|
{to_lines}

四種情境（集中式、Fed IID、α=0.5、α=0.1）都會逾時，不是只有集中式。

## 3. 縮放律驗證（與縮放實驗同一硬體：CI full-scale 全量模型，seeds 1001–1005）
預測＝10,000 列實測耗時 × (全量列數/10,000)^(2+g)，g＝規則數成長指數（CI 縮放實驗 1,800→10,000 列）。

| 資料集 | 情境 | 10,000 列規則數 | 全量列數 | 指數 2+g | 預測秒數 | CI 全量實測中位數 | 預測/實測 |
|---|---|---:|---:|---:|---:|---:|---:|
{val_lines}

\\* 該情境在 CI 上部分模型逾時，實測中位數只含完成者（偏低），比值高估。

- **規則多（10,000 列時 ≥ 500 條）**：預測/實測中位數 {vm.median():.2f}（範圍 {vm.min():.2f}–{vm.max():.2f}，n＝{len(vm)}，不含 * ）→
  縮放律在此區間方向正確但**系統性高估約 {cal:.1f} 倍**；第 4 節的預估已除以 {cal:.2f} 校正。驗證點不多，屬數量級估計。
- **規則少（< 500 條）**：中位數 {vf.median():.1f}（範圍 {vf.min():.2f}–{vf.max():.1f}，n＝{len(vf)}）→ 測試樣式去重後很少，耗時近乎線性，平方律**不適用**（大幅高估）。
- 1,800 列縮放樣本退化（規則數 < 20）、無法估成長指數而排除者：{degen_note}。

## 4. 逾時與高風險資料集（皆為規則多）：多大會撞到 2,700 秒
（預估皆已依第 3 節校正。）

| 資料集 | 情境 | 全量列數 | 規則數 1,800 → 10,000 列 | 10,000 列秒數 | 全量預估秒數 | **達 2,700 秒的列數** | CI 全量逾時/總數 | 本機 TIMEOUT |
|---|---|---:|---|---:|---:|---:|---:|---:|
{hot_lines}

- 縮放實驗只有 Fed IID 與 Fed α=0.1 兩種情境；本機 TIMEOUT 欄為該情境至目前的逾時次數。
- 與 CI 全量實測交叉對照，預估「會逾時」與 CI 實際大多逾時大致一致。不一致（預估在時限內但 CI 半數以上逾時）：{exc_note}。

## 5. 對照：很大但很快的資料集
| 資料集 | 原始列數 | 規則數中位數 | 單一模型最長秒數 |
|---|---:|---:|---:|
{fast_lines}

規則只有數十到數百條，匹配樣式少，所以即使 50 萬～200 萬列也遠低於時限。

## 6. 跨資料集合併擬合（佐證，不用來定門檻）
在規則數 ≥ 500 的 {n_fit:,} 個模型上，log(耗時) 與 log(訓練列 × 測試列 × 規則數) 的關係為斜率 {slope:.2f}、R²＝{r2:.2f}，
表示在規則多的區間，「列數² × 規則數」能解釋大部分耗時差異。但不同資料集的常數可差約兩個數量級（類別數、匹配樣式多樣性不同），
所以**不適合用一條跨資料集公式定出單一列數門檻**；門檻請以第 4 節的逐資料集外推為準。

## 7. 尚未完成的資料集（{len(pending)} 個）
{chr(10).join(f"- {r.dataset}（{int(r.original_rows):,} 列，已成功 {r.complete_models}/168）" for _, r in pending.iterrows())}

依縮放律（Fed IID）預估全量超過 2,700 秒：{expect_to}；預估可在時限內完成或不適用平方律（規則少）：{expect_ok}。
（CI 全量實測逾時比例見第 4 節，可交叉對照。）

## 8. 對研究的意義
- 逾時是**以支持集聯集計分的決策策略在大量規則下的計算成本**，不是 LEM2 本身無法擴展，也不是執行環境錯誤。
- FIRST_MATCH / SIMPLE_VOTING / STANDARD_VOTING 只需樣式 × 規則的計數或加權和，不需乘上訓練列；但協定要求同一模型
  六種策略全部完成才記錄結果，所以最慢的策略決定了整個模型是否逾時。
- 改進方向（屬方法變更，需另行決定，不影響本次協定結果）：support-union 改用稀疏/位元集合運算或預先計算規則支持集交集、
  依策略分開計時與記錄、限制規則數（最小支持度/規則剪枝）。

## 附件
- `fig1_rows_vs_wall.png`：列數 vs 耗時（列數無法單獨預測逾時）
- `fig2_per_source_scaling.png`：各資料集「列數 → 耗時」縮放曲線與 2,700 秒門檻
- `per_source_scaling.csv`、`per_source_observed.csv`
"""
    (out / 'TIMEOUT_ANALYSIS.md').write_text(md, encoding='utf-8')
    print(json.dumps({'models': len(local), 'validation_n': int(len(ratio)), 'ratio_median': round(float(ratio.median()), 2),
                      'ratio_range': [round(float(ratio.min()), 2), round(float(ratio.max()), 2)],
                      'pooled_slope': round(slope, 2), 'pooled_r2': round(r2, 2)}))


if __name__ == '__main__':
    main()
