from __future__ import annotations

import time
from typing import Any, Dict, Mapping
import numpy as np
import pandas as pd

from .core import induce_lem2
from .reduct import find_minimum_cardinality_reducts
from .splitting import stratified_kfold_splits
from .evaluation import majority_class, fit_rule_support_sets, evaluate_rule_model

PAPER_BENCHMARKS = {
    "WANG_2007": {
        "title": "Feature Selection based on Rough Sets and Particle Swarm Optimization",
        "doi": "10.1016/j.patrec.2006.09.003",
        "protocol": "LEM2 + global strength + 10-fold CV",
        "uci": {
            44: {"features":4,"instances":132,"reduct_size":3,"rules":15,"accuracy_pct":89.5,"psorsfs_time_s":95.422},
            19: None,
            12: {"features":4,"instances":625,"reduct_size":4,"rules":207,"accuracy_pct":88.5,"psorsfs_time_s":3001.1},
        },
    }
}


def run_paper_protocol(bundle, cv_folds: int = 10, seed: int = 42) -> Dict[str, Any]:
    """V6.1 Wang-style replication lane.

    The reduct is selected once on the complete labeled dataset to mirror the
    historical benchmark. This is intentionally kept separate from modern
    leakage-free evaluation.
    """
    started = time.perf_counter()
    df = bundle.frame.copy().reset_index(drop=True)
    features = list(bundle.features)
    target = bundle.target
    for col in features + [target]:
        df[col] = df[col].astype(str)
    df["__row_id__"] = np.arange(len(df), dtype=int)

    reduct_candidates = find_minimum_cardinality_reducts(df, features, target)
    reduct = list(sorted(reduct_candidates, key=lambda x: tuple(map(str, x)))[0])
    full_rules = induce_lem2(df, reduct, target, source="PaperFullData", verbose=False)

    rows=[]
    for fold_no,(train,test) in enumerate(stratified_kfold_splits(df,target,cv_folds,seed),1):
        rules=induce_lem2(train,reduct,target,source=f"PaperFold_{fold_no}",verbose=False)
        default=majority_class(train,target)
        support_sets,class_sizes=fit_rule_support_sets(train,rules,target)
        metrics=evaluate_rule_model(test,rules,default,target,prediction_policy="GLOBAL_STRENGTH",rule_support_sets=support_sets,class_sizes=class_sizes)
        rows.append({"fold":fold_no,"accuracy":metrics["accuracy"],"balanced_accuracy":metrics["balanced_accuracy"],"macro_f1":metrics["macro_f1"],"coverage":metrics["coverage"],"rules":len(rules)})
    m=pd.DataFrame(rows)
    return {
        "reduct":reduct,"reduct_candidates":[list(x) for x in reduct_candidates],
        "full_data_rules":full_rules,"full_data_rule_count":len(full_rules),
        "accuracy":float(m.accuracy.mean()),"accuracy_std":float(m.accuracy.std(ddof=0)),
        "balanced_accuracy":float(m.balanced_accuracy.mean()),"macro_f1":float(m.macro_f1.mean()),
        "coverage":float(m.coverage.mean()),"mean_rule_count":float(m.rules.mean()),
        "fold_metrics":m,"prediction_policy":"GLOBAL_STRENGTH","evaluation_mode":"K_FOLD_CV",
        "cv_folds":cv_folds,"runtime_s":float(time.perf_counter()-started),
    }


def published_comparison(bundle, protocol_result: Mapping[str, Any], reference: str = "WANG_2007") -> Dict[str, Any]:
    meta=PAPER_BENCHMARKS[reference]
    uci_id=None
    if str(bundle.source).startswith("uci_id:"):
        try: uci_id=int(str(bundle.source).split(":",1)[1])
        except ValueError: pass
    paper=meta["uci"].get(uci_id)
    our_acc=float(protocol_result["accuracy"])*100
    return {
        "reference":reference,"reference_doi":meta["doi"],"protocol":meta["protocol"],
        "our_reduct_size":len(protocol_result["reduct"]),"our_rules":protocol_result["full_data_rule_count"],
        "our_accuracy_pct":our_acc,
        "paper_reduct_size":paper.get("reduct_size") if paper else None,
        "paper_rules":paper.get("rules") if paper else None,
        "paper_accuracy_pct":paper.get("accuracy_pct") if paper else None,
        "accuracy_delta_pp":our_acc-float(paper["accuracy_pct"]) if paper else None,
    }
