"""Evidence export for every object, class and winner of the frozen 42-seed design.

Reuses the production pipeline; these are model outputs, not simulated predictions.
CSV is emitted per seed as workflow artifacts; only small aggregate tables are published.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import (
    _split_raw, _base_row, _none_row, _policy_row, POLICIES,
)
from roughset.app import _run_split
from roughset.evaluation import matching_rules, population_support_summary

SPLITS=("FULL_DATA","HOLDOUT_80_20")
KEY=("dataset","seed","split_mode","system","client_count","selection_policy")


def serialize(v):
    return json.dumps(v,ensure_ascii=False,separators=(",",":"),default=str)


def audit_block(bundle, cfg, split, system, count):
    conf=deepcopy(cfg)
    conf["evaluation"]["mode"]=split
    conf["federated"]["run_client_sweep"]=False
    conf["federated"]["order_sensitivity_max_permutations"]=1
    conf["experiment"]["run_centralized"]=system=="CENTRALIZED"
    conf["experiment"]["run_federated"]=system=="FEDERATED"
    conf["federated"]["n_clients"]=int(count)
    raw_train,raw_test=_split_raw(bundle,split,int(conf["evaluation"]["seed"]),float(conf["evaluation"]["test_ratio"]))
    result=_run_split(bundle,raw_train,raw_test,conf,quiet=True,prediction_policies=POLICIES,fold=1)
    art=result["structural_artifact"]
    key="centralized" if system=="CENTRALIZED" else "federated"
    rules=art.central_rules if system=="CENTRALIZED" else art.global_rules
    default=art.central_default_class if system=="CENTRALIZED" else art.default_class
    weights=art.central_rule_weights if system=="CENTRALIZED" else art.global_rule_weights
    supports=art.central_rule_support_sets if system=="CENTRALIZED" else art.global_rule_support_sets
    sizes=art.central_class_sizes if system=="CENTRALIZED" else art.global_class_sizes
    outputs={p:result["policy_results"][p][key] for p in POLICIES}
    base=_base_row(bundle=bundle,split_mode=split,system=system,client_count=count,artifact=art)
    aggregate=[_none_row(base)]+[_policy_row(base,p,outputs[p]) for p in POLICIES]
    pre=dict(dataset=bundle.name,seed=int(conf["evaluation"]["seed"]),split_mode=split,system=system,client_count=count)
    detail_rows=[]
    class_records=defaultdict(list)
    for pos,(_,row) in enumerate(art.test.iterrows()):
        matched=matching_rules(row,rules)
        candidates=sorted({str(r.decision) for r in matched})
        decision=str(row[art.target])
        preds={p:str(outputs[p]["predictions"][pos]) for p in POLICIES}
        match_exists=bool(matched)
        truth_in=decision in candidates
        conflict=len(candidates)>1
        support=population_support_summary(matched,supports,sizes) if matched else {}
        votes={}
        classes=sorted({str(x.decision) for x in matched})
        for cls in classes:
            relevant=[r for r in matched if str(r.decision)==cls]
            value=support.get(relevant[0].decision,{})
            T=float(value.get("total_support_occurrences",0))
            U=float(value.get("unique_population",0))
            N=float(value.get("class_size",0))
            P=U/T if T else 0.0
            votes[cls]={
                "FIRST_ORDER":min(i for i,r in enumerate(matched) if str(r.decision)==cls),
                "SIMPLE":float(len(relevant)),
                "STANDARD":float(sum(float(weights.get(r.key,0)) for r in relevant)),
                "GS":U/N if N else 0.0,
                "PS":U,
                "PG":(U*U)/(N*T) if N*T else 0.0,
                "T":T,"U":U,"N":N,"P":P,
            }
        if matched:
            # Re-check every computed score against canonical resolver's answer.
            for p,col in (("SIMPLE_VOTING","SIMPLE"),("STANDARD_VOTING","STANDARD"),
                          ("GLOBAL_STRENGTH","GS"),("POPULATION_STANDARD","PS"),
                          ("POPULATION_GLOBAL","PG")):
                scores={cls:values[col] for cls,values in votes.items()}
                mx=max(scores.values())
                winners=[cls for cls,v in scores.items() if np.isclose(v,mx)]
                expected=str(default) if str(default) in winners else sorted(winners)[0]
                assert preds[p]==expected,(pre,pos,p,expected,preds[p])
            assert preds["FIRST_MATCH"]==str(matched[0].decision)
        else:
            assert all(y==str(default) for y in preds.values()),(pre,pos,preds,default)
        origid=int(row["__row_id__"]) if "__row_id__" in row else int(pos)
        rowclass="NO_MATCH" if not match_exists else ("TRUE_MISSING" if not truth_in else ("CONFLICT" if conflict else "UNIQUE"))
        correct={p:(preds[p]==decision) for p in POLICIES}
        errors={p:("CORRECT" if correct[p] else "NO_MATCH_FALLBACK_ERROR" if not match_exists else
                    "CANDIDATE_MISSING_ERROR" if not truth_in else "WINNER_SELECTION_ERROR") for p in POLICIES}
        detail_rows.append({
            **pre,"row_id":origid,"eval_position":pos,"true_class":decision,
            "original_features":serialize({v:bundle.frame.iloc[origid][v] for v in bundle.features}),
            "preprocessed_features":serialize({v:row[v] for v in art.condition_columns}),
            "default_class":str(default),"matched_count":len(matched),
            "matched_rule_indices":serialize([i for i,r in enumerate(rules) if r in matched]),
            "candidate_classes":serialize(candidates),"candidate_count":len(candidates),
            "has_match":int(match_exists),"true_in_candidate":int(truth_in),"conflict":int(conflict),
            "case_type":rowclass,"policy_predictions":serialize(preds),
            "policy_correct":serialize(correct),"policy_error_type":serialize(errors),
            "class_score_details":serialize(votes)
        })
        class_records[decision].append(detail_rows[-1])
    class_rows=[]
    for label,items in sorted(class_records.items()):
        n=len(items)
        base_cls={**pre,"target_class":label,"n":n,
                  "match_n":sum(x["has_match"] for x in items),
                  "no_match_n":sum(1-x["has_match"] for x in items),
                  "candidate_hit_n":sum(x["true_in_candidate"] for x in items),
                  "conflict_n":sum(x["conflict"] for x in items)}
        base_cls.update({"coverage":base_cls["match_n"]/n,
                         "candidate_coverage":base_cls["candidate_hit_n"]/n,
                         "conflict_rate":base_cls["conflict_n"]/n})
        for p in POLICIES:
            base_cls["correct_"+p]=sum(json.loads(x["policy_correct"])[p] for x in items)
            base_cls["recall_"+p]=base_cls["correct_"+p]/n
            base_cls["winner_selection_errors_"+p]=sum(
                json.loads(x["policy_error_type"])[p]=="WINNER_SELECTION_ERROR" for x in items)
        class_rows.append(base_cls)
    model_rules=[]
    for i,r in enumerate(rules):
        model_rules.append({
            **pre,"rule_index":i,"decision":str(r.decision),
            "conditions":serialize(list(r.conditions)),"rule_key":str(r.key),
            "source":str(r.source),"source_clients":serialize(
                art.rule_provenance.get(r.key,()) if system=="FEDERATED" else ("Centralized",))
        })
    # Validate object-level statistics against the official generated NONE and 6 policy rows.
    assert len(detail_rows)==len(art.test)
    assert np.isclose(np.mean([x["has_match"] for x in detail_rows]),base["coverage"])
    assert np.isclose(np.mean([x["conflict"] for x in detail_rows]),base["conflict_case_rate"])
    assert np.isclose(np.mean([x["true_in_candidate"] for x in detail_rows]),base["true_in_candidate_rate"])
    for p in POLICIES:
        measured=np.mean([json.loads(x["policy_correct"])[p] for x in detail_rows])
        assert np.isclose(measured,outputs[p]["accuracy"]),(pre,p,measured,outputs[p]["accuracy"])
    return aggregate,detail_rows,class_rows,model_rules


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed",type=int,required=True)
    ap.add_argument("--output",default="outputs/object_audit")
    ap.add_argument("--dataset",default="ALL")
    ap.add_argument("--split",default="ALL",choices=("ALL",)+SPLITS)
    args=ap.parse_args()
    assert 1<=args.seed<=42
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    cfg["evaluation"]["seed"]=args.seed
    bundles=[b for b in pinned_bundles() if args.dataset=="ALL" or b.name==args.dataset]
    assert bundles
    aggregates=[];objects=[];classes=[];all_rules=[]
    for bundle in bundles:
        for split in SPLITS:
            if args.split!="ALL" and split!=args.split:continue
            for system,n in [("CENTRALIZED",0)]+[("FEDERATED",n) for n in (2,3,4,5)]:
                a,b,c,d=audit_block(bundle,cfg,split,system,n)
                aggregates+=a;objects+=b;classes+=c;all_rules+=d
                print("AUDIT_BLOCK_OK",args.seed,bundle.name,split,system,n,len(b),flush=True)
    group=pd.DataFrame(aggregates)
    assert not group.duplicated(list(KEY)).any()
    full=args.dataset=="ALL" and args.split=="ALL"
    if full:
        assert len(group)==210
    canon=pd.read_csv("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
    expected=canon[canon.seed==args.seed].set_index(list(KEY))
    got=group.set_index(list(KEY))
    assert set(got.index).issubset(set(expected.index)), 'Object-audit keys must exist in canonical baseline'
    for col in ("rule_count","reduct_size","coverage","conflict_case_rate",
                "true_in_candidate_rate","accuracy","balanced_accuracy","macro_f1"):
        left=pd.to_numeric(expected[col],errors="coerce").reindex(got.index).to_numpy()
        right=pd.to_numeric(got[col],errors="coerce").to_numpy()
        assert np.allclose(left,right,atol=1e-10,rtol=1e-10,equal_nan=True),(args.seed,col)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    for name,records in (("OBJECT_CASES",objects),("CLASS_COVERAGE",classes),
                         ("RULE_INVENTORY",all_rules),("AGGREGATE_RECHECK",aggregates)):
        pd.DataFrame(records).to_csv(out/f"{name}_seed{args.seed:02d}.csv",index=False)
    print("AUDIT_SEED_PASS",args.seed,"models",len(group)//7,"objects",len(objects),
          "class_rows",len(classes),"rule_rows",len(all_rules),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
