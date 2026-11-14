"""Exact semantic parity vs canonical, positive-region preservation and honest heuristics."""
import itertools
import numpy as np
import pandas as pd
import pytest
from roughset.reduct import _positive_region_size,select_minimum_reduct
from roughset.reduct_fast import PartitionCache,exact_cached,greedy_pos

def fixture(seed,n,m,k=3):
    rng=np.random.default_rng(seed)
    data={f"f{i}":rng.integers(0,5+i%2,size=n) for i in range(m)}
    labels=rng.integers(0,k,size=n)
    return pd.DataFrame({**data,"decision":labels})

@pytest.mark.parametrize("seed",[1,7,42])
@pytest.mark.parametrize("m",[2,3,5,7])
def test_all_subsets_pos_match_canonical(seed,m):
    df=fixture(seed,80,m)
    f=[f"f{i}" for i in range(m)]
    cache=PartitionCache(df,f,"decision")
    for k in range(m+1):
        for ids in itertools.combinations(range(m),k):
            attrs=[f[i] for i in ids]
            assert cache.pos(ids)==_positive_region_size(df,attrs,"decision"),(seed,attrs)

@pytest.mark.parametrize("seed",[1,7,42])
def test_exact_cached_matches_minimum_cardinality_and_lexicographic_choice(seed):
    df=fixture(seed,85,6,4);f=[f"f{i}" for i in range(6)]
    old=select_minimum_reduct(df,f,"decision")
    new=exact_cached(df,f,"decision")
    assert new.selected==old.selected_reduct
    assert new.candidate_count==old.candidate_count
    assert new.reduct_size==old.minimum_reduct_size
    assert new.full_positive_region==_positive_region_size(df,f,"decision")

def test_greedy_preserves_training_positive_region_without_claiming_minimality():
    df=fixture(19,140,15,3)
    f=[f"f{i}" for i in range(15)]
    result=greedy_pos(df,f,"decision")
    assert result.positive_region==_positive_region_size(df,f,"decision")
    assert result.is_minimum_cardinality is False
    assert len(result.selected)<=len(f)

def test_xor_and_contradictory_and_missing_values():
    df=pd.DataFrame({"a":["0","0","1","1","0","0"],
                     "b":["0","1","0","1","0","0"],
                     "constant":[1]*6,
                     "decision":["0","1","1","0","0","1"]})
    features=["a","b","constant"]
    cache=PartitionCache(df,features,"decision")
    for m in range(4):
        for ids in itertools.combinations(range(3),m):
            attrs=[features[i] for i in ids]
            assert cache.pos(ids)==_positive_region_size(df,attrs,"decision")
    exact=exact_cached(df,features,"decision")
    greedy=greedy_pos(df,features,"decision")
    assert exact.selected==("a","b")
    assert greedy.positive_region==exact.full_positive_region
    df.loc[3,"a"]=None
    cache=PartitionCache(df,features,"decision")
    for k in range(4):
        for ids in itertools.combinations(range(3),k):
            assert cache.pos(ids)==_positive_region_size(df,[features[i] for i in ids],"decision")

def test_feature_cap_fails_closed():
    df=fixture(3,40,13)
    with pytest.raises(ValueError,match="CAP"):
        exact_cached(df,[f"f{i}" for i in range(13)],"decision",max_features=12)
