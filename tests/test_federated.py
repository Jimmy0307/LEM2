from __future__ import annotations
import math
import pandas as pd
from roughset.core import Rule
from roughset.federated import (
    stratified_client_partition, dirichlet_label_skew_partition, partition_clients,
    union_rules_with_provenance, union_rules, audit_order_sensitivity,
    audit_order_distribution,
)


def _members(clients):
    return {k: tuple(v.astype(str).agg('|'.join, axis=1).tolist()) for k,v in clients.items()}


def test_stratified_partition_matches_reference(ref):
    df=pd.DataFrame({'x':range(12),'class':['A']*6+['B']*6})
    got=stratified_client_partition(df,'class',3,42)
    exp=ref.stratified_client_partition(df,'class',3,42)
    assert _members(got)==_members(exp)


def test_dirichlet_partition_conserves_rows_and_is_reproducible():
    df=pd.DataFrame({'row_id':range(60),'class':['A']*30+['B']*30}).set_index('row_id',drop=False)
    a=dirichlet_label_skew_partition(df,'class',4,0.5,42,100)
    b=dirichlet_label_skew_partition(df,'class',4,0.5,42,100)
    ids_a=[int(x) for part in a.values() for x in part['row_id'].tolist()]
    ids_b=[int(x) for part in b.values() for x in part['row_id'].tolist()]
    assert sorted(ids_a)==list(range(60))
    assert len(ids_a)==len(set(ids_a))
    assert _members(a)==_members(b)


def test_union_preserves_all_sources_and_first_occurrence_order():
    r1=Rule((('A','1'),),'Y','c1')
    r1_dup=Rule((('A','1'),),'Y','c2')
    r2=Rule((('B','2'),),'N','c2')
    merged,sources=union_rules_with_provenance({'c1':[r1],'c2':[r1_dup,r2]})
    assert [r.key for r in merged]==[r1.key,r2.key]
    assert sources[r1.key]==('c1','c2')
    assert sources[r2.key]==('c2',)


def test_order_sensitivity_detects_first_match_instability():
    test=pd.DataFrame({'A':['1'],'D':['Y']})
    local={'c1':[Rule((('A','1'),),'Y','c1')], 'c2':[Rule((('A','1'),),'N','c2')]}
    out=audit_order_sensitivity(test,local,'Y','FIRST_MATCH',max_permutations=120,seed=42)
    assert out['orderings_checked']==2
    assert out['order_sensitivity_rate']==1.0


def test_order_distribution_two_orders_has_expected_range():
    test=pd.DataFrame({'A':['1','1'],'D':['Y','N']})
    local={'c1':[Rule((('A','1'),),'Y','c1')], 'c2':[Rule((('A','1'),),'N','c2')]}
    out=audit_order_distribution(test,local,'Y','D','FIRST_MATCH',max_permutations=120,seed=42)
    assert out['orderings_checked']==2
    assert out['total_possible_orderings']==2
    assert out['order_sampling_complete'] is True
    assert math.isclose(out['order_accuracy_mean'],0.5)
