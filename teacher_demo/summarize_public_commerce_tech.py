"""Audit and publish CC-BY public e-commerce and technical data pilot.

Independent pilot with actual UCI datasets 468 and 601, explicit feature exclusion,
clean 80/20 holdout, 4 seeds, Classical LEM2/C2-C5/6 vote policies.
Results stay outside the frozen 8,820 rows. Any incomplete run fails closed.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path
import pandas as pd
import numpy as np

IN=Path("public_commerce_tech_incoming")
OUT=Path("docs/research/teacher_dashboard/data")
DATADIR=Path("docs/research/public_datasets")
SOURCES={
 "online_shoppers":{"uci_id":468,"cap":1600,"doi":"10.24432/C5F88Q",
 "title":"Online Shoppers Purchasing Intention Dataset",
 "url":"https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset",
 "original":"12330 e-commerce sessions; real anonymized behavioral data",
 "limitation":"Only prespecified six predictors; PageValues excluded as possible transaction outcome proxy; 1600 fixed stratified sampled sessions."},
 "ai4i_maintenance":{"uci_id":601,"cap":2400,"doi":"10.24432/C5HS5C",
 "title":"AI4I 2020 Predictive Maintenance Dataset",
 "url":"https://archive.ics.uci.edu/dataset/601/ai4i",
 "original":"10000 synthetic industrial equipment observations (NOT real factory incidents)",
 "limitation":"Only 6 legitimate features; removed device identifiers and all 5 specific failure-target columns. Stratified random 80/20 may overestimate temporally deployed performance."},
}
SEEDS={1,7,21,42}
POLICIES={"FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"}
TARGETS=("accuracy","balanced_accuracy","macro_f1","minority_recall","conflict_resolution_accuracy")

def validate_job(df,name,seed):
    if len(df)!=35:raise AssertionError("Expected 35 rows "+name+" "+str(seed))
    assert set(df["ext_dataset_key"])=={name}
    assert set(df["scenario"])=={"BASE"}
    assert set(df["seed"])=={seed}
    assert set(df["split_mode"])=={"HOLDOUT_80_20"}
    assert df.groupby("client_count").size().to_dict()=={0:7,2:7,3:7,4:7,5:7}
    assert df.groupby("client_count").selection_policy.nunique().eq(7).all()
    assert not df.duplicated(["client_count","selection_policy"]).any()
    for client,group in df.groupby("client_count"):
        assert set(group.selection_policy)==POLICIES|{"NONE"}
        base=group.loc[group.selection_policy=="NONE"].iloc[0]
        assert np.isclose(base.covered_count+base.no_match_count,base.evaluation_rows)
        assert np.isclose(base.conflict_case_count/base.evaluation_rows,base.conflict_case_rate)
        assert np.isclose(base.covered_count/base.evaluation_rows,base.coverage)
        assert np.isclose(base.true_in_candidate_count/base.evaluation_rows,base.true_in_candidate_rate)
        for x in ["rule_count","coverage","conflict_case_rate","true_in_candidate_rate",
                  "train_rule_coverage_pct","test_rule_coverage_pct","test_minus_train_coverage_pp"]:
            assert np.allclose(group[x].astype(float),float(base[x]),equal_nan=True)
        assert np.isclose(base.test_rule_coverage_pct,100*base.coverage)
        assert np.isclose(base.test_minus_train_coverage_pp,base.test_rule_coverage_pct-base.train_rule_coverage_pct)
        for _,r in group.loc[group.selection_policy.ne("NONE")].iterrows():
            assert np.isclose(r.accuracy,r.overall_correct_count/r.evaluation_rows) if "overall_correct_count" in r.index and pd.notna(r.overall_correct_count) else pd.notna(r.accuracy)
            assert r.minority_test_count>0 and r.minority_test_count<r.evaluation_rows
            assert r.minority_recall>=0 and r.minority_recall<=1

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    DATADIR.mkdir(parents=True,exist_ok=True)
    rows=[]
    profiles=[]
    expected={(k,s) for k in SOURCES for s in SEEDS}
    found=set()
    for f in sorted(IN.glob("STRESS_*_BASE_seed*.csv")):
        df=pd.read_csv(f)
        name=str(df.iloc[0].ext_dataset_key)
        seed=int(df.iloc[0].seed)
        if (name,seed) not in expected or (name,seed) in found:raise AssertionError("Unexpected duplicate "+f.name)
        validate_job(df,name,seed)
        rows.append(df)
        found.add((name,seed))
    if found!=expected:raise AssertionError("Missing public source experiments: "+repr(sorted(expected-found)))
    for f in sorted(IN.glob("PROFILE_*_BASE_seed*.json")):
        p=json.loads(f.read_text(encoding="utf-8"))
        name=p["dataset_key"]
        seed=int(p["seed"])
        assert (name,seed) in found and p["scenario"]=="BASE"
        assert int(p["uci_id"])==SOURCES[name]["uci_id"]
        assert p["license"]=="CC BY 4.0"
        assert int(p["used_rows"])==SOURCES[name]["cap"]
        assert int(p["used_feature_count"])==6
        profiles.append(p)
    assert len(profiles)==len(expected)
    for name in SOURCES:
        subset=[p for p in profiles if p["dataset_key"]==name]
        hashes={p["sha256_prepared_csv"] for p in subset}
        assert len(hashes)==1,("Source drift across seed runs",name,hashes)
        path=IN/f"PUBLIC_DATASET_{name}.csv"
        assert path.is_file(),("Missing acquired public prepared CSV",name)
        x=pd.read_csv(path)
        assert len(x)==SOURCES[name]["cap"],(name,len(x))
        assert list(x.columns)[-1]=="class" and len(x.columns)==7
        assert int(x["class"].nunique())==2
        assert x.isna().sum().sum()==0
        assert set(x.columns)==set(subset[0]["feature_columns"])|{"class"}
        shutil.copy2(path,DATADIR/f"{name}_public_stratified_subset.csv")
    total=pd.concat(rows,ignore_index=True)
    assert len(total)==len(expected)*35==280
    total.to_csv(OUT/"PUBLIC_COMMERCE_TECH_PILOT_RESULTS.csv",index=False)
    pd.DataFrame([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in p.items()} for p in profiles]).to_csv(
        OUT/"PUBLIC_COMMERCE_TECH_PILOT_PROFILES.csv",index=False)
    structs=total.loc[total.selection_policy.eq("NONE")].copy()
    structs["test_coverage_pct"]=structs.coverage*100
    structs["conflict_rate_pct"]=structs.conflict_case_rate*100
    structs["true_candidate_pct"]=structs.true_in_candidate_rate*100
    structs.to_csv(OUT/"PUBLIC_COMMERCE_TECH_PILOT_STRUCTURAL.csv",index=False)
    models=total.loc[total.selection_policy.ne("NONE")].copy()
    summarize=["accuracy","balanced_accuracy","macro_f1","coverage","conflict_case_rate","true_in_candidate_rate",
               "minority_recall","minority_precision","covered_only_accuracy","fallback_accuracy","conflict_resolution_accuracy",
               "train_rule_coverage_pct","test_rule_coverage_pct","test_minus_train_coverage_pp","rule_count"]
    group=["ext_dataset_key","client_count","selection_policy"]
    s=models.groupby(group).agg(
        seeds=("seed","nunique"),
        **{f"mean_{k}":(k,"mean") for k in summarize},
        **{f"sd_{k}":(k,"std") for k in summarize},
    ).reset_index()
    assert s.seeds.eq(4).all()
    s.to_csv(OUT/"PUBLIC_COMMERCE_TECH_PILOT_POLICY_SUMMARY.csv",index=False)
    # Within each seed and architecture same frozen rule set:
    # joint winners share tie; count unique and fractional wins explicitly.
    wins=[]
    for (name,seed,clients),frame in models.groupby(["ext_dataset_key","seed","client_count"]):
        if len(frame)!=6:raise AssertionError("Missing six policies")
        for metric in TARGETS:
            scores=pd.to_numeric(frame[metric],errors="coerce")
            if scores.isna().all():continue
            if scores.isna().any():raise AssertionError("Undefined metric mixed with defined at "+str((name,seed,clients,metric)))
            high=max(scores)
            winners=frame.loc[np.isclose(scores,high,rtol=1e-10,atol=1e-12),"selection_policy"].tolist()
            for p in POLICIES:
                wins.append({"dataset":name,"seed":seed,"client_count":clients,"metric":metric,"policy":p,
                   "co_win":int(p in winners),"sole_win":int(p in winners and len(winners)==1),
                   "fractional_win":1/len(winners) if p in winners else 0,
                   "winner_count":len(winners),"score":float(scores[frame.selection_policy.eq(p)].iloc[0])})
    w=pd.DataFrame(wins)
    assert w.groupby(["dataset","seed","client_count","metric"]).fractional_win.sum().between(.999999,1.000001).all()
    w.to_csv(OUT/"PUBLIC_COMMERCE_TECH_PILOT_WIN_EVENTS.csv",index=False)
    counts=w.groupby(["dataset","metric","policy"]).agg(
       comparisons=("seed","size"),sole_wins=("sole_win","sum"),
       co_wins=("co_win","sum"),fractional_wins=("fractional_win","sum")).reset_index()
    counts.to_csv(OUT/"PUBLIC_COMMERCE_TECH_PILOT_WIN_COUNTS.csv",index=False)
    receipt={
      "status":"EXPLORATORY_4_SEEDS_COMPLETED",
      "method":"Classical positive-region reduct + LEM2 (same training pipeline as baseline)",
      "source":"UCI ML Repository public CC BY 4.0 datasets 468 and 601",
      "seeds":[1,7,21,42],
      "scenarios":["BASE"],
      "dataset_count":2,"original_datasets":{k:dict(v) for k,v in SOURCES.items()},
      "evaluated_configurations":len(total),"rule_systems":len(structs),
      "prediction_rows":len(models),"two_sources":list(SOURCES),
      "prepared_subsets":{name:{"rows":SOURCES[name]["cap"],
         "prepared_sha256":next(p["sha256_prepared_csv"] for p in profiles if p["dataset_key"]==name),
         "file":f"docs/research/public_datasets/{name}_public_stratified_subset.csv"} for name in SOURCES},
      "warnings":[
         "Four seeds, NOT 42; cannot establish robust cross-dataset superiority",
         "Public dataset is CAPPED and uses SIX prespecified features; not full source-data performance",
         "AI4I machine failures are synthetic, not observed industry incidents",
         "Data are stratified into train/test; external deployment can have temporal or distribution shift",
         "No Match means majority-class fallback under baseline, not actual abstention",
         "Class imbalance: report minority recall and Balanced Accuracy, not accuracy alone",
         "All training preprocessing/reduct/rules done on training-only, test held out"],
    }
    (OUT/"PUBLIC_COMMERCE_TECH_PILOT_MANIFEST.json").write_text(
        json.dumps(receipt,indent=2,ensure_ascii=False),encoding="utf-8")
    # Source credits are part of the redistributed dataset subset.
    (DATADIR/"README.md").write_text(
      "# Public business and technology datasets for reproducible LEM2 stress testing\n\n"
      "This folder contains **attributed, reduced and stratified** subsets of two CC BY 4.0 UCI datasets. "
      "They are independently prepared from the public originals; no private-company or user records are included.\n\n"
      "## Online Shoppers Purchasing Intention Dataset\n"
      "- Sakar, C. & Kastro, Y. (2018), UCI ML Repository, DOI: https://doi.org/10.24432/C5F88Q\n"
      "- Source: https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset\n"
      "- Public observations: 12,330; this experiment uses 1,600 stratified sampled sessions and six predefined features.\n"
      "- Revenue target is taken from the original; PageValues is deliberately NOT used.\n\n"
      "## AI4I 2020 Predictive Maintenance Dataset\n"
      "- AI4I 2020 Predictive Maintenance Dataset (2020), UCI ML Repository, DOI: https://doi.org/10.24432/C5HS5C\n"
      "- Source: https://archive.ics.uci.edu/dataset/601/ai4i\n"
      "- This is a **synthetic industrial dataset**; 10,000 public points; experiment uses 2,400 stratified sampled points.\n"
      "- The target is Machine failure; failure-category targets TWF/HDF/PWF/OSF/RNF and device IDs are excluded.\n\n"
      "## License and processing\n"
      "- Both source datasets: Creative Commons Attribution 4.0 International (CC BY 4.0).\n"
      "- License: https://creativecommons.org/licenses/by/4.0/\n"
      "- Modifications: fixed class-stratified downsampling (seed 20261112), feature subset, cleaned column names, class column normalized to string.\n"
      "- Individual 80/20 randomized train/test splits happen later, for experiment seeds 1/7/21/42; only train fits preprocessing and LEM2.\n"
      "- Source-independent evaluations and metadata: ../teacher_dashboard/data/PUBLIC_COMMERCE_TECH_PILOT_*\n"
      "- The frozen original 8,820-row matrix is NOT modified; this is a separate 4-seed feasibility pilot.\n"
      ,encoding="utf-8"
    )
    print("PUBLIC_COMMERCE_TECH_RESEARCH_PASS",len(total),"policies",len(models),"rule_systems",len(structs),flush=True)

if __name__=="__main__":
    main()
