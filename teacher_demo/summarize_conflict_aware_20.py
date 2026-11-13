"""Fail-closed auditor for 20 source-verified, 3-way paired coverage experiments.

Results are descriptive: one seed, inner validation, no test-based model choice.
Verifies all 20 data sources, 2 architectures, 3 variants and frozen-source SHA.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from teacher_demo.public_20_registry import REGISTRY

IN=Path("incoming_conflict_aware")
OUT=Path("docs/research/teacher_dashboard/data")
VARIANTS=("BASE_LEM2","ALL_TRAIN_SUPPLEMENTS","VALIDATION_GATED_CONFLICT_AWARE")
ARCH=(("CENTRALIZED",0),("FEDERATED",3))
KEY=["dataset","seed","system","client_count"]
COMPARED=("coverage_pct","active_conflict_pct","shadow_conflict_pct","candidate_coverage_pct",
          "accuracy_pct","balanced_accuracy_pct","macro_f1_pct","train_coverage_pct",
          "validation_coverage_pct","validation_conflict_pct","validation_accuracy_pct",
          "validation_balanced_accuracy_pct")

def require(test,why):
    if not bool(test):raise AssertionError(why)

def read_one(name):
    files=[IN/f"CONFLICT_AWARE_{k}_{name}.csv" for k in ("RESULTS","GATE_EVENTS","AUDIT")]
    for f in files:require(f.is_file(),"Missing "+str(f))
    result=pd.read_csv(files[0])
    events=pd.read_csv(files[1])
    audit=pd.read_csv(files[2])
    require(len(result)==6 and len(audit)==2,"Expected 6 outcomes, 2 audits for "+name)
    require(set(result.dataset)=={name},"Dataset mismatch")
    require(set(result.seed)=={42} and set(result.inner_seed)=={1042},"Wrong Seed")
    require(set(result.variant)==set(VARIANTS),"Missing variant")
    require(set(result.method_family)=={"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2"},"Wrong induction method")
    require(set(result.evaluation)=={"NESTED_64_16_20_UNREFITTED"},"Wrong split protocol")
    require(set(map(tuple,result[["system","client_count"]].drop_duplicates().to_numpy()))==set(ARCH),"Architecture mismatch")
    require(not result.duplicated(["dataset","system","client_count","variant"]).any(),"Repeated config")
    manifest=Path("docs/research/teacher_dashboard/data/PUBLIC20_MANIFEST.json")
    frozen=json.loads(manifest.read_text(encoding="utf-8"))
    source=next(x for x in frozen["datasets"] if x["key"]==name)
    require(source["status"]=="PASS_ONE_SEED","Original source not validated")
    dataset_file=Path("docs/research/public_datasets_20")/(name+"_prepared.csv")
    require(dataset_file.is_file(),"Missing source "+str(dataset_file))
    digest=hashlib.sha256(dataset_file.read_bytes()).hexdigest()
    require(set(result.source_sha256)=={digest},"Prepared dataset bytes changed")
    require(result.source_uci_id.eq(REGISTRY[name]["id"]).all(),"UCI ID mismatch")
    require(result.source_rows.eq(int(source["used_rows"])).all(),"Source row mismatch")
    for (system,client),group in result.groupby(["system","client_count"]):
        require(len(group)==3,"Not three variants")
        x={k:v.iloc[0] for k,v in group.groupby("variant")}
        base=x["BASE_LEM2"]; allr=x["ALL_TRAIN_SUPPLEMENTS"]; gated=x["VALIDATION_GATED_CONFLICT_AWARE"]
        for col in ("development_rows","validation_rows","outer_test_rows"):
            require(base[col]>0 and group[col].eq(base[col]).all(),"Split changed "+col)
        require(int(base.development_rows+base.validation_rows+base.outer_test_rows)==int(source["used_rows"]),
                "Train/validation/test conservation")
        require(int(base.selected_supplement_rule_count)==0,"BASE must not supplement")
        require(int(allr.selected_supplement_rule_count)==int(base.eligible_rule_count),"ALL must contain all eligible")
        require(int(gated.selected_supplement_rule_count)<=int(allr.selected_supplement_rule_count),"GATED selected more than ALL")
        for metric in COMPARED:
            if metric.endswith("pct"):require(group[metric].between(0,100).all(),"Invalid percentage "+metric)
        for mode,rec in x.items():
            require(int(rec.no_match_count+rec.covered_count)==int(rec.n),"Coverage denominator "+mode)
            require(int(rec.active_conflict_count)<=int(rec.covered_count),"Active conflicts outside accepted "+mode)
            require(int(rec.candidate_correct_count)<=int(rec.covered_count),"Oracle candidate impossible "+mode)
            require(int(rec.shadow_conflict_count)>=int(rec.active_conflict_count),"Shadow below active "+mode)
            require(np.isclose(rec.coverage_gain_pp,rec.coverage_pct-base.coverage_pct),"Coverage delta inconsistent")
            require(np.isclose(rec.accuracy_delta_pp,rec.accuracy_pct-base.accuracy_pct),"Accuracy delta inconsistent")
            require(np.isclose(rec.balanced_accuracy_delta_pp,rec.balanced_accuracy_pct-base.balanced_accuracy_pct),
                    "BA delta inconsistent")
        require(base.coverage_pct<=gated.coverage_pct+1e-9<=allr.coverage_pct+1e-8,
                "Coverage monotonicity fails")
        require(base.active_conflict_pct<=gated.active_conflict_pct+1e-9<=allr.active_conflict_pct+1e-8,
                "Active conflict monotonicity fails")
        # Hard training-validation risk constraints: NOT guaranteed for final TEST.
        require(gated.validation_accuracy_pct>=base.validation_accuracy_pct-1.00000001,
                "Validation accuracy risk gate broken")
        require(gated.validation_balanced_accuracy_pct>=base.validation_balanced_accuracy_pct-2.00000001,
                "Validation BA risk gate broken")
        ev=events[(events.system==system)&(events.client_count==client)]
        require(len(ev)==int(base.eligible_rule_count),"Missing gated rule events")
        require(int(ev.accepted.sum())==int(gated.selected_supplement_rule_count),"Gate accepted count mismatch")
        require(not ev.candidate_index.duplicated().any(),"Candidate event IDs repeated")
        ar=audit[(audit.system==system)&(audit.client_count==client)].iloc[0]
        require(int(ar.gated_accepted_count)==int(gated.selected_supplement_rule_count),"Audit gate mismatch")
        require(int(ar.eligible_count)==int(base.eligible_rule_count),"Audit candidate mismatch")
    return result,events,audit

def main():
    assert len(REGISTRY)==20
    d,e,a=[],[],[]
    for name in sorted(REGISTRY):
        row,events,audit=read_one(name)
        d.append(row);e.append(events);a.append(audit)
    OUT.mkdir(parents=True,exist_ok=True)
    result=pd.concat(d,ignore_index=True)
    events=pd.concat(e,ignore_index=True)
    audit=pd.concat(a,ignore_index=True)
    require(len(result)==120,"20 * 2 * 3 = 120")
    require(len(audit)==40,"40 rule set audits")
    result.to_csv(OUT/"CONFLICT_AWARE_20_RESULTS.csv",index=False)
    events.to_csv(OUT/"CONFLICT_AWARE_20_GATE_EVENTS.csv",index=False)
    audit.to_csv(OUT/"CONFLICT_AWARE_20_AUDIT.csv",index=False)
    pairs=[]
    for (dataset,system,client_count),group in result.groupby(["dataset","system","client_count"]):
        x={k:v.iloc[0] for k,v in group.groupby("variant")}
        b=x["BASE_LEM2"]; allr=x["ALL_TRAIN_SUPPLEMENTS"]; g=x["VALIDATION_GATED_CONFLICT_AWARE"]
        row={"dataset":dataset,"system":system,"client_count":client_count,
            "seed":42,"eligible":int(b.eligible_rule_count),"gated_selected":int(g.selected_supplement_rule_count)}
        for variant,src in (("all",allr),("gated",g)):
            for metric in ("coverage_gain_pp","active_conflict_delta_pp","shadow_conflict_delta_pp",
                           "candidate_gain_pp","accuracy_delta_pp","balanced_accuracy_delta_pp"):
                row[variant+"_"+metric]=float(src[metric])
            row[variant+"_accuracy_pct"]=float(src.accuracy_pct)
            row[variant+"_conflict_pct"]=float(src.active_conflict_pct)
            row[variant+"_coverage_pct"]=float(src.coverage_pct)
            row[variant+"_validation_coverage_pct"]=float(src.validation_coverage_pct)
            row[variant+"_validation_conflict_pct"]=float(src.validation_conflict_pct)
            row[variant+"_selected_rules"]=int(src.selected_supplement_rule_count)
        row["gated_vs_all_conflict_delta_pp"]=float(g.active_conflict_pct-allr.active_conflict_pct)
        row["gated_vs_all_coverage_delta_pp"]=float(g.coverage_pct-allr.coverage_pct)
        row["gated_vs_all_accuracy_delta_pp"]=float(g.accuracy_pct-allr.accuracy_pct)
        row["gated_vs_all_balanced_accuracy_delta_pp"]=float(g.balanced_accuracy_pct-allr.balanced_accuracy_pct)
        pairs.append(row)
    paired=pd.DataFrame(pairs)
    require(len(paired)==40,"Forty architecture-paired comparisons")
    paired.to_csv(OUT/"CONFLICT_AWARE_20_PAIRED.csv",index=False)
    metrics=["coverage_gain_pp","active_conflict_delta_pp","shadow_conflict_delta_pp","candidate_gain_pp",
             "accuracy_delta_pp","balanced_accuracy_delta_pp"]
    by_domain={}
    frozen=json.loads(Path("docs/research/teacher_dashboard/data/PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    traits={x["key"]:x for x in frozen["datasets"]}
    for (domain,type_),items in pd.DataFrame([
        {"key":key,"domain":traits[key]["domain"],"feature_mode":traits[key]["feature_mode"]}
        for key in REGISTRY
    ]).groupby(["domain","feature_mode"]):
        keys=set(items.key)
        subset=paired[paired.dataset.isin(keys)]
        by_domain[domain+" / "+type_]={
           "dataset_count":len(keys),
           "mean_all_test_coverage_gain_pp":float(subset.all_coverage_gain_pp.mean()),
           "mean_gated_test_coverage_gain_pp":float(subset.gated_coverage_gain_pp.mean()),
           "mean_all_conflict_gain_pp":float(subset.all_active_conflict_delta_pp.mean()),
           "mean_gated_conflict_gain_pp":float(subset.gated_active_conflict_delta_pp.mean()),
           "mean_all_accuracy_gain_pp":float(subset.all_accuracy_delta_pp.mean()),
           "mean_gated_accuracy_gain_pp":float(subset.gated_accuracy_delta_pp.mean())}
    manifest={
      "status":"ALL_20_EXPERIMENTS_VALIDATED",
      "new_dataset_count":20,"dataset_architectures":40,
      "comparison_rows":120,"candidate_gate_events":len(events),
      "seed":42,"inner_validation_seed":1042,
      "data":"UCI pre-existing 20 validated fixed class-stratified prepared subsets",
      "method":"Classical positive-region reduct + LEM2, Centralized and Federated C3",
      "protocol":{
       "outer_test":"20% never fit or gate","development":"64% induction + preprocessor",
       "inner_validation":"16% used only to accept/reject supplementary rules",
       "refit_after_gate":False,
       "variants":VARIANTS,
       "baseline_prediction":"GLOBAL_STRENGTH, majority fallback on exact No Match",
       "supplement_activation":"ONLY when original exact rule set has No Match",
       "candidate":"single antecedent deletion; at least five Train examples and 90% Train purity, max80",
       "selection":"fixed Train-quality order; inner validation greedy one-pass",
       "gate":"new validation coverage >0, validation accuracy loss <=1pp, BA loss <=2pp, additive conflict budget max(2pp, 0.35*coverage_gain), score coverage-conflict+2*BA",
       "conflict_types":["active_conflict_pct","shadow_conflict_pct"],
       "not_implemented":"True abstain / VC-DomLEM / original MLEM2 supplemental algorithm"
      },
      "severe_caveats":[
       "One Seed 42, descriptive pilot only; neither significance nor generalization guarantees",
       "Discovery trains on 64%, unlike previously frozen 80%-train benchmark",
       "Gating uses validation labels to select rules; valid test remains untouched but gate can overfit 16%",
       "Conflict guard is validation-based, and DOES NOT guarantee fewer conflicts on unseen test",
       "No Match uses train-majority fallback and is not actual rejection",
       "Source large datasets only run on capped <=1800 rows and <=6 prespecified features"],
      "type_domain_results":by_domain
    }
    (OUT/"CONFLICT_AWARE_20_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("CONFLICT_AWARE_20_AUDIT_PASS",len(result),len(paired),len(events),flush=True)
    for mode in ("all","gated"):
        print("METHOD",mode,"COVERAGE",round(float(paired[mode+"_coverage_gain_pp"].mean()),3),
              "CONFLICT",round(float(paired[mode+"_active_conflict_delta_pp"].mean()),3),
              "ACCURACY",round(float(paired[mode+"_accuracy_delta_pp"].mean()),3),
              "BALANCED_ACCURACY",round(float(paired[mode+"_balanced_accuracy_delta_pp"].mean()),3),flush=True)

if __name__=="__main__":main()
