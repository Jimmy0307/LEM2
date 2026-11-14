"""Audited PMLB >100-table source study, meta-selector, G4-G6 and G8 summaries.

Source-pinned candidates are NOT all independent original real-world domains.
All deployable choices are made using training & INNER validation data ONLY.
Fold observations are grouped by dataset/family for uncertainty.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from teacher_demo.full_factorial_matrix import POLICIES
from teacher_demo.adaptive_six_policy_runner import POLICY_ORDER
from teacher_demo.pmlb_117_runner import specs

IN=Path("incoming_pmlb_117")
OUT=Path("docs/research/teacher_dashboard/data")
OBJECTIVES=("balanced_accuracy","macro_f1","accuracy")
FEATURES=("train_num_classes","train_minority_share","train_continuous_fraction",
          "client_label_js","client_row_cv","client_label_missing_rate",
          "validation_coverage","validation_conflict",
          "validation_correct_candidate","number_rules","dev_rows")
DEPLOYABLE=("FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING",
            "VALIDATION_BEST","GUARDED_SKEW_V1","LOFO_GLOBAL_VAL","LOFO_META_KNN7")
ALL=("FIXED_FIRST_MATCH","FIXED_SIMPLE_VOTING","FIXED_STANDARD_VOTING",
     "FIXED_GLOBAL_STRENGTH","FIXED_POPULATION_STANDARD","FIXED_POPULATION_GLOBAL",
     "VALIDATION_BEST","GUARDED_SKEW_V1","LOFO_GLOBAL_VAL","LOFO_META_KNN7",
     "TEST_ORACLE_DIAGNOSTIC")

def require(a,msg):
    if not bool(a):raise AssertionError(msg)

def read_source():
    registry=specs()
    expected=set(registry)
    receipts={}
    trials=[]
    for name in sorted(expected):
        path=IN/f"RECEIPT_{name}.json"
        require(path.is_file(),"Missing source receipt for "+name)
        item=json.loads(path.read_text(encoding="utf-8"))
        require(item["name"]==name,"Source receipt identity mismatch")
        require(item["research_status"] in ("PASS","PARTIAL","NO_VALID_MODEL"),"Invalid source status")
        require(item["configs_passed"]>=0,"Invalid counts")
        receipts[name]=item
        if item["configs_passed"]:
            f=IN/f"BENCHMARK_{name}.csv"
            require(f.is_file(),"Missing actual model output "+name)
            x=pd.read_csv(f)
            require(len(x)==6*int(item["configs_passed"]),"Policy count mismatch "+name)
            require(x.dataset.eq(name).all(),"Data source mismatch")
            require(x.policy.isin(POLICIES).all() and x.policy.nunique()==6,"Wrong six resolver methods")
            require(set(x.leakage_protocol)=={"64_16_20_NO_REFIT_TRAIN_ONLY_SELECTOR"},"Bad protocol")
            require(x.groupby(["dataset","seed","scenario"]).size().eq(6).all(),"Incomplete cases")
            require(x.groupby(["scenario"]).policy.nunique().eq(6).all(),"Incomplete policies")
            require(x.source_gzip_sha256.eq(item["dataset_source"]["source_gzip_sha256"]).all(),"Unverified gzip SHA")
            require(x.prepared_sha256.eq(item["dataset_source"]["prepared_sha256"]).all(),"Wrong prepared source SHA")
            require(x[["dev_rows","validation_rows","test_rows"]].sum(axis=1).eq(item["dataset_source"]["available_rows"]).all(),"Train val test split conservation broken")
            for col in ("validation_coverage","validation_conflict","validation_correct_candidate",
                        "client_label_js","train_minority_share","test_coverage",
                        "test_balanced_accuracy","validation_balanced_accuracy"):
                require(x[col].between(0,1).all(),name+" bad metric "+col)
            for _,g in x.groupby(["scenario","seed"]):
                require(g.test_coverage.max()-g.test_coverage.min()<1e-10,name+" six methods changed Coverage")
                for feature in FEATURES+("source_gzip_sha256","prepared_sha256"):
                    require(g[feature].nunique(dropna=False)==1,name+" features drift by policy "+feature)
                for obj in OBJECTIVES:
                    require(g["selected_validation_best"].sum()==1 if obj=="balanced_accuracy" else True,
                            "bad deterministic selected validation count")
                require(g.selected_heterogeneity_guard.sum()==1,"guard not unique")
            trials.append(x)
    df=pd.concat(trials,ignore_index=True) if trials else pd.DataFrame()
    assert len(receipts)==117
    return registry,receipts,df

def choose(scores):
    return max(POLICY_ORDER,key=lambda p:(float(scores[p]),-POLICY_ORDER.index(p)))

def meta_choices(target,other,objective):
    # Strictly exclude ALL members of target family (including every seed).
    refs=other[(other.family!=target.family)&(other.scenario==target.scenario)]
    groups=refs.groupby(["dataset","policy"],sort=True)
    val_col="validation_"+objective
    table=groups[val_col].mean().unstack("policy")
    features=refs.groupby("dataset")[list(FEATURES)].mean()
    require(len(table)>=30,"too few OTHER source tables to learn LOTO meta")
    require(set(table.columns)==set(POLICIES),"Meta training lacks six strategies")
    require(target.dataset not in table.index,"Target source leaked")
    require(len(features)==len(table),"Meta profile mismatch")
    # Each PMLB dataset table gets equal weight, not all its seed rows.
    global_choice=choose(table.mean(axis=0))
    mu=features.mean()
    sd=features.std(ddof=0).replace(0,1).fillna(1)
    train_scaled=(features.fillna(mu)-mu)/sd
    target_vector=pd.Series({f:getattr(target,f) for f in FEATURES})
    x=(target_vector.fillna(mu)-mu)/sd
    distance=np.sqrt((train_scaled-x).pow(2).sum(axis=1))
    k=min(7,len(distance))
    neighbors=distance.sort_values(kind="stable").head(k)
    weight=1/(neighbors.to_numpy(dtype=float)+.05);weight/=weight.sum()
    prediction=table.loc[neighbors.index].T @ weight
    return global_choice,choose(prediction),list(neighbors.index),len(table)

def select(data):
    result=[]
    def first(series,k):return series.loc[k]
    for (ds,seed,scenario),group in data.groupby(["dataset","seed","scenario"],sort=True):
        require(len(group)==6,"Incomplete six policies in source config")
        base=group.iloc[0]
        p=group.set_index("policy")
        require(set(p.index)==set(POLICIES),"Missing strategy")
        for objective in OBJECTIVES:
            valid={policy:float(p.loc[policy,"validation_"+objective]) for policy in POLICIES}
            test={policy:float(p.loc[policy,"test_"+objective]) for policy in POLICIES}
            # Sources' *validation* scores only determine the LOTO meta learner.
            global_choice,knn,neighbors,reference_count=meta_choices(
                base,data,objective
            )
            # Dedicated BA switching rule fixed before all tests; no tuning on test.
            val_choice=choose(valid)
            guarded=p.index[p.selected_heterogeneity_guard.eq(1)].tolist()
            require(len(guarded)==1,"Guard chose more than one strategy")
            oracle=choose(test) # DIAGNOSTIC only
            choices={"FIXED_"+str(x):str(x) for x in POLICIES}
            choices.update(VALIDATION_BEST=val_choice,GUARDED_SKEW_V1=guarded[0],
                           LOFO_GLOBAL_VAL=global_choice,LOFO_META_KNN7=knn,
                           TEST_ORACLE_DIAGNOSTIC=oracle)
            for method,policy in choices.items():
                score=float(test[policy])
                result.append({
                   "dataset":ds,"seed":seed,"scenario":scenario,"family":base.family,
                   "source_kind":base.source_kind,"objective":objective,
                   "method":method,"selected_policy":policy,
                   "test_score_pct":100*score,
                   "test_oracle_score_pct":100*test[oracle],
                   "oracle_regret_pp":100*(test[oracle]-score),
                   "val_selected_score_pct":100*valid[policy],
                   "train_num_classes":int(base.train_num_classes),
                   "train_minority_share":float(base.train_minority_share),
                   "train_continuous_fraction":float(base.train_continuous_fraction),
                   "client_label_js":float(base.client_label_js),
                   "client_row_cv":float(base.client_row_cv),
                   "validation_conflict":float(base.validation_conflict),
                   "validation_coverage":float(base.validation_coverage),
                   "validation_correct_candidate":float(base.validation_correct_candidate),
                   "outer_test_coverage":float(base.test_coverage),
                   "number_rules":int(base.number_rules),
                   "dev_rows":int(base.dev_rows),
                   "meta_reference_tables":reference_count if method.startswith("LOFO") else 0,
                   "meta_neighbors":";".join(neighbors) if method=="LOFO_META_KNN7" else "",
                   "test_oracle_non_deployable":method=="TEST_ORACLE_DIAGNOSTIC"
                })
    out=pd.DataFrame(result)
    expected=len(data)//6*3*len(ALL)
    require(len(out)==expected,"Missing selector comparisons")
    require(out.groupby(["dataset","scenario","seed","objective"]).size().eq(len(ALL)).all(),"Selector completeness failure")
    require(out.oracle_regret_pp.ge(-1e-6).all(),"Oracle lower than actual strategy")
    return out

def summarize(data,selection):
    reports=[]
    for (scenario,obj,method),group in selection.groupby(["scenario","objective","method"],sort=True):
        reports.append({
          "scenario":scenario,"objective":obj,"method":method,"configs":len(group),
          "distinct_tables":group.dataset.nunique(),"families":group.family.nunique(),
          "mean_test_pct":float(group.test_score_pct.mean()),
          "mean_regret_pp":float(group.oracle_regret_pp.mean()),
          "mean_label_js":float(group.client_label_js.mean()),
          "mean_validation_conflict_pct":100*float(group.validation_conflict.mean()),
          "mean_validation_coverage_pct":100*float(group.validation_coverage.mean())
        })
    return pd.DataFrame(reports)

def conditions(selection):
    # Train & inner-validation metadata, NOT test-defined groups.
    sub=selection[selection.objective.eq("balanced_accuracy")].copy()
    sub["class_balance"]=np.where(sub.train_minority_share<.1,"minority_lt10",
        np.where(sub.train_minority_share<.25,"minority_10_25","minority_ge25"))
    sub["client_js_band"]=np.where(sub.client_label_js>=.15,"js_ge015",
        np.where(sub.client_label_js>=.05,"js_005_015","js_lt005"))
    sub["conflict_band"]=np.where(sub.validation_conflict>=.4,"conflict_ge40",
        np.where(sub.validation_conflict>=.1,"conflict_10_40","conflict_lt10"))
    sub["coverage_band"]=np.where(sub.validation_coverage>=.8,"coverage_ge80",
        np.where(sub.validation_coverage>=.3,"coverage_30_80","coverage_lt30"))
    sub["feature_type"]=np.where(sub.train_continuous_fraction==0,"all_discrete_train",
        np.where(sub.train_continuous_fraction>=.999,"all_numeric_continuous_train","mixed_train"))
    sub["classes"]=np.where(sub.train_num_classes==2,"binary",np.where(sub.train_num_classes<=5,"3to5","6plus"))
    groups=[]
    for field in ("scenario","class_balance","client_js_band","conflict_band","coverage_band","feature_type","classes","source_kind"):
        for (value,method),g in sub.groupby([field,"method"]):
            groups.append({
              "group_by":field,"group":value,"method":method,
              "comparisons":len(g),"distinct_tables":g.dataset.nunique(),
              "distinct_families":g.family.nunique(),
              "mean_balanced_accuracy_pct":float(g.test_score_pct.mean()),
              "mean_oracle_regret_pp":float(g.oracle_regret_pp.mean())
            })
    out=pd.DataFrame(groups)
    return out

def family_bootstrap(selection,objective="balanced_accuracy",reps=1500):
    pairs=selection[selection.objective.eq(objective)]
    out=[]
    for scenario,sub in pairs.groupby("scenario"):
        for method in ("VALIDATION_BEST","GUARDED_SKEW_V1","LOFO_GLOBAL_VAL","LOFO_META_KNN7",
                       "FIXED_SIMPLE_VOTING"):
            for base in ("FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING"):
                if method==base:continue
                pivot=sub[sub.method.isin([method,base])].pivot_table(
                    index=["dataset","family","seed"],columns="method",
                    values="test_score_pct")
                diffs=(pivot[method]-pivot[base]).groupby(level="family").mean()
                vals=diffs.to_numpy(dtype=float)
                if not len(vals):continue
                rng=np.random.default_rng(20261114)
                bs=vals[rng.integers(0,len(vals),size=(reps,len(vals)))].mean(axis=1)
                out.append({
                  "scenario":scenario,"objective":objective,"method":method,
                  "benchmark":base,"families":len(vals),
                  "mean_gain_pp":float(vals.mean()),
                  "ci95_low_pp":float(np.quantile(bs,.025)),
                  "ci95_high_pp":float(np.quantile(bs,.975)),
                  "improved_families":int((vals>1e-8).sum()),
                  "harmed_families":int((vals < -1e-8).sum()),
                  "tied_families":int((abs(vals)<=1e-8).sum())
                })
    return pd.DataFrame(out)

def summarize_scaling(data):
    if data.empty:return pd.DataFrame()
    # These rows are measured at the 900-row and six-feature FEASIBILITY cap.
    # Correlation with ORIGINAL rows/features is not a true full-scale test.
    x=data.drop_duplicates(["dataset","seed","scenario"])
    summary=(x.groupby("scenario",as_index=False)
             .agg(configs=("dataset","size"),median_fit_seconds=("fit_seconds","median"),
                  p90_fit_seconds=("fit_seconds",lambda s:float(s.quantile(.9))),
                  max_fit_seconds=("fit_seconds","max"),
                  median_maxrss_mb=("maxrss_mb","median"),
                  p90_maxrss_mb=("maxrss_mb",lambda s:float(s.quantile(.9))),
                  median_rule_count=("number_rules","median")))
    return summary

def main():
    global IN
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default=str(IN))
    parser.add_argument("--min-dataset-count",type=int,default=101)
    parser.add_argument("--prefix",default="PMLB_117")
    args=parser.parse_args()
    IN=Path(args.input)
    OUT.mkdir(parents=True,exist_ok=True)
    prefix=args.prefix
    require(prefix in ("PMLB_117","PMLB_117_3SEED"),"Invalid output namespace")
    registry,receipt,data=read_source()
    audit=pd.DataFrame([
      {
        "dataset":name,"family":registry[name]["family"],"source_kind":registry[name]["kind"],
        "source_url":registry[name]["source_url"],
        "upstream_original_rows":registry[name]["upstream_rows"],
        "upstream_original_features":registry[name]["upstream_features"],
        "source_read_valid":bool(x["dataset_source"]),
        "configs_passed":x["configs_passed"],"status":x["research_status"],
        "errors_json":json.dumps(x["failures"],ensure_ascii=False),
        "source_sha256":x["dataset_source"]["source_gzip_sha256"] if x["dataset_source"] else "",
        "prepared_sha256":x["dataset_source"]["prepared_sha256"] if x["dataset_source"] else "",
        "actual_sample_rows":x["dataset_source"]["available_rows"] if x["dataset_source"] else 0,
        "wall_seconds":x["wall_seconds"]
      } for name,x in sorted(receipt.items())
    ])
    audit.to_csv(OUT/(prefix+"_SOURCE_AUDIT.csv"),index=False)
    counted=audit[audit.configs_passed>0]
    iid=audit[audit.dataset.isin(set(data[data.scenario.eq("IID")].dataset))]
    n_unique_source=int(counted.source_sha256.nunique())
    n_unique_prepared=int(counted.prepared_sha256.nunique())
    status="PASS_OVER_100_PUBLIC_BENCHMARK_TABLES" if len(iid)>100 and n_unique_prepared>100 else "PARTIAL_UNDER_100_VALID_TABLES"
    manifest={
      "status":status,"registered_candidates":len(registry),
      "source_valid_count":int(audit.source_read_valid.sum()),
      "successful_models":len(counted),"successful_iid_tables":len(iid),
      "unique_raw_source_sha":n_unique_source,
      "unique_prepared_sha":n_unique_prepared,
      "unique_families_in_success":counted.family.nunique(),
      "family_identity_note":"PMLB family is partially heuristic: not a guarantee of independent real-world domains",
      "real_vs_synthetic_note":"PMLB includes synthetic/generated tasks and related original UCI sources; not 117 new real-domain datasets",
      "source_github":"https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68",
      "source_paper":"https://academic.oup.com/bioinformatics/article/38/3/878/6408434",
      "source_license":"Original per-dataset licensing not presumed from PMLB code; raw rows not redistributed",
      "seed_protocol":"seed(s) "+",".join(str(x) for x in sorted(data.seed.unique()))+" on PMLB; 64/16/20; 3 Client; IID and Dirichlet alpha .5/.1",
      "seeds":sorted(int(x) for x in data.seed.unique()),
      "config_pass_counts":data.groupby("scenario").dataset.nunique().to_dict() if not data.empty else {},
      "raw_evaluation_rows":len(data),
      "model_configurations":len(data)//6,
      "thresholds":{"guard_client_js":.1,"guard_validation_conflict":.1,"guard_val_ba_gain":.02},
      "output_status":"Evidence only; preselected rules shared across six strategy results",
      "cautions":[
       "Even three PMLB seeds cannot establish independence of related PMLB tasks: per-origin dedup/licensing review still needed",
       "PMLB has multiple related classification tasks and synthetic datasets; don't treat as independent source domains",
       "Model fits <=900 rows x <=6 features; original millions of rows / high-dimensional metadata not actually fit",
       "Unknown original per-dataset license: do not republish datasets themselves",
       "No Meta or Guard thresholds changed using outer Test labels",
       "Some Dirichlet configurations may fail; count failed scenarios explicitly",
       "IID/nonIID may substantially shift true candidate coverage and rule counts independently from resolver",
       "Meta source family grouping is heuristic, not final origin reconciliation"]
    }
    if len(data):
        data.to_csv(OUT/(prefix+"_SIX_POLICY_RAW.csv"),index=False,float_format="%.10f")
        selection=select(data)
        selection.to_csv(OUT/(prefix+"_POLICY_SELECTIONS.csv"),index=False,float_format="%.10f")
        summarize(data,selection).to_csv(OUT/(prefix+"_METHOD_SUMMARY.csv"),index=False,float_format="%.10f")
        conditions(selection).to_csv(OUT/(prefix+"_CONDITION_ATLAS.csv"),index=False,float_format="%.10f")
        family_bootstrap(selection).to_csv(OUT/(prefix+"_FAMILY_BOOTSTRAP.csv"),index=False,float_format="%.10f")
        summarize_scaling(data).to_csv(OUT/(prefix+"_FEASIBILITY_RUNTIME.csv"),index=False,float_format="%.10f")
        manifest["selector_evaluations"]=len(selection)
    (OUT/(prefix+"_MANIFEST.json")).write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("PMLB_117_AUDIT",status,"sources",manifest["source_valid_count"],
          "IID",len(iid),"unique_prepared",n_unique_prepared,"configs",manifest["model_configurations"],flush=True)
    if status!="PASS_OVER_100_PUBLIC_BENCHMARK_TABLES":
        raise AssertionError("Threshold >100 validated source-deduplicated tables NOT met: "+json.dumps({
          k:manifest[k] for k in ("successful_iid_tables","unique_prepared_sha","source_valid_count")}))
    print("PMLB_117_MORE_THAN_100_REAL_BENCHMARK_TABLES_VALIDATED_PASS",flush=True)

if __name__=="__main__":main()
