"""Summarise per-model wall time / RSS of checkpoints written after a given time."""
import json
import sys
import time
from pathlib import Path

root = Path(sys.argv[1]) / 'checkpoints'
since = time.time() - float(sys.argv[2]) * 3600 if len(sys.argv) > 2 else 0
rows = []
for f in root.glob('*/seed*__*.json'):
    if f.name.endswith('.failure.json') or f.stat().st_mtime < since:
        continue
    t = json.loads(f.read_text())['timing']
    rows.append((t['dataset'], t['seed'], t['scenario'], t['wall_seconds'], t['peak_rss_mb']))
for r in sorted(rows):
    print(f'{r[0]:28s} s{r[1]:02d} {r[2]:12s} wall={r[3]:8.1f}s rss={r[4]:7.0f}MB')
fails = [f for f in root.glob('*/*.failure.json') if f.stat().st_mtime >= since]
for f in fails:
    d = json.loads(f.read_text())
    print('FAILURE', d['dataset'], d['seed'], d['scenario'], d['status'], str(d.get('error', ''))[:120])
print(f'models={len(rows)} failures={len(fails)}')
