"""Scheduling profile from the published full-scale CI timings (same run_model).

per_model = (completed wall seconds + 2700 s per TIMEOUT) / attempted models.
Used only to order jobs and size seed chunks / memory; never affects results.
"""
import json
import sys

import pandas as pd

timings, failures, out = sys.argv[1:-2], sys.argv[-2], sys.argv[-1]
t = pd.concat([pd.read_csv(f) for f in timings])
t = t[t.phase.isna()].drop_duplicates(['dataset', 'seed', 'scenario'], keep='last')
f = pd.read_csv(failures)
timeouts = f[f.status == 'TIMEOUT'].groupby('dataset').size()
g = t.groupby('dataset').agg(n=('wall_seconds', 'size'), wall=('wall_seconds', 'sum'), rss_mb=('peak_rss_mb', 'max'))
g = g.reindex(g.index.union(timeouts.index))
g['n'] = g.n.fillna(0)
g['wall'] = g.wall.fillna(0)
g['rss_mb'] = g.rss_mb.fillna(1200)
g['timeouts'] = timeouts.reindex(g.index).fillna(0)
g['per_model'] = (g.wall + 2700 * g.timeouts) / (g.n + g.timeouts)
prof = {d: {'per_model': round(float(r.per_model), 2), 'rss_mb': round(float(r.rss_mb), 1)} for d, r in g.iterrows()}
with open(out, 'w') as fh:
    json.dump(prof, fh, indent=1, sort_keys=True)
print(len(prof), 'datasets profiled; projected CI CPU-h for 168 models each:',
      round(sum(v['per_model'] for v in prof.values()) * 168 / 3600, 1))
