"""Run reproducible LEM2 210-row factorial for a single seed (1..42).

All three UCI source tables are pinned locally to avoid network flakiness.
Seed 42 must match the canonical frozen baseline before the 42-seed sweep.
"""
from __future__ import annotations

import argparse
import itertools
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from roughset.adapters import load_uci_dataset_by_id
from teacher_demo.full_factorial_matrix import run_full_factorial, _validate_runtime_output

ROOT=Path("research/seed_sweep_inputs")
NAMES={12:"Balance Scale",19:"Car Evaluation",44:"Hayes-Roth"}

def pinned_fetcher(id):
    id=int(id)
    if id==12:
        data=[]
        for lw,ld,rw,rd in itertools.product(range(1,6),repeat=4):
            label="L" if lw*ld>rw*rd else "R" if lw*ld<rw*rd else "B"
            data.append((lw,ld,rw,rd,label))
        frame=pd.DataFrame(data,columns=["left-weight","left-distance","right-weight","right-distance","class"])
        assert frame.shape==(625,5)
    elif id==19:
        frame=pd.read_csv(ROOT/"uci_19_car.data",header=None,dtype=str,
                          names=["buying","maint","doors","persons","lug_boot","safety","class"])
        assert frame.shape==(1728,7) and frame["class"].value_counts().to_dict()=={"unacc":1210,"acc":384,"good":69,"vgood":65}
    elif id==44:
        frame=pd.read_csv(ROOT/"uci_44_hayes_roth.data",header=None,
                          names=["name","hobby","age","educational level","marital status","class"])
        assert frame.shape==(132,6)
    else:
        raise ValueError(f"Unsupported pinned UCI ID {id}")
    X=frame.drop(columns=["class"])
    y=frame[["class"]]
    return SimpleNamespace(data=SimpleNamespace(features=X,targets=y),
                           metadata=SimpleNamespace(name=NAMES[id]))

def pinned_bundles():
    return [load_uci_dataset_by_id(i,fetcher=pinned_fetcher) for i in (12,19,44)]

def verify_frozen_seed42(df):
    path=Path("docs/research/full_factorial_20261029/tables/FULL_FACTORIAL_RESULTS.csv")
    frozen=pd.read_csv(path)
    key=["dataset","split_mode","system","client_count","selection_policy"]
    a=df.sort_values(key).reset_index(drop=True)
    b=frozen.sort_values(key).reset_index(drop=True)
    assert len(a)==len(b)==210
    assert a[key].astype(str).equals(b[key].astype(str)), "Seed 42 key layout differs from canonical"
    cols=["rule_count","reduct_size","coverage","conflict_case_rate",
          "true_in_candidate_rate","accuracy","balanced_accuracy","macro_f1"]
    for col in cols:
        x=pd.to_numeric(a[col],errors="coerce").to_numpy(dtype=float)
        y=pd.to_numeric(b[col],errors="coerce").to_numpy(dtype=float)
        if not np.allclose(x,y,rtol=1e-10,atol=1e-10,equal_nan=True):
            bad=np.flatnonzero(~np.isclose(x,y,rtol=1e-10,atol=1e-10,equal_nan=True))
            raise AssertionError(f"Seed42 snapshot not equivalent: {col}; {len(bad)} rows; first={bad[:5].tolist()}")
    print("SEED_42_FROZEN_REFERENCE_VERDICT=PASS",flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=int,required=True)
    parser.add_argument("--output",default="outputs/seed_sweep_1_42")
    args=parser.parse_args()
    if not 1<=args.seed<=42: raise ValueError("seed must be 1..42")
    cfg=deepcopy(json.loads(Path("config.json").read_text(encoding="utf-8-sig")))
    cfg["evaluation"]["seed"]=args.seed
    df=run_full_factorial(cfg,pinned_bundles())
    _validate_runtime_output(df)
    assert len(df)==210 and (pd.to_numeric(df["seed"])==args.seed).all()
    if args.seed==42: verify_frozen_seed42(df)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    filename=out/f"ff_seed{args.seed:02d}.csv"
    df.to_csv(filename,index=False,encoding="utf-8-sig")
    print(f"SEED_SWEEP_PASS seed={args.seed} rows={len(df)} path={filename}",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
