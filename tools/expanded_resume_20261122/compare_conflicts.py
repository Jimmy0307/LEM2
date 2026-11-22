"""Compare every conflicting shard file against the main copy.

A conflict where metric rows, source SHA and deterministic timing fields are
identical (only wall-clock/RSS differ) is a benign recomputation.
"""
import json
import sys
from pathlib import Path

DETERMINISTIC = ('dataset', 'seed', 'scenario', 'partition_status', 'partition_attempts',
                 'continuous_features', 'categorical_features')


def canon(x):
    return json.dumps(x, sort_keys=True)


main, work = Path(sys.argv[1]), Path(sys.argv[2])
for line in Path(sys.argv[3]).read_text().splitlines():
    if '"conflicts": ["' not in line:
        continue
    ev = json.loads(line)
    ds_dir, _ = ev['job'].split('/')
    for name in ev['conflicts']:
        a, b = main / 'checkpoints' / ds_dir / name, work / ev['job'] / 'checkpoints' / ds_dir / name
        if not b.exists():
            print(ev['job'], name, 'SHARD_FILE_GONE')
            continue
        x, y = json.loads(a.read_text()), json.loads(b.read_text())
        if name.endswith('.failure.json'):
            same = x.get('status') == y.get('status')
        else:
            same = (canon(x['rows']) == canon(y['rows'])
                    and x['source_prepared_sha256'] == y['source_prepared_sha256']
                    and all(canon(x['timing'].get(k)) == canon(y['timing'].get(k)) for k in DETERMINISTIC))
        print(ev['job'], name, 'BENIGN_IDENTICAL_RESULTS' if same else 'REAL_DIFFERENCE')
