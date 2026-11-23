"""Batch case orchestration + paired result reporting, independent of algorithm.

Do not merge algorithms with different dataset/source/split/seed/scenario/feature
contracts. The only scientific comparison is matched pairs with a named baseline.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from pathlib import Path
import json
import traceback
import pandas as pd
from .runner import Case, run_case, write_checkpoint, case_identity

def load_manifest(path: Path) -> list[Case]:
    d=json.loads(path.read_text(encoding='utf8'))
    if set(d) != {'api_version','jobs'} or d['api_version'] != '1.0':
        raise ValueError('manifest must include only api_version=1.0 and jobs')
    if not isinstance(d['jobs'],list) or not d['jobs']:
        raise ValueError('jobs must be nonempty')
    return [Case.from_dict(j) for j in d['jobs']]

def execute_batch(cases: list[Case], output: Path, external_plugins=None, *, fail_fast=False):
    output.mkdir(parents=True, exist_ok=True)
    report={'total':len(cases),'successful':0,'skipped_verified':0,'failed':0,
            'runs':[],'failures':[]}
    for case in cases:
        try:
            run_id,source_sha,code_sha=case_identity(case, external_plugins)
            checkpoint=output/(run_id+'.json')
            if checkpoint.exists():
                record=json.loads(checkpoint.read_text(encoding='utf8'))
                if record.get('status')!='SUCCESS' or record.get('run_id') != run_id or record.get('source_sha256')!=source_sha or record.get('software_sha')!=code_sha:
                    raise RuntimeError('checkpoint contract mismatch')
                report['skipped_verified']+=1
                report['runs'].append({'status':'SKIPPED_VERIFIED','algorithm':case.algorithm,'run_id':run_id})
                continue
            receipt=run_case(case,external_plugins)
            path,created=write_checkpoint(receipt,output)
            report['successful' if created else 'skipped_verified']+=1
            report['runs'].append({'status':'SUCCESS' if created else 'SKIPPED_VERIFIED','algorithm':case.algorithm,
                                   'run_id':run_id,'checkpoint':path.name})
        except Exception as exc:
            failure={'status':'FAILED','dataset_id':case.dataset_id,'algorithm':case.algorithm,
                     'scenario':case.scenario,'seed':case.seed,'error_type':type(exc).__name__,
                     'message':str(exc)[:1500]}
            report['failed']+=1;report['failures'].append(failure)
            if fail_fast:break
    summary=output/'BATCH_SUMMARY.json'
    # Atomic summary replacement, not an immutable scientific checkpoint.
    tmp=summary.with_suffix('.tmp')
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8')
    tmp.replace(summary)
    return report

def paired_comparison(directory: Path, baseline: str) -> pd.DataFrame:
    """Matched pairs ONLY, with explicit baseline & absolute accuracy recorded.

    This function never picks the best model on test: comparisons must name
    a baseline algorithm, e.g. 'majority'.
    """
    records=[]
    for p in sorted(directory.glob('*.json')):
        if p.name=='BATCH_SUMMARY.json':continue
        try:d=json.loads(p.read_text(encoding='utf8'))
        except (ValueError,OSError):continue
        if d.get('status')!='SUCCESS' or 'metrics' not in d:continue
        records.append(d)
    if not records:raise ValueError('no completed model checkpoints')
    fields=['dataset_id','source_sha256','scenario','seed','split','target','selected_features','n_test']
    def join_key(r):
        return tuple(tuple(r[k]) if isinstance(r[k],list) else r[k] for k in fields)
    baselines={}
    for d in records:
        if d['algorithm']==baseline:
            k=join_key(d)
            if k in baselines:raise ValueError('ambiguous duplicate baseline for a matched key')
            baselines[k]=d
    if not baselines:raise ValueError(f'baseline algorithm {baseline!r} is not present')
    output=[]
    for d in records:
        if d['algorithm']==baseline:continue
        base=baselines.get(join_key(d))
        if base is None:continue
        output.append({
            'dataset_id':d['dataset_id'],'seed':d['seed'],'scenario':d['scenario'],
            'split':d['split'],'algorithm':d['algorithm'],'baseline_algorithm':baseline,
            'source_sha256':d['source_sha256'],'n_test':d['n_test'],
            'accuracy':d['metrics']['accuracy'],'baseline_accuracy':base['metrics']['accuracy'],
            'accuracy_difference_pp':100*(d['metrics']['accuracy']-base['metrics']['accuracy']),
            'balanced_accuracy':d['metrics']['balanced_accuracy'],
            'baseline_balanced_accuracy':base['metrics']['balanced_accuracy'],
            'balanced_accuracy_difference_pp':100*(d['metrics']['balanced_accuracy']-base['metrics']['balanced_accuracy']),
        })
    if not output:raise ValueError('no matched non-baseline algorithm checkpoints; cannot compare')
    return pd.DataFrame(output)
