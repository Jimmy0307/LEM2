"""Interface, data leakage, local Spark-task API and resumable receipt tests.

These are deliberately small: no 188×42 rerun, no network, no Spark installation.
"""
from __future__ import annotations
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from federated_decision_making.api import Capabilities, FitRequest, Predictions, validate_request
from federated_decision_making.registry import load_algorithm
from federated_decision_making.runner import Case, _split, run_case, write_checkpoint
from federated_decision_making.spark_job import process


def sample(n=80):
    # No source IDs passed as features. Real schema has explicit target.
    return pd.DataFrame({
        'feat_a':[str(i%4) for i in range(n)],
        'feat_b':['A' if i%3 else 'B' for i in range(n)],
        'label':['cat' if i%2 else 'dog' for i in range(n)],
    })


def make_case(path, **changes):
    kwargs={'dataset_id':'unit_toy','csv':str(path),'target':'label',
            'features':('feat_a','feat_b'),'algorithm':'majority',
            'scenario':'CENTRALIZED','seed':5,'split':'64_16_20'}
    kwargs.update(changes)
    return Case(**kwargs)


@pytest.mark.parametrize('split', ['80_20','60_20_20','64_16_20'])
def test_split_holdout_invariant_and_disjoint(split):
    df=sample();train,val,test=_split(df,'label',7,split)
    a,b,c=[set(x.__row_id__) for x in (train,val,test)]
    assert not (a & b or a & c or b & c)
    assert a | b | c == set(range(len(df)))
    _,_,ref=_split(df,'label',7,'80_20')
    assert c==set(ref.__row_id__)


def test_registered_plugin_capabilities_and_unimplemented_errors():
    assert load_algorithm('majority').capabilities.algorithm=='majority'
    assert load_algorithm('lem2').capabilities.supports_rules
    for unknown in ['prism','ripper','drsa']:
        with pytest.raises(NotImplementedError):load_algorithm(unknown)
    with pytest.raises(ValueError, match='cannot override built-in'):
        load_algorithm('lem2',{'lem2':'fake:Class'})


def test_contract_disallows_federated_fallback_or_undocumented_missing():
    df=sample()
    req=FitRequest(train=df,clients={'c':df},features=('feat_a',),target='label',mode='FED_IID',seed=1)
    with pytest.raises(ValueError,match='does not support'):
        validate_request(Capabilities('custom'),req)
    missing=df.copy();missing.loc[0,'feat_a']=None
    with pytest.raises(ValueError,match='missing values'):
        validate_request(Capabilities('custom'),replace(req,train=missing,clients={'c':missing},mode='CENTRALIZED'))


def test_feature_budget_not_hardcoded_to_six(tmp_path):
    df=sample()
    for i in range(7):df[f'extra_{i}']=str(i)
    f=tmp_path/'multi.csv';df.to_csv(f,index=False)
    fields=tuple(col for col in df.columns if col!='label')
    rec=run_case(make_case(f,features=fields))
    assert rec['feature_count']==9
    assert rec['algorithm']=='majority'
    assert rec['metrics']['coverage'] is None, 'non-rule baseline cannot report fake 0 coverage'


def test_external_plugin_api_and_majority_control(tmp_path):
    f=tmp_path/'test.csv';sample().to_csv(f,index=False)
    rec=run_case(make_case(f,scenario='FED_IID'))
    assert rec['n_clients']==3
    assert rec['n_train']+rec['n_validation']+rec['n_test']==rec['n_source']
    assert rec['metrics']['accuracy']==rec['majority_only']['accuracy']
    assert rec['metrics']['candidate_coverage'] is None
    assert rec['software_sha']
    out=tmp_path/'checkpoints'
    path,created=write_checkpoint(rec,out)
    assert created
    p2,created2=write_checkpoint(rec,out)
    assert p2==path and not created2
    assert len(list(out.glob('*.json')))==1
    with pytest.raises(RuntimeError,match='conflict'):
        write_checkpoint({**rec,'source_sha256':'different'},out)


