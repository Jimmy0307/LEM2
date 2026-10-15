from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import pytest

from roughset.adapters import prepare_custom_frame, load_local_file
from roughset.schema import resolve_schema
from roughset.preprocessing import detect_feature_types, fit_shared_preprocessor, apply_preprocessor
from roughset.splitting import stratified_train_test_split, stratified_kfold_splits
from roughset.sources import discover_local_files, parse_uci_sources


def test_custom_frame_missing_values_fail_fast():
    df = pd.DataFrame({'x':[1,None], 'class':['A','B']})
    with pytest.raises(ValueError):
        prepare_custom_frame(df, target='class')


def test_schema_explicit_roles_take_priority(tmp_path: Path):
    df = pd.DataFrame({'age':[20,40,60], 'dept':['IT','HR','IT'], 'level':['J','M','S'], 'class':['A','B','A']})
    schema = {'target':'class','continuous':['age'],'categorical':['dept'],'ordinal':{'level':['J','M','S']},'ignore':[]}
    path = tmp_path/'d.schema.json'; path.write_text(json.dumps(schema), encoding='utf-8')
    r = resolve_schema(df, schema_path=path)
    assert r.target == 'class'
    assert r.continuous == ['age']
    assert r.categorical == ['dept']
    assert r.ordinal == {'level':['J','M','S']}
    assert set(r.features) == {'age','dept','level'}


def test_target_is_not_guessed_from_last_column(tmp_path: Path):
    df = pd.DataFrame({'x':[1,2], 'y':[3,4], 'outcome':['A','B']})
    with pytest.raises(ValueError, match='target'):
        resolve_schema(df)


def test_train_only_preprocessor_does_not_refit_on_test():
    train = pd.DataFrame({'x':[0.0,1.0,2.0,3.0], 'class':['A','A','B','B']})
    test = pd.DataFrame({'x':[1000.0], 'class':['B']})
    prep = fit_shared_preprocessor({'Train':train}, ['x'], 'class', ['x'], [], 3)
    before = prep['bin_edges']['x'].copy()
    _ = apply_preprocessor(test, prep, 'class')
    assert (prep['bin_edges']['x'] == before).all()
    assert before[-1] == 3.0


def test_local_discovery_is_batch_and_sorted(tmp_path: Path):
    (tmp_path/'b.csv').write_text('x,class\n1,A\n2,B\n', encoding='utf-8')
    (tmp_path/'a.csv').write_text('x,class\n1,A\n2,B\n', encoding='utf-8')
    (tmp_path/'ignore.txt').write_text('x', encoding='utf-8')
    assert [p.name for p in discover_local_files(tmp_path)] == ['a.csv','b.csv']


def test_parse_uci_sources_supports_id_and_doi(tmp_path: Path):
    p=tmp_path/'uci_sources.txt'
    p.write_text('# comment\nuci_id:44\ndoi:10.24432/C5501T\n\n', encoding='utf-8')
    items=parse_uci_sources(p)
    assert items[0].kind == 'uci_id' and items[0].value == '44'
    assert items[1].kind == 'doi' and items[1].value == '10.24432/C5501T'


def test_splits_match_reference(ref):
    df=pd.DataFrame({'x':range(12),'class':['A']*6+['B']*6})
    g1=stratified_train_test_split(df,'class',0.25,42)
    g2=ref.stratified_train_test_split(df,'class',0.25,42)
    assert g1[0].index.tolist()==g2[0].index.tolist()
    assert g1[1].index.tolist()==g2[1].index.tolist()
    f1=stratified_kfold_splits(df,'class',3,42)
    f2=ref.stratified_kfold_splits(df,'class',3,42)
    assert [(a.index.tolist(),b.index.tolist()) for a,b in f1] == [(a.index.tolist(),b.index.tolist()) for a,b in f2]


def test_parse_uci_sources_accepts_plain_id_and_plain_doi(tmp_path: Path):
    p=tmp_path/'uci_sources.txt'
    p.write_text('44\n10.24432/C5501T\n',encoding='utf-8')
    items=parse_uci_sources(p)
    assert [(x.kind,x.value) for x in items] == [('uci_id','44'),('doi','10.24432/C5501T')]


def test_known_uci_id_preserves_v61_categorical_profile_and_drops_hayes_name():
    from types import SimpleNamespace
    from roughset.adapters import load_uci_dataset_by_id
    X = pd.DataFrame({
        'name':[1,2,3],
        'hobby':[1,2,3],
        'age':[1,2,3],
        'educational level':[1,2,3],
        'marital status':[1,2,3],
    })
    y = pd.DataFrame({'class':['1','2',None]})
    fake = SimpleNamespace(data=SimpleNamespace(features=X, targets=y), metadata=SimpleNamespace(name='Hayes-Roth'))
    bundle = load_uci_dataset_by_id(44, fetcher=lambda id: fake)
    assert 'name' not in bundle.features
    assert len(bundle.frame) == 2
    assert set(bundle.schema.categorical) == set(bundle.features)
    assert bundle.schema.continuous == []


def test_schema_can_leave_feature_roles_for_auto_detection(tmp_path: Path):
    df=pd.DataFrame({'x':range(20),'class':['A']*10+['B']*10})
    p=tmp_path/'d.schema.json'; p.write_text(json.dumps({'target':'class'}),encoding='utf-8')
    r=resolve_schema(df,schema_path=p)
    assert r.features == ['x']
    assert r.continuous == []
    assert r.categorical == []


def test_known_uci_doi_resolves_without_network(tmp_path: Path):
    from roughset.sources import resolve_uci_doi
    cache=tmp_path/'cache.json'
    assert resolve_uci_doi('10.24432/C5501T', cache_file=cache) == 44
    assert cache.exists()


def test_parse_uci_sources_accepts_doi_url(tmp_path: Path):
    p=tmp_path/'uci_sources.txt'
    p.write_text('https://doi.org/10.24432/C5501T\n',encoding='utf-8')
    items=parse_uci_sources(p)
    assert [(x.kind,x.value) for x in items] == [('doi','10.24432/C5501T')]


def test_known_uci_doi_resolution_is_case_insensitive(tmp_path: Path):
    from roughset.sources import resolve_uci_doi
    assert resolve_uci_doi('10.24432/c5501t', cache_file=tmp_path/'c.json') == 44
