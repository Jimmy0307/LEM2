"""Aggregate external UCI exploratory stress artifacts without inventing missing results."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np

NAMES=("tictactoe","cmc","glass","nursery","wisconsin_original","voting_records","zoo")
SEEDS=(1,42)
SCENARIOS=("BASE","TRAIN_LABEL_FLIP20")
OUT=Path("docs/research/teacher_dashboard/data")

def main():
    src=Path("external_stress_artifacts")
    OUT.mkdir(parents=True,exist_ok=True)
    paths=sorted(src.glob("STRESS_*.csv"))
    profiles=sorted(src.glob("PROFILE_*.json"))
    expected={(d,s,c) for d in NAMES for s in SEEDS for c in SCENARIOS}
    observed=set();frames=[];pmeta=[]
    for path in paths:
        df=pd.read_csv(path)
        if len(df)!=35:raise AssertionError("Not exactly 35 outcomes: "+path.name)
        spec=df.iloc[0]
        k=(str(spec.ext_dataset_key),int(spec.seed),str(spec.scenario))
        if k not in expected or k in observed:raise AssertionError("Unknown/duplicate job "+repr(k))
        assert set(df.selection_policy)=={"NONE","FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING",
                                         "GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"}
        assert df.groupby("client_count").size().to_dict()=={0:7,2:7,3:7,4:7,5:7}
        assert df.groupby("client_count").selection_policy.nunique().eq(7).all()
        assert df.iloc[0].split_mode=="HOLDOUT_80_20"
        # Cohesive structural metrics across 6 policies for each fixed rule set.
        for key,one in df.groupby("client_count"):
            assert np.allclose(one.conflict_case_rate.values,one.conflict_case_rate.iloc[0])
            assert np.allclose(one.coverage.values,one.coverage.iloc[0])
            assert np.isclose(one.conflict_case_count.iloc[0]/one.evaluation_rows.iloc[0],
                              one.conflict_case_rate.iloc[0])
        observed.add(k)
        frames.append(df)
    for path in profiles:
        m=json.loads(path.read_text(encoding="utf-8"))
        k=(m["dataset_key"],int(m["seed"]),m["scenario"])
        if k not in observed:raise AssertionError("Profile without valid scored run "+repr(k))
        pmeta.append(m)
    assert len(pmeta)==len(observed),"Missing profiles"
    if not frames:raise AssertionError("No external experiments completed")
    data=pd.concat(frames,ignore_index=True)
    if data.duplicated(["ext_dataset_key","seed","scenario","system","client_count","selection_policy"]).any():
        raise AssertionError("Duplicate experiment result")
    data.to_csv(OUT/"EXTREME_UCI_PILOT_RESULTS.csv",index=False)
    structural=data[data.selection_policy.eq("NONE")].copy()
    structural["conflict_rate_pct"]=100*structural.conflict_case_rate
    structural["coverage_pct"]=100*structural.coverage
    structural["true_in_candidate_pct"]=100*structural.true_in_candidate_rate
    structural.to_csv(OUT/"EXTREME_UCI_PILOT_CONFLICT.csv",index=False)
    strategies=data[data.selection_policy.ne("NONE")].copy()
    summary=(strategies.groupby(["ext_dataset_key","scenario","client_count","selection_policy"],dropna=False)
       .agg(seeds=("seed","nunique"),accuracy=("accuracy","mean"),
            balanced_accuracy=("balanced_accuracy","mean"),macro_f1=("macro_f1","mean"),
            conflict_only_accuracy=("conflict_resolution_accuracy","mean"),
            conflict_resolvable_accuracy=("accuracy_in_resolvable_conflict","mean"),
            conflict_rate=("conflict_case_rate","mean"),coverage=("coverage","mean"),
            true_in_candidate=("true_in_candidate_rate","mean"),
            conflict_resolvable_rate=("conflict_resolvable_rate","mean"),
            mean_rule_count=("rule_count","mean")).reset_index())
    summary.to_csv(OUT/"EXTREME_UCI_PILOT_POLICY_SUMMARY.csv",index=False)
    profiles_df=pd.DataFrame([{k:v if not isinstance(v,(dict,list)) else json.dumps(v,sort_keys=True)
                               for k,v in row.items()} for row in pmeta])
    profiles_df.to_csv(OUT/"EXTREME_UCI_PILOT_PROFILES.csv",index=False)
    dataset_seeds={name:sorted(int(s) for x,s,c in observed if x==name and c=="BASE") for name in NAMES}
    receipt={
     "status":"EXPLORATORY_2_SEED_PILOT" if len(observed)==len(expected) else "PARTIAL_EXPLORATORY_PILOT",
     "expected_jobs":len(expected),"completed_jobs":len(observed),
     "missing_jobs":[{"dataset":x,"seed":s,"scenario":c} for x,s,c in sorted(expected-observed)],
     "rows":len(data),"n_datasets":len({x for x,s,c in observed}),
     "seeds":[1,42],"scenarios":list(SCENARIOS),
     "dataset_seeds":dataset_seeds,
     "method":"Classical positive-region reduct + LEM2, exact minimum cardinality",
     "disclaimer":"Pilot is 2-seed only. Not 42-seed, not external clinical validity, and not combined with frozen 8820 baseline.",
     "source":"UCI ML Repository via ucimlrepo. See EXTREME_UCI_PILOT_PROFILES.csv for URL, hashes, original and used columns.",
     "metrics":"NoMatch, Conflict, Candidate availability computed independently on same test. Six policies share same rule set.",
    }
    (OUT/"EXTREME_UCI_PILOT_MANIFEST.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding="utf-8")
    print("EXTERNAL_UCI_PILOT_AGGREGATE_PASS",len(observed),len(expected),len(data),flush=True)

if __name__=="__main__":main()
