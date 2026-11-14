"""Research-stage partition-cache reduct engine, separate from frozen exact baseline.

EXACT_CACHE enumerates ALL minimum cardinality reducts like canonical code.
GREEDY_POS is a non-minimum approximate reduct and must NEVER be reported as
a minimum-cardinality reduct. It preserves the EXACT integer train POS count
(by checking equality), and may lose generalization after dropping features.
Evaluation must report test performance, reduct size and wall time separately.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FastReductResult:
    selected: tuple[str, ...]
    positive_region: int
    full_positive_region: int
    reduct_size: int
    is_minimum_cardinality: bool
    candidate_count: int
    feature_count: int
    n_rows: int
    positive_region_queries: int
    cache_entries: int
    selection_seconds: float
    algorithm: str


class PartitionCache:
    """Integer-coded partitions, common-prefix partition memoization.

    For a subset A, POS_A(D) = sum(size(E)) across decision-pure
    equivalence classes E of IND(A).
    This is *exact* even with identical condition rows but contradictory
    decisions. Missing values are coded as explicit category.
    """

    def __init__(self, df: pd.DataFrame, features: list[str] | tuple[str, ...], target: str,
                 max_cache_entries: int = 2048):
        if not len(df): raise ValueError("Empty training table")
        self.features=tuple(features)
        if len(set(self.features))!=len(self.features):raise ValueError("Duplicate features")
        if target in self.features:raise ValueError("Target leakage")
        self.n=len(df)
        self.codes=[pd.factorize(df[k],sort=False,use_na_sentinel=False)[0].astype(np.int64)
                    for k in self.features]
        self.y=pd.factorize(df[target],sort=False,use_na_sentinel=False)[0].astype(np.int64)
        self.cache={():np.zeros(self.n,dtype=np.int64)}
        self.cache_limit=max(int(max_cache_entries),1)
        self.positive_cache={}
        self.requests=0
    def partition(self, subset: tuple[int,...]):
        k=tuple(subset)
        hit=self.cache.get(k)
        if hit is not None:return hit
        if not k:return self.cache[()]
        prev=self.partition(k[:-1])
        arr=np.stack((prev,self.codes[k[-1]]),axis=1)
        _,codes=np.unique(arr,axis=0,return_inverse=True)
        if len(self.cache)<self.cache_limit:self.cache[k]=codes
        return codes
    def pos(self, subset: tuple[int,...]):
        subset=tuple(subset);self.requests+=1
        if subset in self.positive_cache:return self.positive_cache[subset]
        group=self.partition(subset)
        mx=int(group.max())+1
        smallest=np.full(mx,np.iinfo(np.int64).max,dtype=np.int64)
        largest=np.full(mx,-1,dtype=np.int64)
        np.minimum.at(smallest,group,self.y)
        np.maximum.at(largest,group,self.y)
        counts=np.bincount(group,minlength=mx)
        count=int(counts[smallest==largest].sum())
        if len(self.positive_cache)<self.cache_limit:self.positive_cache[subset]=count
        return count
    def full(self):return self.pos(tuple(range(len(self.features))))


def exact_cached(df, features, target, max_features=12):
    """Identical exact-minimum search semantics as canonical, but cached POS.

    Reject beyond max_features instead of silently producing an approximate
    result named 'exact'. For larger dimensionality use greedy_pos separately.
    """
    start=time.perf_counter()
    f=tuple(features)
    if len(f)>max_features:raise ValueError("EXACT_ENUMERATION_FEATURE_CAP_EXCEEDED")
    c=PartitionCache(df,f,target,max_cache_entries=max(2048,2**len(f)))
    full=c.full()
    found=[]
    for k in range(len(f)+1):
        for subset in itertools.combinations(range(len(f)),k):
            if c.pos(subset)==full:found.append(tuple(f[i] for i in subset))
        if found:break
    if not found:raise AssertionError("Full set must satisfy full POS")
    # Preserve canonical's ordering of candidate reducts, not enumeration order.
    selected=tuple(sorted(set(found)))[0]
    result=FastReductResult(selected=selected,positive_region=c.pos(tuple(f.index(x) for x in selected)),
        full_positive_region=full,reduct_size=len(selected),is_minimum_cardinality=True,
        candidate_count=len(found),feature_count=len(f),n_rows=len(df),
        positive_region_queries=c.requests,cache_entries=len(c.cache),
        selection_seconds=time.perf_counter()-start,algorithm="EXACT_PARTITION_CACHE")
    return result


def greedy_pos(df, features, target, max_cache_entries=4096):
    """Approximate reduct that guarantees full-training POS preservation.

    Greedy step maximizes POS of the next extension; equal gains use fixed
    source-feature order. It can get trapped into a larger reduct than exact.
    Backward removal applies the same integer POS test to prune. This is NOT
    a proof of minimum cardinality, even when result happens to be minimal.
    """
    start=time.perf_counter()
    f=tuple(features)
    c=PartitionCache(df,f,target,max_cache_entries=max_cache_entries)
    goal=c.full()
    chosen=()
    remaining=list(range(len(f)))
    while c.pos(chosen)<goal:
        if not remaining:raise AssertionError("Greedy did not reach full POS")
        scored=[(c.pos(tuple(sorted(chosen+(j,)))),j) for j in remaining]
        # Stable source order for exact tie.
        best=max(scored,key=lambda item:(item[0],-item[1]))[1]
        chosen=tuple(sorted(chosen+(best,)))
        remaining.remove(best)
    # Backward remove in REVERSE source order.
    for ix in reversed(tuple(chosen)):
        smaller=tuple(j for j in chosen if j!=ix)
        if c.pos(smaller)==goal:chosen=smaller
    assert c.pos(chosen)==goal
    return FastReductResult(selected=tuple(f[i] for i in chosen),
        positive_region=c.pos(chosen),full_positive_region=goal,
        reduct_size=len(chosen),is_minimum_cardinality=False,
        candidate_count=-1,feature_count=len(f),n_rows=len(df),
        positive_region_queries=c.requests,cache_entries=len(c.cache),
        selection_seconds=time.perf_counter()-start,algorithm="GREEDY_POS_EXPERIMENTAL")
