#!/usr/bin/env bash
# Count eligible datasets with a usable local source (main or prefetch staging).
cd "$HOME/lem2_expanded"
"$HOME/lem2_venv/bin/python" -I - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, '/home/user/lem2_expanded')
from experiments.expanded_42seeds_20261120.run import selected_registry
_, c = selected_registry()
roots = [Path('/home/user/lem2_runs/expanded_188_42seeds'), Path('/home/user/lem2_runs/source_prefetch')]
missing, failures = [], []
for d in c.dataset:
    name = d.replace(':', '__')
    if not any((r / 'checkpoints' / name / 'source.pkl').exists() and (r / 'checkpoints' / name / 'SOURCE.json').exists() for r in roots):
        missing.append(d)
    if any((r / 'checkpoints' / name / 'SOURCE_FAILURE.json').exists() for r in roots):
        failures.append(d)
print(f'eligible={len(c)} with_local_source={len(c) - len(missing)} missing={missing} stale_failure_files={failures}')
PY
