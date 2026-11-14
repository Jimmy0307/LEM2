"""Independent prospective G4 group-by-data-source aggregation.

Target data: 20 authenticated UCI prepared CSV × NEW seeds (11,23) ×
IID/Dirichlet(.5,.1) × 9 candidate policies (6 fixed, inner ValidationBest,
Conflict-bucket routing, test Oracle diagnostic).
Nested testing; test not used to fit selector. No meta cross-domain gain claim.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.g4_rule_conflict_router import SEEDS,REGIMES,POLICY_ORDER,DEFAULT_BASE

IN=Path("g4_router_incoming")
OUT=Path("docs/research/teacher_dashboard/data")
METHODS={"FIXED_"+p for p in POLICY_ORDER}|{
 "VALIDATION_BEST","CONFLICT_BUCKET_ROUTER_V1","TEST_ORACLE_DIAGNOSTIC"}
def bootstrap(data,method,baseline,seed=20261115):
    d=data[data.method.isin((method,baseline))]
    mat=d.pivot_table(index=["dataset","seed"],columns="method",
                       values="outer_test_balanced_accuracy")
    v=(100*(mat[method]-mat[baseline])).groupby(level="dataset").mean()
    assert len(v)==20 and np.isfinite(v).all()
    vals=v.to_numpy()
    rng=np.random.default_rng(seed)
    draws=rng.integers(0,len(vals),size=(3000,len(vals)))
    means=vals[draws].mean(axis=1)
    return {"mean_gain_pp":float(vals.mean()),
            "ci95_low_pp":float(np.quantile(means,.025)),
            "ci95_high_pp":float(np.quantile(means,.975)),
            "independent_source_clusters":20,
            "improved_datasets":int((vals>1e-10).sum()),
            "harmed_datasets":int((vals < -1e-10).sum()),
            "tied_datasets":int((abs(vals)<=1e-10).sum())}
def main():
    registry=json.loads((OUT/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    original={x["key"]:x for x in registry["datasets"]}
    assert set(original)==set(REGISTRY)
    frames=[];gates=[]
    for dataset in sorted(REGISTRY):
      for seed in SEEDS:
       for regime in REGIMES:
        stem=f"{dataset}_seed{seed}_{regime}"
        path=IN/f"G4_ROUTER_{stem}.csv"
        event=IN/f"G4_EVENTS_{stem}.json"
        assert path.exists() and event.exists(),stem
        row=pd.read_csv(path)
        e=json.loads(event.read_text(encoding="utf-8"))
        assert len(row)==9 and set(row.method)==METHODS,stem
        assert row.source_sha256.eq(original[dataset]["published_file_sha256"]).all(),stem+" wrong source"
        assert set(row.seed)=={seed} and set(row.scenario)=={regime} and set(row.dataset)=={dataset}
        assert len(set(row.outer_test_coverage.round(12)))==1
        assert len(set(row.outer_test_conflict.round(12)))==1
        assert len(set(row.outer_test_candidate_correct.round(12)))==1
        assert row.dev_rows.add(row.inner_rows).add(row.outer_rows).eq(original[dataset]["used_rows"]).all()
        assert row.outer_test_balanced_accuracy.between(0,1).all()
        assert row.outer_test_accuracy.between(0,1).all()
        assert row.outer_test_conflict.between(0,1).all()
        assert bool(row.loc[row.method.eq("TEST_ORACLE_DIAGNOSTIC"),"is_deployable"].iloc[0]) is False
        assert row.loc[~row.method.eq("TEST_ORACLE_DIAGNOSTIC"),"is_deployable"].all()
        assert e["dataset"]==dataset and e["seed"]==seed and e["scenario"]==regime
        for x in e["validation_gate_events"]:
          if x["accepted"]:assert x["val_n"]>=10
        frames.append(row)
        gates.append({"dataset":dataset,"seed":seed,"scenario":regime,
            "selected_buckets":len(e["selection"]),
            "validation_buckets":len(e["validation_gate_events"]),
            "source_sha256":e["source_sha256"]})
    df=pd.concat(frames,ignore_index=True)
    assert len(df)==20*2*3*9
    OUT.mkdir(parents=True,exist_ok=True)
    df.to_csv(OUT/"G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv",index=False,float_format="%.10f")
    pd.DataFrame(gates).to_csv(OUT/"G4_ROUTER_UCI20_GATE_DECISIONS.csv",index=False)
    sm=(df.groupby(["scenario","method"]).agg(
         configs=("dataset","size"),sources=("dataset","nunique"),
         balanced_accuracy_pct=("outer_test_balanced_accuracy",lambda x:100*float(x.mean())),
         accuracy_pct=("outer_test_accuracy",lambda x:100*float(x.mean())),
         macro_f1_pct=("outer_test_macro_f1",lambda x:100*float(x.mean())),
         mean_conflict_pct=("outer_test_conflict",lambda x:100*float(x.mean())),
         mean_coverage_pct=("outer_test_coverage",lambda x:100*float(x.mean())),
         mean_candidate_correct_pct=("outer_test_candidate_correct",lambda x:100*float(x.mean())),
         mean_selected_bucket_count=("selected_bucket_count","mean")
         ).reset_index())
    sm.to_csv(OUT/"G4_ROUTER_UCI20_NEW_SEEDS_SUMMARY.csv",index=False,float_format="%.10f")
    bs=[]
    for regime in REGIMES:
        sub=df[df.scenario.eq(regime)]
        base="FIXED_"+DEFAULT_BASE[regime]
        for method in ("CONFLICT_BUCKET_ROUTER_V1","VALIDATION_BEST"):
            for ref in dict.fromkeys((base,"FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING","VALIDATION_BEST")):
                if method==ref:continue
                bs.append({"scenario":regime,"candidate":method,"baseline":ref,
                           **bootstrap(sub,method,ref)})
    pd.DataFrame(bs).to_csv(OUT/"G4_ROUTER_UCI20_DATASET_BOOTSTRAP.csv",index=False,float_format="%.10f")
    record={"status":"SOURCE_AUDITED_20_UCI_NEW_SEEDS_NESTED_ROUTING",
         "datasets":20,"seeds":list(SEEDS),"regimes":list(REGIMES),
         "configurations":20*2*3,"method_rows":len(df),
         "source_hash_policy":"PUBLIC20 published_file_sha256",
         "selection_uses_test_labels":False,
         "architecture":"FEDERATED_C3",
         "protocol":"64percent_induction_16percent_validation_20percent_unseen_test_no_refit",
         "noniid_regimes":["DIRICHLET_LABEL_SKEW_ALPHA_0.5","DIRICHLET_LABEL_SKEW_ALPHA_0.1"],
         "why_not_confirmation":[
           "Dataset domains overlap with earlier PMLB; only seeds are new",
           "Heuristic/router thresholds chosen after prior exploratory results",
           "20 source-level CI exploratory, not causal effect of label skew",
           "Exact coverage and original conflict rate invariant among six resolvers",
           "Even favorable effect needs truly distinct externally held-out source domains"],
         "files":["G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv",
                  "G4_ROUTER_UCI20_NEW_SEEDS_SUMMARY.csv",
                  "G4_ROUTER_UCI20_GATE_DECISIONS.csv",
                  "G4_ROUTER_UCI20_DATASET_BOOTSTRAP.csv"]}
    (OUT/"G4_ROUTER_UCI20_MANIFEST.json").write_text(
         json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
    print("G4_ROUTER_SOURCE_AND_LEAKAGE_AUDIT_PASS",len(df),"configs",60,flush=True)
    print(sm[sm.method.isin(["CONFLICT_BUCKET_ROUTER_V1","VALIDATION_BEST",
          "FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING"])][[
          "scenario","method","balanced_accuracy_pct"]].to_string(index=False),flush=True)
if __name__=="__main__":main()
