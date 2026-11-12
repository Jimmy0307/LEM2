"""20 new public UCI domain stress studies: exact Classical LEM2 + train-only supplements.

One initial seed (42) per dataset is FEASIBILITY, never 42-seed inference.
Two comparable architectures Centralized and Federated C3.
Five/six policy comparison uses same 80/20 HOLDOUT rule set.
Supplementary rules generalize one IF condition only, based on TRAIN.
The same threshold is PREDECLARED: min support 5, purity>=.90;
recompute train/test coverage against exact same original rule system.
This is author-defined simplified supplement, NOT original MLEM2 or VC-DomLEM.
"""
from __future__ import annotations
import argparse
import json
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.app import _run_split
from roughset.evaluation import matching_rules
from teacher_demo.extreme_dataset_runner import read_external
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.full_factorial_matrix import POLICIES,_base_row,_none_row,_policy_row,_split_raw
from teacher_demo.supplementary_rule_coverage_pilot import generate,extend_predict

SEED=42
STRUCTURES=(("CENTRALIZED",0),("FEDERATED",3))
PURITY=0.90
SUPPORT=5
MAX_PROPOSAL_RULES=240

def get_coverage(data,rules):
    if len(data)<1:raise ValueError("empty evaluation set")
    return float(np.mean([bool(matching_rules(row,rules)) for _,row in data.iterrows()]))

