"""Actual held-out classification quality of GREEDY_POS reduct vs full features.

Two strategies share SAME train-only discretization & untouched test rows.
This compares approximate POS-preserving selected columns with all selected
source columns; FULL is not the exact minimum-cardinality reduct.
Source original features are the first k columns, not an optimized semantic
feature selection. Under 24 feature / big data the entire LEM2 pipeline
remains unverified (this is intentionally a bounded quality study).
"""
from __future__ import annotations
import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd
from roughset.app import _feature_types
from roughset.preprocessing import fit_shared_preprocessor,apply_preprocessor
from roughset.pipeline import induce_lem2_on_reduct
from roughset.reduct import _positive_region_size
from roughset.reduct_fast import greedy_pos
from roughset.evaluation import evaluate_rule_model,majority_class,fit_rule_support_sets
from teacher_demo.full_factorial_matrix import _split_raw
from teacher_demo.pmlb_117_runner import prepare
from teacher_demo.pmlb_resource_staircase import subbundle

DATASETS=("adult","connect_4","spambase")
ROWS=(600,1600)
FEATURES=(8,12,16)

def one(name,out):
    bundle,meta=prepare(name,max_rows=max(ROWS),max_features=max(FEATURES))
    results=[];errors=[]
    for n in ROWS:
      for k in FEATURES:
        if n>len(bundle.frame) or k>len(bundle.features):
            continue
        try:
            b=subbundle(bundle,n,k)
            rawtrain,rawtest=_split_raw(b,"HOLDOUT_80_20",seed=42,test_ratio=.2)
            # Train-only preprocessing; never use test for discretization
            continuous,categorical=_feature_types(b,rawtrain,{"unique_numeric_threshold":10})
            prep=fit_shared_preprocessor({"Train":rawtrain},b.features,b.target,
                      continuous,categorical,3)
            train=apply_preprocessor(rawtrain,prep,b.target)
            test=apply_preprocessor(rawtest,prep,b.target)
            available=tuple(prep["condition_columns"])
            original_positive=_positive_region_size(train,available,b.target)
            greed=greedy_pos(train,available,b.target)
            assert greed.positive_region==original_positive
            for method,subset in (("FULL_SOURCE_FEATURE_SET",available),
                                  ("GREEDY_POS_PRESERVING_REDUCT",greed.selected)):
                started=time.perf_counter()
                rules=induce_lem2_on_reduct(train,subset,b.target,source="G8_RESEARCH")
                train_supp,cls=fit_rule_support_sets(train,rules,b.target)
                t=time.perf_counter()-started
                e=evaluate_rule_model(test,rules,majority_class(train,b.target),b.target,
                          prediction_policy="GLOBAL_STRENGTH",
                          rule_support_sets=train_supp,class_sizes=cls)
                results.append({"dataset":name,"rows":n,"features":k,
                    "method":method,"train_rows":len(train),"test_rows":len(test),
                    "reduct_features":len(subset),"train_full_pos":original_positive,
                    "train_selected_pos":_positive_region_size(train,subset,b.target),
                    "reduct_selection_seconds":greed.selection_seconds if method.startswith("GREEDY") else None,
                    "rules":len(rules),"rule_induction_and_support_seconds":t,
                    "test_coverage_pct":100*float(e["coverage"]),
                    "test_balanced_accuracy_pct":100*float(e["balanced_accuracy"]),
                    "test_accuracy_pct":100*float(e["accuracy"]),
                    "test_macro_f1_pct":100*float(e["macro_f1"]),
                    "source_gzip_sha256":meta["source_gzip_sha256"],
                    "prepared_sha256":meta["prepared_sha256"],
                    "peak_rss_mb_since_process_start":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                    "protocol":"STRATIFIED_HOLDOUT80_20_SAME_DISCRETIZATION_AND_SOURCE_ROWS",
                    "not_minimum_cardinality_claim":method.startswith("GREEDY")})
            print("G8_FULL_LEM2_QUALITY_PASS",name,n,k,flush=True)
        except Exception as e:
            errors.append({"rows":n,"features":k,"error":type(e).__name__+":"+str(e)[:500]})
            print("G8_FULL_LEM2_QUALITY_FAIL",name,n,k,str(e)[:400],flush=True)
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    if results:pd.DataFrame(results).to_csv(output/f"G8_QUALITY_{name}.csv",index=False)
    (output/f"G8_QUALITY_RECEIPT_{name}.json").write_text(
        json.dumps({"dataset":name,"source":meta,"success_rows":len(results),
          "errors":errors,"scope":"G8_OUTER_TEST_RULE_LEARNING_600_1600_ROWS_8_16_FEATURES",
          "all_original_feature_baseline_is_not_exact_reduct":True},indent=2),encoding="utf-8")

def main():
    p=argparse.ArgumentParser();p.add_argument("--dataset",required=True,choices=DATASETS)
    p.add_argument("--output",default="outputs/g8_quality")
    x=p.parse_args();one(x.dataset,x.output)
if __name__=="__main__":main()
