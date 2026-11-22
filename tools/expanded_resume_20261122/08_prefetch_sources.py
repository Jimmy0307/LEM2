"""Download every eligible source ahead of time using run.py's own code path.

Calls run.run_dataset(item, staging, seeds=[], timeout): this executes exactly
run.py's source loading, SOURCE.json and source.pkl writing (and SHA check on
an existing cache) and then runs no model.  Output goes to a staging directory,
never to the main run directory.  Re-runnable: already cached sources are only
re-verified by run.py itself.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import time


def fetch(repo, item, staging):
    sys.path.insert(0, repo)
    from experiments.expanded_42seeds_20261120.run import run_dataset
    t0 = time.time()
    try:
        dataset, status = run_dataset(item, staging, [], 2700)
    except Exception as exc:  # e.g. cached SHA mismatch raised by run.py
        return item['dataset'], f'ERROR {type(exc).__name__}: {exc}'[:300], time.time() - t0
    return dataset, status, time.time() - t0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--main', required=True)
    p.add_argument('--staging', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--workers', type=int, default=6)
    p.add_argument('--only', default='', help='comma list of datasets to (re)fetch')
    p.add_argument('--warm-openml', action='store_true', help='download OpenML parquet first, no deadline')
    a = p.parse_args()
    only = {d for d in a.only.split(',') if d}
    sys.path.insert(0, a.repo)
    from experiments.expanded_42seeds_20261120.run import selected_registry
    _, chosen = selected_registry()
    staging = Path(a.staging)
    (staging / 'checkpoints').mkdir(parents=True, exist_ok=True)
    todo = []
    for item in chosen.to_dict('records'):
        name = item['dataset'].replace(':', '__')
        if only and item['dataset'] not in only:
            continue
        if (Path(a.main) / 'checkpoints' / name / 'source.pkl').exists():
            continue
        todo.append(item)
    print(json.dumps({'to_fetch': len(todo)}), flush=True)
    if a.warm_openml:
        # Slow links: download the raw OpenML parquet into the exact cache path
        # run.py uses (<dest>/openml), with no deadline. run_dataset below then
        # builds the source from that cache through the unchanged code path.
        from experiments.full_scale_20261118.sources import load_openml
        for item in todo:
            if item['cohort'] != 'OML51':
                continue
            cache = staging / 'checkpoints' / item['dataset'].replace(':', '__') / 'openml'
            t0 = time.time()
            try:
                load_openml(int(item['did']), str(cache))
                status = 'WARMED'
            except Exception as exc:
                status = f'WARM_FAILED {type(exc).__name__}: {exc}'[:300]
            print(json.dumps({'dataset': item['dataset'], 'warm': status,
                              'seconds': round(time.time() - t0, 1)}), flush=True)
    results = []
    with ProcessPoolExecutor(a.workers) as pool:
        futs = [pool.submit(fetch, a.repo, item, str(staging)) for item in todo]
        for fut in as_completed(futs):
            dataset, status, secs = fut.result()
            results.append({'dataset': dataset, 'status': status, 'seconds': round(secs, 1)})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    ok = [r for r in results if r['status'] == 'ATTEMPTED']
    summary = {'requested': len(todo), 'cached_ok': len(ok), 'failed': len(results) - len(ok),
               'failures': [r for r in results if r['status'] != 'ATTEMPTED'], 'results': results}
    Path(a.report).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
