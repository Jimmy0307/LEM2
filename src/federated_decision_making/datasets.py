"""Algorithm-neutral data splitting & label-skew partition contracts.

The algorithms are source-compatible with roughset.splitting and
roughset.federated (2026-11-23 baseline); parity is tested explicitly.
Having a neutral copy prevents PRISM/RIPPER/DRSA APIs depending on LEM2.
"""
from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd


def stratified_train_test_split(df, target_col, test_ratio=.2, seed=42):
    if not 0 < test_ratio < 1:
        raise ValueError('test_ratio must be between 0 and 1')
    rng=np.random.default_rng(seed)
    test_ids=[]
    for _,group in df.groupby(target_col,sort=False):
        ids=group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        n_test=max(1,int(round(len(ids)*test_ratio)))
        if n_test>=len(ids):n_test=len(ids)-1
        if n_test<1:raise ValueError('Each class needs at least 2 rows for holdout')
        test_ids.extend(ids[:n_test].tolist())
    holdout=set(test_ids)
    return (df.loc[[i for i in df.index if i not in holdout]].copy(),
            df.loc[sorted(holdout)].copy())


def stratified_client_partition(train_df,target_col,n_clients=3,seed=42):
    if n_clients<1:raise ValueError('n_clients must be >=1')
    rng=np.random.default_rng(seed);buckets=[[] for _ in range(n_clients)]
    for _,group in train_df.groupby(target_col,sort=False):
        ids=group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        for i,row_id in enumerate(ids):buckets[i%n_clients].append(int(row_id))
    clients={}
    for i,ids in enumerate(buckets,1):
        if not ids:raise ValueError('Empty client')
        clients[f'Client_{i}']=train_df.loc[ids].copy().reset_index(drop=True)
    return clients


def dirichlet_label_skew_partition(train_df,target_col,n_clients=3,alpha=.5,seed=42,max_retries=100):
    if n_clients<1 or alpha<=0 or max_retries<1 or len(train_df)<n_clients:
        raise ValueError('invalid Dirichlet client partition parameters')
    rng=np.random.default_rng(seed)
    names=[f'Client_{i}' for i in range(1,n_clients+1)]
    for _ in range(max_retries):
        buckets={name:[] for name in names}
        for _,group in train_df.groupby(target_col,sort=False,dropna=False):
            ids=group.index.to_numpy(copy=True)
            rng.shuffle(ids)
            p=rng.dirichlet(np.full(n_clients,float(alpha)))
            counts=rng.multinomial(len(ids),p)
            start=0
            for name,count in zip(names,counts):
                end=start+int(count)
                if end>start:buckets[name].extend(ids[start:end].tolist())
                start=end
            if start!=len(ids):raise AssertionError('partition did not exhaust class')
        if all(buckets.values()):
            assigned=[idx for name in names for idx in buckets[name]]
            if len(assigned)!=len(train_df) or len(set(assigned))!=len(assigned) or set(assigned)!=set(train_df.index):
                raise AssertionError('client partition lost or duplicated rows')
            return {name:train_df.loc[buckets[name]].copy().reset_index(drop=True) for name in names}
    raise ValueError('Dirichlet partition failed to obtain nonempty clients after max_retries')


def partition(train,target,scenario,seed,client_count=3):
    if scenario=='CENTRALIZED':return {'central':train}
    if scenario=='FED_IID':return stratified_client_partition(train,target,client_count,seed)
    if scenario in ('FED_A05','FED_A01'):
        return dirichlet_label_skew_partition(train,target,client_count,
                                              alpha=.5 if scenario=='FED_A05' else .1,seed=seed)
    raise ValueError('unknown scenario')
