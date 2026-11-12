"""Aggregate 20 genuinely acquired public UCI datasets; never fill failed jobs.

Model evidence = one seed (42), exact-reduct Classical/Federated C3.
One fixed train-only supplement heuristic A/B with purity >= .90.
A source dataset is marked PASS only with verifiable baseline+supplement+profile+CSV.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from teacher_demo.public_20_registry import REGISTRY

IN=Path("public_20_incoming")
OUT=Path("docs/research/teacher_dashboard/data")
PUBLIC=Path("docs/research/public_datasets_20")
RESULTS=Path("docs/research/teacher_dashboard/public20")
POLICIES={"FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH",
          "POPULATION_STANDARD","POPULATION_GLOBAL"}
SYSTEMS={("CENTRALIZED",0),("FEDERATED",3)}

def check(ok,why):
    if not bool(ok):raise AssertionError(why)

def validate(name):
    cfg=REGISTRY[name]
    p=IN/f"PUBLIC20_PROFILE_{name}.json"
    base=IN/f"PUBLIC20_BASE_{name}.csv"
    supp=IN/f"PUBLIC20_SUPPLEMENT_{name}.csv"
    raw=IN/f"PUBLIC20_DATA_{name}.csv"
    for f in [p,base,supp,raw]:
        check(f.is_file(),"Missing mandatory source artifact "+str(f))
    profile=json.loads(p.read_text(encoding="utf-8"))
    check(profile["dataset_key"]==name and int(profile["uci_id"])==cfg["id"],"Wrong source")
    check(profile["source_url"]==cfg["url"],"Untrusted source URL")
    check(int(profile["used_rows"])<=int(profile["source_rows"]),"Invalid sample cap")
    check(int(profile["used_feature_count"])<=6,"Exact reduct feature cap")
    check(int(profile["used_rows"])>=max(50,int(profile["min_class_count"])*2),"Insufficient sampled data")
    check(set(profile["class_counts"])!="","Invalid class counts")
    frame=pd.read_csv(raw)
    check(len(frame)==int(profile["used_rows"]),"Prepared input size mismatch")
    check(len(frame.columns)==int(profile["used_feature_count"])+1,"Prepared CSV column mismatch")
    check(frame.columns[-1]=="class","Target column")
    check(frame.isna().sum().sum()==0,"Missing values in prepared data")
    check(set(map(str,frame["class"].unique()))==set(map(str,profile["class_counts"])),"Label classes mismatch")
    check(set(frame.columns[:-1])==set(profile["feature_columns"]),"Feature schema mismatch")
    b=pd.read_csv(base)
    u=pd.read_csv(supp)
    check(len(b)==14,"Expected two architectures * (NONE+six policies)")
    check(len(u)==2,"Expected two train-only supplementary comparisons")
    check(set(b.public_dataset_key)=={name},"Dataset key mismatch")
    check(set(b.seed)=={42} and set(u.seed)=={42},"One seed pilot only")
    check(set(b.selection_policy)==POLICIES|{"NONE"},"Wrong policies")
    check(set(map(tuple,b[["system","client_count"]].drop_duplicates().to_numpy()))==SYSTEMS,"Wrong architectures")
    check(set(map(tuple,u[["system","client_count"]].drop_duplicates().to_numpy()))==SYSTEMS,"Supplement architectures")
    check(not b.duplicated(["system","client_count","selection_policy"]).any(),"Duplicate outcome")
    for (system,client),group in b.groupby(["system","client_count"]):
        none=group[group.selection_policy=="NONE"].iloc[0]
        check(len(group)==7,"Policy count")
        # Stratified splitting uses ceil per class, so 26 classes may yield
        # more than round(20% * N) test examples. Validate actual disjoint
        # train/test conservation, not an incorrect global rounding formula.
        check(int(none.evaluation_rows)>0 and int(none.evaluation_rows)<len(frame),
              "Holdout denominator out of range")
        check(int(none.train_rows)+int(none.evaluation_rows)==len(frame),
              "Train/test conservation mismatch")
        check(np.isclose(none.covered_count/none.evaluation_rows,none.coverage),"Coverage mismatch")
        check(np.isclose(none.conflict_case_count/none.evaluation_rows,none.conflict_case_rate),"Conflict mismatch")
        check(np.isclose(none.true_in_candidate_count/none.evaluation_rows,none.true_in_candidate_rate),"Candidate mismatch")
        check(np.allclose(group.train_coverage_pct,none.train_coverage_pct),"Train Coverage structural mismatch")
        check(np.allclose(group.test_coverage_pct,none.test_coverage_pct),"Test Coverage structural mismatch")
        check(np.isclose(none.test_coverage_pct,100*none.coverage),"Test Coverage percentage mismatch")
        for _,row in group[group.selection_policy!="NONE"].iterrows():
            check(0<=row.accuracy<=1 and 0<=row.balanced_accuracy<=1,"Invalid model outcome")
        aug=u[(u.system==system)&(u.client_count==client)].iloc[0]
        check(np.isclose(aug.baseline_train_coverage_pct,none.train_coverage_pct),"Train base mismatch")
        check(np.isclose(aug.baseline_test_coverage_pct,none.test_coverage_pct),"Test base mismatch")
        check(np.isclose(aug.baseline_accuracy_pct,100*group[group.selection_policy=="GLOBAL_STRENGTH"].iloc[0].accuracy),
              "Supplement baseline accuracy mismatch")
        check(aug.augmented_test_coverage_pct+1e-9>=aug.baseline_test_coverage_pct,
              "Augmentation must not shrink coverage")
        check(aug.augmented_train_coverage_pct+1e-9>=aug.baseline_train_coverage_pct,
              "Augmentation must not shrink training coverage")
        check(np.isclose(aug.augmented_test_coverage_pct-aug.baseline_test_coverage_pct,
                         aug.test_coverage_gain_pp,atol=1e-8),"Augmentation delta mismatch")
    return profile,b,u,frame

def main():
    OUT.mkdir(parents=True,exist_ok=True);PUBLIC.mkdir(parents=True,exist_ok=True);RESULTS.mkdir(parents=True,exist_ok=True)
    successes={};failed={}
    for k in sorted(REGISTRY):
        error=IN/f"PUBLIC20_ERROR_{k}.json"
        if error.is_file():
            failed[k]=json.loads(error.read_text(encoding="utf-8"))
            continue
        try:
            successes[k]=validate(k)
        except Exception as e:
            failed[k]={"dataset_key":k,"error":type(e).__name__+": "+str(e),"stage":"AGGREGATION_VALIDATION"}
    frames=[];supps=[];catalog=[]
    for k,cfg in sorted(REGISTRY.items()):
        entry={
            "key":k,"uci_id":cfg["id"],"name":cfg["name"],"domain":cfg["domain"],
            "feature_mode":cfg["feature_mode"],"trait":cfg["research_trait"],
            "original_source":cfg["url"],"source_license_claim":cfg["source_license_claim"],
            "planned_sample_cap":cfg["cap_rows"],"feature_contract":cfg["fixed_feature_contract"],
            "expected_classes":cfg["expected_classes"],"notes":cfg.get("notes","")
        }
        if k in successes:
            p,b,u,frame=successes[k]
            frames.append(b);supps.append(u)
            dest=PUBLIC/f"{k}_prepared.csv"
            shutil.copy2(IN/f"PUBLIC20_DATA_{k}.csv",dest)
            entry.update(status="PASS_ONE_SEED",source_rows=p["source_rows"],
                         used_rows=p["used_rows"],used_feature_count=p["used_feature_count"],
                         observed_classes=p["class_counts"],prepared_sha256=p["sha256_prepared_csv"],
                         published_file=str(dest),
                         published_file_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
        else:entry.update(status="FAILED_NOT_IMPUTED",error=failed.get(k,{"error":"No reported artifact"}))
        catalog.append(entry)
    if frames:
        b=pd.concat(frames,ignore_index=True)
        u=pd.concat(supps,ignore_index=True)
        b.to_csv(OUT/"PUBLIC20_BASE_RESULTS.csv",index=False)
        u.to_csv(OUT/"PUBLIC20_SUPPLEMENT_RESULTS.csv",index=False)
        grouped=(b[b.selection_policy.ne("NONE")]
            .groupby(["public_dataset_key","system","client_count","selection_policy"],dropna=False)
            .agg(seed_count=("seed","nunique"),accuracy=("accuracy","mean"),
                balanced_accuracy=("balanced_accuracy","mean"),macro_f1=("macro_f1","mean"),
                train_coverage_pct=("train_coverage_pct","mean"),test_coverage_pct=("test_coverage_pct","mean"),
                conflict_rate=("conflict_case_rate","mean"),candidate_rate=("true_in_candidate_rate","mean"),
                rule_count=("rule_count","mean")).reset_index())
        grouped.to_csv(OUT/"PUBLIC20_POLICY_SUMMARY.csv",index=False)
        # Same dataset and client architecture, six policies, split ties rather
        # than treating tied methods as independent wins.
        win=[]
        for (dataset,client),group in b[(b.selection_policy!="NONE")].groupby(["public_dataset_key","client_count"]):
            for metric in ("accuracy","balanced_accuracy","macro_f1"):
                score=group[metric].to_numpy(dtype=float)
                if np.isnan(score).all():continue
                if not np.isfinite(score).all():raise AssertionError("Invalid policy metric")
                highest=score.max()
                winners=group[np.isclose(score,highest,rtol=1e-10,atol=1e-12)].selection_policy.tolist()
                for p in POLICIES:
                    win.append({"dataset":dataset,"client_count":client,"objective":metric,
                      "policy":p,"co_win":int(p in winners),"sole_win":int(p in winners and len(winners)==1),
                      "fractional_win":1/len(winners) if p in winners else 0,
                      "winners":len(winners)})
        pd.DataFrame(win).to_csv(OUT/"PUBLIC20_POLICY_WINS.csv",index=False)
        summary=[]
        for dataset,one in u.groupby("dataset"):
            entry={"dataset":dataset,"n_architectures":len(one),"seed":42}
            for key in ("baseline_train_coverage_pct","augmented_train_coverage_pct","train_coverage_gain_pp",
                        "baseline_test_coverage_pct","augmented_test_coverage_pct","test_coverage_gain_pp",
                        "accuracy_gain_pp","balanced_accuracy_gain_pp"):
                entry[key]=float(one[key].mean())
            summary.append(entry)
        pd.DataFrame(summary).to_csv(OUT/"PUBLIC20_SUPPLEMENT_SUMMARY.csv",index=False)
    status="ALL_20_ONE_SEED_PASS" if len(successes)==20 else "PARTIAL_FEASIBILITY_SOME_FAILED"
    manifest={
       "status":status,"n_registered":20,"passed_count":len(successes),
       "failed_count":len(failed),"passed_keys":sorted(successes),"failed":failed,
       "seed":[42],"new_dataset_registry":"teacher_demo/public_20_registry.py",
       "method":"Classical positive-region exact reduct + LEM2; Centralized and Federated C3",
       "policies":["NONE"]+sorted(POLICIES),"results_per_dataset":14,
       "original_20_raw_results":14*len(successes),
       "supplement_conditions":{"method":"simplified one antecedent drop from first 240 rules",
          "train_purity":.90,"train_min_support":5,"max_supplemental_rules":80,
          "extra_rules_fit_using":"TRAIN ONLY","test_label_tuning":False,
          "not_reproduction_of":"2015 MLEM2 supplementary rules"},
       "limits":[
         "Only one seed 42; an early feasibility scan, not statistical validation",
         "Original UCI datasets with large sample sizes were sampled to <=1800 for exact reduct",
         "Only up to six prespecified features used per dataset; no full-high-dimensional claim",
         "Sequential temporal/group holdout is NOT evaluated here",
         "Unmatched baseline still predicts training majority rather than rejecting",
         "Study differences across domains before confirmatory 42-seed expansion"],
       "datasets":catalog
    }
    (OUT/"PUBLIC20_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    (PUBLIC/"README.md").write_text(
       "# 20 new public source datasets for the Classical/Federated LEM2 feasibility scan\n\n"+
       "Only passed, prepared, fixed class-stratified and six-feature-max UCI subsets are redistributed. Original source files stay on UCI; source links, licenses and data transformation descriptions are in the manifest. All columns named class as the target. No raw personal company records.\n\n"+
       "License source claim: CC BY 4.0 for the UCI entries, verify source-page license before downstream distribution. Attribution to the respective UCI dataset and original contributors is required. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/\n\n"+
       "Experiment is a 1-seed pilot (42), two architectures C0/C3, and train-only single-antecedent-drop supplements with purity 0.90; not a full 42-seed confirmation or full-data scale benchmark.\n\n"+
       "See ../teacher_dashboard/data/PUBLIC20_MANIFEST.json for 20 detailed source references, original and selected rows/features, and validated failures.\n",
       encoding="utf-8")
    print("PUBLIC20_AGGREGATE",status,"PASSED",len(successes),"FAILED",len(failed),flush=True)
    for k,err in sorted(failed.items()):print("PUBLIC20_FAILED",k,str(err)[:240],flush=True)

if __name__=="__main__":main()
