from __future__ import annotations
import pandas as pd
from roughset.core import Rule, equivalence_classes, lower_approximation, induce_lem2


def _sig(rules):
    return [(tuple(sorted(r.conditions)), r.decision) for r in rules]


def test_rule_key_preserves_consequent():
    yes = Rule((('A', 1),), 'Y')
    no = Rule((('A', 1),), 'N')
    assert yes.key != no.key


def test_lower_approximation_matches_reference(ref):
    df = pd.DataFrame({'A':[0,0,1], 'B':[0,0,0], 'D':['N','Y','Y']})
    got = lower_approximation(df, ['A','B'], 'D', 'Y')
    exp = ref.lower_approximation(df, ['A','B'], 'D', 'Y')
    assert got == exp == {2}


def test_lem2_matches_reference_on_deterministic_fixture(ref):
    df = pd.DataFrame({'A':[0,0,1,1], 'B':[0,1,0,1], 'D':['N','N','Y','Y']})
    got = induce_lem2(df, ['A','B'], 'D')
    exp = ref.induce_lem2(df, ['A','B'], 'D')
    assert _sig(got) == _sig(exp)
    assert _sig(got) == [((('A', 0),), 'N'), ((('A', 1),), 'Y')]


def test_inconsistent_table_only_induces_certain_region(ref):
    df = pd.DataFrame({'A':[0,0,1], 'B':[0,0,0], 'D':['N','Y','Y']})
    got = induce_lem2(df, ['A','B'], 'D')
    exp = ref.induce_lem2(df, ['A','B'], 'D')
    assert _sig(got) == _sig(exp)
    assert _sig(got) == [((('A', 1),), 'Y')]
