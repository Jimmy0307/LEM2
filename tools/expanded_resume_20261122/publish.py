"""Publish each finished dataset (all 168 models decided) as its own commit+push.

Reads the WSL run directory (read only), copies result files (never source.pkl
or raw caches) into the publish worktree under docs/research/expanded_188_42seeds,
commits one dataset per commit with [skip ci], and pushes after every commit.
Push conflicts are resolved by fetch + rebase (results-only paths); never forced.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

SCENARIOS = ('CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01')
SEEDS = range(1, 43)
SUMMARY_FILES = ('STATUS.json', 'COMPLETENESS.csv', 'MISSING.csv', 'FAILURES.csv', 'TIMINGS.csv',
                 'PAIRED_SUMMARY.csv', 'RUN_MANIFEST.json', 'REVISION_COMPATIBILITY.json',
                 'MANIFEST_HISTORY.jsonl', 'SOURCE_REGISTRY.csv')
BRANCH = 'research/expanded-42seeds-20261120'
TRAILER = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
README = """# 188 datasets x 42 seeds (expanded_42seeds_20261120) - incremental results

Status: **in progress** until STATUS.json says COMPLETE. Do not present partial
paired summaries as a 42-seed result.

* Code: experiments/expanded_42seeds_20261120 at 56e293c (tree 3dc3d175, identical to
  original 3566580). Contract migration evidence: REVISION_COMPATIBILITY.json;
  original manifest and source records: ORIGINAL_3566580/.
* Fidelity gate: all 1,559 checkpoints produced under 3566580 were recomputed
  bit-identically (rows, source SHA, partition, feature typing) before resuming.
* Execution: WSL2 Ubuntu, Python 3.12.3, numpy 2.3.5, pandas 2.2.3, unmodified
  run.py per (dataset, seed chunk) under an external memory-aware scheduler.
* checkpoints/<dataset>/ is pushed only when all 168 models have a decision
  (result JSON or recorded failure such as TIMEOUT). Raw third-party data is
  never published. RESULTS.csv / PAIRED_COMPARISONS.csv are omitted for size
  (GitHub 100 MB limit); regenerate with
  `python -m experiments.expanded_42seeds_20261120.run --audit --output <dir>`.
