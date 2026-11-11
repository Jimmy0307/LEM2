"""Produce two-layer, metric-aware leaderboards without pseudo-replication."""
from __future__ import annotations
import json
import math
from pathlib import Path
import pandas as pd
import numpy as np

SRC=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
OUT=Path("docs/research/teacher_dashboard/data/model_comparison.json")
METRICS=["accuracy","balanced_accuracy","macro_f1","coverage","conflict_case_rate","true_in_candidate_rate"]
POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH",
          "POPULATION_STANDARD","POPULATION_GLOBAL")
def safe(v):
    return None if pd.isna(v) else float(v)
def main():
    df=pd.read_csv(SRC)
    assert len(df)==8820
    held=df[(df.split_mode=="HOLDOUT_80_20") & (df.selection_policy!="NONE")].copy()
    assert len(held)==3*42*5*6
    dims=["dataset","system","client_count","selection_policy"]
    by_dataset=[]
    for (ds,sys,c,pol),rows in held.groupby(dims,sort=True):
        assert len(rows)==42, (ds,sys,c,pol,len(rows))
        rec={"dataset":ds,"system":sys,"client_count":int(c),"policy":pol,
             "seeds":42,"n_dataset_independent":1}
        for m in METRICS:
            rec[m]=float(rows[m].mean())
            rec[m+"_sd_across_seeds"]=float(rows[m].std(ddof=1))
            rec[m+"_min"]=float(rows[m].min())
            rec[m+"_max"]=float(rows[m].max())
        by_dataset.append(rec)
    data=pd.DataFrame(by_dataset)
    overall=[]
    for (sys,c,pol),rows in data.groupby(["system","client_count","policy"],sort=True):
        assert len(rows)==3
        rec={"system":sys,"client_count":int(c),"policy":pol,"dataset_count":3,
            "seed_count_per_dataset":42,"total_config_rows":126}
        for m in METRICS:
            rec[m]=float(rows[m].mean())
            rec[m+"_dataset_min"]=float(rows[m].min())
            rec[m+"_dataset_max"]=float(rows[m].max())
        overall.append(rec)
    for m in ("accuracy","balanced_accuracy","macro_f1"):
        value=max(r[m] for r in overall)
        assert value>0
    for row in overall+by_dataset:
        assert row["accuracy"]>=0 and row["accuracy"]<=1
    # A tiny sample of robust pairing: within each independent dataset, seed-aligned
    # comparisons. Avoid interpreting 42 seeds as 42 independently sampled datasets.
    contrasts=[]
    for ds,rs in held.groupby("dataset"):
        for c in (0,2,3,4,5):
            sub=rs[rs.client_count==c]
            std=sub[sub.selection_policy=="STANDARD_VOTING"].set_index("seed")
            gs=sub[sub.selection_policy=="GLOBAL_STRENGTH"].set_index("seed")
            assert std.index.is_unique and gs.index.is_unique and len(std)==len(gs)==42
            for m in ("accuracy","balanced_accuracy","macro_f1"):
                d=(gs[m]-std[m]).to_numpy(dtype=float)
                contrasts.append({"dataset":ds,"client_count":c,"metric":m,
                                  "difference":"GLOBAL_STRENGTH minus STANDARD_VOTING",
                                  "mean_pp":float(d.mean()*100),
                                  "median_pp":float(np.median(d)*100),
                                  "min_pp":float(d.min()*100),
                                  "max_pp":float(d.max()*100),
                                  "positive_seed_count":int((d>0).sum()),
                                  "negative_seed_count":int((d<0).sum()),"zero_seed_count":int((d==0).sum()),
                                  "seed_count":42,"generalizability":"conditional on fixed dataset"})
    overall.sort(key=lambda r:(-r["balanced_accuracy"],r["system"],r["client_count"],r["policy"]))
    body={
      "version":"2026-11-11 independent calculation from frozen 8820",
      "source":str(SRC),"protocol":"HOLDOUT_80_20",
      "dataset_weighting":"Equal weight across 3 datasets; 42 seeds equally within dataset",
      "independent_datasets":3,"seeds_per_dataset":42,
      "warning":"Averaging 42 seeds is descriptive split robustness, NOT independent external validation; FULL_DATA excluded from winner ranking.",
      "metrics_definition":{
          "accuracy":"correct test predictions / test rows",
          "balanced_accuracy":"mean of recall over true classes in the evaluation set",
          "macro_f1":"mean of per-class F1 over union of true and predicted labels",
          "coverage":"any rule matches test row",
          "conflict_case_rate":"matches involve two or more distinct predicted class labels",
          "true_in_candidate_rate":"true class appears in the matched rule decisions"
      },
      "overall_3_dataset_equal":overall,
      "by_dataset":by_dataset,
      "paired_GS_minus_STD":contrasts
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(body,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("COMPARISON_EXACT_FROM_8820=PASS",len(overall),len(by_dataset),len(contrasts),flush=True)
if __name__=="__main__":
    main()
