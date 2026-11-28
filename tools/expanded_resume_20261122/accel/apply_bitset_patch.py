"""Apply the exact bitset support-union acceleration to fedrs/predict.py (accel worktree only).

Replaces the dense block matrix product in ``_resolve_support_chunked`` by an
OR-of-packed-bitsets over ONLY the rules each pattern actually matches. The union
size U is the same integer as ((lhs @ support) > 0).sum(), so every score and
prediction is bit-identical. U is cached per (class, match pattern) on the
RuleContext so the three support-based policies (and both rule variants) reuse it.
"""
import sys
from pathlib import Path

path = Path(sys.argv[1])
src = path.read_text(encoding="utf-8")

OLD = '''        lhs = M[np.ix_(active, cols)].astype(np.int32)
        total = np.zeros(len(active), dtype=np.int64)
        # Bound both the converted support slice and the dense product.
        block = max(1, (32 * 1024 * 1024) // (4 * (len(cols) + len(active))))
        for start in range(0, n_train, block):
            stop = min(start + block, n_train)
            support = ctx.support[cols, start:stop].astype(np.int32)
            total += ((lhs @ support) > 0).sum(axis=1)
        U = total.astype(float)'''
NEW = '''        total = _union_sizes(M[np.ix_(active, cols)], ctx, k)
        U = total.astype(float)'''
assert src.count(OLD) == 1, "target block not found exactly once"
src = src.replace(OLD, NEW)

HELPERS = '''

# --------------------------------------- exact bitset support unions ------
# |union of Supp_G(r) over the matched class-k rules| per match pattern.
# Equivalent to ((lhs @ support) > 0).sum(axis=1) but touches only matched rules.

def _class_bitsets(ctx: RuleContext, k: int):
    cache = ctx.__dict__.setdefault("_bitset_cache", {})
    if k not in cache:
        cols = np.flatnonzero(ctx.rule_class == k)
        rows = np.flatnonzero(ctx.support[cols].any(axis=0))  # class-k rows covered by some rule
        n_words = max(1, -(-len(rows) // 64))
        bits = np.zeros((len(cols), n_words * 8), dtype=np.uint8)
        for start in range(0, len(cols), 256):  # bound the dense temporary
            stop = min(start + 256, len(cols))
            packed = np.packbits(ctx.support[cols[start:stop]][:, rows], axis=1)
            bits[start:stop, :packed.shape[1]] = packed
        cache[k] = bits.view(np.uint64)
    return cache[k]


def _union_sizes(lhs: np.ndarray, ctx: RuleContext, k: int) -> np.ndarray:
    bits = _class_bitsets(ctx, k)
    memo = ctx.__dict__.setdefault("_union_memo", {})
    out = np.empty(lhs.shape[0], dtype=np.int64)
    keys = np.packbits(lhs, axis=1)
    for i in range(lhs.shape[0]):
        key = (k, keys[i].tobytes())
        value = memo.get(key)
        if value is None:
            sel = np.flatnonzero(lhs[i])
            acc = np.bitwise_or.reduce(bits[sel], axis=0) if sel.size else np.zeros(bits.shape[1], np.uint64)
            value = int(np.bitwise_count(acc).sum())
            memo[key] = value
        out[i] = value
    return out
'''
anchor = "\n\ndef resolve_scalable("
assert src.count(anchor) == 1
src = src.replace(anchor, HELPERS + anchor)
path.write_text(src, encoding="utf-8")
print("patched", path)
