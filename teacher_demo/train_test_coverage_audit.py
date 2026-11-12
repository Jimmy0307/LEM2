"""Train-vs-test rule-set coverage audit, 42-seed Classical LEM2 holdout.

Key contract:
- Train -> build preprocessing, reduct, local/global rules once.
- SAME frozen rules and TRAIN-FITTED transform -> measure both train & held-out test.
- Test coverage is reconciled to the existing policy-independent NONE baseline.
- Never interpret Full Data resubstitution as out-of-sample evidence.
- Coverage is antecedent matching, NOT prediction accuracy or true-class-in-candidate.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from roughset.app import _run_split
from roughset.core import Rule
from roughset.evaluation import matching_rules
from teacher_demo.full_factorial_matrix import _split_raw
from teacher_demo.seed_sweep_runner import pinned_bundles

POLICY=("FIRST_MATCH",)  # shared rule set: no need to evaluate all 6 decision policies
SYSTEMS=(("CENTRALIZED",0),("FEDERATED",2),("FEDERATED",3),("FEDERATED",4),("FEDERATED",5))
BASELINE=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
IDENTITY=("dataset","seed","split_mode","system","client_count")
FIELDS=("evaluation_rows","covered_count","no_match_count",
        "conflict_case_count","true_in_candidate_count","rule_count")


def inspect_rows(data: pd.DataFrame, rules: Sequence[Rule], target: str,
                 *, default_class: Any) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return one structural summary, one row per class, and row-level match diagnostics."""
    if data.empty:
        raise ValueError("Cannot evaluate coverage on empty population")
    rows=[]
    for pos,(_,row) in enumerate(data.iterrows()):
        matches=matching_rules(row,rules)
        candidates={str(r.decision) for r in matches}
        truth=str(row[target])
        rows.append({
            "position":pos, "label":truth,
            "covered":int(bool(matches)),
            "true_candidate":int(truth in candidates),
            "conflict":int(len(candidates)>1),
            "no_match_default_correct":int(not matches and truth==str(default_class)),
            "matching_rule_count":len(matches),
        })
    df=pd.DataFrame(rows)
    total=len(df)
    summary={
        "rows":int(total),
        "covered_count":int(df.covered.sum()),
        "no_match_count":int(total-df.covered.sum()),
        "true_candidate_count":int(df.true_candidate.sum()),
        "conflict_count":int(df.conflict.sum()),
        "no_match_default_correct_count":int(df.no_match_default_correct.sum()),
        "no_match_default_accuracy":(
            float(df.no_match_default_correct.sum()/(total-df.covered.sum()))
            if total-int(df.covered.sum()) else float("nan")
        ),
        "coverage":float(df.covered.mean()),
        "true_candidate_rate":float(df.true_candidate.mean()),
        "conflict_rate":float(df.conflict.mean()),
        "avg_matched_rules":float(df.matching_rule_count.mean()),
    }
    class_rows=[]
    for label,group in df.groupby("label",sort=True):
        n=len(group)
        class_rows.append({
            "target_class":str(label),"rows":int(n),
            "covered_count":int(group.covered.sum()),"coverage":float(group.covered.mean()),
            "true_candidate_count":int(group.true_candidate.sum()),
            "true_candidate_rate":float(group.true_candidate.mean()),
            "conflict_count":int(group.conflict.sum()),"conflict_rate":float(group.conflict.mean()),
        })
    return summary,class_rows,rows


