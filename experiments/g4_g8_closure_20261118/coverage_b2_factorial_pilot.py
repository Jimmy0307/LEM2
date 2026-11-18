"""Bounded exploratory factorial: nonempty evidence, TRUE fallback and train-only supplements.

Arms per frozen model: A (original UNION) / B2 (TRUE-only fallback) x
NO_SUPPLEMENTS / ALL_TRAIN_SUPPLEMENTS / VALIDATION_GATED_SUPPLEMENTS.

The gate is selected ONLY on 16% inner validation, never outer 20% Test.
This is a bounded post-hoc feasibility POC on previously explored UCI sources,
not a new-source confirmatory experiment or proof of algorithm novelty.

Usage:
 python -m experiments.g4_g8_closure_20261118.coverage_b2_factorial_pilot \
    --dataset iris --seed 203 --regime NONIID_01 --discretizer EQUAL_WIDTH_3 \
    --out /tmp/g4-g8-coverage-pilot
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.redesign_20261116.workers import uci20_source
from fedrs.conflict_cuts import make_discretizer
from fedrs.experiment import fit_model, nested_split
from fedrs.partition import original_partition
from fedrs.predict import RULE_VARIANTS, match_matrix, variant_matrix, resolve
from fedrs.metrics import scores
from teacher_demo.supplementary_rule_coverage_pilot import generate

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "docs/research/redesign_20261116/data"
VARIANTS = ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK")
ARMS = ("NO_SUPPLEMENTS", "ALL_TRAIN_SUPPLEMENTS", "VALIDATION_GATED_SUPPLEMENTS")


def supp_matrix(frame: pd.DataFrame, supplements) -> np.ndarray:
    out = np.ones((len(frame), len(supplements)), dtype=bool)
    cache = {}
    for j, s in enumerate(supplements):
        for feat, val in s.conditions:
            if feat not in cache:
                cache[feat] = frame[feat].astype(str).to_numpy()
            out[:, j] &= cache[feat] == str(val)
    return out


def eval_arm(frame, fm, variant, supplements, matrix, selected, policy, minority):
    assert variant in VARIANTS
    y = frame[fm.target].astype(str).to_numpy()
    M = match_matrix(frame, fm.ctx.rules)
    Mv = variant_matrix(M, fm.ctx, variant)
    specific = M[:, ~fm.ctx.is_empty].any(axis=1)
    true_hit = M[:, fm.ctx.is_empty].any(axis=1)
    baseline_effective_hit = Mv.any(axis=1)
    eligible = ~baseline_effective_hit if variant == "A_ALL_RULES" else ~specific
    # Supplement supersedes TRUE-only fallback when B2 has no specific evidence.
    idx = tuple(selected)
    has_supp = np.zeros(len(frame), dtype=bool)
    if idx:
        has_supp = matrix[:, list(idx)].any(axis=1)
    rescued = eligible & has_supp
    out_pred = resolve(Mv, fm.ctx, policy)
    cand = []
    actual_active = np.zeros(len(frame), dtype=bool)
    shadow_conflict = np.zeros(len(frame), dtype=bool)
    effective_hit = baseline_effective_hit.copy()
    effective_hit |= rescued
    truths = np.zeros(len(frame), dtype=bool)
    changed = np.zeros(len(frame), dtype=bool)
    for i in range(len(frame)):
        original_ids = np.flatnonzero(Mv[i])
        original_candidates = {str(fm.ctx.rules[j].decision) for j in original_ids}
        supp_ids = [j for j in idx if matrix[i,j]]
        supp_candidates = {str(supplements[j].decision) for j in supp_ids}
        shadow = {str(fm.ctx.rules[j].decision) for j in np.flatnonzero(M[i])} | supp_candidates
        shadow_conflict[i] = len(shadow) > 1
        if rescued[i]:
            # Train-only scoring; no access to y[i] until AFTER final decision.
            values = {}
            for j in supp_ids:
                s = supplements[j]
                d = str(s.decision)
                values[d] = max(values.get(d, (-1.0,-1)), (float(s.purity), int(s.correct)))
            top = max(values.values())
            winners = sorted(d for d,v in values.items()
                             if np.isclose(v[0],top[0],rtol=0,atol=1e-12) and v[1]==top[1])
            choice = str(fm.ctx.default_class) if fm.ctx.default_class in winners else winners[0]
            changed[i] = choice != str(out_pred[i])
            out_pred[i] = choice
            active_candidates = supp_candidates
        else:
            active_candidates = original_candidates
        actual_active[i] = len(active_candidates) > 1
        truths[i] = str(y[i]) in active_candidates
    m = scores(y, out_pred)
    minority_mask = y == minority
    minority_recall = float((out_pred[minority_mask] == y[minority_mask]).mean()) if minority_mask.any() else None
    nonempty_evidence = specific | rescued
    if variant == "B2_TRUE_AS_FALLBACK":
        assert np.array_equal(baseline_effective_hit, M.any(axis=1))
    assert not np.any(rescued & specific)
    assert (effective_hit.sum() + (~effective_hit).sum()) == len(frame)
    return {
        "n":len(frame),
        "original_nonempty_coverage_pct":100*float(specific.mean()),
        "original_TRUE_only_coverage_pct":100*float(((~specific) & true_hit).mean()),
        "effective_coverage_pct":100*float(effective_hit.mean()),
        "nonempty_evidence_coverage_pct":100*float(nonempty_evidence.mean()),
        "fallback_no_match_pct":100*float((~effective_hit).mean()),
        "abstention_pct":0.0,
        "active_conflict_pct":100*float(actual_active.mean()),
        "shadow_conflict_pct":100*float(shadow_conflict.mean()),
        "correct_candidate_pct":100*float(truths.mean()),
        "rescued_count":int(rescued.sum()),
        "rescued_changed_prediction_count":int(changed.sum()),
        "test_ba_pct":100*m["ba"],"test_accuracy_pct":100*m["accuracy"],
        "test_macro_f1_pct":100*m["macro_f1"], "minority_recall_pct":(100*minority_recall if minority_recall is not None else None),
    }


def select_validated(frame, fm, variant, candidates, masks, policy, minority, max_gate=20):
    base = eval_arm(frame, fm, variant, candidates, masks, [], policy, minority)
    selected=[]
    events=[]
    current=base
    def gain(d):
        return (d["nonempty_evidence_coverage_pct"]-base["nonempty_evidence_coverage_pct"]
                -(d["active_conflict_pct"]-base["active_conflict_pct"])
                +2*(d["test_ba_pct"]-base["test_ba_pct"]))
    for i,c in enumerate(candidates):
        if len(selected)>=max_gate: break
        t = eval_arm(frame, fm, variant, candidates, masks, selected+[i], policy, minority)
        accepted = (
            t["nonempty_evidence_coverage_pct"] > current["nonempty_evidence_coverage_pct"]+1e-9
            and base["test_accuracy_pct"]-t["test_accuracy_pct"] <= 1.0+1e-9
            and base["test_ba_pct"]-t["test_ba_pct"] <= 2.0+1e-9
            and t["active_conflict_pct"]-base["active_conflict_pct"] <= 2.0+1e-9
            and gain(t) > gain(current)+1e-9
        )
        events.append({"candidate_index":i, "decision":str(c.decision),"train_purity":c.purity,
                       "train_support":c.support, "accepted":accepted,
                       "validation_nonempty_evidence_delta_pp":t["nonempty_evidence_coverage_pct"]-base["nonempty_evidence_coverage_pct"],
                       "validation_ba_delta_pp":t["test_ba_pct"]-base["test_ba_pct"]})
        if accepted:
            selected.append(i);current=t
    return selected,events


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--regime",choices=["IID","NONIID_05","NONIID_01"],required=True)
    p.add_argument("--discretizer",choices=["EQUAL_WIDTH_3","FED_MD_HIST"],required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--max-supp",type=int,default=30)
    a=p.parse_args()
    if a.max_supp<=0 or a.max_supp>80:
        raise ValueError("max-supp should be in 1..80")
    dest=a.out.resolve()
    if dest==FROZEN.resolve() or FROZEN.resolve() in dest.parents or ROOT.resolve()==dest:
        raise ValueError("Refusing to write in frozen data or repo root")
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError("Output directory must be new/empty; never overwrite prior evidence")
    src=uci20_source(a.dataset)
    dev,val,test=nested_split(src.frame,src.target,a.seed)
    clients=original_partition(dev,src.target,3,a.seed,a.regime)
    disc=make_discretizer(a.discretizer,src.features)
    fm=fit_model(src.features,src.continuous,src.categorical,src.target,clients,dev,val,test,disc)
    train=fm.frames["dev"]
    minority=str(dev[src.target].astype(str).value_counts().sort_values().index[0])
    supp,proposals=generate(train,fm.rules[:240],src.target,min_support=5,min_purity=.9,max_candidates=a.max_supp)
    mval=supp_matrix(fm.frames["val"],supp)
    mtest=supp_matrix(fm.frames["test"],supp)
    results=[]
    events=[]
    for variant in VARIANTS:
        frozen,trace=select_validated(fm.frames["val"],fm,variant,supp,mval,
                                       "GLOBAL_STRENGTH",minority)
        events.extend([{"variant":variant,**e} for e in trace])
        for arm in ARMS:
            selected = ([] if arm=="NO_SUPPLEMENTS" else
                        list(range(len(supp))) if arm=="ALL_TRAIN_SUPPLEMENTS" else frozen)
            result=eval_arm(fm.frames["test"],fm,variant,supp,mtest,selected,
                            "GLOBAL_STRENGTH",minority)
            results.append({"dataset":a.dataset,"source_sha256":src.sha256,
                            "seed":a.seed,"regime":a.regime,"discretizer":a.discretizer,
                            "rule_variant":variant,"supplement_arm":arm,
                            "supplement_source":"POOLED_DEVELOPMENT_CENTRALIZED_DIAGNOSTIC",
                            "original_rules":len(fm.rules),"true_rules":int(fm.ctx.is_empty.sum()),
                            "candidate_supplements":len(supp),"selected_supplements":len(selected),
                            "minority_class":minority,**result})
    base = {x["rule_variant"]:x for x in results if x["supplement_arm"]=="NO_SUPPLEMENTS"}
    for row in results:
        b=base[row["rule_variant"]]
        row["delta_BA_vs_own_variant_base_pp"]=row["test_ba_pct"]-b["test_ba_pct"]
        row["delta_nonempty_evidence_vs_own_variant_base_pp"]=row["nonempty_evidence_coverage_pct"]-b["nonempty_evidence_coverage_pct"]
        if row["nonempty_evidence_coverage_pct"]+1e-9 < b["nonempty_evidence_coverage_pct"]:
            raise AssertionError("Supplement reduced nonempty evidence coverage")
    dest.mkdir(parents=True,exist_ok=True)
    prefix=f"{a.dataset}_seed{a.seed}_{a.regime}_{a.discretizer}"
    output=dest/(prefix+"_ROWS.csv")
    events_path=dest/(prefix+"_GATE_EVENTS.csv")
    pd.DataFrame(results).to_csv(output,index=False)
    pd.DataFrame(events).to_csv(events_path,index=False)
    manifest={"status":"EXPLORATORY_PILOT_NOT_CONFIRMATORY","dataset":a.dataset,"seed":a.seed,
              "regime":a.regime,"discretizer":a.discretizer,
              "source_sha256":src.sha256,
              "design":"EW3/FED_MD and A/B2 and NoSupp/AllSupp/ValidationGated",
              "gate_uses":"INNER_VALIDATION_ONLY","outer_test_used_for_selection":False,
              "supplement_provenance":"POOLED_DEV_CENTRALIZED_DIAGNOSTIC_ONLY_NOT_PRIVACY_PRESERVING",
              "federated_deployability_claim":False,
              "comparison_note":"TRUE-only is not nonempty evidence; default majority prediction is not Abstention",
              "result_rows":len(results),"candidate_supplements":len(supp),
              "sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (output,events_path)}}
    (dest/(prefix+"_MANIFEST.json")).write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("G4G8_COVERAGE_B2_FACTORIAL_PILOT_PASS",prefix,"rows",len(results),"candidates",len(supp),flush=True)
    print(pd.DataFrame(results)[["rule_variant","supplement_arm","nonempty_evidence_coverage_pct",
            "effective_coverage_pct","original_TRUE_only_coverage_pct","active_conflict_pct",
            "test_ba_pct","minority_recall_pct","delta_BA_vs_own_variant_base_pp"]].to_csv(index=False),flush=True)


if __name__=="__main__":
    main()
