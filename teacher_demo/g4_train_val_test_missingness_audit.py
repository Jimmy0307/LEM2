"""Reproducible 20-source G4 split coverage / prepared-source missingness audit.

Each source: newly re-fit ORIGINAL frozen reduct+LEM2 for seeds11,23 and
IID/nonIID alpha .5/.1. Compare output Val and Test exact coverage/conflict
against PREVIOUS G4 source results (fail closed). Evaluate matching SAME
fitted rules against Development, Validation, Test -- never refit per split.
Never use held-out Test labels in fitting or routing. Test true labels are
read only for diagnostic Candidate Correct and class coverage after fit.
Prepared CSV null/sentinel is NOT original UCI raw-source missingness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.app import _run_split
from roughset.evaluation import matching_rules
from roughset.preprocessing import apply_preprocessor
from roughset.splitting import stratified_train_test_split
from teacher_demo.full_factorial_matrix import _split_raw
from teacher_demo.conflict_aware_coverage_pilot import load_bundle
from teacher_demo.g4_rule_conflict_router import SEEDS,REGIMES,rule_buckets
from teacher_demo.public_20_registry import REGISTRY

PREP=Path("docs/research/public_datasets_20")
G4=Path("docs/research/teacher_dashboard/data/G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv")
RAW_MARKERS={"","?","na","n/a","null","none","nan","<na>","__missing_feature__","__missing__"}
UNKNOWN_MARKERS={"unknown","unk","not known"}
EPS=3e-8

def profile(name):
    cfg=REGISTRY[name]
    path=PREP/f"{name}_prepared.csv"
    frame=pd.read_csv(path,dtype="string",keep_default_na=False)
    assert "class"==frame.columns[-1]
    cols=list(frame.columns[:-1])
    declared=cfg["feature_mode"]
    cont=list(cfg.get("continuous_columns",[]) if declared=="EXPLICIT_MIXED" else
              cols if declared=="ALL_CONTINUOUS" else [])
    cat=[c for c in cols if c not in cont]
    null_token={};unknown={};empty={}
    for k in cols:
        strings=frame[k].fillna("").astype(str).str.strip().str.lower()
        null_token[k]=int(strings.isin(RAW_MARKERS).sum())
        unknown[k]=int(strings.isin(UNKNOWN_MARKERS).sum())
        empty[k]=int(strings.eq("").sum())
    # Published prepared source is the immediately consumed G4 input, NOT raw UCI archive.
    return {
     "dataset":name,
     "feature_mode":declared,"source_domain":cfg["domain"],"research_trait":cfg["research_trait"],
     "used_rows":len(frame),"n_features":len(cols),
     "n_numeric_continuous":len(cont),"n_declared_categorical":len(cat),
     "continuous_feature_names":";".join(cont),
     "categorical_feature_names":";".join(cat),
     "prepared_null_sentinel_cells":sum(null_token.values()),
     "prepared_unknown_literal_cells":sum(unknown.values()),
     "prepared_empty_cells":sum(empty.values()),
     "prepared_null_sentinel_columns":";".join(k for k,v in null_token.items() if v),
     "prepared_unknown_literal_columns":";".join(k for k,v in unknown.items() if v),
     "prepared_feature_cells":len(frame)*len(cols),
     "prepared_lexical_markers_json":json.dumps({"null_sentinel":null_token,"unknown_literal":unknown},sort_keys=True),
     "prepared_file_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
     "raw_source_missingness_status":"NOT_MEASURED_FROM_RAW_UCI",
     "warning":"Unknown is a literal category and is not necessarily missing; empty/sentinels may be imputed or preserved at acquisition."
    }

def audit_bucket(frame,rules,target):
    b,candidates,covered,conflict=rule_buckets(frame,rules)
    truth=frame[target].astype(str).to_numpy()
    candidate=np.asarray([y in cand for y,cand in zip(truth,candidates)],dtype=bool)
    row_count=len(frame)
    assert row_count>0 and np.all(candidate<=covered)
    class_counts=frame[target].astype(str).value_counts().to_dict()
    class_cov={c:{"rows":int(np.sum(truth==str(c))),
                  "exact_cov_pct":100*float(np.mean(covered[truth==str(c)]))} for c in sorted(class_counts)}
    return {"rows":row_count,"exact_coverage_pct":100*float(covered.mean()),
      "no_match_pct":100*float((~covered).mean()),
      "conflict_pct":100*float(conflict.mean()),
      "candidate_correct_pct":100*float(candidate.mean()),
      "matched_without_true_candidate_pct":100*float((covered&~candidate).mean()),
      "class_counts_json":json.dumps(class_counts,sort_keys=True),
      "coverage_by_class_json":json.dumps(class_cov,sort_keys=True)}

def run(name,output):
    meta=profile(name)
    bundle,sha=load_bundle(name)
    assert sha==meta["prepared_file_sha256"]
    baseline=pd.read_csv(G4)
    baseline=baseline[(baseline.dataset==name)&baseline.method.eq("CONFLICT_BUCKET_ROUTER_V1")]
    assert len(baseline)==6,(name,len(baseline))
    results=[]
    for seed in SEEDS:
      train,test=_split_raw(bundle,"HOLDOUT_80_20",seed,.20)
      dev,val=stratified_train_test_split(train,bundle.target,test_ratio=.2,seed=1000+seed)
      ids=[set(x["__row_id__"].astype(int)) for x in (dev,val,test)]
      assert not(ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2]),"LEAKAGE"
      for regime,(strategy,alpha) in REGIMES.items():
        cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
        cfg["evaluation"].update(mode="HOLDOUT",seed=seed)
        cfg["experiment"].update(run_centralized=False,run_federated=True)
        cfg["federated"].update(n_clients=3,partition=strategy,
             dirichlet_alpha=alpha,run_client_sweep=False,
             order_sensitivity_max_permutations=1)
        fit=_run_split(bundle,dev,val,cfg,quiet=True,prediction_policies=("GLOBAL_STRENGTH",),fold=1)
        art=fit["structural_artifact"]
        outer=apply_preprocessor(test,fit["preprocessor"],bundle.target)
        tr=audit_bucket(art.train,art.global_rules,art.target)
        va=audit_bucket(art.test,art.global_rules,art.target)
        te=audit_bucket(outer,art.global_rules,art.target)
        old=baseline[(baseline.seed==seed)&baseline.scenario.eq(regime)]
        assert len(old)==1
        old=old.iloc[0]
        assert [tr["rows"],va["rows"],te["rows"]]==[int(old.dev_rows),int(old.inner_rows),int(old.outer_rows)]
        assert abs(va["exact_coverage_pct"]-100*old.inner_validation_coverage)<EPS,(name,seed,regime,"val coverage")
        assert abs(te["exact_coverage_pct"]-100*old.outer_test_coverage)<EPS,(name,seed,regime,"test coverage")
        assert abs(va["conflict_pct"]-100*old.inner_validation_conflict)<EPS,(name,seed,regime,"val conflict")
        assert abs(te["conflict_pct"]-100*old.outer_test_conflict)<EPS,(name,seed,regime,"test conflict")
        assert abs(te["candidate_correct_pct"]-100*old.outer_test_candidate_correct)<EPS
        ncont=sum(str(x).endswith("_bin") for x in fit["preprocessor"]["condition_columns"])
        rec={"dataset":name,"seed":seed,"scenario":regime,
             "source_sha256":sha,"feature_mode":meta["feature_mode"],
             "used_rows":len(bundle.frame),"n_features":meta["n_features"],
             "n_declared_continuous":meta["n_numeric_continuous"],
             "n_declared_categorical":meta["n_declared_categorical"],
             "n_discretized_continuous":ncont,
             "n_rules":len(art.global_rules),"raw_train_rows":len(dev)+len(val),
             "dev_rows":tr["rows"],"validation_rows":va["rows"],"test_rows":te["rows"],
             "dev_coverage_pct":tr["exact_coverage_pct"],
             "val_coverage_pct":va["exact_coverage_pct"],
             "test_coverage_pct":te["exact_coverage_pct"],
             "dev_no_match_pct":tr["no_match_pct"],
             "val_no_match_pct":va["no_match_pct"],
             "test_no_match_pct":te["no_match_pct"],
             "dev_conflict_pct":tr["conflict_pct"],
             "val_conflict_pct":va["conflict_pct"],
             "test_conflict_pct":te["conflict_pct"],
             "dev_candidate_correct_pct":tr["candidate_correct_pct"],
             "val_candidate_correct_pct":va["candidate_correct_pct"],
             "test_candidate_correct_pct":te["candidate_correct_pct"],
             "val_covered_wrong_candidate_pct":va["matched_without_true_candidate_pct"],
             "test_covered_wrong_candidate_pct":te["matched_without_true_candidate_pct"],
             "train_minus_test_cov_pp":tr["exact_coverage_pct"]-te["exact_coverage_pct"],
             "val_minus_test_cov_pp":va["exact_coverage_pct"]-te["exact_coverage_pct"],
             "val_minus_test_conflict_pp":va["conflict_pct"]-te["conflict_pct"],
             "dev_class_counts_json":tr["class_counts_json"],
             "val_class_counts_json":va["class_counts_json"],
             "test_class_counts_json":te["class_counts_json"],
             "dev_class_coverage_json":tr["coverage_by_class_json"],
             "test_class_coverage_json":te["coverage_by_class_json"],
             "prepared_null_sentinel_cells":meta["prepared_null_sentinel_cells"],
             "prepared_unknown_literal_cells":meta["prepared_unknown_literal_cells"],
             "source_raw_missing_not_measured":True,
             "validation_test_matches_published_g4":True,
             "method":"SAME_FROZEN_CLASSICAL_LEM2_TRAIN_VAL_TEST_EXACT_MATCH"}
        results.append(rec)
        print("G4_COVERAGE_MATCHED_PUBLISHED_PASS",name,seed,regime,
             round(tr["exact_coverage_pct"],2),round(va["exact_coverage_pct"],2),
             round(te["exact_coverage_pct"],2),"conf",round(te["conflict_pct"],2),flush=True)
    assert len(results)==6
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(results).to_csv(out/f"COVERAGE_G4_{name}.csv",index=False)
    (out/f"PROFILE_G4_{name}.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
    print("G4_SPLIT_AND_PREPARED_MISSINGNESS_SOURCE_AUDIT_PASS",name,flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=sorted(REGISTRY),required=True)
    p.add_argument("--output",default="outputs/g4_type_coverage")
    a=p.parse_args();run(a.dataset,a.output)
if __name__=="__main__":main()
