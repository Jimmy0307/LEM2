"""Algorithm-agnostic research executor with auditable, resumable receipts.

Works identically for local CLI and Spark tasks. It never writes original 188x42
checkpoints. Outputs small JSON receipts; original CSV is not copied to outputs.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid
from typing import Any, Mapping

import numpy as np
import pandas as pd
from .datasets import stratified_train_test_split, partition
from .evaluation import scores
from .api import FitRequest, Predictions, validate_request
from .registry import load_algorithm

SPLITS = {'80_20': 0.0, '64_16_20': 0.20, '60_20_20': 0.25}
SCENARIOS = {
    'CENTRALIZED': None, 'FED_IID': 'IID',
    'FED_A05': 'NONIID_05', 'FED_A01': 'NONIID_01',
}

@dataclass(frozen=True)
class Case:
    dataset_id: str
    csv: str
    target: str
    features: tuple[str, ...]
    algorithm: str = 'lem2'
    scenario: str = 'CENTRALIZED'
    seed: int = 1
    split: str = '64_16_20'
    options: Mapping[str, object] = field(default_factory=dict)
    ordinal_directions: Mapping[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, x: Mapping[str, Any]):
        allowed = set(cls.__dataclass_fields__)
        unknown = set(x) - allowed
        if unknown:
            raise ValueError(f'unknown Case fields: {sorted(unknown)}')
        return cls(**{**x,'features':tuple(x['features'])})


def _software_sha() -> str:
    """Hash installed package code identically on disk or in Spark ZIP archives."""
    from importlib.metadata import PackageNotFoundError, version
    from importlib.resources import files
    root=files('federated_decision_making')
    h=hashlib.sha256()
    try: h.update(version('federated-decision-making').encode())
    except PackageNotFoundError: h.update(b'uninstalled-source')
    def walk(node, prefix=''):
        for child in sorted(node.iterdir(), key=lambda x:x.name):
            relative=f'{prefix}/{child.name}' if prefix else child.name
            if child.is_dir():
                yield from walk(child,relative)
            elif child.name.endswith('.py'):
                yield relative, child.read_bytes()
    for name,data in walk(root):
        h.update(name.encode());h.update(data)
    return h.hexdigest()


def _split(df: pd.DataFrame, target: str, seed: int, split: str):
    if split not in SPLITS:
        raise ValueError(f'unsupported split {split}')
    raw = df.copy().reset_index(drop=True)
    # Stable, unique positions; never fed to algorithms as a condition attribute.
    raw['__row_id__'] = np.arange(len(raw),dtype=int)
    outer, test = stratified_train_test_split(raw,target,test_ratio=.20,seed=seed)
    fraction = SPLITS[split]
    if fraction:
        train, val = stratified_train_test_split(outer,target,test_ratio=fraction,seed=1000+seed)
    else:
        train, val = outer, outer.iloc[:0].copy()
    a,b,c = [set(x['__row_id__']) for x in (train,val,test)]
    if a & b or a & c or b & c or len(a|b|c)!=len(raw):
        raise AssertionError('train/val/test leakage detected')
    return train,val,test


def _metrics(y: np.ndarray, pred: Predictions):
    pred.validate(len(y))
    metric = scores(y, [str(x) for x in pred.labels])
    out = {'accuracy':float(metric['accuracy']), 'balanced_accuracy':float(metric['ba']),
           'macro_f1':float(metric['macro_f1'])}
    out['coverage'] = (float(np.mean(pred.covered)) if pred.covered is not None else None)
    if pred.candidates is not None:
        present = [str(yy) in tuple(map(str, choices)) for yy, choices in zip(y,pred.candidates)]
        out['candidate_coverage'] = float(np.mean(present))
        out['conflict'] = float(np.mean([len(set(c))>=2 for c in pred.candidates]))
        collisions = [i for i,c in enumerate(pred.candidates) if len(set(c))>=2]
        out['conflict_only_accuracy'] = (float(np.mean([str(pred.labels[i])==str(y[i]) for i in collisions]))
                                         if collisions else None)
    else:
        out.update(candidate_coverage=None,conflict=None,conflict_only_accuracy=None)
    return out


def _fingerprint(case: Case, source_sha: str, software_sha: str, algorithm_sha: str):
    versioned = {'api':'research-platform.v1', 'case':asdict(case), 'source_sha256':source_sha,
                 'software_sha':software_sha, 'algorithm_sha':algorithm_sha}
    return hashlib.sha256(json.dumps(versioned,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]


def case_identity(case: Case, external_plugins: dict[str, str] | None = None) -> tuple[str, str, str]:
    from .registry import plugin_code_fingerprint
    raw = Path(case.csv).read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    core_sha = _software_sha()
    algorithm_sha = plugin_code_fingerprint(case.algorithm, external_plugins)
    combined_sha = hashlib.sha256((core_sha + algorithm_sha).encode()).hexdigest()
    return _fingerprint(case, source_sha, combined_sha, algorithm_sha), source_sha, combined_sha


def run_case(case: Case, external_plugins: dict[str,str] | None = None) -> dict:
    """Pure execution (no checkpoint writes): suitable as Spark RDD task.

    The 20% Test labels are accessed only AFTER fit; no method-selection loop
    or feature choice uses Test. Strategy selection belongs in independent arms.
    """
    if not case.dataset_id or '/' in case.dataset_id or '\\' in case.dataset_id:
        raise ValueError('dataset_id must be a nonempty safe name')
    if case.scenario not in SCENARIOS or case.split not in SPLITS:
        raise ValueError('unknown scenario or split')
    if len(case.features)==0 or len(set(case.features))!=len(case.features):
        raise ValueError('select distinct features explicitly; no silent six-feature cap')
    source=Path(case.csv)
    run_id,source_sha,software_sha=case_identity(case,external_plugins)
    df=pd.read_csv(source)
    required = set(case.features) | {case.target}
    if not required.issubset(df.columns):
        raise ValueError(f'missing required source fields: {sorted(required-set(df.columns))}')
    if case.target in case.features:
        raise ValueError('target leakage: target cannot be a feature')
    if df[case.target].isna().any():
        raise ValueError('missing decision labels require an explicit reviewed target policy')
    # Feature missingness is delegated to a declared plugin capability.
    # Built-ins reject via validate_request; no imputation or leakage.
    # All algorithms use the same held-out source and selected conditions.
    selected=df[list(case.features)+[case.target]].copy()
    train,val,test=_split(selected,case.target,case.seed,case.split)
    # Exclude internal row ID from algorithm input; still use IDs for checks.
    columns=list(case.features)+[case.target]
    train,val,test=[x[columns].copy() for x in (train,val,test)]
    clients=partition(train,case.target,case.scenario,case.seed,client_count=3)
    plugin=load_algorithm(case.algorithm, external_plugins)
    request=FitRequest(train=train,clients=clients,features=tuple(case.features),target=case.target,
                       mode=case.scenario,seed=case.seed,options=case.options,
                       ordinal_directions=case.ordinal_directions)
    validate_request(plugin.capabilities,request)
    start=time.perf_counter()
    model=plugin.fit(request)
    fit_s=time.perf_counter()-start
    start=time.perf_counter()
    output=model.predict(test[list(case.features)])  # inference features only
    predict_s=time.perf_counter()-start
    truth=test[case.target].astype(str).to_numpy()
    metric=_metrics(truth,output)
    counts=train[case.target].astype(str).value_counts()
    baseline=sorted(str(k) for k,v in counts.items() if int(v)==int(counts.max()))[0]
    majority=_metrics(truth,Predictions(labels=[baseline]*len(test)))
    receipt = {
        'status':'SUCCESS', 'run_id':run_id,'api_version':'1.0','dataset_id':case.dataset_id,
        'source_sha256':source_sha,'software_sha':software_sha,
        'algorithm':case.algorithm,'capabilities':asdict(plugin.capabilities),
        'scenario':case.scenario,'seed':case.seed,'split':case.split,
        'selected_features':list(case.features),'feature_count':len(case.features),
        'target':case.target,'n_source':len(selected),'n_train':len(train),
        'n_validation':len(val),'n_test':len(test),
        'n_clients':len(clients), 'client_sizes':{k:len(v) for k,v in clients.items()},
        'options':dict(case.options), 'metrics':metric,
        'majority_only':majority,'model_diagnostics':model.diagnostics(),
        'fit_seconds':fit_s,'predict_seconds':predict_s,
        'host':socket.gethostname(),
        'research_contract':'outer_80_20_test_unchanged;algorithm_plugin_fits_training_only',
    }
    return receipt


def write_checkpoint(record: dict, output: Path, overwrite: bool = False):
    """Exclusive POSIX checkpoint creation, safe under retried jobs.

    For Spark: write on the DRIVER only after collect; executors are read-only.
    """
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    path=output / (record['run_id'] + '.json')
    data=json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2,default=str)+'\n'
    if path.exists():
        old=json.loads(path.read_text(encoding='utf-8'))
        if old.get('run_id')!=record['run_id'] or old.get('source_sha256')!=record['source_sha256']:
            raise RuntimeError(f'checkpoint identity conflict: {path}')
        # Ignore runtime/host variations, but never quietly accept changed science.
        if old.get('metrics')!=record.get('metrics') or old.get('model_diagnostics')!=record.get('model_diagnostics'):
            raise RuntimeError(f'checkpoint result conflict (different scientific outputs): {path}')
        return path,False
    tmp=output / ('.'+record['run_id']+'.'+uuid.uuid4().hex+'.tmp')
    try:
        tmp.write_text(data,encoding='utf-8')
        # Atomic no-clobber on a single POSIX filesystem. Avoid rsync collision.
        os.link(tmp,path)
        return path,True
    except FileExistsError:
        return write_checkpoint(record,output)
    finally:
        tmp.unlink(missing_ok=True)
