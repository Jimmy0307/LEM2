from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from roughset.app import run_application


def test_local_folder_batch_run_creates_separate_outputs(tmp_path: Path):
    local=tmp_path/'real_data'/'local'; schemas=tmp_path/'real_data'/'schemas'; outputs=tmp_path/'outputs'
    local.mkdir(parents=True); schemas.mkdir(parents=True)
    for name in ['alpha','beta']:
        pd.DataFrame({
            'age':[20,22,40,42,60,62,30,32],
            'dept':['IT','IT','HR','HR','IT','IT','HR','HR'],
            'class':['A','A','B','B','A','A','B','B'],
        }).to_csv(local/f'{name}.csv',index=False)
        (schemas/f'{name}.schema.json').write_text(json.dumps({
            'target':'class','continuous':['age'],'categorical':['dept'],'ordinal':{},'ignore':[]
        }),encoding='utf-8')
    config={
        'input':{'mode':'AUTO','local_folder':str(local),'schemas_folder':str(schemas),'uci_sources_file':str(tmp_path/'real_data'/'uci_sources.txt'),'run_local_files':True,'run_uci_sources':False},
        'experiment':{'run_centralized':True,'run_federated':False,'prediction_policy':'FIRST_MATCH'},
        'evaluation':{'mode':'HOLDOUT','test_ratio':0.25,'cv_folds':2,'seed':42},
        'preprocessing':{'auto_discretize':True,'unique_numeric_threshold':10,'n_bins':3},
        'federated':{'n_clients':2,'partition':'STRATIFIED','dirichlet_alpha':0.5,'dirichlet_max_retries':100,'client_counts':[2,3],'run_client_sweep':False,'order_sensitivity_max_permutations':120},
        'report':{'outputs_folder':str(outputs),'show_rules':False,'show_rule_limit':10}
    }
    result=run_application(config)
    assert set(result['datasets'])=={'alpha','beta'}
    assert (outputs/'alpha'/'summary.json').exists()
    assert (outputs/'beta'/'summary.json').exists()


def test_no_data_is_clear_error(tmp_path: Path):
    config={
        'input':{'mode':'AUTO','local_folder':str(tmp_path/'empty'),'schemas_folder':str(tmp_path/'schemas'),'uci_sources_file':str(tmp_path/'none.txt'),'run_local_files':True,'run_uci_sources':True},
    }
    import pytest
    with pytest.raises(ValueError,match='No datasets'):
        run_application(config)


def test_dataset_output_preserves_existing_generated_files(tmp_path: Path):
    from roughset.app import _write_dataset_output
    folder=tmp_path/'outputs'/'d'; folder.mkdir(parents=True)
    stale=folder/'conflict_cases.csv'; stale.write_text('old,data\n',encoding='utf-8')
    result={
        'name':'d','source':'local:d.csv','rows':2,'features':['x'],'target':'class','evaluation_mode':'HOLDOUT',
        'preprocessor':{},'centralized':None,'federated':None,
    }
    _write_dataset_output(result,folder)
    assert stale.read_text(encoding="utf-8") == "old,data\n"


def test_dataset_manifest_records_resolved_feature_roles(tmp_path: Path):
    local=tmp_path/'real_data'/'local'; schemas=tmp_path/'real_data'/'schemas'; outputs=tmp_path/'outputs'
    local.mkdir(parents=True); schemas.mkdir(parents=True)
    pd.DataFrame({'age':[20,22,40,42,60,62,30,32],'dept':['IT','IT','HR','HR','IT','IT','HR','HR'],'class':['A','A','B','B','A','A','B','B']}).to_csv(local/'d.csv',index=False)
    (schemas/'d.schema.json').write_text(json.dumps({'target':'class','continuous':['age'],'categorical':['dept'],'ordinal':{},'ignore':[]}),encoding='utf-8')
    cfg={'input':{'local_folder':str(local),'schemas_folder':str(schemas),'uci_sources_file':str(tmp_path/'none.txt'),'run_local_files':True,'run_uci_sources':False},'experiment':{'run_centralized':True,'run_federated':False},'evaluation':{'mode':'HOLDOUT','test_ratio':0.25,'seed':42},'federated':{'run_client_sweep':False},'report':{'outputs_folder':str(outputs),'show_rules':False}}
    run_application(cfg)
    manifest=json.loads((outputs/'d'/'dataset_manifest.json').read_text(encoding='utf-8'))
    assert manifest['schema']['continuous'] == ['age']
    assert manifest['schema']['categorical'] == ['dept']

def test_run_and_dataset_manifests_record_environment(tmp_path: Path):
    local=tmp_path/'real_data'/'local'; schemas=tmp_path/'real_data'/'schemas'; outputs=tmp_path/'outputs'
    local.mkdir(parents=True); schemas.mkdir(parents=True)
    pd.DataFrame({'x':[0,0,1,1,0,1,0,1],'class':['N','N','Y','Y','N','Y','N','Y']}).to_csv(local/'env.csv',index=False)
    (schemas/'env.schema.json').write_text(json.dumps({'target':'class','continuous':[],'categorical':['x'],'ordinal':{},'ignore':[]}),encoding='utf-8')
    cfg={'input':{'local_folder':str(local),'schemas_folder':str(schemas),'uci_sources_file':str(tmp_path/'none.txt'),'run_local_files':True,'run_uci_sources':False},'experiment':{'run_centralized':True,'run_federated':False},'evaluation':{'mode':'HOLDOUT','test_ratio':0.25,'seed':42},'federated':{'run_client_sweep':False},'report':{'outputs_folder':str(outputs),'show_rules':False}}
    run_application(cfg)
    run_manifest=json.loads((outputs/'run_manifest.json').read_text(encoding='utf-8'))
    dataset_manifest=json.loads((outputs/'env'/'dataset_manifest.json').read_text(encoding='utf-8'))
    assert run_manifest['environment']['python']['version']
    assert run_manifest['environment']['packages']['numpy']['installed'] is True
    assert dataset_manifest['environment']['packages']['pandas']['installed'] is True
