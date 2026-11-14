"""Cross-domain, nonleaky six-policy selection evaluation.

60 jobs: 20 UCI datasets × seeds 1,7,42, Centralized + Fed C3,
one 64/16/20 nested split per dataset/seed. Six policy scores on the
inner validation + once on outer test. No outer test scores are used to
choose any executable policy.

Selector portfolio:
 LOCAL_VALIDATION_BEST: best inner validation objective same dataset.
 LODO_GLOBAL_VAL: globally best on all OTHER 19 domains' validation.
 LODO_META_KNN_5: nearest five OTHER domains by train+validation meta-features,
                  choose highest weighted OTHER-domain validation performance.
 FIXED policies: all six for comparison.
 TEST_ORACLE_DIAGNOSTIC: best outer test objective; *unachievable upper bound*.
 Cross-domain meta hyperparameters fixed in source (K=5, features, tie order).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from teacher_demo.full_factorial_matrix import POLICIES
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.adaptive_six_policy_runner import SEEDS,OBJECTIVES,POLICY_ORDER

IN=Path("adaptive_six_incoming")
OUT=Path("docs/research/teacher_dashboard/data")
META_FEATURES=(
 "log_dev_rows","num_features","continuous_ratio","num_classes",
 "majority_share","minority_share","normalized_class_entropy",
 "mean_feature_cardinality_fraction","log_rule_count",
 "mean_rule_condition_count","num_clients","client_row_cv",
 "client_label_js_divergence","client_missing_class_fraction",
 "inner_rule_coverage","inner_rule_conflict",
 "inner_correct_candidate_coverage","inner_mean_matching_rules",
)
STRATEGIES=tuple("FIXED_"+p for p in POLICIES)+(
 "LOCAL_VALIDATION_BEST","LODO_GLOBAL_VAL","LODO_META_KNN_5","TEST_ORACLE_DIAGNOSTIC")
K=5

def require(ok,reason):
    if not bool(ok):raise AssertionError(reason)

def validate_one(dataset,seed):
    path=IN/f"ADAPTIVE_SIX_{dataset}_seed{seed}.csv"
    require(path.exists(),"Missing real UCI results "+str(path))
    x=pd.read_csv(path)
    require(len(x)==12,"expected two architectures x six policies for "+path.name)
    require(set(x.dataset)=={dataset} and set(x.seed)=={seed},"wrong identity")
    require(set(x.client_count)=={0,3},"wrong clients")
    require(set(x.policy)==set(POLICIES),"wrong policy vocabulary")
    require(set(x.protocol)=={"NESTED_64_16_20_NO_REFIT"},"wrong train/val/test protocol")
    require(set(x.method)=={"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2"},"wrong induction")
    require(x.groupby("client_count").size().eq(6).all(),"six comparisons per frozen ruleset")
    require(not x.duplicated(["client_count","policy"]).any(),"duplicated policy experiment")
    manifest=json.loads((OUT/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    source=next(m for m in manifest["datasets"] if m["key"]==dataset)
    require(source["status"]=="PASS_ONE_SEED","unverified public source")
    require(set(x.source_sha256)=={source["published_file_sha256"]},"input hash mismatch")
    require(x.total_rows.eq(source["used_rows"]).all(),"sample size changed")
    require(x.development_rows.add(x.inner_validation_rows).add(x.outer_test_rows).eq(x.total_rows).all(),
            "split conservation broken")
    require(x[["development_rows","inner_validation_rows","outer_test_rows"]].gt(0).all().all(),"empty sample")
    diag=x[["inner_rule_coverage","inner_rule_conflict","inner_correct_candidate_coverage"]]
    require(((diag>=0)&(diag<=1)).all().all(),
            "incorrect validation diagnostic range")
    for obj in OBJECTIVES:
        require(x["inner_val_"+obj].between(0,1).all(),"bad inner objective")
        require(x["outer_test_"+obj].between(0,1).all(),"bad outer objective")
        for _,g in x.groupby("client_count"):
            require(g["is_inner_best_"+obj].sum()==1,"local policy selector did not return unique winner")
            p=max(POLICY_ORDER,key=lambda p:(float(g.loc[g.policy.eq(p),"inner_val_"+obj].iloc[0]),-POLICY_ORDER.index(p)))
            require(str(g.loc[g["is_inner_best_"+obj].eq(1),"policy"].iloc[0])==p,
                    "validation winner incorrect")
    for c,g in x.groupby("client_count"):
        for col in META_FEATURES+("rule_count","inner_validation_rows","development_rows","outer_test_rows"):
            require(np.allclose(g[col],g[col].iloc[0],equal_nan=True),"frozen feature differs across policy: "+col)
        require(g.outer_test_exact_coverage.max()-g.outer_test_exact_coverage.min()<1e-10,
                "six strategies changed frozen exact rule coverage")
        require(g.inner_rule_conflict.iloc[0]<=g.inner_rule_coverage.iloc[0]+1e-9,
                "conflict > coverage")
    return x

def choose(score):
    return max(POLICY_ORDER,key=lambda p:(float(score[p]),-POLICY_ORDER.index(p)))

def global_validation_selector(target,reference,obj):
    # Average across each OTHER dataset first, then equal-weight domains.
    train=reference.loc[reference.client_count.eq(target.client_count)]
    # Each of the 19 reference datasets contributes one mean per policy.
    v=train.groupby(["dataset","policy"])["inner_val_"+obj].mean().unstack("policy")
    require(len(v)==19 and v.shape[1]==6,"global reference must contain 19 full domains")
    return choose(v.mean(axis=0)), v

def knn_selector(target,reference,obj):
    # Source-level, not seed-level kNN; each other dataset carries equal
    # weight after aggregation of 3 seeds. Fit scaler only to other 19 domains.
    train=reference.loc[reference.client_count.eq(target.client_count)]
    features=train.groupby("dataset")[list(META_FEATURES)].mean()
    labels=train.groupby(["dataset","policy"])["inner_val_"+obj].mean().unstack("policy")
    require(len(features)==19 and labels.shape==(19,6),"LODO must exclude target dataset")
    require(target.dataset not in features.index,"Test domain leaked into meta reference")
    mu=features.mean(axis=0)
    sd=features.std(axis=0,ddof=0).replace(0,1).fillna(1)
    m=features.fillna(mu)
    # Choose only defined train/validation meta features, no Test labels
    centered=(m-mu)/sd
    x=(pd.Series({k:getattr(target,k) for k in META_FEATURES}).fillna(mu)-mu)/sd
    dist=np.sqrt(((centered-x)**2).sum(axis=1))
    nearest=dist.sort_values(kind="stable").head(K)
    weights=1/(nearest.to_numpy(dtype=float)+.05)
    weights=weights/weights.sum()
    expected=(labels.loc[nearest.index].T @ weights)
    return choose(expected),list(nearest.index),expected.to_dict()

def select_for_matchups(data):
    out=[]
    # Every target uses every OTHER DOMAIN only; same dataset other seeds forbidden.
    for (ds,seed,client),block in data.groupby(["dataset","seed","client_count"],sort=True):
        require(len(block)==6,"missing target six strategies")
        g=block.set_index("policy")
        target=block.iloc[0]
        other=data[data.dataset.ne(ds)]
        require(other.dataset.nunique()==19,"not leave-one-dataset-out")
        assert not(other.dataset.eq(ds)).any()
        for objective in OBJECTIVES:
            val="inner_val_"+objective;te="outer_test_"+objective
            val_score={p:float(g.loc[p,val]) for p in POLICIES}
            test_score={p:float(g.loc[p,te]) for p in POLICIES}
            local=choose(val_score)
            global_best,history=global_validation_selector(target,other,objective)
            knn,neighbors,prediction=knn_selector(target,other,objective)
            # Diagnostic ceiling is calculated AFTER all selectable outputs
            # have been fixed, and must never train the meta learner.
            oracle=choose(test_score)
            choices={"FIXED_"+p:p for p in POLICIES}
            choices.update(LOCAL_VALIDATION_BEST=local,LODO_GLOBAL_VAL=global_best,
                           LODO_META_KNN_5=knn,TEST_ORACLE_DIAGNOSTIC=oracle)
            for method,policy in choices.items():
                out.append({
                   "dataset":ds,"seed":seed,"client_count":client,
                   "architecture":"CENTRALIZED" if client==0 else "FEDERATED_C3",
                   "objective":objective,"method":method,"policy":policy,
                   "outer_test_score_pct":100*test_score[policy],
                   "inner_val_score_pct":100*val_score[policy],
                   "oracle_test_score_pct":100*test_score[oracle],
                   "test_regret_pp":100*(test_score[oracle]-test_score[policy]),
                   "meta_reference_dataset_count":19 if method.startswith("LODO") else 0,
                   "meta_features_only_train_or_inner_val":True,
                   "meta_reference_excludes_own_dataset":True,
                   "diagnostic_test_oracle_not_deployable":method=="TEST_ORACLE_DIAGNOSTIC",
                   "nearest_meta_datasets":";".join(neighbors) if method=="LODO_META_KNN_5" else "",
                   "inner_val_margin_pp":100*(max(val_score.values())-sorted(val_score.values())[-2]),
                   "test_coverage_pct":100*float(target.outer_test_exact_coverage),
                   "validation_conflict_pct":100*float(target.inner_rule_conflict)
                })
    df=pd.DataFrame(out)
    require(len(df)==20*len(SEEDS)*2*len(OBJECTIVES)*len(STRATEGIES),"selection count mismatch")
    require(df.groupby(["dataset","seed","client_count","objective"]).size().eq(len(STRATEGIES)).all(),
            "incomplete methods for target ruleset")
    require(df.test_regret_pp.ge(-1e-7).all(),"Oracle upper bound breached")
    return df

def dataset_bootstrap_ci(pair,focus,baseline,seed=20261114,reps=1000):
    subset=pair[(pair.method==focus)|(pair.method==baseline)]
    pivot=subset.pivot_table(index=["dataset","seed","client_count"],
                             columns="method",values="outer_test_score_pct")
    diffs=(pivot[focus]-pivot[baseline]).groupby("dataset").mean()
    arr=diffs.to_numpy(dtype=float)
    assert len(arr)==20
    rng=np.random.default_rng(seed)
    draws=rng.integers(0,len(arr),size=(reps,len(arr)))
    values=arr[draws].mean(axis=1)
    return {"mean_gain_pp":float(arr.mean()),
            "ci95_low_pp":float(np.quantile(values,.025)),
            "ci95_high_pp":float(np.quantile(values,.975)),
            "n_independent_dataset_clusters":20,
            "dataset_improved":int((arr>1e-10).sum()),
            "dataset_harmed":int((arr < -1e-10).sum()),
            "dataset_tied":int((abs(arr)<=1e-10).sum())}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    list_of_runs=[validate_one(ds,s) for ds in sorted(REGISTRY) for s in SEEDS]
    data=pd.concat(list_of_runs,ignore_index=True)
    require(len(data)==20*len(SEEDS)*2*6,"720 six-policy rows")
    require(data.groupby(["dataset","seed","client_count"]).size().eq(6).all(),"Missing frozen configs")
    data.to_csv(OUT/"ADAPTIVE_SIX_20_ALL_POLICIES.csv",index=False,float_format="%.10f")
    selections=select_for_matchups(data)
    selections.to_csv(OUT/"ADAPTIVE_SIX_20_SELECTORS.csv",index=False,float_format="%.10f")
    summary=(selections.groupby(["objective","method"],sort=True)
             .agg(comparisons=("dataset","size"),datasets=("dataset","nunique"),
                  mean_outer_test_pct=("outer_test_score_pct","mean"),
                  mean_regret_pp=("test_regret_pp","mean"),
                  sd_outer_test_pct=("outer_test_score_pct","std"),
                  mean_validation_conflict_pct=("validation_conflict_pct","mean"),
                  mean_test_coverage_pct=("test_coverage_pct","mean")).reset_index())
    require(summary.comparisons.eq(120).all(),"must be 120 paired tests per objective/method")
    summary.to_csv(OUT/"ADAPTIVE_SIX_20_SUMMARY.csv",index=False,float_format="%.10f")
    ci=[]
    for obj in OBJECTIVES:
      subset=selections[selections.objective.eq(obj)]
      for meta in ("LOCAL_VALIDATION_BEST","LODO_GLOBAL_VAL","LODO_META_KNN_5"):
        for ref in ("FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING","FIXED_STANDARD_VOTING"):
          ci.append({"objective":obj,"candidate":meta,"benchmark":ref,
                     **dataset_bootstrap_ci(subset,meta,ref)})
    pd.DataFrame(ci).to_csv(OUT/"ADAPTIVE_SIX_20_DATASET_BOOTSTRAP.csv",index=False,float_format="%.10f")
    simple=summary[summary.objective.eq("balanced_accuracy")].set_index("method")
    receipt={
       "status":"VALIDATED_20_DOMAINS_3_SEEDS_6_POLICIES",
       "dataset_count":20,"seeds":list(SEEDS),"architectures":["CENTRALIZED","FEDERATED_C3"],
       "frozen_rulesets":120,"policy_eval_rows":len(data),
       "outer_selector_evaluations":len(selections),
       "objectives":list(OBJECTIVES),"strategy_count":len(STRATEGIES),
       "protocol":{"train_fit":"64% induction","inner_select":"16% validation",
                   "untouched_outer_test":"20% held-out",
                   "no_outer_refit":True,
                   "cross_domain":"Leave one WHOLE dataset out, ALL seeds and architectures",
                   "meta_training_labels":"other 19 domains' validation scores ONLY",
                   "meta_features":list(META_FEATURES),
                   "meta_model":"K=5 inverse Euclidean distance, reference-only z-score with 0.05 regularizer",
                   "meta_hyperparameters_tuned_on_test":False,
                   "local_policy":"best inner validation performance; deterministic tie order",
                   "cross_domain_fixed_baseline":"best 19-domain validation mean, no held-out domain",
                   "oracle":"Best outer test, DIAGNOSTIC ONLY, NEVER executable"},
       "limitations":[
          "Three seeds only; dataset-level cluster n=20",
          "Prepared capped UCI subsets <=1800 rows and <=6 features; no large full-data benchmarks",
          "Only IID stratified clients C3, not nonIID nor C2/C4/C5 in this experiment",
          "Original training split 64% not 80%; results not directly comparable to frozen 8,820",
          "Meta training on 19 datasets; estimator hyperparameters fixed a priori but no dedicated meta-hyperparameter search",
          "Validation used to pick six strategies, which is legitimate but itself can overfit with small minority classes",
          "High exact rule coverage does not guarantee correct candidate or high Balanced Accuracy",
          "Fixed six strategies are selection functions on Classical LEM2 rules, not six independent inductive learners"],
       "mean_balanced_accuracy_by_strategy":{
          k:float(v) for k,v in simple.mean_outer_test_pct.to_dict().items()
       },
       "files":[
         "ADAPTIVE_SIX_20_ALL_POLICIES.csv","ADAPTIVE_SIX_20_SELECTORS.csv",
         "ADAPTIVE_SIX_20_SUMMARY.csv","ADAPTIVE_SIX_20_DATASET_BOOTSTRAP.csv"]
    }
    (OUT/"ADAPTIVE_SIX_20_MANIFEST.json").write_text(
         json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("ADAPTIVE_SIX_SELECTOR_QA_PASS",len(data),len(selections),flush=True)
    for x in summary[summary.objective.eq("balanced_accuracy")].sort_values("mean_outer_test_pct",ascending=False).to_dict("records"):
        print("BA_METHOD",x["method"],"MEAN",round(x["mean_outer_test_pct"],4),
              "REGRET",round(x["mean_regret_pp"],4),flush=True)

if __name__=="__main__":main()
