"""Re-materialise source.pkl for datasets whose original SOURCE.json exists.

run.py re-downloads a source and rewrites SOURCE.json whenever source.pkl is
missing, without comparing against the earlier record.  This tool loads each
source with the same run.py code path, and writes source.pkl (same atomic
pickle format as run.py) only if the fresh source reproduces the original
SOURCE.json exactly.  SOURCE.json is never written.  Mismatches are reported
and leave the dataset untouched so the runner cannot silently mix sources.
"""
import argparse
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import pickle
import sys


def fresh_metadata(source, item):
    meta = {f.name: getattr(source, f.name) for f in fields(source) if f.name != 'frame'}
    meta.update(dataset=item['dataset'], used_rows=len(source.frame), cohort=item['cohort'])
    # Same serialisation as run.atomic_json, so comparison is like-for-like.
    return json.loads(json.dumps(meta, ensure_ascii=False, default=str))


def prepared_sha(source):
    return hashlib.sha256(source.frame.to_csv(index=False).encode()).hexdigest()


def verify_one(dest, item, read_source, invoke_with_deadline):
    meta_path, pkl_path = dest / 'SOURCE.json', dest / 'source.pkl'
    original = json.loads(meta_path.read_text())
    if pkl_path.exists():
        with pkl_path.open('rb') as fh:
            cached = pickle.load(fh)
        ok = prepared_sha(cached) == original['prepared_sha256']
        return dict(status='CACHED_OK' if ok else 'CACHED_SHA_MISMATCH')
    result = invoke_with_deadline(read_source, (item, str(dest / 'openml')), 300)
    if result['status'] != 'OK':
        return dict(status='SOURCE_LOAD_FAILED', error=f"{result['status']}: {result.get('error', '')}"[:500])
    source = result['value']
    sha = prepared_sha(source)
    fresh = fresh_metadata(source, item)
    diffs = sorted(k for k in set(fresh) | set(original) if fresh.get(k) != original.get(k))
    if sha != original['prepared_sha256'] or diffs:
        return dict(status='SOURCE_MISMATCH', fresh_sha=sha, differing_fields=diffs)
    tmp = pkl_path.with_suffix('.tmp')
    with tmp.open('wb') as fh:
        pickle.dump(source, fh)
    tmp.replace(pkl_path)
    return dict(status='VERIFIED_WROTE_PKL', fresh_sha=sha)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--report', required=True)
    a = p.parse_args()
    sys.path.insert(0, a.repo)
    from experiments.expanded_42seeds_20261120.run import read_source, selected_registry
    from experiments.full_scale_20261118.runner import invoke_with_deadline

    _, chosen = selected_registry()
    items = {r['dataset']: r for r in chosen.to_dict('records')}
    report = []
    for dest in sorted((Path(a.output) / 'checkpoints').iterdir()):
        if not (dest / 'SOURCE.json').exists():
            continue
        dataset = json.loads((dest / 'SOURCE.json').read_text())['dataset']
        if dataset not in items:
            report.append(dict(dataset=dataset, status='NOT_IN_ELIGIBLE_REGISTRY'))
            continue
        outcome = verify_one(dest, items[dataset], read_source, invoke_with_deadline)
        outcome = {'dataset': dataset, **outcome}
        report.append(outcome)
        print(json.dumps(outcome, ensure_ascii=False), flush=True)
    Path(a.report).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    bad = [r for r in report if r['status'] not in ('VERIFIED_WROTE_PKL', 'CACHED_OK')]
    print(f'verified={len(report) - len(bad)} problems={len(bad)}', flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
