"""Bitset support unions must equal the original dense block product exactly."""
import numpy as np
import pytest

from fedrs import predict
from fedrs.predict import RuleContext


def dense_union(lhs, ctx, cols):
    """Original implementation (56e293c), kept verbatim for the comparison."""
    lhs = lhs.astype(np.int32)
    n_train = ctx.support.shape[1]
    total = np.zeros(len(lhs), dtype=np.int64)
    block = max(1, (32 * 1024 * 1024) // (4 * (len(cols) + len(lhs))))
    for start in range(0, n_train, block):
        stop = min(start + block, n_train)
        support = ctx.support[cols, start:stop].astype(np.int32)
        total += ((lhs @ support) > 0).sum(axis=1)
    return total


def random_ctx(rng, n_rules, n_train, n_classes, density):
    y = rng.integers(0, n_classes, n_train).astype(str)
    rule_class = rng.integers(0, n_classes, n_rules)
    classes = tuple(sorted({str(c) for c in rule_class}, key=str))
    lookup = {c: i for i, c in enumerate(classes)}
    decisions = np.asarray([str(c) for c in rule_class], dtype=object)
    support = (rng.random((n_rules, n_train)) < density) & (y[None, :] == decisions[:, None])
    return RuleContext(
        rules=tuple(range(n_rules)), decisions=decisions, classes=classes,
        rule_class=np.asarray([lookup[d] for d in decisions]), support=support,
        weights=support.sum(axis=1).astype(float),
        class_sizes={c: int((y == c).sum()) for c in classes}, default_class=classes[0],
        is_empty=np.zeros(n_rules, dtype=bool))


@pytest.mark.parametrize("seed", range(12))
def test_union_sizes_match_dense_product(seed):
    rng = np.random.default_rng(seed)
    n_rules = int(rng.integers(1, 400))
    n_train = int(rng.integers(1, 3000))  # includes non-multiples of 8 / 64
    ctx = random_ctx(rng, n_rules, n_train, int(rng.integers(1, 5)), float(rng.choice([0.001, 0.05, 0.5])))
    M = rng.random((int(rng.integers(1, 300)), n_rules)) < float(rng.choice([0.002, 0.02, 0.3]))
    for k in range(len(ctx.classes)):
        cols = np.flatnonzero(ctx.rule_class == k)
        lhs = M[:, cols]
        np.testing.assert_array_equal(predict._union_sizes(lhs, ctx, k), dense_union(lhs, ctx, cols))


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("policy", ["GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL"])
def test_resolve_scalable_matches_reference_resolve(seed, policy):
    rng = np.random.default_rng(100 + seed)
    ctx = random_ctx(rng, int(rng.integers(5, 300)), int(rng.integers(10, 2000)), int(rng.integers(2, 5)), 0.05)
    M = rng.random((int(rng.integers(5, 400)), ctx.n_rules)) < 0.03
    assert predict.resolve_scalable(M, ctx, policy).tolist() == predict.resolve(M, ctx, policy).tolist()
