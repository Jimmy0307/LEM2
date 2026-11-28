"""Unit tests for the merge rules of orchestrate.py (no model computation)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import orchestrate as o  # noqa: E402

DS = 'UCI20:iris'


def noop_validate(record, dataset, seed, scenario):
    assert record['timing']['seed'] == seed


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def record(seed, value=1):
    return {'rows': [{'v': value}], 'timing': {'seed': seed}, 'source_prepared_sha256': 'abc'}


def setup(tmp_path, main_sha='abc', shard_sha='abc'):
    main, shard = tmp_path / 'main', tmp_path / 'shard'
    for root, sha in ((main, main_sha), (shard, shard_sha)):
        d = root / 'checkpoints' / o.ds_dir(DS)
        write(d / 'SOURCE.json', {'prepared_sha256': sha})
        (d / 'source.pkl').write_bytes(b'x')
    return main, shard, o.Job(DS, (1, 2), 0, 0)


def ck(root, name):
    return root / 'checkpoints' / o.ds_dir(DS) / name


def test_new_results_are_copied(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(shard, 'seed01__CENTRALIZED.json'), record(1))
    write(ck(shard, 'seed02__FED_IID.failure.json'), {'status': 'TIMEOUT'})
    stats = o.merge(job, shard, main, noop_validate)
    assert stats['ok'] == 1 and stats['failures'] == 1 and not stats['conflicts']
    assert json.loads(ck(main, 'seed01__CENTRALIZED.json').read_text()) == record(1)


def test_existing_main_file_is_never_overwritten(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(main, 'seed01__CENTRALIZED.json'), record(1, value=1))
    write(ck(shard, 'seed01__CENTRALIZED.json'), record(1, value=2))
    stats = o.merge(job, shard, main, noop_validate)
    assert stats['conflicts'] == ['seed01__CENTRALIZED.json']
    assert json.loads(ck(main, 'seed01__CENTRALIZED.json').read_text())['rows'] == [{'v': 1}]


def test_identical_file_is_accepted(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(main, 'seed01__CENTRALIZED.json'), record(1))
    write(ck(shard, 'seed01__CENTRALIZED.json'), record(1))
    stats = o.merge(job, shard, main, noop_validate)
    assert stats['identical'] == 1 and not stats['conflicts']


def test_failure_does_not_shadow_success(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(main, 'seed01__FED_A01.json'), record(1))
    write(ck(shard, 'seed01__FED_A01.failure.json'), {'status': 'TIMEOUT'})
    stats = o.merge(job, shard, main, noop_validate)
    assert stats['conflicts'] and not ck(main, 'seed01__FED_A01.failure.json').exists()


def test_source_sha_conflict_blocks_merge(tmp_path):
    main, shard, job = setup(tmp_path, main_sha='abc', shard_sha='zzz')
    write(ck(shard, 'seed01__CENTRALIZED.json'), record(1))
    stats = o.merge(job, shard, main, noop_validate)
    assert stats['source'] == 'SOURCE_CONFLICT'
    assert not ck(main, 'seed01__CENTRALIZED.json').exists()
    assert json.loads(ck(main, 'SOURCE.json').read_text())['prepared_sha256'] == 'abc'


def test_invalid_record_raises(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(shard, 'seed02__CENTRALIZED.json'), record(1))  # seed mismatch
    try:
        o.merge(job, shard, main, noop_validate)
    except AssertionError:
        return
    raise AssertionError('invalid record was merged')


def test_source_dir_prefers_main_then_cache(tmp_path):
    main, cache = tmp_path / 'main', tmp_path / 'cache'
    assert o.source_dir(DS, main, cache) is None
    write(ck(cache, 'SOURCE.json'), {'prepared_sha256': 'c'})
    assert o.source_dir(DS, main, cache) is None          # half a cache entry is not usable
    (ck(cache, 'source.pkl')).write_bytes(b'c')
    assert o.source_dir(DS, main, cache) == ck(cache, '')
    write(ck(main, 'SOURCE.json'), {'prepared_sha256': 'm'})
    (ck(main, 'source.pkl')).write_bytes(b'm')
    assert o.source_dir(DS, main, cache) == ck(main, '')
    job = o.Job(DS, (1,), 0, 0)
    (main / 'RUN_MANIFEST.json').write_text('{}')
    shard = o.seed_job_dir(job, main, tmp_path / 'work', cache)
    assert (shard / 'checkpoints' / o.ds_dir(DS) / 'source.pkl').read_bytes() == b'm'


def test_load_control_overrides_and_fallback(tmp_path):
    class A:
        max_jobs, max_heavy, mem_budget_gb, mem_reserve_gb = 16, 8, 12.0, 1.5
    assert o.load_control(tmp_path, A) == {'max_jobs': 16, 'max_heavy': 8, 'mem_budget_gb': 12.0, 'mem_reserve_gb': 1.5}
    (tmp_path / 'ORCHESTRATOR_CONTROL.json').write_text('{"max_jobs": 20, "mem_budget_gb": 24}')
    ctl = o.load_control(tmp_path, A)
    assert ctl['max_jobs'] == 20 and ctl['mem_budget_gb'] == 24.0 and ctl['max_heavy'] == 8
    (tmp_path / 'ORCHESTRATOR_CONTROL.json').write_text('{"max_jobs": ')  # half-written file
    assert o.load_control(tmp_path, A)['max_jobs'] == 16


def test_snapshot_handles_read_only_frozen_tree(tmp_path):
    main = tmp_path / 'run' / 'expanded'
    frozen = main / 'ORIGINAL_3566580' / 'source_records' / 'X'
    write(frozen / 'SOURCE.json', {'a': 1})
    write(main / 'STATUS.json', {'s': 1})
    (main / 'checkpoints' / 'D').mkdir(parents=True)
    (main / 'checkpoints' / 'D' / 'source.pkl').write_bytes(b'raw')
    for p in sorted(main.joinpath('ORIGINAL_3566580').rglob('*'), reverse=True) + [main / 'ORIGINAL_3566580']:
        p.chmod(0o444 if p.is_file() else 0o555)
    snap = o.snapshot(main, tmp_path / 'snaps')
    import zipfile
    names = zipfile.ZipFile(snap).namelist()
    assert any(n.endswith('ORIGINAL_3566580/source_records/X/SOURCE.json') for n in names)
    assert not any(n.endswith('source.pkl') for n in names)          # raw data never archived
    assert not (main.parent / '.snapshot_tmp').exists()              # temp tree removed
    assert (main / 'ORIGINAL_3566580' / 'source_records' / 'X' / 'SOURCE.json').exists()  # originals untouched


def full_record(seed, wall, value=1):
    return {'rows': [{'v': value}], 'source_prepared_sha256': 'abc',
            'timing': {'seed': seed, 'wall_seconds': wall, 'partition_status': 'OK'}}


def test_recomputation_differing_only_in_timing_is_identical(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(main, 'seed01__CENTRALIZED.json'), full_record(1, 10.0))
    write(ck(shard, 'seed01__CENTRALIZED.json'), full_record(1, 99.0))
    stats = o.merge(job, shard, main, noop_validate)
    assert stats['identical'] == 1 and not stats['conflicts']
    assert json.loads(ck(main, 'seed01__CENTRALIZED.json').read_text())['timing']['wall_seconds'] == 10.0


def test_different_metrics_still_conflict(tmp_path):
    main, shard, job = setup(tmp_path)
    write(ck(main, 'seed01__CENTRALIZED.json'), full_record(1, 10.0, value=1))
    write(ck(shard, 'seed01__CENTRALIZED.json'), full_record(1, 10.0, value=2))
    assert o.merge(job, shard, main, noop_validate)['conflicts'] == ['seed01__CENTRALIZED.json']


def test_job_dir_carries_decided_models(tmp_path):
    main, cache = tmp_path / 'main', tmp_path / 'cache'
    write(ck(main, 'SOURCE.json'), {'prepared_sha256': 'm'})
    ck(main, 'source.pkl').write_bytes(b'm')
    write(ck(main, 'seed01__CENTRALIZED.json'), full_record(1, 1.0))
    write(ck(main, 'seed01__FED_IID.failure.json'), {'status': 'TIMEOUT'})
    write(ck(main, 'seed05__CENTRALIZED.json'), full_record(5, 1.0))   # other seed: not carried
    (main / 'RUN_MANIFEST.json').write_text('{}')
    shard = o.seed_job_dir(o.Job(DS, (1, 2), 0, 0), main, tmp_path / 'work', cache)
    names = {p.name for p in (shard / 'checkpoints' / o.ds_dir(DS)).iterdir()}
    assert {'seed01__CENTRALIZED.json', 'seed01__FED_IID.failure.json'} <= names
    assert 'seed05__CENTRALIZED.json' not in names


def test_chunking_and_pending(tmp_path):
    assert o.chunk([1, 2, 3, 4, 5], 2) == [(1, 2), (3, 4), (5,)]
    main = tmp_path / 'main'
    for sc in o.SCENARIOS:
        write(ck(main, f'seed01__{sc}.json'), record(1))
    write(ck(main, 'seed02__CENTRALIZED.failure.json'), {})
    assert o.pending_seeds(main, DS) == list(range(2, 43))


def test_deferred_datasets_are_scheduled_last_without_dropping_jobs(tmp_path):
    main = tmp_path / 'main'
    registry = [{'dataset': d, 'original_rows': 1000} for d in ('A:slow_doomed', 'B:fast', 'C:medium')]
    profile = {'A:slow_doomed': {'per_model': 2700}, 'B:fast': {'per_model': 10}, 'C:medium': {'per_model': 300}}
    base = o.plan(main, registry, profile, set())
    deferred = o.plan(main, registry, profile, set(), frozenset({'A:slow_doomed'}))
    assert base[0].dataset == 'A:slow_doomed'                       # heaviest-first by default
    assert sorted(j.key for j in base) == sorted(j.key for j in deferred)   # same jobs, order only
    first_deferred = next(i for i, j in enumerate(deferred) if j.dataset == 'A:slow_doomed')
    assert all(j.dataset == 'A:slow_doomed' for j in deferred[first_deferred:])
    assert deferred[0].dataset == 'C:medium'                          # others keep heaviest-first
