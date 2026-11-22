"""Progress, failure breakdown and remaining-work projection for the main run."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, '/home/user/lem2_expanded')
from experiments.expanded_42seeds_20261120.run import selected_registry  # noqa: E402

MAIN = Path('/home/user/lem2_runs/expanded_188_42seeds')
PROFILE = json.loads(Path('/home/user/lem2_runs/schedule_profile.json').read_text())
SC = ('CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01')
_, reg = selected_registry()
ok = fail = 0
fail_status, fail_by_ds = Counter(), Counter()
remaining = []
for d in reg.dataset:
    dest = MAIN / 'checkpoints' / d.replace(':', '__')
    pend = 0
    for s in range(1, 43):
        for sc in SC:
            p = dest / f'seed{s:02d}__{sc}.json'
            f = dest / f'seed{s:02d}__{sc}.failure.json'
            if p.exists():
                ok += 1
            elif f.exists():
                fail += 1
                st = json.loads(f.read_text()).get('status', '?')
                fail_status[st] += 1
                fail_by_ds[(d, st)] += 1
            else:
                pend += 1
    if pend:
        remaining.append((d, pend, PROFILE.get(d, {}).get('per_model', 30.0)))
print(f'decided={ok + fail} ok={ok} failed={fail} pending={sum(r[1] for r in remaining)} of 31584')
print('failures by status:', dict(fail_status))
for (d, st), n in sorted(fail_by_ds.items(), key=lambda x: -x[1]):
    print(f'  {d:28s} {st:22s} {n}')
remaining.sort(key=lambda r: -r[1] * r[2])
cpu_h = sum(n * min(pm, 2700) for _, n, pm in remaining) / 3600
print(f'pending datasets={len(remaining)} projected CPU-h at CI speed={cpu_h:.1f}')
for d, n, pm in remaining[:12]:
    print(f'  {d:28s} pending={n:4d} ci_per_model={pm:7.1f}s  ~{n * min(pm, 2700) / 3600:6.1f} CPU-h')