def audit_block(bundle, seed: int, system: str, clients: int, base_config: dict,
                baseline: pd.DataFrame) -> tuple[dict, list[dict]]:
    conf=deepcopy(base_config)
    conf["evaluation"]["seed"]=seed
    conf["evaluation"]["mode"]="HOLDOUT_80_20"
    conf["federated"]["partition"]="STRATIFIED"
    conf["federated"]["n_clients"]=clients
    conf["federated"]["run_client_sweep"]=False
    conf["federated"]["order_sensitivity_max_permutations"]=1
    conf["experiment"]["run_centralized"]=system=="CENTRALIZED"
    conf["experiment"]["run_federated"]=system=="FEDERATED"
    raw_train,raw_test=_split_raw(bundle,"HOLDOUT_80_20",seed,float(conf["evaluation"]["test_ratio"]))
    if set(raw_train["__row_id__"]) & set(raw_test["__row_id__"]):
        raise AssertionError("Train/Test row ID leakage")
    result=_run_split(bundle,raw_train,raw_test,conf,quiet=True,
                      prediction_policies=POLICY,fold=1)
    art=result["structural_artifact"]
    rules=art.central_rules if system=="CENTRALIZED" else art.global_rules
    default=art.central_default_class if system=="CENTRALIZED" else art.default_class
    tr,tr_classes,tr_rows=inspect_rows(art.train,rules,art.target,default_class=default)
    te,te_classes,te_rows=inspect_rows(art.test,rules,art.target,default_class=default)
    # STRICT comparison: do not silently overwrite existing frozen 8820 observations.
    mask=(baseline.dataset.eq(bundle.name)&baseline.seed.eq(seed)&
          baseline.system.eq(system)&baseline.client_count.eq(clients))
    matched=baseline.loc[mask]
    if len(matched)!=1:raise AssertionError(f"Expected one canonical NONE block, found {len(matched)}")
    source=matched.iloc[0]
    expected={
       "evaluation_rows":te["rows"],"covered_count":te["covered_count"],
       "no_match_count":te["no_match_count"],"conflict_case_count":te["conflict_count"],
       "true_in_candidate_count":te["true_candidate_count"],"rule_count":len(rules)
    }
    for k,v in expected.items():
        if int(source[k])!=v:raise AssertionError(f"Canonical mismatch {bundle.name}/{seed}/{system}/{clients}/{k}: {source[k]} != {v}")
    if not np.isclose(float(source.coverage),te["coverage"],atol=1e-10,rtol=1e-10):
        raise AssertionError("Test coverage mismatch to frozen baseline")
    if not np.isclose(float(source.conflict_case_rate),te["conflict_rate"],atol=1e-10,rtol=1e-10):
        raise AssertionError("Conflict rate mismatch to frozen baseline")
    if not np.isclose(float(source.true_in_candidate_rate),te["true_candidate_rate"],atol=1e-10,rtol=1e-10):
        raise AssertionError("Candidate rate mismatch to frozen baseline")

    # Diagnostic of *preprocessed condition signatures* unseen in training.
    # Does not use test labels or modify the matching rules.
    columns=list(art.condition_columns)
    def signature(df):
        return [tuple(str(x) for x in row) for row in df[columns].itertuples(index=False,name=None)]
    tr_sig=set(signature(art.train))
    te_sig=signature(art.test)
    unseen=np.asarray([x not in tr_sig for x in te_sig],dtype=bool)
    test_covered=np.asarray([r["covered"] for r in te_rows],dtype=bool)
    labels=sorted(set(x["target_class"] for x in tr_classes+te_classes))
    tr_map={x["target_class"]:x for x in tr_classes}
    te_map={x["target_class"]:x for x in te_classes}
    class_rows=[]
    identity={"dataset":bundle.name,"seed":int(seed),"split_mode":"HOLDOUT_80_20",
              "system":system,"client_count":int(clients)}
    for label in labels:
        x=tr_map.get(label);y=te_map.get(label)
        if x is None or y is None:
            raise AssertionError(f"Expected class in both stratified train/test: {label}")
        class_rows.append({
          **identity,"target_class":label,
          "train_rows":x["rows"],"test_rows":y["rows"],
          "train_covered_count":x["covered_count"],
          "test_covered_count":y["covered_count"],
          "train_coverage":x["coverage"],"test_coverage":y["coverage"],
          "coverage_gap_pp":100*(y["coverage"]-x["coverage"]),
          "train_true_candidate_rate":x["true_candidate_rate"],
          "test_true_candidate_rate":y["true_candidate_rate"],
          "candidate_gap_pp":100*(y["true_candidate_rate"]-x["true_candidate_rate"]),
          "train_conflict_rate":x["conflict_rate"],
          "test_conflict_rate":y["conflict_rate"],
        })
    record={
      **identity,"method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2","source":"pinned UCI 12,19,44",
      "rule_count":len(rules),
      "train_rows":tr["rows"],"test_rows":te["rows"],
      "train_covered_count":tr["covered_count"],
      "test_covered_count":te["covered_count"],
      "train_coverage":tr["coverage"],"test_coverage":te["coverage"],
      "coverage_gap_pp":100*(te["coverage"]-tr["coverage"]),
      "coverage_deficit_pp":100*max(tr["coverage"]-te["coverage"],0.0),
      "train_no_match_count":tr["no_match_count"],
      "test_no_match_count":te["no_match_count"],
      "train_true_candidate_count":tr["true_candidate_count"],
      "test_true_candidate_count":te["true_candidate_count"],
      "train_true_candidate_rate":tr["true_candidate_rate"],
      "test_true_candidate_rate":te["true_candidate_rate"],
      "candidate_gap_pp":100*(te["true_candidate_rate"]-tr["true_candidate_rate"]),
      "train_conflict_count":tr["conflict_count"],
      "test_conflict_count":te["conflict_count"],
      "train_conflict_rate":tr["conflict_rate"],
      "test_conflict_rate":te["conflict_rate"],
      "conflict_gap_pp":100*(te["conflict_rate"]-tr["conflict_rate"]),
      "train_fallback_correct_count":tr["no_match_default_correct_count"],
      "test_fallback_correct_count":te["no_match_default_correct_count"],
      "test_fallback_accuracy":te["no_match_default_accuracy"],
      "test_unseen_signature_count":int(unseen.sum()),
      "test_unseen_signature_rate":float(unseen.mean()),
      "test_coverage_seen_signature":(
        float(test_covered[~unseen].mean()) if (~unseen).any() else float("nan")),
      "test_coverage_unseen_signature":(
        float(test_covered[unseen].mean()) if unseen.any() else float("nan")),
      "validation":"MATCHES_CANONICAL_NONE"
    }
    print("COVERAGE_PAIR_PASS",bundle.name,"seed",seed,system,clients,
          "train",tr["coverage"],"test",te["coverage"],"gap_pp",record["coverage_gap_pp"],flush=True)
    return record,class_rows


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed",required=True,type=int)
    ap.add_argument("--output",default="outputs/train_test_coverage")
    args=ap.parse_args()
    if not 1<=args.seed<=42:raise ValueError("Seed must be 1..42")
    base_config=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    canonical=pd.read_csv(BASELINE)
    assert len(canonical)==8820
    canonical=canonical[(canonical.split_mode=="HOLDOUT_80_20")&
                        (canonical.selection_policy=="NONE")]
    assert len(canonical)==42*3*5
    records=[];class_records=[]
    for bundle in pinned_bundles():
        for system,clients in SYSTEMS:
            record,classes=audit_block(bundle,args.seed,system,clients,base_config,canonical)
            records.append(record);class_records.extend(classes)
    assert len(records)==15
    assert len({(r["dataset"],r["seed"],r["system"],r["client_count"]) for r in records})==15
    target=Path(args.output);target.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(records).to_csv(target/f"COVERAGE_PAIRS_seed{args.seed:02d}.csv",index=False)
    pd.DataFrame(class_records).to_csv(target/f"COVERAGE_BY_CLASS_seed{args.seed:02d}.csv",index=False)
    print("COVERAGE_SEED_REPLAY_PASS",args.seed,len(records),len(class_records),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
