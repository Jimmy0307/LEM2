"""Gated git_revision migration for RUN_MANIFEST.json (3566580 -> current HEAD).

run.py requires the stored contract to equal the live contract exactly, and
git_revision is part of it.  The program was re-created on GitHub via the API
with an identical tree but a new commit SHA, so the contract check would
reject resuming.  This tool does NOT bypass that check and does NOT modify
run.py.  It migrates the manifest only when every condition holds:

  1. working tree clean and HEAD^{tree} equals the declared original tree;
  2. stored manifest is byte-identical to the frozen original copy;
  3. stored manifest equals the live contract in every field but git_revision,
     and its git_revision is the declared original commit;
  4. the source-verification report shows every cached source reproduced;
  5. the fidelity gate recomputed every completed checkpoint identically.

The original manifest stays frozen in ORIGINAL_3566580/, the evidence goes to
REVISION_COMPATIBILITY.json, and each migration is appended to
MANIFEST_HISTORY.jsonl.  The new manifest is exactly what run.py itself writes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


def live_contract(repo, timeout):
    """Mirror of run.main()'s contract construction (same imports, same order)."""
    sys.path.insert(0, repo)
    from experiments.expanded_42seeds_20261120.run import SEEDS, VARIANTS, selected_registry
    from experiments.full_scale_20261118.model import SCENARIOS
    from fedrs.predict import POLICIES
    full, _ = selected_registry()
    return {'git_revision': git(repo, 'rev-parse', 'HEAD'),
            'registry_sha256': hashlib.sha256(full.to_csv(index=False).encode()).hexdigest(),
            'seeds': list(SEEDS), 'scenarios': list(SCENARIOS), 'policies': list(POLICIES),
            'variants': list(VARIANTS), 'split': 'NESTED_64_16_20', 'n_clients': 3,
            'timeout_seconds': timeout, 'full_rows': True,
            'source_feature_contract': 'existing full_scale_20261118 adapters'}


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(cond, message, failures):
    if not cond:
        failures.append(message)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--original-commit', required=True)
    p.add_argument('--expected-tree', required=True)
    p.add_argument('--source-report', required=True)
    p.add_argument('--gate-report', required=True)
    p.add_argument('--timeout', type=float, default=2700)
    a = p.parse_args()
    out = Path(a.output)
    manifest, frozen = out / 'RUN_MANIFEST.json', out / 'ORIGINAL_3566580' / 'RUN_MANIFEST.json'
    timeout = int(a.timeout) if a.timeout == int(a.timeout) else a.timeout  # run.py default is int 2700
    contract = live_contract(a.repo, timeout)
    stored = json.loads(manifest.read_text())

    if stored == contract and (out / 'REVISION_COMPATIBILITY.json').exists():
        print('ALREADY_MIGRATED', contract['git_revision'])
        return 0

    failures = []
    head, tree = contract['git_revision'], git(a.repo, 'rev-parse', 'HEAD^{tree}')
    check(git(a.repo, 'status', '--porcelain') == '', 'working tree not clean', failures)
    check(tree == a.expected_tree, f'HEAD tree {tree} != expected {a.expected_tree}', failures)
    check(sha256_file(manifest) == sha256_file(frozen), 'stored manifest differs from frozen original', failures)
    check(stored.get('git_revision') == a.original_commit, 'stored git_revision is not the declared original', failures)
    diff = sorted(k for k in set(stored) | set(contract) if k != 'git_revision' and stored.get(k) != contract.get(k))
    check(not diff, f'contract fields differ beyond git_revision: {diff}', failures)
    sources = json.loads(Path(a.source_report).read_text())
    check(sources and all(r['status'] in ('VERIFIED_WROTE_PKL', 'CACHED_OK') for r in sources),
          'source verification not clean', failures)
    gate = json.loads(Path(a.gate_report).read_text())
    n_ckpt = sum(1 for f in (out / 'checkpoints').glob('*/seed*__*.json') if not f.name.endswith('.failure.json'))
    check(gate.get('verdict') == 'PASS' and gate.get('original_models') == n_ckpt,
          f"fidelity gate not PASS over all {n_ckpt} checkpoints", failures)
    if failures:
        print('REFUSED:\n  ' + '\n  '.join(failures))
        return 1

    record = {
        'migrated_at_utc': datetime.now(timezone.utc).isoformat(),
        'reason': 'Program re-created via GitHub API: identical tree, new commit SHA; run.py contract compares git_revision exactly.',
        'original_commit': a.original_commit,
        'original_commit_tree_declared': a.expected_tree,
        'original_commit_locally_available': False,
        'current_commit': head, 'current_tree_verified': tree,
        'fields_changed': ['git_revision'],
        'original_manifest_frozen_copy': 'ORIGINAL_3566580/RUN_MANIFEST.json',
        'original_manifest_sha256': sha256_file(frozen),
        'registry_sha256': contract['registry_sha256'],
        'source_verification': {'report': a.source_report, 'datasets': len(sources),
                                'statuses': sorted({r['status'] for r in sources})},
        'fidelity_gate': {'report': a.gate_report, 'verdict': gate['verdict'],
                          'recomputed_models': gate['original_models'], 'problems': gate['problems']},
    }
    tmp = out / 'REVISION_COMPATIBILITY.tmp'
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    tmp.replace(out / 'REVISION_COMPATIBILITY.json')
    with (out / 'MANIFEST_HISTORY.jsonl').open('a') as fh:
        fh.write(json.dumps({'at': record['migrated_at_utc'], 'from': stored, 'to': contract}) + '\n')
    tmp = manifest.with_suffix('.tmp')  # same atomic write and format as run.atomic_json
    tmp.write_text(json.dumps(contract, ensure_ascii=False, default=str, indent=2))
    tmp.replace(manifest)
    print('MIGRATED', a.original_commit, '->', head)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