def test_cli_lem2_adapter_centralized_and_federated(tmp_path):
    pytest.importorskip('fedrs')
    pytest.importorskip('roughset')
    df=sample(80);f=tmp_path/'toy.csv';df.to_csv(f,index=False)
    for scenario in ['CENTRALIZED','FED_IID']:
        c=make_case(f,algorithm='lem2',scenario=scenario,
            options={'selection_policy':'STANDARD_VOTING','rule_variant':'B2_TRUE_AS_FALLBACK'})
        rec=run_case(c)
        assert rec['status']=='SUCCESS'
        assert rec['capabilities']['supports_rules']
        assert rec['model_diagnostics']['n_rules']>=0
        assert rec['metrics']['coverage'] is not None
        assert rec['metrics']['candidate_coverage'] is not None
        assert rec['n_test']>0


def test_spark_task_function_without_spark_runtime(tmp_path):
    f=tmp_path/'toy.csv';sample().to_csv(f,index=False)
    job=make_case(f).__dict__
    result=process(job)
    assert result['status']=='SUCCESS',result
    failure=process({**job,'algorithm':'prism'})
    assert failure['status']=='FAILED'
    assert failure['error_type']=='NotImplementedError'
    assert 'not installed' in failure['error']


def test_ordinal_metadata_requires_decision_order(tmp_path):
    df=sample(); f=tmp_path/'input.csv';df.to_csv(f,index=False)
    plugin=load_algorithm('majority')
    request=FitRequest(train=df,clients={'central':df},features=('feat_a','feat_b'),
                       target='label',mode='CENTRALIZED',seed=1)
    with pytest.raises(ValueError,match='ordered-criterion'):
        validate_request(Capabilities(algorithm='drsa',ordered_decision_required=True),request)


def test_neutral_data_partition_parity_to_frozen_code():
    pytest.importorskip('roughset')
    from federated_decision_making.datasets import (stratified_train_test_split as neutral_split,
        stratified_client_partition as neutral_stratified,
        dirichlet_label_skew_partition as neutral_dirichlet)
    from roughset.splitting import stratified_train_test_split as frozen_split
    from roughset.federated import (stratified_client_partition as frozen_stratified,
                                    dirichlet_label_skew_partition as frozen_dirichlet)
    source=sample(120)
    for seed in (1, 5, 42):
        x,y=neutral_split(source,'label',.2,seed)
        xx,yy=frozen_split(source,'label',.2,seed)
        pd.testing.assert_frame_equal(x,xx)
        pd.testing.assert_frame_equal(y,yy)
        for alpha in (.1,.5):
            n=neutral_dirichlet(x,'label',3,alpha,seed)
            f=frozen_dirichlet(x,'label',3,alpha,seed)
            for key in n:pd.testing.assert_frame_equal(n[key],f[key])
        n=neutral_stratified(x,'label',3,seed)
        f=frozen_stratified(x,'label',3,seed)
        for key in n:pd.testing.assert_frame_equal(n[key],f[key])


def test_neutral_metrics_parity_to_frozen_metrics():
    pytest.importorskip('fedrs')
    from federated_decision_making.evaluation import scores as platform_scores
    from fedrs.metrics import scores as baseline_scores
    truth=['A','A','B','B','C','C','C']
    for prediction in (truth, ['C']*len(truth), ['A','B','A','B','C','C','B']):
        assert platform_scores(truth,prediction)==baseline_scores(truth,prediction)


def test_batch_resume_and_explicit_matched_baseline(tmp_path):
    from federated_decision_making.batch import execute_batch, paired_comparison
    f=tmp_path/'data.csv';sample(120).to_csv(f,index=False)
    from federated_decision_making.runner import Case
    base=make_case(f,algorithm='majority',scenario='CENTRALIZED',split='80_20')
    # Same algorithm results cannot fabricate a delta against a distinct model.
    first=execute_batch([base],tmp_path/'results')
    assert first['successful']==1
    again=execute_batch([base],tmp_path/'results')
    assert again['skipped_verified']==1
    with pytest.raises(ValueError,match='no matched non-baseline'):
        paired_comparison(tmp_path/'results','majority')
    # Expected: different source/seeds are not paired.
    other=make_case(f,scenario='FED_IID')
    result=execute_batch([other],tmp_path/'results')
    assert result['successful']==1
    assert first['failed']==0
