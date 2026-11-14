"""Leakage-aware adaptive six-policy selector experiment on 20 public UCI datasets.

Each dataset/seed has one fixed induction rule system per architecture.
Induction=64%, inner validation=16%, untouched outer test=20%.
Source data are the previously verified prepared/attributed UCI subsets.
Records all six policies' inner validation AND outer test metrics, but choices
are made from INNER VALIDATION only and never from outer test outcomes.
Meta selection across datasets happens in a separate leave-one-dataset-out
aggregate pass, using only induction/validation features and policy scores.

This is a research POC; no new LEM2 induction algorithm is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.app import _run_split
from roughset.evaluation import (
    evaluate_rule_model, matching_rules, target_coverage_by_class
)
from roughset.federated import partition_clients
from roughset.preprocessing import apply_preprocessor
from roughset.splitting import stratified_train_test_split
from teacher_demo.full_factorial_matrix import POLICIES,_split_raw
from teacher_demo.conflict_aware_coverage_pilot import load_bundle
from teacher_demo.public_20_registry import REGISTRY

SEEDS=(1,7,42)
ARCHITECTURES=(("CENTRALIZED",0),("FEDERATED",3))
OBJECTIVES=("balanced_accuracy","macro_f1","accuracy")
POLICY_ORDER=("SIMPLE_VOTING","GLOBAL_STRENGTH","STANDARD_VOTING",
              "FIRST_MATCH","POPULATION_STANDARD","POPULATION_GLOBAL")
assert set(POLICY_ORDER)==set(POLICIES)

def train_stats(dev,bundle,rules,clients):
    labels=dev[bundle.target].astype(str)
    proportions=labels.value_counts(normalize=True)
    p=proportions.to_numpy(dtype=float)
    c=len(p)
    entropy=float(-(p*np.log(np.maximum(p,1e-12))).sum()/math.log(c)) if c>1 else 0.
    n=len(dev)
    feats=bundle.features
    cardinal=[dev[f].nunique(dropna=False)/n for f in feats]
    conds=[len(r.conditions) for r in rules]
    stats={
       "log_dev_rows":float(np.log1p(n)),
       "num_features":len(feats),
       "continuous_ratio":len(bundle.schema.continuous)/len(feats),
       "num_classes":c,
       "majority_share":float(p.max()),
       "minority_share":float(p.min()),
       "normalized_class_entropy":entropy,
       "mean_feature_cardinality_fraction":float(np.mean(cardinal)),
       "log_rule_count":float(np.log1p(len(rules))),
       "mean_rule_condition_count":float(np.mean(conds)) if conds else 0.,
       "num_clients":len(clients),
       "client_row_cv":0.,
       "client_label_js_divergence":0.,
       "client_missing_class_fraction":0.
    }
    if clients:
        sizes=np.asarray([len(x) for x in clients.values()],dtype=float)
        stats["client_row_cv"]=float(sizes.std()/sizes.mean())
        classes=sorted(labels.unique())
        global_dist=np.array([(labels==v).mean() for v in classes],dtype=float)
        js=[]
        missing=[]
        for table in clients.values():
            local=table[bundle.target].astype(str)
            q=np.array([(local==v).mean() for v in classes],dtype=float)
            mid=.5*(global_dist+q)
            kl=lambda x,y:float((x[x>0]*np.log(x[x>0]/y[x>0])).sum())
            js.append(.5*(kl(global_dist,mid)+kl(q,mid))/math.log(2))
            missing.append(float((q==0).mean()))
        stats["client_label_js_divergence"]=float(np.mean(js))
        stats["client_missing_class_fraction"]=float(np.mean(missing))
    return stats

def rule_validation_stats(art,rules):
    n=len(art.test)
    covered=conflict=right_candidate=0
    hits=[]
    for _,row in art.test.iterrows():
        matched=matching_rules(row,rules)
        labels={str(r.decision) for r in matched}
        covered+=bool(matched)
        conflict+=len(labels)>1
        right_candidate+=str(row[art.target]) in labels
        hits.append(len(matched))
    assert n>0
    return {
       "inner_rule_coverage":covered/n,
       "inner_rule_conflict":conflict/n,
       "inner_correct_candidate_coverage":right_candidate/n,
       "inner_mean_matching_rules":float(np.mean(hits)),
       "inner_num_conflicting_cases":conflict
    }

def run_one(dataset,seed,outdir):
    bundle,sha=load_bundle(dataset)
    outer_train,outer_test=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
    induction,validation=stratified_train_test_split(
        outer_train,bundle.target,test_ratio=.20,seed=1000+seed
    )
    ids=[set(x.__row_id__.astype(int)) for x in (induction,validation,outer_test)]
    assert len(ids[0]|ids[1]|ids[2])==len(bundle.frame)
    assert not(ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2])
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    cfg["evaluation"]["seed"]=int(seed)
    cfg["evaluation"]["mode"]="HOLDOUT_80_20"
    cfg["federated"]["partition"]="STRATIFIED"
    cfg["federated"]["run_client_sweep"]=False
    cfg["federated"]["order_sensitivity_max_permutations"]=1
    rows=[]
    for arch,client_count in ARCHITECTURES:
        cfgx=deepcopy(cfg)
        cfgx["experiment"]["run_centralized"]=arch=="CENTRALIZED"
        cfgx["experiment"]["run_federated"]=arch=="FEDERATED"
        cfgx["federated"]["n_clients"]=client_count
        # No evaluation/test outcomes are passed into induction or the selector.
        fit=_run_split(bundle,induction,validation,cfgx,quiet=True,
                       prediction_policies=POLICIES,fold=1)
        art=fit["structural_artifact"]
        rules=art.central_rules if client_count==0 else art.global_rules
        default=art.central_default_class if client_count==0 else art.default_class
        weights=art.central_rule_weights if client_count==0 else art.global_rule_weights
        supports=art.central_rule_support_sets if client_count==0 else art.global_rule_support_sets
        classes=art.central_class_sizes if client_count==0 else art.global_class_sizes
        clients={} if client_count==0 else partition_clients(
            induction,bundle.target,n_clients=client_count,seed=seed,
            strategy=cfgx["federated"]["partition"],
            dirichlet_alpha=cfgx["federated"]["dirichlet_alpha"],
            dirichlet_max_retries=cfgx["federated"]["dirichlet_max_retries"]
        )
        profile={**train_stats(induction,bundle,rules,clients),**rule_validation_stats(art,rules)}
        # Enumerate six outcomes on inner validation; only these can choose policy.
        validation_metrics={}
        for policy in POLICIES:
            key="centralized" if client_count==0 else "federated"
            result=fit["policy_results"][policy][key]
            assert result is not None, (dataset,seed,client_count,policy)
            validation_metrics[policy]={obj:float(result[obj]) for obj in OBJECTIVES}
        # Frozen rule system and all eligibility decisions precede viewing test.
        inner_choices={
            obj:max(POLICY_ORDER,key=lambda p:(validation_metrics[p][obj],-POLICY_ORDER.index(p)))
            for obj in OBJECTIVES
        }
        test=apply_preprocessor(outer_test,fit["preprocessor"],bundle.target)
        assert len(test)==len(outer_test)
        for policy in POLICIES:
            measured=evaluate_rule_model(
                test,rules,default,bundle.target,prediction_policy=policy,
                rule_weights=weights,rule_support_sets=supports,class_sizes=classes
            )
            row={
                "dataset":dataset,"uci_id":REGISTRY[dataset]["id"],"seed":seed,
                "architecture":arch,"client_count":client_count,"policy":policy,
                "source_sha256":sha,
                "development_rows":len(art.train),"inner_validation_rows":len(art.test),
                "outer_test_rows":len(test),"total_rows":len(bundle.frame),
                "feature_mode":REGISTRY[dataset]["feature_mode"],
                "source_original_rows":REGISTRY[dataset].get("cap_rows"),
                "rule_count":len(rules),
                "method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
                "protocol":"NESTED_64_16_20_NO_REFIT",
                "inner_val_accuracy":validation_metrics[policy]["accuracy"],
                "inner_val_balanced_accuracy":validation_metrics[policy]["balanced_accuracy"],
                "inner_val_macro_f1":validation_metrics[policy]["macro_f1"],
                "outer_test_accuracy":float(measured["accuracy"]),
                "outer_test_balanced_accuracy":float(measured["balanced_accuracy"]),
                "outer_test_macro_f1":float(measured["macro_f1"]),
                "outer_test_exact_coverage":float(measured["coverage"]),
                "is_inner_best_accuracy":int(policy==inner_choices["accuracy"]),
                "is_inner_best_balanced_accuracy":int(policy==inner_choices["balanced_accuracy"]),
                "is_inner_best_macro_f1":int(policy==inner_choices["macro_f1"]),
                **profile
            }
            rows.append(row)
        print("ADAPTIVE_SELECTOR_ARCH_PASS",dataset,seed,arch,"rules",len(rules),
              "val_best_BA",inner_choices["balanced_accuracy"],flush=True)
    assert len(rows)==12
    dest=Path(outdir);dest.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(dest/f"ADAPTIVE_SIX_{dataset}_seed{seed}.csv",index=False)
    print("ADAPTIVE_SELECTOR_CONFIG_PASS",dataset,seed,"12",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=sorted(REGISTRY),required=True)
    p.add_argument("--seed",type=int,choices=SEEDS,required=True)
    p.add_argument("--output",default="outputs/adaptive_six")
    a=p.parse_args();run_one(a.dataset,a.seed,a.output)

if __name__=="__main__":main()
