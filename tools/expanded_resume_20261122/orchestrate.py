"""Memory-aware parallel driver around the UNMODIFIED expanded_42seeds run.py.

Why: run.py parallelises only across datasets and runs every >500k-row source
serially at the end, so a handful of slow sources (each model near the
2,700 s deadline) would serialise ~16 days of work.  This driver keeps the
scientific path untouched and only changes scheduling:

* each job = (dataset, seed chunk) runs `python -m ...run --dataset D --seeds S`
  in its own isolated directory, pre-seeded with the main RUN_MANIFEST.json
  (so run.py's own contract check runs for every job) and the verified source;
* finished checkpoints are validated with run.validate_record and copied into
  the main directory atomically; existing main files are never overwritten
  (an identical file is accepted, a different one is reported as CONFLICT);
* the main directory has a single writer (this process); audit runs serially;
* jobs are admitted heaviest-first under a memory budget and a live
  MemAvailable reserve.
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

SCENARIOS = ('CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01')
ALL_SEEDS = tuple(range(1, 43))
THREAD_ENV = {k: '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                               'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')}


@dataclass(frozen=True)
class Job:
    dataset: str
    seeds: tuple
    cost: float      # projected seconds (scheduling only)
    mem_gb: float    # projected peak GB (scheduling only)
    heavy: bool = False  # per-model projection > 600 s: capped so they keep fast cores

    @property
    def key(self):
        return f"{self.dataset.replace(':', '__')}/s{self.seeds[0]:02d}-{self.seeds[-1]:02d}"


def log(main, event):
    event = {'t': time.strftime('%Y-%m-%dT%H:%M:%S'), **event}
    line = json.dumps(event, ensure_ascii=False)
    print(line, flush=True)
    with (main / 'ORCHESTRATOR_LOG.jsonl').open('a') as fh:
        fh.write(line + '\n')


RAMP_SECONDS = 300
CONTROL_KEYS = ('max_jobs', 'max_heavy', 'mem_budget_gb', 'mem_reserve_gb')


def load_control(main, a):
    """Live-tunable limits from ORCHESTRATOR_CONTROL.json (falls back to CLI args)."""
    base = {k: getattr(a, k) for k in CONTROL_KEYS}
    path = main / 'ORCHESTRATOR_CONTROL.json'
    try:
        ctl = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        return base  # unreadable mid-edit: keep CLI defaults this round
    return {k: type(base[k])(ctl.get(k, base[k])) for k in CONTROL_KEYS}


def mem_available_gb():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) / 1024 / 1024
    return 0.0


def ds_dir(dataset):
    return dataset.replace(':', '__')


def pending_seeds(main, dataset):
    dest = main / 'checkpoints' / ds_dir(dataset)
    out = []
    for seed in ALL_SEEDS:
        for sc in SCENARIOS:
            path = dest / f'seed{seed:02d}__{sc}.json'
            if not path.exists() and not path.with_suffix('.failure.json').exists():
                out.append(seed)
                break
    return out


def chunk(seeds, size):
    return [tuple(seeds[i:i + size]) for i in range(0, len(seeds), size)]


def plan(main, registry, profile, only, defer=frozenset()):
    jobs = []
    for item in registry:
        dataset = item['dataset']
        if only and dataset not in only:
            continue
        seeds = pending_seeds(main, dataset)
        if not seeds:
            continue
        prof = profile.get(dataset, {})
        per_model = float(prof.get('per_model', 30.0))
        rss_gb = float(prof.get('rss_mb', 600.0)) / 1024
        rows = int(item['original_rows'])
        # Measured locally: job parent ~0.4x + model child ~1x of the CI peak RSS.
        mem = max(0.6, 1.5 * rss_gb + (1.0 if rows > 500_000 else 0.5))
        per_seed = 4 * per_model
        size = 1 if per_seed > 600 else 3 if per_seed > 120 else 7 if per_seed > 20 else 42
        for c in chunk(seeds, size):
            jobs.append(Job(dataset, c, per_seed * len(c), round(mem, 2), per_model > 600))
    # Deferred datasets (e.g. near-certain per-model timeouts) go last; scheduling only.
    return sorted(jobs, key=lambda j: (j.dataset in defer, -j.cost))


def source_dir(job_dataset, main, cache):
    """Main copy first; otherwise the prefetched run.py-written staging copy."""
    for root in (main, cache):
        if root is None:
            continue
        src = root / 'checkpoints' / ds_dir(job_dataset)
        if (src / 'SOURCE.json').exists() and (src / 'source.pkl').exists():
            return src
    return None


def seed_job_dir(job, main, work, cache=None):
    shard = work / job.key
    if shard.exists():
        shutil.rmtree(shard)
    dest = shard / 'checkpoints' / ds_dir(job.dataset)
    dest.mkdir(parents=True)
    shutil.copy2(main / 'RUN_MANIFEST.json', shard / 'RUN_MANIFEST.json')
    src = source_dir(job.dataset, main, cache)
    if src is not None:  # run.py re-verifies the pickle SHA against SOURCE.json
        for name in ('SOURCE.json', 'source.pkl'):
            shutil.copy2(src / name, dest / name)
    # Carry already-decided models so run.py validates and skips them instead of
    # recomputing (e.g. a seed half-finished before a driver restart).
    m_dest = main / 'checkpoints' / ds_dir(job.dataset)
    for seed in job.seeds:
        for sc in SCENARIOS:
            for suffix in ('.json', '.failure.json'):
                f = m_dest / f'seed{seed:02d}__{sc}{suffix}'
                if f.exists():
                    shutil.copy2(f, dest / f.name)
    return shard


def same_result(a, b):
    """True when two checkpoint files hold the same decision (timing may differ)."""
    x, y = json.loads(a.read_text()), json.loads(b.read_text())
    if a.name.endswith('.failure.json'):
        return x.get('status') == y.get('status')
    keys = ('dataset', 'seed', 'scenario', 'partition_status', 'partition_attempts',
            'continuous_features', 'categorical_features')
    canon = lambda v: json.dumps(v, sort_keys=True)  # noqa: E731
    return (canon(x['rows']) == canon(y['rows'])
            and x.get('source_prepared_sha256') == y.get('source_prepared_sha256')
            and all(canon(x['timing'].get(k)) == canon(y['timing'].get(k)) for k in keys))


def atomic_copy(src, dst):
    tmp = dst.with_name(dst.name + '.mergetmp')
    shutil.copy2(src, tmp)
    tmp.replace(dst)


def merge(job, shard, main, validate_record):
    """Copy new results into main; never overwrite. Returns counters."""
    s_dest = shard / 'checkpoints' / ds_dir(job.dataset)
    m_dest = main / 'checkpoints' / ds_dir(job.dataset)
    m_dest.mkdir(parents=True, exist_ok=True)
    stats = dict(ok=0, failures=0, identical=0, conflicts=[], source='')
    s_meta, m_meta = s_dest / 'SOURCE.json', m_dest / 'SOURCE.json'
    if s_meta.exists() and (s_dest / 'source.pkl').exists():
        if m_meta.exists():
            same = json.loads(s_meta.read_text())['prepared_sha256'] == json.loads(m_meta.read_text())['prepared_sha256']
            if not same:
                stats['source'] = 'SOURCE_CONFLICT'
                return stats  # refuse to merge models computed on a different source
            stats['source'] = 'SOURCE_SAME'
        else:
            atomic_copy(s_dest / 'source.pkl', m_dest / 'source.pkl')
            atomic_copy(s_meta, m_meta)
            stats['source'] = 'SOURCE_NEW'
        (m_dest / 'SOURCE_FAILURE.json').unlink(missing_ok=True)
    elif (s_dest / 'SOURCE_FAILURE.json').exists():
        if not m_meta.exists():
            atomic_copy(s_dest / 'SOURCE_FAILURE.json', m_dest / 'SOURCE_FAILURE.json')
        stats['source'] = 'SOURCE_FAILURE'
        return stats
    for seed in job.seeds:
        for sc in SCENARIOS:
            name = f'seed{seed:02d}__{sc}'
            for suffix in ('.json', '.failure.json'):
                src, dst = s_dest / (name + suffix), m_dest / (name + suffix)
                if not src.exists():
                    continue
                if suffix == '.json':
                    validate_record(json.loads(src.read_text()), job.dataset, seed, sc)
                if dst.exists() or (suffix == '.failure.json' and (m_dest / (name + '.json')).exists()):
                    if dst.exists() and (dst.read_bytes() == src.read_bytes() or same_result(dst, src)):
                        stats['identical'] += 1  # main copy kept; recomputation agreed
                    else:
                        stats['conflicts'].append(name + suffix)
                    continue
                atomic_copy(src, dst)
                stats['ok' if suffix == '.json' else 'failures'] += 1
    return stats


def run_job(job, a, main, work):
    shard = seed_job_dir(job, main, work, Path(a.source_cache) if a.source_cache else None)
    env = {**os.environ, **THREAD_ENV}
    cmd = [a.python, '-m', 'experiments.expanded_42seeds_20261120.run', '--output', str(shard),
           '--dataset', job.dataset, '--seeds', ','.join(map(str, job.seeds)), '--workers', '1']
    if getattr(a, 'timeout', None):  # supplementary extended-deadline runs only; default keeps run.py's 2700 s
        cmd += ['--timeout', str(a.timeout)]
    t0 = time.time()
    with (shard / 'run.log').open('w') as fh:
        code = subprocess.run(cmd, cwd=a.repo, env=env, stdout=fh, stderr=subprocess.STDOUT).returncode
    return shard, code, time.time() - t0


def audit(a, main, lock):
    with lock:
        r = subprocess.run([a.python, '-m', 'experiments.expanded_42seeds_20261120.run', '--audit',
                            '--output', str(main)], cwd=a.repo, capture_output=True, text=True)
    lines = (r.stdout.strip().splitlines() or ['{}'])
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {'audit_error': (r.stderr or r.stdout)[-500:]}


def force_rmtree(path):
    """rmtree that also removes copies of the frozen read-only ORIGINAL_3566580 tree."""
    def make_writable_and_retry(func, target, _exc):
        os.chmod(target, 0o700)
        parent = os.path.dirname(target)
        if parent:
            os.chmod(parent, 0o700)
        func(target)
    if path.exists():
        for root, dirs, _ in os.walk(path):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o700)
        shutil.rmtree(path, onexc=make_writable_and_retry)


def snapshot(main, snap_dir, keep=3):
    """Zip result files (no raw source data / caches) to durable storage."""
    snap_dir.mkdir(parents=True, exist_ok=True)
    name = snap_dir / f"checkpoint_{time.strftime('%Y%m%dT%H%M%S')}"
    tmp_root = main.parent / '.snapshot_tmp'
    force_rmtree(tmp_root)
    shutil.copytree(main, tmp_root / main.name, ignore=shutil.ignore_patterns('source.pkl', 'openml', '*.tmp', '*.mergetmp'))
    shutil.make_archive(str(name), 'zip', tmp_root)
    force_rmtree(tmp_root)
    for old in sorted(snap_dir.glob('checkpoint_*.zip'))[:-keep]:
        old.unlink()
    return str(name) + '.zip'


def main_loop():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--python', required=True)
    p.add_argument('--main', required=True)
    p.add_argument('--work', required=True)
    p.add_argument('--profile', required=True, help='JSON {dataset: {per_model, rss_mb}}')
    p.add_argument('--max-jobs', type=int, default=8)
    p.add_argument('--max-heavy', type=int, default=8, help='concurrent jobs with per-model projection > 600 s')
    p.add_argument('--mem-budget-gb', type=float, default=11.0)
    p.add_argument('--mem-reserve-gb', type=float, default=2.0)
    p.add_argument('--datasets', default='', help='comma list to restrict (speed test)')
    p.add_argument('--seeds', default='', help='comma list to restrict (speed test)')
    p.add_argument('--snapshot-dir', default='')
    p.add_argument('--source-cache', default='', help='prefetch staging dir written by run.run_dataset')
    p.add_argument('--audit-every-min', type=float, default=30)
    p.add_argument('--timeout', type=float, default=None, help='per-model deadline passed to run.py (default: run.py default)')
    p.add_argument('--defer', default='', help='comma list of datasets scheduled after all others (order only)')
    a = p.parse_args()
    sys.path.insert(0, a.repo)
    from experiments.expanded_42seeds_20261120.run import selected_registry, validate_record

    main, work = Path(a.main), Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    _, chosen = selected_registry()
    registry = chosen.to_dict('records')
    profile = json.loads(Path(a.profile).read_text())
    by_dir = {ds_dir(r['dataset']): r['dataset'] for r in registry}
    for shard in sorted(work.glob('*/s??-??')):  # recover results left by an interrupted run
        dataset = by_dir.get(shard.parent.name)
        if not dataset:
            continue
        lo, hi = int(shard.name[1:3]), int(shard.name[4:6])
        stats = merge(Job(dataset, tuple(range(lo, hi + 1)), 0, 0), shard, main, validate_record)
        log(main, {'kind': 'recovered', 'shard': f'{shard.parent.name}/{shard.name}', **stats})
        if not stats['conflicts'] and stats['source'] != 'SOURCE_CONFLICT':
            shutil.rmtree(shard, ignore_errors=True)
    only = {d for d in a.datasets.split(',') if d}
    defer = frozenset(x for x in a.defer.split(',') if x)
    jobs = plan(main, registry, profile, only, defer)
    if a.seeds:
        keep = {int(s) for s in a.seeds.split(',')}
        jobs = [Job(j.dataset, tuple(s for s in j.seeds if s in keep), j.cost, j.mem_gb, j.heavy)
                for j in jobs if keep & set(j.seeds)]
    # A dataset whose source is not cached yet runs one job first; the rest wait for its source.
    log(main, {'kind': 'plan', 'jobs': len(jobs), 'datasets': len({j.dataset for j in jobs}),
               'models': sum(len(j.seeds) for j in jobs) * 4, 'max_jobs': a.max_jobs,
               'mem_budget_gb': a.mem_budget_gb})
    lock = threading.Lock()
    running, started = {}, {}
    source_busy = set()
    last_audit = time.time()
    totals = dict(ok=0, failures=0, conflicts=0, jobs_done=0)
    cache = Path(a.source_cache) if a.source_cache else None
    last_ctl = None
    with ThreadPoolExecutor(max_workers=64) as pool:
        while jobs or running:
            ctl = load_control(main, a)
            if ctl != last_ctl:
                log(main, {'kind': 'control', **ctl})
                last_ctl = ctl
            admitted = True
            while admitted and jobs and len(running) < ctl['max_jobs']:
                admitted = False
                now = time.time()
                # Jobs younger than RAMP_SECONDS have not reached peak RSS yet: pre-deduct them.
                ramping = sum(j.mem_gb for f, j in running.items() if now - started[f] < RAMP_SECONDS)
                heavy_running = sum(j.heavy for j in running.values())
                est_total = sum(j.mem_gb for j in running.values())
                avail = mem_available_gb()
                for idx, job in enumerate(jobs):
                    cached = source_dir(job.dataset, main, cache) is not None
                    if not cached and job.dataset in source_busy:
                        continue
                    if job.heavy and heavy_running >= ctl['max_heavy']:
                        continue
                    if running and est_total + job.mem_gb > ctl['mem_budget_gb']:
                        continue
                    if running and avail - ramping - job.mem_gb < ctl['mem_reserve_gb']:
                        continue
                    jobs.pop(idx)
                    if not cached:
                        source_busy.add(job.dataset)
                    fut = pool.submit(run_job, job, a, main, work)
                    running[fut], started[fut] = job, time.time()
                    log(main, {'kind': 'start', 'job': job.key, 'models': 4 * len(job.seeds),
                               'mem_gb': job.mem_gb, 'est_total_gb': round(est_total + job.mem_gb, 2),
                               'mem_available_gb': round(avail, 2), 'ramping_gb': round(ramping, 2),
                               'running': len(running), 'queued': len(jobs)})
                    admitted = True
                    break
            if not running:
                time.sleep(5)
                continue
            done, _ = wait(list(running), timeout=60, return_when=FIRST_COMPLETED)
            for fut in done:
                job = running.pop(fut)
                started.pop(fut, None)
                source_busy.discard(job.dataset)
                try:
                    shard, code, secs = fut.result()
                    with lock:
                        stats = merge(job, shard, main, validate_record)
                except Exception as exc:  # report, never hide
                    log(main, {'kind': 'job_error', 'job': job.key, 'error': f'{type(exc).__name__}: {exc}'})
                    continue
                totals['ok'] += stats['ok']
                totals['failures'] += stats['failures']
                totals['conflicts'] += len(stats['conflicts'])
                totals['jobs_done'] += 1
                log(main, {'kind': 'done', 'job': job.key, 'exit': code, 'seconds': round(secs, 1),
                           **{k: v for k, v in stats.items()}, 'remaining_jobs': len(jobs) + len(running)})
                if code == 0 and not stats['conflicts'] and stats['source'] != 'SOURCE_CONFLICT':
                    shutil.rmtree(shard, ignore_errors=True)
            if time.time() - last_audit > a.audit_every_min * 60:
                last_audit = time.time()
                try:  # bookkeeping must never stop job scheduling
                    state = audit(a, main, lock)
                    snap = snapshot(main, Path(a.snapshot_dir)) if a.snapshot_dir else ''
                    log(main, {'kind': 'audit', **state, 'snapshot': snap, **totals})
                except Exception as exc:
                    log(main, {'kind': 'audit_error', 'error': f'{type(exc).__name__}: {exc}'[:400]})
    state = audit(a, main, lock)
    try:
        snap = snapshot(main, Path(a.snapshot_dir)) if a.snapshot_dir else ''
    except Exception as exc:
        snap = f'SNAPSHOT_ERROR {type(exc).__name__}: {exc}'[:300]
    log(main, {'kind': 'final_audit', **state, 'snapshot': snap, **totals})
    if not a.datasets and not a.seeds:  # full run only: lets the publisher stop
        (main / 'ORCHESTRATOR_DONE').write_text(json.dumps(state))


if __name__ == '__main__':
    main_loop()
