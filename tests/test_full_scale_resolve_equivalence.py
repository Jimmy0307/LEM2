"""Regression coverage for bounded-memory policy resolution."""
import numpy as np
import pandas as pd
import pytest
import os
from pathlib import Path
import subprocess
import sys
import textwrap

from fedrs.experiment import fit_model, nested_split
from fedrs.predict import POLICIES, build_context, match_matrix, resolve
from fedrs import predict
from roughset.core import Rule
from teacher_demo.conflict_aware_coverage_pilot import load_bundle


@pytest.mark.parametrize("seed", [3, 13, 29])
def test_context_support_matches_reference_match_matrix(seed):
    rng = np.random.default_rng(seed)
    train = pd.DataFrame({"x": rng.integers(0, 4, 90).astype(str),
                          "y": rng.integers(0, 3, 90).astype(str),
                          "target": rng.integers(0, 3, 90).astype(str)})
    rules = [Rule((("x", str(i % 4)), ("y", str(i % 3))), str(i % 3)) for i in range(12)]
    rules += [Rule((), "1")]
    ctx = build_context(rules, train, "target", "0")
    expected = (match_matrix(train, rules) & (train.target.to_numpy()[:, None] == ctx.decisions[None, :])).T
    np.testing.assert_array_equal(ctx.support, expected)
    np.testing.assert_array_equal(ctx.weights, expected.sum(axis=1))


@pytest.mark.parametrize("seed", [2, 17, 45])
def test_random_rule_sets_match_original(seed):
    rng = np.random.default_rng(seed)
    train = pd.DataFrame({"x": rng.integers(0, 4, 100).astype(str),
                          "y": rng.integers(0, 4, 100).astype(str),
                          "target": rng.integers(0, 3, 100).astype(str)})
    rules = [Rule((("x", str(rng.integers(4))), ("y", str(rng.integers(4)))),
                  str(rng.integers(3))) for _ in range(18)]
    rules += [Rule((), "0")]
    ctx = build_context(rules, train, "target", "0")
    M = rng.integers(0, 2, (2100, len(rules)), dtype=np.uint8).astype(bool)
    M[:100] = M[100:200]
    M[0] = False  # unmatched rows must retain the training majority fallback
    for policy in POLICIES:
        np.testing.assert_array_equal(predict.resolve_scalable(M, ctx, policy), resolve(M, ctx, policy))


@pytest.mark.parametrize("name", ["iris", "haberman", "wine"])
def test_fitted_real_data_match_original(name):
    bundle, _ = load_bundle(name)
    dev, val, test = nested_split(bundle.frame, bundle.target, 1001)
    fm = fit_model(bundle.features, bundle.schema.continuous, bundle.schema.categorical,
                   bundle.target, {"central": dev}, dev, val, test)
    M = match_matrix(fm.frames["test"], fm.rules)
    for policy in POLICIES:
        np.testing.assert_array_equal(predict.resolve_scalable(M, fm.ctx, policy), resolve(M, fm.ctx, policy))


def test_empty_inputs_and_no_rules():
    frame = pd.DataFrame({"target": ["a", "b"]})
    ctx = build_context([], frame, "target", "a")
    for n in (0, 3):
        M = np.zeros((n, 0), dtype=bool)
        for policy in POLICIES:
            np.testing.assert_array_equal(predict.resolve_scalable(M, ctx, policy), resolve(M, ctx, policy))


def test_context_and_matching_at_300000_rows():
    base = pd.DataFrame({"x": ["0", "1", "2"], "target": ["a", "b", "a"]})
    frame = pd.concat([base] * 100000, ignore_index=True)
    rules = [Rule((("x", str(i)),), d) for i in range(3) for d in ("a", "b")]
    ctx = build_context(rules, frame, "target", "a")
    matrix = match_matrix(frame, rules)
    assert matrix.shape == (300000, 6)
    assert ctx.support.shape == (6, 300000)
    expected = match_matrix(base, rules)
    np.testing.assert_array_equal(matrix[:3], expected)
    np.testing.assert_array_equal(ctx.support[:, :3], (expected & (base.target.to_numpy()[:, None] == ctx.decisions)).T)
    for policy in POLICIES:
        actual = predict.resolve_scalable(matrix, ctx, policy)
        expected_pred = resolve(expected, ctx, policy)
        np.testing.assert_array_equal(actual[:3], expected_pred)
        np.testing.assert_array_equal(actual, np.tile(expected_pred, 100000))


@pytest.mark.skipif(sys.platform != "linux", reason="Linux address-space limit")
def test_large_rule_context_and_matching_under_memory_limit():
    script = textwrap.dedent('''
        import resource
        import numpy as np
        import pandas as pd
        from roughset.core import Rule
        from fedrs.predict import build_context, match_matrix
        limit = 2_000_000_000
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        frame = pd.DataFrame({'x': np.tile(['0', '1', '2'], 100000),
                              'target': np.tile(['a', 'b', 'a'], 100000)})
        rules = [Rule((('x', str(i % 3)),), 'a' if i % 2 else 'b') for i in range(2000)]
        ctx = build_context(rules, frame, 'target', 'a')
        assert ctx.support.shape == (2000, 300000)
        assert ctx.support[0, :3].tolist() == [False, False, False]
        matched = match_matrix(frame, rules)
        assert matched.shape == (300000, 2000)
        assert matched[:3, 0].tolist() == [True, False, False]
        assert ctx.support.shape == (2000, 300000)
    ''')
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    run = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                         env=env, text=True, capture_output=True, timeout=180)
    assert run.returncode == 0, run.stderr


@pytest.mark.skipif(sys.platform != "linux", reason="Linux address-space limit")
def test_population_resolution_bounds_support_conversion_memory():
    script = textwrap.dedent('''
        import resource
        import numpy as np
        from roughset.core import Rule
        from fedrs.predict import RuleContext, resolve_scalable
        limit = 1_300_000_000
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        r, n = 1000, 300000
        support = np.ones((r, n), dtype=bool)
        rules = tuple(Rule((), 'a') for _ in range(r))
        ctx = RuleContext(rules, np.array(['a'] * r, dtype=object), ('a',), np.zeros(r, dtype=int),
                          support, np.full(r, float(n)), {'a': n}, 'a', np.ones(r, dtype=bool))
        matrix = np.vstack([np.zeros(r, dtype=bool), np.ones(r, dtype=bool)])
        for policy in ('GLOBAL_STRENGTH', 'POPULATION_STANDARD', 'POPULATION_GLOBAL'):
            assert resolve_scalable(matrix, ctx, policy).tolist() == ['a', 'a']
    ''')
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    run = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                         env=env, text=True, capture_output=True, timeout=180)
    assert run.returncode == 0, run.stderr
