from __future__ import annotations
from typing import List
import numpy as np


def stratified_train_test_split(df, target_col, test_ratio=0.20, seed=42):
    if not 0 < test_ratio < 1:
        raise ValueError("test_ratio must be between 0 and 1.")
    rng = np.random.default_rng(seed)
    test_ids: List[int] = []
    for _, group in df.groupby(target_col, sort=False):
        ids = group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        n_test = max(1, int(round(len(ids) * test_ratio)))
        if n_test >= len(ids):
            n_test = len(ids) - 1
        if n_test < 1:
            raise ValueError("Each class needs at least 2 rows for holdout evaluation.")
        test_ids.extend(ids[:n_test].tolist())
    test_id_set = set(test_ids)
    train = df.loc[[i for i in df.index if i not in test_id_set]].copy()
    test = df.loc[sorted(test_id_set)].copy()
    return train, test


def stratified_kfold_splits(df, target_col, n_splits=10, seed=42):
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2.")
    class_counts = df[target_col].value_counts()
    if class_counts.empty:
        raise ValueError("Target column has no classes.")
    if int(class_counts.min()) < n_splits:
        raise ValueError(f"n_splits={n_splits} exceeds the smallest class size={int(class_counts.min())}.")
    rng = np.random.default_rng(seed)
    fold_test_ids = [[] for _ in range(n_splits)]
    for _, group in df.groupby(target_col, sort=False):
        ids = group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        chunks = np.array_split(ids, n_splits)
        for fold_no, chunk in enumerate(chunks):
            fold_test_ids[fold_no].extend(int(x) for x in chunk)
    all_ids = set(int(i) for i in df.index)
    folds=[]
    for test_ids in fold_test_ids:
        test_set=set(test_ids)
        folds.append((df.loc[sorted(all_ids-test_set)].copy(), df.loc[sorted(test_set)].copy()))
    return folds