def run(dataset,output):
    if dataset not in REGISTRY:raise ValueError(f"dataset not in NEW 20 public registry: {dataset}")
    bundle,profile=read_external(dataset)
    raw_train,raw_test=_split_raw(bundle,"HOLDOUT_80_20",SEED,.2)
    config=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    config["evaluation"]["seed"]=SEED
    config["evaluation"]["mode"]="HOLDOUT_80_20"
    config["federated"]["partition"]="STRATIFIED"
    config["federated"]["run_client_sweep"]=False
    config["federated"]["order_sensitivity_max_permutations"]=1
    raw_metrics=[];supp_metrics=[]
    for architecture,client_count in STRUCTURES:
        x=deepcopy(config)
        x["experiment"]["run_centralized"]=architecture=="CENTRALIZED"
        x["experiment"]["run_federated"]=architecture=="FEDERATED"
        x["federated"]["n_clients"]=client_count
        result=_run_split(bundle,raw_train,raw_test,x,quiet=True,prediction_policies=POLICIES,fold=1)
        art=result["structural_artifact"]
        rules=art.central_rules if architecture=="CENTRALIZED" else art.global_rules
        train_cov=get_coverage(art.train,rules)
        test_cov=get_coverage(art.test,rules)
        baseline={
            **_base_row(bundle=bundle,split_mode="HOLDOUT_80_20",system=architecture,
                        client_count=client_count,artifact=art),
            "public_dataset_key":dataset,
            "method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
            "pilot":"NEW_20_SEED42",
            "original_source_rows":profile["source_rows"],
            "used_rows":profile["used_rows"],
            "selected_features":profile["used_feature_count"],
            "source_sha256":profile["sha256_prepared_csv"],
            "train_coverage_pct":100*train_cov,
            "test_coverage_pct":100*test_cov,
            "train_test_gap_pp":100*(test_cov-train_cov),
            "class_count":len(profile["class_counts"]),
        }
        raw_metrics.append(_none_row(baseline))
        for policy in POLICIES:
            key="centralized" if architecture=="CENTRALIZED" else "federated"
            pred=result["policy_results"][policy][key]
            if pred is None:raise RuntimeError("policy output missing: "+policy)
            raw_metrics.append(_policy_row(baseline,policy,pred))
        assert len(raw_metrics)==(7 if architecture=="CENTRALIZED" else 14)
        key="centralized" if architecture=="CENTRALIZED" else "federated"
        original=result["policy_results"]["GLOBAL_STRENGTH"][key]["predictions"]
        # Max proposal source rules caps runtime on high rule-count datasets;
        # full original set still evaluates exact model / base coverage.
        subset=list(rules[:MAX_PROPOSAL_RULES])
        supplement,count=generate(art.train,subset,art.target,
                                  min_support=SUPPORT,min_purity=PURITY,max_candidates=80)
        new_test=extend_predict(art.test,rules,supplement,original,
                                art.central_default_class if architecture=="CENTRALIZED" else art.default_class,
                                art.target)
        # For TRAIN improved coverage we only reuse matching part of the rule system;
        # predictions are placeholders, not interpreted as train classification.
        train_dummy=[str(art.central_default_class if architecture=="CENTRALIZED" else art.default_class)]*len(art.train)
        new_train=extend_predict(art.train,rules,supplement,train_dummy,
                                 art.central_default_class if architecture=="CENTRALIZED" else art.default_class,
                                 art.target)
        assert np.isclose(new_test["original_exact_coverage"],test_cov)
        assert np.isclose(new_train["original_exact_coverage"],train_cov)
        supp_metrics.append({
          "dataset":dataset,"seed":SEED,"system":architecture,"client_count":client_count,
          "method":"ONE_ANTECEDENT_DROP_TRAIN_ONLY_PURITY90_PILOT",
          "baseline_policy":"GLOBAL_STRENGTH",
          "selected_feature_count":len(bundle.features),
          "original_rules":len(rules),"max_proposal_rules":MAX_PROPOSAL_RULES,
          "source_rules_considered":len(subset),
          "supplement_candidates_proposed":count,
          "supplement_rules_selected":len(supplement),
          "purity":PURITY,"min_support":SUPPORT,"proposal_budget":80,
          "train_rows":len(art.train),"test_rows":len(art.test),
          "baseline_train_coverage_pct":100*train_cov,
          "baseline_test_coverage_pct":100*test_cov,
          "augmented_train_coverage_pct":100*new_train["augmented_coverage"],
          "augmented_test_coverage_pct":100*new_test["augmented_coverage"],
          "train_coverage_gain_pp":new_train["added_coverage_pp"],
          "test_coverage_gain_pp":new_test["added_coverage_pp"],
          "baseline_accuracy_pct":100*new_test["baseline_accuracy"],
          "augmented_accuracy_pct":100*new_test["new_accuracy"],
          "accuracy_gain_pp":new_test["accuracy_gain_pp"],
          "baseline_balanced_accuracy_pct":100*new_test["baseline_balanced_accuracy"],
          "augmented_balanced_accuracy_pct":100*new_test["new_balanced_accuracy"],
          "balanced_accuracy_gain_pp":new_test["balanced_accuracy_gain_pp"],
          "rescued_test_objects":new_test["rescued_count"],
          "rescued_test_correct":new_test["rescued_correct"],
          "rescued_fallback_correct":new_test["rescued_original_fallback_correct"],
          "new_conflict_in_rescued":new_test["rescued_new_conflict_count"],
          "remaining_unmatched_test_objects":new_test["remaining_unmatched_count"],
          "source_sha256":profile["sha256_prepared_csv"],
          "status":"EXPLORATORY_1_SEED_NOT_VALIDATED"
        })
        print("PUBLIC20_ARCH_PASS",dataset,architecture,client_count,
              "original",len(rules),"train/test",round(train_cov,4),round(test_cov,4),
              "new",len(supplement),round(new_test["augmented_coverage"],4),flush=True)
    if len(raw_metrics)!=14 or len(supp_metrics)!=2:raise AssertionError("14 baseline + 2 augment")
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    bundle.frame.to_csv(dest/f"PUBLIC20_DATA_{dataset}.csv",index=False)
    pd.DataFrame(raw_metrics).to_csv(dest/f"PUBLIC20_BASE_{dataset}.csv",index=False)
    pd.DataFrame(supp_metrics).to_csv(dest/f"PUBLIC20_SUPPLEMENT_{dataset}.csv",index=False)
    profile.update({"seed":SEED,"experiment_family":"PUBLIC_20_EXTERNAL",
      "source":"UCI repository via ucimlrepo","method":"Classical reduct + LEM2",
      "original_source_is_full_model_training":False,
      "architecture_count":2,"policy_count":6,"baseline_rows":14,
      "supplement_rows":2,"split":"HOLDOUT_80_20",
      "research_limits":"one fixed seed; up to 6 features; stratified source subsample; no external-validity claims"})
    (dest/f"PUBLIC20_PROFILE_{dataset}.json").write_text(
        json.dumps(profile,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PUBLIC20_DATASET_PASS",dataset,"source_rows",profile["source_rows"],
          "used_rows",profile["used_rows"],"classes",len(profile["class_counts"]),flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",required=True,choices=sorted(REGISTRY))
    ap.add_argument("--output",default="outputs/public_20")
    args=ap.parse_args()
    run(args.dataset,args.output)

if __name__=="__main__":main()
