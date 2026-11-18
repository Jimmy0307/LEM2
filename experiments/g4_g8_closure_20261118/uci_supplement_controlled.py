"""Real, previously explored UCI20 controlled supplemental rule experiment.

Exploratory only: sources and seeds were already seen in the prior G4–G8
research, so this is NOT new-source confirmatory research. Uses stored prepared
UCI20 CSVs in GitHub checkout, not the private OpenML cache.

Holdout always untouched for fit/threshold selection. Same split, partition,
cut model, reduct and original LEM2 rules for baseline B2 vs train-only
supplement. All errors and source SHA preserved. Output only to scratch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import pandas as pd

from fedrs.experiment import DEFAULT_BASE, fit_model, nested_split
from fedrs.partition import original_partition
from fedrs.supplement_exploratory import supplement_test
from experiments.redesign_20261116.common import UCI20, uci20_bundle

SOURCES = ("adult_income", "bank_marketing", "magic_gamma", "mushroom", "wine")
REGIMES = ("IID", "NONIID_05", "NONIID_01")
SEEDS = (11, 23)


def run_case(dataset: str, seed: int, regime: str, n_clients: int):
    bundle, raw_sha = uci20_bundle(dataset)
    df=bundle.frame
    dev,val,test=nested_split(df,bundle.target,seed)
    clients=original_partition(dev,bundle.target,n_clients,seed,regime)
    t0=perf_counter()
    fm=fit_model(bundle.features,bundle.schema.continuous,bundle.schema.categorical,
                 bundle.target,clients,dev,val,test,"EQUAL_WIDTH_3")
    policy=DEFAULT_BASE[regime]
    res=supplement_test(fm,min_support=5,min_purity=.90,base_policy=policy)
    elapsed=perf_counter()-t0
    return {"dataset":dataset,"prepared_sha256":raw_sha,"seed":seed,"regime":regime,
            "n_clients":n_clients,"dev_rows":len(dev),"val_rows":len(val),"test_rows":len(test),
            "single_class_clients":sum(m.n_classes==1 for m in fm.local.values()),
            "true_rules":sum(not rule.conditions for rule in fm.rules),
            "original_rules":len(fm.rules),"model_and_eval_seconds":elapsed,**res}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--datasets",default=",".join(SOURCES))
    ap.add_argument("--regimes",default="IID,NONIID_05,NONIID_01")
    ap.add_argument("--seeds",default="11,23")
    ap.add_argument("--clients",default="3")
    ap.add_argument("--max-tasks",type=int,default=0)
    args=ap.parse_args()
    data=tuple(d for d in args.datasets.split(",") if d)
    regimes=tuple(r for r in args.regimes.split(",") if r)
    seeds=tuple(int(s) for s in args.seeds.split(",") if s)
    counts=tuple(int(s) for s in args.clients.split(",") if s)
    if not data or not regimes or not seeds or not counts:
        raise ValueError("Datasets/seeds/regimes/clients must be explicit and nonempty")
    if any(d not in UCI20 for d in data) or any(r not in REGIMES for r in regimes):
        raise ValueError("Unknown source or regime")
    if any(k < 2 for k in counts) or len(set(data)) != len(data):
        raise ValueError("Invalid client count or duplicate source")
    tasks=[(d,s,r,k) for d in data for s in seeds for r in regimes for k in counts]
    if args.max_tasks:
        tasks=tasks[:args.max_tasks]
    dest=args.output.resolve()
    published=(Path(__file__).resolve().parents[2]/"docs/research/redesign_20261116/data").resolve()
    if dest.is_relative_to(published):
        raise SystemExit("Never write into published Gate5 evidence")
    dest.mkdir(parents=True,exist_ok=True)
    ok,fail=[],[]
    for n,(d,s,r,k) in enumerate(tasks,1):
        try:
            item=run_case(d,s,r,k)
            ok.append(item)
            print("UCI_SUPPLEMENT_TASK_PASS",n,len(tasks),d,s,r,k,
                  "strict_cov",round(item["strict_nonempty_coverage"],4),
                  "gainBA_pp",round(item["test_ba_gain_pp"],4),flush=True)
        except Exception as exc:
            fail.append({"dataset":d,"seed":s,"regime":r,"n_clients":k,
                         "error_type":type(exc).__name__,"error":str(exc)[:400]})
            print("UCI_SUPPLEMENT_TASK_FAIL",n,len(tasks),d,s,r,k,type(exc).__name__,flush=True)
    pd.DataFrame(ok).to_csv(dest/"G5_REAL_UCI20_SUPPLEMENT_EXPLORATORY.csv",index=False)
    pd.DataFrame(fail,columns=("dataset","seed","regime","n_clients","error_type","error")).to_csv(
        dest/"G5_REAL_UCI20_SUPPLEMENT_FAILURES.csv",index=False)
    (dest/"G5_REAL_UCI20_SUPPLEMENT_MANIFEST.json").write_text(
        json.dumps({"designation":"EXPLORATORY_REUSED_UCI20_ONLY",
                    "input":"GitHub-prepared UCI20; source sha per result row",
                    "sources":data,"seeds":seeds,"regimes":regimes,"client_counts":counts,
                    "tasks":len(tasks),"succeeded":len(ok),"failed":len(fail),
                    "no_new_prereg_confirmatory":True,
                    "thresholds":{"min_support":5,"min_purity":.90},
                    "base_policy":"IID GS / NonIID SIMPLE; B2 true fallback",
                    "test_used_to_fit_or_select":False,
                    "federated_privacy_guarantee":False},
                   ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if ok:
        df=pd.DataFrame(ok)
        print("UCI_SUPPLEMENT_REAL_DATA_SUMMARY")
        print(df.groupby(["regime"]).agg(
            n=("dataset","count"),n_sources=("dataset","nunique"),
            original_strict_coverage=("strict_nonempty_coverage","mean"),
            augmented_strict_coverage=("augmented_strict_coverage","mean"),
            mean_ba_gain_pp=("test_ba_gain_pp","mean"),
            improved=("test_ba_gain_pp",lambda x: int((x>1e-12).sum())),
            worsened=("test_ba_gain_pp",lambda x: int((x < -1e-12).sum()))
        ).round(5).to_string())
    if fail:
        print("UCI_SUPPLEMENT_FAILURES",fail)
        raise RuntimeError(f"{len(fail)} failed real-UCI exploratory tasks; all failures recorded")
    print("UCI_SUPPLEMENT_REAL_EXPLORATORY_PASS",len(ok))


if __name__=="__main__":
    main()
