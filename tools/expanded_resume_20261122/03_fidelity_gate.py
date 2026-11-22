"""Behavioural equivalence gate: recompute every completed 3566580 checkpoint
with the current checkout and require identical metric rows.

Each dataset runs in its own isolated output directory (seeded only with the
verified SOURCE.json/source.pkl), so the main run directory is never touched.
Compared exactly: every metric row, source_prepared_sha256, and the
deterministic timing fields (partition status/attempts, feature typing).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import sys

DETERMINISTIC_TIMING = ('dataset', 'seed', 'scenario', 'partition_status', 'partition_attempts',
                        'continuous_features', 'categorical_features')


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def completed(src_dir):
    out = {}
    for path in sorted(src_dir.glob('seed*__*.json')):
        if path.name.endswith('.failure.json'):
            continue
        out[path.name] = json.loads(path.read_text())
    return out


def prepare(gate_root, src_dir):
    gate = gate_root / src_dir.name
    if gate.exists():
        shutil.rmtree(gate)
    dest = gate / 'checkpoints' / src_dir.name
    dest.mkdir(parents=True)
    for name in ('SOURCE.json', 'source.pkl'):
        shutil.copy2(src_dir / name, dest / name)
    return gate, dest


def rerun(repo, python, gate, dataset, seeds, log):
    cmd = [python, '-m', 'experiments.expanded_42seeds_20261120.run', '--output', str(gate),
           '--dataset', dataset, '--seeds', ','.join(map(str, seeds)), '--workers', '1']
    with log.open('w') as fh:
        return subprocess.run(cmd, cwd=repo, stdout=fh, stderr=subprocess.STDOUT).returncode


def compare(original, gate_dest):
    problems = []
    for name, rec in original.items():
        path = gate_dest / name
        if not path.exists():
            problems.append(dict(file=name, issue='NOT_RECOMPUTED'))
            continue
        new = json.loads(path.read_text())
        if canonical(rec['rows']) != canonical(new['rows']):
            problems.append(dict(file=name, issue='ROWS_DIFFER'))
        if rec['source_prepared_sha256'] != new['source_prepared_sha256']:
            problems.append(dict(file=name, issue='SOURCE_SHA_DIFFERS'))
        for key in DETERMINISTIC_TIMING:
            if canonical(rec['timing'].get(key)) != canonical(new['timing'].get(key)):
                problems.append(dict(file=name, issue=f'TIMING_{key}_DIFFERS'))
    return problems


def gate_dataset(args, src_dir):
    original = completed(src_dir)
    dataset = json.loads((src_dir / 'SOURCE.json').read_text())['dataset']
    seeds = sorted({int(n[4:6]) for n in original})
    gate, dest = prepare(Path(args.gate_root), src_dir)
    code = rerun(args.repo, args.python, gate, dataset, seeds, gate / 'gate.log')
    problems = compare(original, dest) if code == 0 else [dict(issue=f'RUNNER_EXIT_{code}')]
    result = dict(dataset=dataset, original_models=len(original), seeds=len(seeds),
                  matched=len(original) - len({p.get('file') for p in problems if p.get('file')}),
                  runner_exit=code, problems=problems[:50], problem_count=len(problems))
    print(json.dumps({k: v for k, v in result.items() if k != 'problems'}), flush=True)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--python', required=True)
    p.add_argument('--output', required=True, help='main run directory (read only here)')
    p.add_argument('--gate-root', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--parallel', type=int, default=12)
    a = p.parse_args()
    dirs = [d for d in sorted((Path(a.output) / 'checkpoints').iterdir()) if any(d.glob('seed*__*.json'))]
    with ThreadPoolExecutor(a.parallel) as pool:
        results = list(pool.map(lambda d: gate_dataset(a, d), dirs))
    total = sum(r['original_models'] for r in results)
    bad = sum(r['problem_count'] for r in results)
    summary = dict(datasets=len(results), original_models=total, problems=bad,
                   verdict='PASS' if bad == 0 and total else 'FAIL', results=results)
    Path(a.report).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}), flush=True)
    return 0 if summary['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
