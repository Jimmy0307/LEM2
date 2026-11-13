"""Conflict-aware supplementary rule selection on 20 public UCI datasets.

Three paired models, ONE frozen development rule set per dataset/architecture:
 A BASE: Classical positive-region reduct + LEM2 with Global Strength
 B ALL: every Train-developed purity>=.90, support>=5 supplementary rule (max80)
 C GATED: greedily accept supplementary rules only when INNER VALIDATION
          coverage rises without breaching active conflict/risk budgets.

CRITICAL: true nested partition:
    Outer Holdout test: 20% (never used for induction, candidate discovery or gate)
    Outer Train: 80% -> Development 80% / Validation 20%
    Model fitting, reduct, preprocessing, supp purity: Development only.
    Gating/conflict/accuracy thresholds: Validation only.
    Final Test: once after gate frozen. No model refit on outer train.
These results DO NOT equal earlier 80%-train baseline values.

Supplements are invoked ONLY on exact No Match (priority to original rules).
Thus "active conflict" measures conflicting candidate decisions among the
rule layer actually invoked; "shadow conflict" measures full naive union.
No-Match is fallback majority, not an actual abstention decision.
This is author-defined supplement heuristic and rule gate; NOT VC-DomLEM.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from roughset.adapters import DatasetBundle
from roughset.app import _run_split
from roughset.evaluation import matching_rules,predict_table,balanced_accuracy,macro_f1_score
from roughset.preprocessing import apply_preprocessor
from roughset.schema import DatasetSchema
from roughset.splitting import stratified_train_test_split
from teacher_demo.full_factorial_matrix import _split_raw
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.supplementary_rule_coverage_pilot import generate

DATA=Path("docs/research/public_datasets_20")
SEED=42
INNER_SEED=1042
PURITY=.90
SUPPORT=5
MAX_SOURCE_RULES=240
MAX_SUPP=80
MAX_GATED=40
VALIDATION_ACC_LOSS_PP=1.0
VALIDATION_BA_LOSS_PP=2.0
CONFLICT_FLOOR_PP=2.0
CONFLICT_RATIO=.35
CONFLICT_PENALTY=1.0
BA_REWARD=2.0
ARCHITECTURES=(("CENTRALIZED",0),("FEDERATED",3))

def load_bundle(name):
    cfg=REGISTRY[name]
    p=DATA/(name+"_prepared.csv")
    if not p.is_file():raise FileNotFoundError(p)
    raw=p.read_bytes()
    df=pd.read_csv(p)
    assert df.columns[-1]=="class" and len(df.columns)>=2
    feats=[c for c in df if c!="class"]
    expected=cfg.get("feature_columns") or feats
    assert feats==expected,(name,feats,expected)
    if cfg["feature_mode"]=="EXPLICIT_MIXED": continuous=list(cfg["continuous_columns"])
    elif cfg["feature_mode"]=="ALL_CONTINUOUS":continuous=list(feats)
    else:continuous=[]
    categorical=[x for x in feats if x not in continuous]
    for x in categorical:df[x]=df[x].astype("string").fillna("__MISSING_FEATURE__").astype(str)
    for x in continuous:df[x]=pd.to_numeric(df[x],errors="raise")
    df["class"]=df["class"].astype(str)
    assert df.isna().sum().sum()==0
    schema=DatasetSchema(target="class",features=feats,continuous=continuous,categorical=categorical)
    bundle=DatasetBundle(cfg["name"],df,feats,"class",schema,f"uci_id:{cfg['id']}:prepared")
    return bundle,hashlib.sha256(raw).hexdigest()

def original_projection(data,rules,default,weights,supports,classes,target):
    preds,matched=predict_table(data,rules,default,prediction_policy="GLOBAL_STRENGTH",
               rule_weights=weights,rule_support_sets=supports,class_sizes=classes)
    exact=np.asarray([bool(x) for x in matched],dtype=bool)
    base_cands=[{str(r.decision) for r in m} for m in matched]
    true=data[target].astype(str).to_numpy()
    assert len(preds)==len(true)
    return {
      "pred":np.asarray(preds,dtype=str),"exact":exact,
      "candidates":base_cands,"true":true,"n":len(true)
    }

def candidate_masks(data,supplements):
    n=len(data);m=len(supplements)
    out=np.zeros((n,m),dtype=bool)
    raw={a:data[a].astype(str).to_numpy() for s in supplements for a,_ in s.conditions}
    for j,s in enumerate(supplements):
        mask=np.ones(n,dtype=bool)
        for attr,value in s.conditions:mask &= (raw[attr]==str(value))
        out[:,j]=mask
    return out

class EvalView:
    def __init__(self,proj,supplements,masks,default):
        self.p=proj;self.supp=supplements;self.m=masks;self.default=str(default)
        self.n=int(proj["n"])
        assert self.m.shape==(self.n,len(self.supp))

    def measure(self,selected):
        selected=list(selected)
        assert len(selected)==len(set(selected))
        pred=self.p["pred"].copy()
        true=self.p["true"]
        exact=self.p["exact"]
        candidates=[set(x) for x in self.p["candidates"]]
        active_conflicts=np.fromiter((len(x)>1 for x in candidates),count=self.n,dtype=bool)
        shadow_conflicts=active_conflicts.copy()
        rescued=np.zeros(self.n,dtype=bool)
        for i in range(self.n):
            matching=[self.supp[j] for j in selected if self.m[i,j]]
            if matching:
                full=candidates[i]|{str(x.decision) for x in matching}
                shadow_conflicts[i]=len(full)>1
            if exact[i] or not matching:continue
            rescued[i]=True
            # Identical resolution contract as previous unconditional pilot:
            # maximum (train_purity, training_correct), tie to train majority.
            score={}
            for s in matching:
                d=str(s.decision)
                value=(float(s.purity),int(s.correct))
                if d not in score or value>score[d]:score[d]=value
            top=max(score.values())
            winners=sorted(d for d,v in score.items() if
                            np.isclose(v[0],top[0],rtol=0,atol=1e-12) and v[1]==top[1])
            pred[i]=self.default if self.default in winners else winners[0]
            candidates[i]={str(s.decision) for s in matching}
            active_conflicts[i]=len(candidates[i])>1
        covered=exact|rescued
        acc=100*float((pred==true).mean())
        ba=100*float(balanced_accuracy(true,pred))
        macro=100*float(macro_f1_score(true,pred))
        return {
          "n":self.n,"predictions":pred,
          "covered_count":int(covered.sum()),"coverage_pct":100*float(covered.mean()),
          "no_match_count":int((~covered).sum()),"no_match_pct":100*float((~covered).mean()),
          "active_conflict_count":int(active_conflicts.sum()),
          "active_conflict_pct":100*float(active_conflicts.mean()),
          "shadow_conflict_count":int(shadow_conflicts.sum()),
          "shadow_conflict_pct":100*float(shadow_conflicts.mean()),
          "candidate_correct_count":int(sum(truth in classes for truth,classes in zip(true,candidates))),
          "candidate_coverage_pct":100*float(np.mean([truth in classes for truth,classes in zip(true,candidates)])),
          "accuracy_pct":acc,"balanced_accuracy_pct":ba,"macro_f1_pct":macro,
          "rescued_count":int(rescued.sum()),
          "rescued_correct_count":int((rescued&(pred==true)).sum()),
          "rescued_changed_prediction_count":int((rescued&(pred!=self.p["pred"])).sum())
        }

def gate_select(validation_view):
    baseline=validation_view.measure([])
    allrules=validation_view.measure(list(range(len(validation_view.supp))))
    selected=[]
    current=baseline
    events=[]
    # Fixed greedy one-pass order is derived from TRAIN purity/support,
    # never from validation label rankings or test results.
    for j,s in enumerate(validation_view.supp):
        if len(selected)>=MAX_GATED:break
        trial=validation_view.measure(selected+[j])
        added=trial["coverage_pct"]-current["coverage_pct"]
        conflict_from_base=trial["active_conflict_pct"]-baseline["active_conflict_pct"]
        coverage_from_base=trial["coverage_pct"]-baseline["coverage_pct"]
        acc_loss=baseline["accuracy_pct"]-trial["accuracy_pct"]
        ba_loss=baseline["balanced_accuracy_pct"]-trial["balanced_accuracy_pct"]
        score=lambda x: (x["coverage_pct"]-baseline["coverage_pct"]
             -CONFLICT_PENALTY*(x["active_conflict_pct"]-baseline["active_conflict_pct"])
             +BA_REWARD*(x["balanced_accuracy_pct"]-baseline["balanced_accuracy_pct"]))
        accepted=bool(
            added>1e-9 and
            acc_loss<=VALIDATION_ACC_LOSS_PP+1e-9 and
            ba_loss<=VALIDATION_BA_LOSS_PP+1e-9 and
            conflict_from_base <= max(CONFLICT_FLOOR_PP,CONFLICT_RATIO*coverage_from_base)+1e-9 and
            score(trial)>score(current)+1e-9
        )
        events.append({
            "candidate_index":j,"decision":str(s.decision),"conditions":repr(s.conditions),
            "train_support":int(s.support),"train_purity_pct":100*float(s.purity),
            "new_validation_match_count":int(trial["covered_count"]-current["covered_count"]),
            "validation_conflict_delta_pp":float(trial["active_conflict_pct"]-current["active_conflict_pct"]),
            "validation_accuracy_delta_pp":float(trial["accuracy_pct"]-current["accuracy_pct"]),
            "validation_BA_delta_pp":float(trial["balanced_accuracy_pct"]-current["balanced_accuracy_pct"]),
            "validation_score_gain":float(score(trial)-score(current)),
            "accepted":accepted
        })
        if accepted:
            selected.append(j);current=trial
    return selected,baseline,allrules,current,events

def flatten(name,system,clients,mode,metric,vs_baseline,meta):
    fields={k:v for k,v in metric.items() if k!="predictions"}
    row={"dataset":name,"seed":SEED,"inner_seed":INNER_SEED,"system":system,
         "client_count":clients,"variant":mode,**fields,**meta}
    row["coverage_gain_pp"]=row["coverage_pct"]-vs_baseline["coverage_pct"]
    row["active_conflict_delta_pp"]=row["active_conflict_pct"]-vs_baseline["active_conflict_pct"]
    row["shadow_conflict_delta_pp"]=row["shadow_conflict_pct"]-vs_baseline["shadow_conflict_pct"]
    row["candidate_gain_pp"]=row["candidate_coverage_pct"]-vs_baseline["candidate_coverage_pct"]
    row["accuracy_delta_pp"]=row["accuracy_pct"]-vs_baseline["accuracy_pct"]
    row["balanced_accuracy_delta_pp"]=row["balanced_accuracy_pct"]-vs_baseline["balanced_accuracy_pct"]
    return row

def one(name,output):
    bundle,digest=load_bundle(name)
    outer_train,outer_test=_split_raw(bundle,"HOLDOUT_80_20",SEED,.2)
    induction,validation=stratified_train_test_split(outer_train,bundle.target,test_ratio=.20,seed=INNER_SEED)
    all_ids=[set(x["__row_id__"].astype(int)) for x in (induction,validation,outer_test)]
    assert not(all_ids[0]&all_ids[1] or all_ids[0]&all_ids[2] or all_ids[1]&all_ids[2])
    cfg=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    cfg["evaluation"]["seed"]=SEED
    cfg["evaluation"]["mode"]="HOLDOUT_80_20"
    cfg["federated"]["partition"]="STRATIFIED"
    cfg["federated"]["run_client_sweep"]=False
    cfg["federated"]["order_sensitivity_max_permutations"]=1
    rows=[];events=[];rule_audits=[]
    for system,c in ARCHITECTURES:
        x=deepcopy(cfg)
        x["experiment"]["run_centralized"]=system=="CENTRALIZED"
        x["experiment"]["run_federated"]=system=="FEDERATED"
        x["federated"]["n_clients"]=c
        # Only discovery data are fitted. The inner holdout acts as validation
        # and outer test is not supplied to this function.
        result=_run_split(bundle,induction,validation,x,quiet=True,
                          prediction_policies=("GLOBAL_STRENGTH",),fold=1)
        art=result["structural_artifact"]
        test=apply_preprocessor(outer_test,result["preprocessor"],bundle.target)
        assert len(test)>0 and len(art.test)>0 and len(art.train)>0
        rules=list(art.central_rules if system=="CENTRALIZED" else art.global_rules)
        default=art.central_default_class if system=="CENTRALIZED" else art.default_class
        weights=art.central_rule_weights if system=="CENTRALIZED" else art.global_rule_weights
        supports=art.central_rule_support_sets if system=="CENTRALIZED" else art.global_rule_support_sets
        classes=art.central_class_sizes if system=="CENTRALIZED" else art.global_class_sizes
        def view(data,supp):
            projection=original_projection(data,rules,default,weights,supports,classes,art.target)
            return EvalView(projection,supp,candidate_masks(data,supp),default)
        selected_rules,candidates=generate(
            art.train,rules[:MAX_SOURCE_RULES],art.target,
            min_support=SUPPORT,min_purity=PURITY,max_candidates=MAX_SUPP
        )
        valview=view(art.test,selected_rules)
        selection,_,_,_,gate_events=gate_select(valview)
        # Final test is evaluated ONLY AFTER all candidates are filtered.
        testview=view(test,selected_rules)
        trainview=view(art.train,selected_rules)
        variants={
          "BASE_LEM2":[],
          "ALL_TRAIN_SUPPLEMENTS":list(range(len(selected_rules))),
          "VALIDATION_GATED_CONFLICT_AWARE":selection
        }
        base_test=testview.measure([])
        base_train=trainview.measure([])
        base_val=valview.measure([])
        for mode,idxs in variants.items():
            test_metrics=testview.measure(idxs)
            train_metrics=trainview.measure(idxs)
            validation_metrics=valview.measure(idxs)
            metadata={
              "source_sha256":digest,
              "source_uci_id":REGISTRY[name]["id"],
              "source_rows":len(bundle.frame),
              "development_rows":len(art.train),
              "validation_rows":len(art.test),
              "outer_test_rows":len(test),
              "train_coverage_pct":train_metrics["coverage_pct"],
              "train_coverage_gain_pp":train_metrics["coverage_pct"]-base_train["coverage_pct"],
              "validation_coverage_pct":validation_metrics["coverage_pct"],
              "validation_conflict_pct":validation_metrics["active_conflict_pct"],
              "validation_accuracy_pct":validation_metrics["accuracy_pct"],
              "validation_balanced_accuracy_pct":validation_metrics["balanced_accuracy_pct"],
              "original_rule_count":len(rules),
              "proposed_rule_count":candidates,
              "eligible_rule_count":len(selected_rules),
              "selected_supplement_rule_count":len(idxs),
              "source_rule_budget":MAX_SOURCE_RULES,
              "method_family":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
              "supplement_type":"TRAIN_ONLY_ONE_ANTECEDENT_DROP_NOT_MLEM2",
              "evaluation":"NESTED_64_16_20_UNREFITTED",
              "validation_policy":"ONE_PASS_GREEDY_GATED_V1"
            }
            rows.append(flatten(name,system,c,mode,test_metrics,base_test,metadata))
            assert test_metrics["n"]==len(test)
            assert test_metrics["no_match_count"]+test_metrics["covered_count"]==len(test)
            assert test_metrics["active_conflict_count"]<=test_metrics["covered_count"]
            assert test_metrics["candidate_correct_count"]<=test_metrics["covered_count"]
        for event in gate_events:
            events.append({"dataset":name,"seed":SEED,"system":system,
                           "client_count":c,**event})
        rule_audits.append({
           "dataset":name,"seed":SEED,"system":system,"client_count":c,
           "candidate_count":candidates,"eligible_count":len(selected_rules),
           "gated_accepted_count":len(selection),
           "gated_rejected_count":len(selected_rules)-len(selection),
           "validation_coverage_base":base_val["coverage_pct"],
           "test_coverage_base":base_test["coverage_pct"],
           "test_conflict_base":base_test["active_conflict_pct"],
           "test_shadow_conflict_all":testview.measure(variants["ALL_TRAIN_SUPPLEMENTS"])["shadow_conflict_pct"]
        })
        print("CONFLICT_AWARE_TRIAL_PASS",name,system,"rules",len(rules),
              "supp",len(selected_rules),"gate",len(selection),
              "testcoverage",round(base_test["coverage_pct"],2),flush=True)
    assert len(rows)==6 and len(rule_audits)==2
    target=Path(output);target.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(target/f"CONFLICT_AWARE_RESULTS_{name}.csv",index=False)
    pd.DataFrame(events,columns=["dataset","seed","system","client_count","candidate_index","decision",
        "conditions","train_support","train_purity_pct","new_validation_match_count","validation_conflict_delta_pp",
        "validation_accuracy_delta_pp","validation_BA_delta_pp","validation_score_gain","accepted"]).to_csv(
        target/f"CONFLICT_AWARE_GATE_EVENTS_{name}.csv",index=False)
    pd.DataFrame(rule_audits).to_csv(target/f"CONFLICT_AWARE_AUDIT_{name}.csv",index=False)
    print("CONFLICT_AWARE_DATASET_PASS",name,len(rows),len(events),flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",required=True,choices=sorted(REGISTRY))
    ap.add_argument("--output",default="outputs/conflict_aware")
    a=ap.parse_args()
    one(a.dataset,a.output)

if __name__=="__main__":main()
