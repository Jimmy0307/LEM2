"""Resumable 188-source x seeds 1..42 extension of the frozen full-scale lane.

Uses existing full-row adapters and run_model without modifying induction,
partition, discretization, prediction, or train/validation/test semantics.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import time

import pandas as pd
from experiments.full_scale_20261118.registry import source_registry
from experiments.full_scale_20261118.runner import invoke_with_deadline
from experiments.full_scale_20261118.model import SCENARIOS, run_model
from fedrs.predict import POLICIES

SEEDS = tuple(range(1, 43))
VARIANTS = ('A_ALL_RULES', 'B2_TRUE_AS_FALLBACK')

def atomic_json(path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, default=str, indent=2))
    tmp.replace(path)

def selected_registry():
    full = source_registry()
    chosen = full[full.status == 'PENDING'].copy()
    assert len(chosen) == 188 and not chosen.dataset.duplicated().any()
    return full, chosen

def read_source(item, cache):
    from experiments.full_scale_20261118.sources import load_openml, load_pmlb, load_uci
    if item['cohort'] == 'PMLB':
        return load_pmlb(item['name'])
    if item['cohort'] == 'OML51':
        return load_openml(int(item['did']), cache)
    return load_uci(item['name'])

def validate_record(record, dataset, seed, scenario):
    rows = record['rows']
    expected = {(v, p) for v in VARIANTS for p in POLICIES}
    actual = [(r['rule_variant'], r['selection_policy']) for r in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError('Missing or duplicated policy/variant rows')
    for row in rows:
        if row['dataset'] != dataset or row['seed'] != seed:
            raise ValueError('Checkpoint dataset/seed mismatch')
        system = 'CENTRALIZED' if scenario == 'CENTRALIZED' else 'FEDERATED'
        if row['system'] != system or row['client_count'] != (0 if system == 'CENTRALIZED' else 3):
            raise ValueError('Checkpoint architecture mismatch')
        alpha = {'CENTRALIZED':None, 'FED_IID':None, 'FED_A05':.5, 'FED_A01':.1}[scenario]
        actual_alpha = row['dirichlet_alpha']
        if (alpha is None and actual_alpha is not None) or (alpha is not None and actual_alpha != alpha):
            raise ValueError('Checkpoint partition mismatch')
    timing = record['timing']
    if (timing['dataset'],timing['seed'],timing['scenario']) != (dataset,seed,scenario):
        raise ValueError('Checkpoint timing mismatch')

def run_dataset(item, output, seeds, timeout):
    dataset = item['dataset']
    dest = Path(output) / 'checkpoints' / dataset.replace(':', '__')
    dest.mkdir(parents=True, exist_ok=True)
    source_path = dest / 'source.pkl'
    metadata_path = dest / 'SOURCE.json'
    if not source_path.exists():
        result = invoke_with_deadline(read_source, (item, str(dest/'openml')), 300)
        if result['status'] != 'OK':
            atomic_json(dest/'SOURCE_FAILURE.json', result)
            print('SOURCE_FAILURE',dataset,result['status'],flush=True)
            return dataset,result['status']
        source = result['value']
        # Source bytes are cached only locally; output delivery excludes raw data.
        meta = {f.name:getattr(source,f.name) for f in fields(source) if f.name != 'frame'}
        meta.update(dataset=dataset,used_rows=len(source.frame),cohort=item['cohort'])
        atomic_json(metadata_path, meta)
        temp = source_path.with_suffix('.tmp')
        with temp.open('wb') as f:
            pickle.dump(source,f)
        temp.replace(source_path)
        (dest/'SOURCE_FAILURE.json').unlink(missing_ok=True)
    else:
        with source_path.open('rb') as f:
            source = pickle.load(f)
        meta = json.loads(metadata_path.read_text())
        actual = hashlib.sha256(source.frame.to_csv(index=False).encode()).hexdigest()
        if actual != meta['prepared_sha256']:
            raise ValueError('Cached source SHA mismatch: '+dataset)
    for seed in seeds:
        for scenario in SCENARIOS:
            path = dest / f'seed{seed:02d}__{scenario}.json'
            failed = path.with_suffix('.failure.json')
            if path.exists():
                validate_record(json.loads(path.read_text()),dataset,seed,scenario)
                continue
            if failed.exists():
                continue  # Explicit retry removes only chosen failure records.
            result = invoke_with_deadline(run_model, (source,dataset,seed,scenario), timeout)
            if result['status'] == 'OK':
                validate_record(result['value'],dataset,seed,scenario)
                result['value']['source_prepared_sha256'] = meta['prepared_sha256']
                atomic_json(path,result['value'])
            else:
                atomic_json(failed,{'dataset':dataset,'seed':seed,'scenario':scenario,**result})
            print('MODEL',dataset,seed,scenario,result['status'],flush=True)
            if result['status'] == 'ConflictBoundViolation':
                raise RuntimeError('Conflict bound violated: '+dataset)
    return dataset,'ATTEMPTED'

def audit(output):
    output=Path(output)
    _, registry=selected_registry()
    summaries=[];rows=[];failures=[];missing=[];timings=[]
    for item in registry.to_dict('records'):
        dataset=item['dataset']
        dest=output/'checkpoints'/dataset.replace(':','__')
        complete=0
        for seed in SEEDS:
            for scenario in SCENARIOS:
                path=dest/f'seed{seed:02d}__{scenario}.json'
                failed=path.with_suffix('.failure.json')
                if path.exists():
                    record=json.loads(path.read_text())
                    validate_record(record,dataset,seed,scenario)
                    rows.extend({**r,'scenario':scenario,'source_prepared_sha256':record['source_prepared_sha256']} for r in record['rows'])
                    timings.append(record['timing'])
                    complete+=1
                else:
                    key=dict(dataset=dataset,seed=seed,scenario=scenario)
                    if failed.exists():
                        f=json.loads(failed.read_text())
                        failures.append(f)
                        key['status']=f['status']
                    elif (dest/'SOURCE_FAILURE.json').exists():
                        f=json.loads((dest/'SOURCE_FAILURE.json').read_text())
                        key['status']='SOURCE_'+f['status']
                    else:
                        key['status']='NOT_RUN'
                    missing.append(key)
        summaries.append(dict(dataset=dataset,cohort=item['cohort'],expected_models=168,
                              complete_models=complete,missing_models=168-complete,
                              status='COMPLETE' if complete==168 else 'INCOMPLETE'))
    pd.DataFrame(summaries).to_csv(output/'COMPLETENESS.csv',index=False)
    pd.DataFrame(missing,columns=['dataset','seed','scenario','status']).to_csv(output/'MISSING.csv',index=False)
    pd.DataFrame(failures).to_csv(output/'FAILURES.csv',index=False)
    pd.DataFrame(timings).to_csv(output/'TIMINGS.csv',index=False)
    if rows:
        df=pd.DataFrame(rows)
        key=['dataset','seed','scenario','rule_variant','selection_policy']
        assert not df.duplicated(key).any()
        df.to_csv(output/'RESULTS.csv',index=False)
        central=df[df.scenario=='CENTRALIZED']
        fed=df[df.scenario!='CENTRALIZED']
        pairkey=['dataset','seed','rule_variant','selection_policy','source_prepared_sha256']
        paired=fed.merge(central,on=pairkey,suffixes=('_fed','_central'),validate='many_to_one')
        for metric in ['accuracy_pct','balanced_accuracy_pct','test_coverage_pct','candidate_coverage_pct','conflict_rate_pct','rule_count']:
            paired[metric+'_delta_fed_minus_central']=paired[metric+'_fed']-paired[metric+'_central']
        paired.to_csv(output/'PAIRED_COMPARISONS.csv',index=False)
        metrics=['accuracy_pct_delta_fed_minus_central','balanced_accuracy_pct_delta_fed_minus_central',
                 'test_coverage_pct_delta_fed_minus_central','conflict_rate_pct_delta_fed_minus_central']
        if not paired.empty:
            summary=paired.groupby(['dataset','scenario_fed','rule_variant','selection_policy'])[metrics].agg(['count','mean','std','min','max'])
            summary.to_csv(output/'PAIRED_SUMMARY.csv')
    state=dict(datasets=188,complete_datasets=sum(s['status']=='COMPLETE' for s in summaries),
               expected_models=188*168,complete_models=sum(s['complete_models'] for s in summaries),
               expected_rows=188*168*12,complete_rows=len(rows),missing_models=len(missing),
               status='COMPLETE' if not missing else 'INCOMPLETE')
    atomic_json(output/'STATUS.json',state)
    print(json.dumps(state),flush=True)
    return state

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='outputs/expanded_188_42seeds')
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--timeout',type=float,default=2700)
    p.add_argument('--seeds',default=','.join(map(str,SEEDS)))
    p.add_argument('--dataset')
    p.add_argument('--audit',action='store_true')
    a=p.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if a.audit:
        audit(out);return
    seeds=[int(x) for x in a.seeds.split(',')]
    if not seeds or len(set(seeds))!=len(seeds) or not set(seeds)<=set(SEEDS):
        raise ValueError('Seeds must be unique integers 1..42')
    full,chosen=selected_registry()
    contract={'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'registry_sha256':hashlib.sha256(full.to_csv(index=False).encode()).hexdigest(),
              'seeds':list(SEEDS),'scenarios':list(SCENARIOS),'policies':list(POLICIES),
              'variants':list(VARIANTS),'split':'NESTED_64_16_20','n_clients':3,
              'timeout_seconds':a.timeout,'full_rows':True,'source_feature_contract':'existing full_scale_20261118 adapters'}
    manifest=out/'RUN_MANIFEST.json'
    if manifest.exists() and json.loads(manifest.read_text())!=contract:
        raise ValueError('Run contract changed; use a separate output directory')
    atomic_json(manifest,contract)
    full.to_csv(out/'SOURCE_REGISTRY.csv',index=False)
    if a.dataset:
        chosen=chosen[chosen.dataset==a.dataset]
        if len(chosen)!=1:raise ValueError('Unknown eligible dataset')
    items=chosen.sort_values(['original_rows','dataset']).to_dict('records')
    # Isolate the ten largest sources, preserving the upstream resource contract.
    small=[v for v in items if v['original_rows']<=500000]
    large=[v for v in items if v['original_rows']>500000]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        pending={pool.submit(run_dataset,item,str(out),seeds,a.timeout):item for item in small}
        for future in as_completed(pending):
            print('DATASET',future.result(),flush=True)
            audit(out)
    for item in large:
        print('DATASET',run_dataset(item,str(out),seeds,a.timeout),flush=True)
        audit(out)
    audit(out)

if __name__=='__main__':main()