* Summary CSV/JSON files reflect the latest periodic audit at commit time.
"""


def git(wt, *args, check=True):
    r = subprocess.run(['git', *args], cwd=wt, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[-400:]}")
    return r


def decided(ds_path):
    names = {p.name for p in ds_path.iterdir()}
    for seed in SEEDS:
        for sc in SCENARIOS:
            base = f'seed{seed:02d}__{sc}'
            if base + '.json' not in names and base + '.failure.json' not in names:
                return None
    ok = sum(1 for n in names if n.startswith('seed') and n.endswith('.json') and not n.endswith('.failure.json'))
    return ok, 168 - ok


def result_files(ds_path):
    return sorted(p for p in ds_path.iterdir()
                  if p.name == 'SOURCE.json' or (p.name.startswith('seed') and p.name.endswith('.json')))


def sync_summary(main, dest):
    for name in SUMMARY_FILES:
        if (main / name).exists():
            shutil.copy2(main / name, dest / name)
    orig = main / 'ORIGINAL_3566580'
    if orig.exists() and not (dest / 'ORIGINAL_3566580').exists():
        shutil.copytree(orig, dest / 'ORIGINAL_3566580')
    if not (dest / 'README.md').exists():
        (dest / 'README.md').write_text(README, encoding='utf-8')


def push(wt, log):
    for attempt in range(1, 4):
        r = git(wt, 'push', 'origin', f'HEAD:{BRANCH}', check=False)
        if r.returncode == 0:
            return True
        log({'kind': 'push_retry', 'attempt': attempt, 'error': r.stderr.strip()[-300:]})
        git(wt, 'fetch', 'origin', f'+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}', check=False)
        if git(wt, 'rebase', f'origin/{BRANCH}', check=False).returncode:
            git(wt, 'rebase', '--abort', check=False)
            log({'kind': 'push_blocked', 'error': 'rebase conflict; manual review needed'})
            raise RuntimeError('rebase conflict on publish branch; stopping for manual review')
        time.sleep(10 * attempt)
    return False


def cycle(main, wt, rel, log):
    dest = wt / rel
    dest.mkdir(parents=True, exist_ok=True)
    published = 0
    for ds_path in sorted((main / 'checkpoints').iterdir()):
        status = decided(ds_path) if ds_path.is_dir() else None
        if not status:
            continue
        files = result_files(ds_path)
        target = dest / 'checkpoints' / ds_path.name
        if target.exists() and {p.name for p in target.iterdir()} == {p.name for p in files}:
            continue
        target.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, target / f.name)
        sync_summary(main, dest)
        git(wt, 'add', '--', rel)
        if not git(wt, 'diff', '--cached', '--quiet', check=False).returncode:
            continue
        dataset = json.loads((ds_path / 'SOURCE.json').read_text())['dataset']
        ok, failed = status
        state = json.loads((main / 'STATUS.json').read_text()) if (main / 'STATUS.json').exists() else {}
        msg = (f'data(expanded): publish {dataset} 168/168 decided ({ok} ok, {failed} failed) [skip ci]\n\n'
               f"Run status at publish: {state.get('complete_models', '?')}/{state.get('expected_models', 31584)} "
               f"models complete; {state.get('complete_datasets', '?')}/188 datasets COMPLETE.\n\n{TRAILER}")
        git(wt, 'commit', '-q', '-m', msg)
        pushed = push(wt, log)
        log({'kind': 'published', 'dataset': dataset, 'ok': ok, 'failed': failed, 'pushed': pushed,
             'commit': git(wt, 'rev-parse', '--short', 'HEAD').stdout.strip()})
        published += 1
        if not pushed:  # e.g. network down: keep the local commit, retry next cycle
            return published
    return published


def push_pending(wt, log):
    """Push local commits left unpushed by an earlier failed cycle."""
    git(wt, 'fetch', 'origin', f'+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}', check=False)
    ahead = git(wt, 'rev-list', '--count', f'origin/{BRANCH}..HEAD', check=False).stdout.strip()
    if ahead and ahead != '0':
        ok = push(wt, log)
        log({'kind': 'published' if ok else 'push_deferred', 'pending_commits': int(ahead), 'pushed': ok})
        return ok
    return True


def main_loop():
    p = argparse.ArgumentParser()
    p.add_argument('--main', required=True)
    p.add_argument('--worktree', required=True)
    p.add_argument('--log', required=True)
    p.add_argument('--interval', type=float, default=300)
    p.add_argument('--once', action='store_true')
    a = p.parse_args()
    main, wt, rel = Path(a.main), Path(a.worktree), 'docs/research/expanded_188_42seeds'

    def log(event):
        line = json.dumps({'t': time.strftime('%Y-%m-%dT%H:%M:%S'), **event}, ensure_ascii=False)
        print(line, flush=True)
        with open(a.log, 'a', encoding='utf-8') as fh:
            fh.write(line + '\n')

    if git(wt, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip() != BRANCH:
        sys.exit('publish worktree is not on ' + BRANCH)
    while True:
        try:
            n = cycle(main, wt, rel, log) if push_pending(wt, log) else 0
        except OSError as exc:  # WSL share briefly unavailable (e.g. VM restart): retry next cycle
            log({'kind': 'publisher_io_retry', 'error': f'{type(exc).__name__}: {exc}'[:300]})
            time.sleep(a.interval)
            continue
        except Exception as exc:  # surface, then stop: never publish blindly
            log({'kind': 'publisher_error', 'error': f'{type(exc).__name__}: {exc}'})
            raise
        state = json.loads((main / 'STATUS.json').read_text()) if (main / 'STATUS.json').exists() else {}
        log({'kind': 'cycle', 'published_now': n, 'complete_models': state.get('complete_models'),
             'missing_models': state.get('missing_models')})
        finished = (main / 'ORCHESTRATOR_DONE').exists()
        if a.once or finished:
            return
        time.sleep(a.interval)


if __name__ == '__main__':
    main_loop()
