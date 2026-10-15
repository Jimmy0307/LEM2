from __future__ import annotations
import pandas as pd
from roughset.reduct import dependency_degree, find_minimum_cardinality_reducts, find_minimal_reducts


def test_dependency_and_reduct_match_hand_calculation(ref):
    df = pd.DataFrame({'A':[0,0,1,1], 'B':[0,1,0,1], 'D':['N','N','Y','Y']})
    assert dependency_degree(df, ['A','B'], 'D') == 1.0
    assert dependency_degree(df, ['A'], 'D') == 1.0
    assert dependency_degree(df, ['B'], 'D') == 0.0
    assert find_minimum_cardinality_reducts(df, ['A','B'], 'D') == [('A',)]
    assert find_minimal_reducts(df, ['A','B'], 'D') == [('A',)]
    assert find_minimal_reducts(df, ['A','B'], 'D') == ref.find_minimal_reducts(df, ['A','B'], 'D')
