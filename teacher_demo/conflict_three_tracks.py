"""Three REAL rule-level investigations on frozen published public data, Seed 42.

TRACK A: Letter 26-class coverage/candidate/conflict decomposition, each true class.
TRACK B: Wine & Grid, conflict-aware PRUNING on TRAIN in-sample only; TEST untouched.
TRACK C: Haberman, Banknote & Rice, rule-by-rule marginal TRAIN-only supplement
         selection; evaluate exact/rule-union and fallback-only effects on unseen TEST.

No single-run result may be called 42-seed, an independently validated
hyperparameter selection, a full MLEM2 reimplementation, or VC-DomLEM.
A locked prepared CSV and the existing 280-row baseline gate exact comparability.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.adapters import DatasetBundle
from roughset.schema import DatasetSchema
from roughset.core import Rule
from roughset.app import _run_split
from roughset.evaluation import matching_rules, predict_table, balanced_accuracy, classification_accuracy
from teacher_demo.full_factorial_matrix import _split_raw
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.supplementary_rule_coverage_pilot import generate, extend_predict

BASE=Path("docs/research/teacher_dashboard/data/PUBLIC20_BASE_RESULTS.csv")
PREP=Path("docs/research/public_datasets_20")
TRACKS={"letter":"A","wine":"B","grid_stability":"B","haberman":"C","banknote":"C","rice":"C"}
ARCH=("CENTRALIZED",0),("FEDERATED",3)
SEED=42

def check(cond,why):
    if not bool(cond):raise AssertionError(why)

def prepare(key):
    cfg=REGISTRY[key];path=PREP/f"{key}_prepared.csv"
    check(path.is_file(),"prepared source absent "+key)
    f=pd.read_csv(path)
    features=list(f.columns[:-1])
    continuous=list(cfg["continuous_columns"]) if cfg.get("feature_mode")=="EXPLICIT_MIXED" else (
        features if cfg["feature_mode"]=="ALL_CONTINUOUS" else [])
    categorical=[x for x in features if x not in continuous]
    for c in categorical:f[c]=f[c].astype(str)
    f["class"]=f["class"].astype(str)
    sc=DatasetSchema(target="class",features=features,continuous=continuous,categorical=categorical)
    bundle=DatasetBundle(cfg["name"],f,features,"class",sc,"uci_id:"+str(cfg["id"]))
    return bundle,hashlib.sha256(path.read_bytes()).hexdigest()

def arrays(frame,rules):
    n=len(frame);nr=len(rules)
    values={f:frame[f].astype(str).to_numpy() for f in frame.columns if f!="class"}
    m=np.ones((n,nr),dtype=bool)
    for j,rule in enumerate(rules):
        for k,v in rule.conditions:
            m[:,j]&=values[k]==str(v)
    return m

def lens(match,rules,truth):
    labels=sorted(set(map(str,truth))|set(map(lambda r:str(r.decision),rules)))
    if not labels:
        raise AssertionError("No labels")
    matrix=np.stack([match[:,[j for j,r in enumerate(rules) if str(r.decision)==label]].sum(axis=1)
                     if any(str(r.decision)==label for r in rules)
                     else np.zeros(len(match),dtype=int)
                     for label in labels],axis=1)
    return measures(matrix,labels,truth),matrix,labels

def measures(cnt,labels,truth):
    n=len(truth)
    if not n:raise ValueError("Empty subset")
    t=np.asarray([str(x) for x in truth])
    idx={key:i for i,key in enumerate(labels)}
    any_match=(cnt>0).any(axis=1)
    conflicting=(cnt>0).sum(axis=1)>1
    candidate=np.asarray([cnt[i,idx.get(v,-1)]>0 if v in idx else False for i,v in enumerate(t)])
    unique_correct=any_match & ~conflicting & candidate
    return {
        "objects":n,
        "coverage_pct":float(100*any_match.mean()),
        "conflict_pct":float(100*conflicting.mean()),
        "correct_candidate_pct":float(100*candidate.mean()),
        "conflict_free_coverage_pct":float(100*(any_match&~conflicting).mean()),
        "unique_correct_candidate_pct":float(100*unique_correct.mean()),
        "hit_count":int(any_match.sum()),
        "conflict_count":int(conflicting.sum()),
        "candidate_count":int(candidate.sum()),
    }

def reduced_metrics(train, test, rules, selected_indices):
    chosen=[rules[j] for j in selected_indices]
    t,l1,la=lens(arrays(train,chosen),chosen,train["class"].astype(str).tolist())
    u,l2,lb=lens(arrays(test,chosen),chosen,test["class"].astype(str).tolist())
    return t,u

def fixed_run(bundle,seed,arch,clients):
    x=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    x["evaluation"]["seed"]=seed;x["evaluation"]["mode"]="HOLDOUT_80_20"
    x["federated"]["partition"]="STRATIFIED"
    x["federated"]["run_client_sweep"]=False
    x["federated"]["order_sensitivity_max_permutations"]=1
    x["federated"]["n_clients"]=clients
    x["experiment"]["run_centralized"]=arch=="CENTRALIZED"
    x["experiment"]["run_federated"]=arch=="FEDERATED"
    tr,te=_split_raw(bundle,"HOLDOUT_80_20",seed,.2)
    check(not set(tr["__row_id__"])&set(te["__row_id__"]),"Train/Test contamination")
    a=_run_split(bundle,tr,te,x,quiet=True,prediction_policies=("GLOBAL_STRENGTH",),fold=1)
    artifact=a["structural_artifact"]
    rules=list(artifact.central_rules if arch=="CENTRALIZED" else artifact.global_rules)
    default=artifact.central_default_class if arch=="CENTRALIZED" else artifact.default_class
    contexts={
        "rule_support_sets":artifact.central_rule_support_sets if arch=="CENTRALIZED" else artifact.global_rule_support_sets,
        "class_sizes":artifact.central_class_sizes if arch=="CENTRALIZED" else artifact.global_class_sizes
    }
    raw=pd.read_csv(BASE)
    canonical=raw[(raw.public_dataset_key==bundle.source.split(":")[-1])] # unused, source uses numeric ID
    expected=raw[(raw.dataset==bundle.name)&(raw.seed==seed)&
                 (raw.system==arch)&(raw.client_count==clients)&(raw.selection_policy=="NONE")]
    check(len(expected)==1,"No frozen baseline for source "+bundle.name)
    baseline=expected.iloc[0]
    mt,ct,lt=lens(arrays(artifact.test,rules),rules,artifact.test["class"].to_numpy())
    check(int(baseline.evaluation_rows)==len(artifact.test),"Different holdout rows")
    check(int(baseline.rule_count)==len(rules),"Different induced rules")
    check(np.isclose(mt["coverage_pct"]/100,float(baseline.coverage),atol=1e-9),"Replay coverage mismatch")
    check(np.isclose(mt["conflict_pct"]/100,float(baseline.conflict_case_rate),atol=1e-9),"Replay conflict mismatch")
    check(np.isclose(mt["correct_candidate_pct"]/100,float(baseline.true_in_candidate_rate),atol=1e-9),"Replay candidate mismatch")
    return a,artifact,rules,default,contexts

def track_A(key,arch,clients,artifact,rules,results):
    t=artifact.test;truth=t["class"].astype(str).to_numpy()
    mm=arrays(t,rules);met,cnt,labels=lens(mm,rules,truth)
    out=results["policy_results"]["GLOBAL_STRENGTH"]["centralized" if arch=="CENTRALIZED" else "federated"]
    preds=np.asarray([str(x) for x in out["predictions"]])
    for cls in sorted(set(truth)):
        ix=truth==cls
        sub=measures(cnt[ix],labels,truth[ix])
        sub.update({"track":"A_LETTER_PER_CLASS","dataset":key,"system":arch,"client_count":clients,
                    "true_class":cls,"pred_correct_count":int((preds[ix]==truth[ix]).sum()),
                    "class_recall_pct":float(100*(preds[ix]==truth[ix]).mean()),
                    "class_rules":sum(str(r.decision)==cls for r in rules),
                    "seed":SEED})
        yield sub
    # Distinguish hits that CAN and CANNOT be resolved by winner selection.
    for i in range(len(t)):
        matched=np.flatnonzero(mm[i])
        cands=sorted({str(rules[j].decision) for j in matched})
        yield {"track":"A_LETTER_OBJECT_RECAP","dataset":key,"system":arch,"client_count":clients,
          "test_position":i,"true_class":truth[i],"candidate_classes_json":json.dumps(cands),
          "predicted_global_strength":preds[i],"covered":int(bool(matched.size)),
          "conflict":int(len(cands)>1),"candidate_correct":int(truth[i] in cands),
          "prediction_correct":int(preds[i]==truth[i]),"matched_rules":len(matched),
          "seed":SEED}
    for j,r in enumerate(rules):
        trainmask=arrays(artifact.train,[r])[:,0]
        testmask=mm[:,j]
        score=float((artifact.train.loc[trainmask,"class"].astype(str)==str(r.decision)).mean()) if trainmask.any() else np.nan
        yield {"track":"A_LETTER_RULE_AUDIT","dataset":key,"system":arch,"client_count":clients,
          "rule_index":j,"decision":str(r.decision),"antecedent_len":len(r.conditions),
          "conditions_json":json.dumps([[str(a),str(v)] for a,v in r.conditions]),
          "training_antecedent_support":int(trainmask.sum()),
          "training_purity":score,
          "test_antecedent_matches":int(testmask.sum()),
          "test_correct_target_matches":int(((truth==str(r.decision))&testmask).sum()),
          "seed":SEED}

def score_train(counts,labels,truth):
    m=measures(counts,labels,truth)
    # Deliberately fixed in advance; selected only on TRAIN data.
    return m["correct_candidate_pct"]-0.7*m["conflict_pct"]-0.1*(100-m["coverage_pct"])

def track_B(key,arch,clients,artifact,rules,default,contexts):
    train=artifact.train;test=artifact.test
    base_train,l0,labels=lens(arrays(train,rules),rules,train["class"].to_numpy())
    base_test,_l1,labels2=lens(arrays(test,rules),rules,test["class"].to_numpy())
    M=arrays(train,rules);truth=train["class"].astype(str).to_numpy()
    current=l0.copy();active=np.ones(len(rules),dtype=bool)
    loc={v:i for i,v in enumerate(labels)}
    # Fixed train-only, one-pass low-support-first removal, max 75 rules.
    candidates=sorted(range(len(rules)),key=lambda j:(int(M[:,j].sum()),j))
    removals=[]
    score=score_train(current,labels,truth)
    max_removed=75
    for j in candidates:
        if len(removals)>=max_removed:break
        which=loc[str(rules[j].decision)]
        trial=current.copy()
        trial[:,which]-=M[:,j].astype(int)
        check((trial>=0).all(),"Rule support matrix negative")
        obs=measures(trial,labels,truth)
        if (obs["coverage_pct"]>=base_train["coverage_pct"]-2.0-1e-10 and
            obs["correct_candidate_pct"]>=base_train["correct_candidate_pct"]-1.0-1e-10 and
            score_train(trial,labels,truth)>score+1e-10):
            removals.append(j);current=trial;score=score_train(trial,labels,truth)
    selected=[i for i in range(len(rules)) if active[i] and i not in set(removals)]
    selected_rules=[rules[i] for i in selected]
    train_after,test_after=reduced_metrics(train,test,rules,selected)
    orig_preds,_=predict_table(test,rules,default,"GLOBAL_STRENGTH",**contexts)
    new_preds,_=predict_table(test,selected_rules,default,"GLOBAL_STRENGTH",**contexts)
    true=test["class"].astype(str).to_numpy()
    accuracy=lambda pred:100*classification_accuracy(true,list(map(str,pred)))
    ba=lambda pred:100*balanced_accuracy(true,list(map(str,pred)))
    return {"track":"B_CONFLICT_AWARE_TRAIN_ONLY_PRUNE","dataset":key,"system":arch,
      "client_count":clients,"seed":SEED,"original_rule_count":len(rules),"remaining_rules":len(selected_rules),
      "rules_removed":len(removals),"removed_indices_json":json.dumps(removals),
      "selection_data":"SAME TRAIN USED TO FIT RULES - IN_SAMPLE HEURISTIC; NEVER TEST",
      "selection_score":"candidate_pct-0.70*conflict_pct-0.10*no_match_pct",
      "train_before_coverage_pct":base_train["coverage_pct"],"train_after_coverage_pct":train_after["coverage_pct"],
      "train_before_conflict_pct":base_train["conflict_pct"],"train_after_conflict_pct":train_after["conflict_pct"],
      "train_before_candidate_pct":base_train["correct_candidate_pct"],"train_after_candidate_pct":train_after["correct_candidate_pct"],
      "test_before_coverage_pct":base_test["coverage_pct"],"test_after_coverage_pct":test_after["coverage_pct"],
      "test_before_conflict_pct":base_test["conflict_pct"],"test_after_conflict_pct":test_after["conflict_pct"],
      "test_before_candidate_pct":base_test["correct_candidate_pct"],"test_after_candidate_pct":test_after["correct_candidate_pct"],
      "test_before_unambiguous_pct":base_test["unique_correct_candidate_pct"],
      "test_after_unambiguous_pct":test_after["unique_correct_candidate_pct"],
      "test_original_accuracy_pct":accuracy(orig_preds),"test_pruned_accuracy_pct":accuracy(new_preds),
      "test_original_ba_pct":ba(orig_preds),"test_pruned_ba_pct":ba(new_preds),
      "test_conflict_delta_pp":test_after["conflict_pct"]-base_test["conflict_pct"],
      "test_coverage_delta_pp":test_after["coverage_pct"]-base_test["coverage_pct"],
      "test_accuracy_delta_pp":accuracy(new_preds)-accuracy(orig_preds),
      "test_ba_delta_pp":ba(new_preds)-ba(orig_preds)}

def track_C(key,arch,clients,artifact,rules,default,results):
    train=artifact.train;test=artifact.test
    proposals,count=generate(train,rules[:240],artifact.target,min_support=5,
                             min_purity=.90,max_candidates=80)
    candidates=[Rule(conditions=p.conditions,decision=p.decision,source="TRAIN_ONLY_SUPPLEMENT") for p in proposals]
    initial_train,M,labels=lens(arrays(train,rules),rules,train["class"].to_numpy())
    original_test,_,_=lens(arrays(test,rules),rules,test["class"].to_numpy())
    accepted=[]
    events=[]
    live=list(rules)
    before=initial_train
    for i,(proposal,r) in enumerate(zip(proposals,candidates)):
        # Rebuild on TRAIN for each candidate to measure true marginal effect.
        after,_,_=lens(arrays(train,live+[r]),live+[r],train["class"].to_numpy())
        dC=after["coverage_pct"]-before["coverage_pct"]
        dK=after["conflict_pct"]-before["conflict_pct"]
        dT=after["correct_candidate_pct"]-before["correct_candidate_pct"]
        # A conservative predeclared budget: new conflict may not exceed 25%
        # of extra coverage; no impact gets rejected.
        take=(dC>1e-10 and dK<=0.25*dC+1e-9 and dT>=-1e-9)
        if take:live.append(r);accepted.append(proposal);before=after
        events.append({"track":"C_MARGINAL_RULE_ADD","dataset":key,"system":arch,
           "client_count":clients,"seed":SEED,"candidate_index":i,
           "conditions_json":json.dumps([[str(a),str(b)] for a,b in proposal.conditions]),
           "decision":str(proposal.decision),"train_support":proposal.support,
           "train_purity":proposal.purity,"marginal_coverage_pp":dC,
           "marginal_conflict_pp":dK,"marginal_candidate_pp":dT,
           "accepted":int(take),"reason":"PASS_GAIN_VS_CONFLICT_GATE" if take else "NO_GAIN_OR_CONFLICT_BUDGET",
           "threshold_conflict_per_new_cover":0.25})
    final_test,_,_=lens(arrays(test,live),live,test["class"].to_numpy())
    baseline=results["policy_results"]["GLOBAL_STRENGTH"]["centralized" if arch=="CENTRALIZED" else "federated"]
    preds=baseline["predictions"]
    rescued=extend_predict(test,rules,accepted,preds,default,artifact.target)
    summary={"track":"C_SAFE_TRAIN_ONLY_SUPPLEMENT","dataset":key,"system":arch,"client_count":clients,
      "seed":SEED,"proposals":count,"threshold_passed_candidates":len(proposals),
      "accepted_supplements":len(accepted),"rule_count_original":len(rules),
      "rule_count_augmented":len(live),"train_orig_coverage_pct":initial_train["coverage_pct"],
      "train_new_coverage_pct":before["coverage_pct"],
      "train_orig_conflict_pct":initial_train["conflict_pct"],
      "train_new_conflict_pct":before["conflict_pct"],
      "test_orig_coverage_pct":original_test["coverage_pct"],
      "test_new_coverage_pct":final_test["coverage_pct"],
      "test_orig_conflict_pct":original_test["conflict_pct"],
      "test_new_conflict_pct":final_test["conflict_pct"],
      "test_orig_candidate_pct":original_test["correct_candidate_pct"],
      "test_new_candidate_pct":final_test["correct_candidate_pct"],
      "test_baseline_accuracy_pct":100*rescued["baseline_accuracy"],
      "test_fallback_rescued_accuracy_pct":100*rescued["new_accuracy"],
      "test_fallback_rescued_accuracy_delta_pp":rescued["accuracy_gain_pp"],
      "test_fallback_rescued_ba_delta_pp":rescued["balanced_accuracy_gain_pp"],
      "test_fallback_rescued_count":rescued["rescued_count"],
      "method_limit":"Train-derived proposals/gate, fixed single Seed; no nested validation"}
    check(final_test["coverage_pct"]>=original_test["coverage_pct"]-1e-8,"Adding rules reduced matching")
    check(final_test["conflict_pct"]>=original_test["conflict_pct"]-1e-8,"Adding rules reduced decision conflict")
    return summary,events

def run(key,output):
    bundle,sha=prepare(key)
    outputs=[]
    for arch,clients in ARCH:
        res,art,rules,default,contexts=fixed_run(bundle,SEED,arch,clients)
        if TRACKS[key]=="A":
            outputs.extend(track_A(key,arch,clients,art,rules,res))
        elif TRACKS[key]=="B":
            outputs.append(track_B(key,arch,clients,art,rules,default,contexts))
        else:
            main,events=track_C(key,arch,clients,art,rules,default,res)
            outputs.extend([main,*events])
        print("THREE_TRACKS_ARCH_PASS",key,TRACKS[key],arch,clients,len(rules),flush=True)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(outputs).to_csv(output/f"TRACK_{TRACKS[key]}_{key}.csv",index=False)
    receipt={"dataset":key,"track":TRACKS[key],"seed":SEED,"architectures":[0,3],
             "model":"Classical reduct + LEM2","source_sha256":sha,"prepared_rows":len(bundle.frame),
             "row_count":len(outputs),"source":"committed exact prepared data, same seed and row split",
             "baseline_crosscheck":"Exact coverage, conflict, candidate and rule count against published PUBLIC20_BASE",
             "selection_only_train":True,"test_labels_for_parameter_selection":False,
             "warning":"Exploratory one seed; B prunes on in-sample TRAIN; not nested validation"}
    (output/f"TRACK_{TRACKS[key]}_{key}.json").write_text(
        json.dumps(receipt,indent=2,ensure_ascii=False),encoding="utf-8")
    print("THREE_TRACKS_DATASET_PASS",key,TRACKS[key],len(outputs),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",choices=sorted(TRACKS),required=True)
    p.add_argument("--output",default="outputs/three_tracks")
    a=p.parse_args();run(a.dataset,a.output)
if __name__=="__main__":main()
