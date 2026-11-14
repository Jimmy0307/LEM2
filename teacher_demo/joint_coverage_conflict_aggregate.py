"""Evidence-only 20 UCI x 3 seeds x C0/C3 paired coverage/conflict audit.

The active supplemental layer runs ONLY when original LEM2 rules No Match;
the original exact rule conflict is unchanged. Full union of rules may have
shadow conflicts but those are distinct from active inference conflicts.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.joint_coverage_conflict_3seed import SEEDS

IN=Path("joint_coverage_incoming")
OUT=Path("docs/research/teacher_dashboard/data")
MODES=("BASE_LEM2","ALL_TRAIN_SUPPLEMENTS","VALIDATION_GATED_CONFLICT_AWARE")
SYSTEMS=("CENTRALIZED","FEDERATED")

def bootstrap(df,method,baseline,metric,arch):
    source=df[(df.system==arch)&df.variant.isin((method,baseline))]
    pivot=source.pivot(index=["dataset","seed"],columns="variant",values=metric)
    gains=(pivot[method]-pivot[baseline]).groupby(level="dataset").mean().to_numpy()
    assert len(gains)==20 and np.isfinite(gains).all()
    rng=np.random.default_rng(20261115)
    draws=rng.integers(0,len(gains),size=(3000,len(gains)))
    m=gains[draws].mean(axis=1)
    return {"mean_delta_pp":float(gains.mean()),
            "bootstrap_low_pp":float(np.quantile(m,.025)),
            "bootstrap_high_pp":float(np.quantile(m,.975)),
            "datasets_improved":int((gains>1e-10).sum()),
            "datasets_harmed":int((gains < -1e-10).sum()),
            "datasets_equal":int((abs(gains)<=1e-10).sum())}

def main():
    sources=json.loads((OUT/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    checks={x["key"]:x for x in sources["datasets"]}
    assert set(checks)==set(REGISTRY)
    rows=[];events=[];audits=[]
    for ds in sorted(REGISTRY):
      for seed in SEEDS:
        by_kind={}
        for kind in ("RESULTS","EVENTS","AUDIT"):
            f=IN/f"JOINT_{kind}_{ds}_seed{seed}.csv"
            assert f.exists(),f
            by_kind[kind]=pd.read_csv(f)
        r=by_kind["RESULTS"];e=by_kind["EVENTS"];a=by_kind["AUDIT"]
        assert len(r)==6 and len(a)==2
        assert r.dataset.eq(ds).all() and r.seed.eq(seed).all()
        assert r.source_sha256.eq(checks[ds]["published_file_sha256"]).all()
        assert r.groupby(["system"]).size().eq(3).all()
        assert set(r.variant)==set(MODES)
        assert r.development_rows.add(r.validation_rows).add(r.outer_test_rows).eq(checks[ds]["used_rows"]).all()
        assert r.coverage_pct.between(0,100).all()
        assert r.active_conflict_pct.between(0,100).all()
        for sys,g in r.groupby("system"):
            assert set(g.variant)==set(MODES)
            assert g.source_sha256.nunique()==1
            base=g.set_index("variant").loc["BASE_LEM2"]
            assert all(g.coverage_pct>=base.coverage_pct-1e-8)
            assert all(g.covered_count+g.no_match_count==g.n)
            assert all(g.active_conflict_count<=g.covered_count)
            assert g.loc[g.variant.eq("BASE_LEM2"),"selected_supplement_rule_count"].eq(0).all()
            assert g.loc[g.variant.eq("BASE_LEM2"),"coverage_gain_pp"].abs().lt(1e-8).all()
        assert a.system.nunique()==2
        rows.append(r);events.append(e);audits.append(a)
    raw=pd.concat(rows,ignore_index=True)
    assert len(raw)==20*3*2*3
    OUT.mkdir(parents=True,exist_ok=True)
    raw.to_csv(OUT/"G2_JOINT_COVERAGE_CONFLICT_3SEED_RESULTS.csv",index=False,float_format="%.10f")
    pd.concat(events,ignore_index=True).to_csv(OUT/"G2_JOINT_COVERAGE_CONFLICT_3SEED_EVENTS.csv",index=False)
    pd.concat(audits,ignore_index=True).to_csv(OUT/"G2_JOINT_COVERAGE_CONFLICT_3SEED_AUDIT.csv",index=False)
    metrics=("coverage_pct","no_match_pct","active_conflict_pct",
             "shadow_conflict_pct","candidate_coverage_pct",
             "accuracy_pct","balanced_accuracy_pct","macro_f1_pct",
             "selected_supplement_rule_count","rescued_count","rescued_correct_count")
    summary=(raw.groupby(["system","variant"],sort=True)
             .agg(**{k:(k,"mean") for k in metrics},
                  source_count=("dataset","nunique"),
                  paired_configs=("dataset","size"))
             .reset_index())
    assert summary.paired_configs.eq(60).all()
    summary.to_csv(OUT/"G2_JOINT_COVERAGE_CONFLICT_3SEED_SUMMARY.csv",index=False,float_format="%.10f")
    ci=[]
    for arch in SYSTEMS:
      for method in ("ALL_TRAIN_SUPPLEMENTS","VALIDATION_GATED_CONFLICT_AWARE"):
       for metric in ("coverage_pct","active_conflict_pct","shadow_conflict_pct",
                      "candidate_coverage_pct","balanced_accuracy_pct","accuracy_pct"):
        ci.append({"system":arch,"method":method,"baseline":"BASE_LEM2",
                   "metric":metric,**bootstrap(raw,method,"BASE_LEM2",metric,arch)})
    pd.DataFrame(ci).to_csv(OUT/"G2_JOINT_COVERAGE_CONFLICT_3SEED_CLUSTER_BOOTSTRAP.csv",
                            index=False,float_format="%.10f")
    # No-match/rejection semantics MUST NOT be conflated.
    receipt={"status":"SOURCE_AUDITED_20_UCI_3SEEDS_NESTED_CONFLICT_AWARE_SUPPLEMENTS",
       "datasets":20,"seeds":list(SEEDS),"architectures":list(SYSTEMS),
       "frozen_models":120,"variant_rows":len(raw),
       "source_audit":"Each row matches original UCI prepared published SHA",
       "gated_supplement_rules_selected_on_inner_validation_only":True,
       "raw_induction_rules_unchanged":True,
       "augmented_coverage_is_not_exact_Lem2_rule_coverage":True,
       "active_conflict_is_not_full_union_shadow_conflict":True,
       "no_match_is_not_abstention":True,
       "criteria_not_retuned_after_test":True,
       "warnings":["Validation gate may overfit small classes","This is a custom one-condition-drop supplement, not MLEM2 or VC-DOMLEM",
                   "No new mechanism can increase exact original LEM2 coverage unless rules are actually augmented",
                   "Three seeds across 20 domains is exploratory, not definitive causal proof",
                   "Separately report coverage gain, correct candidate gain, conflict cost, BA and accuracy"],
       "files":["G2_JOINT_COVERAGE_CONFLICT_3SEED_RESULTS.csv",
                "G2_JOINT_COVERAGE_CONFLICT_3SEED_EVENTS.csv",
                "G2_JOINT_COVERAGE_CONFLICT_3SEED_AUDIT.csv",
                "G2_JOINT_COVERAGE_CONFLICT_3SEED_SUMMARY.csv",
                "G2_JOINT_COVERAGE_CONFLICT_3SEED_CLUSTER_BOOTSTRAP.csv"]}
    (OUT/"G2_JOINT_COVERAGE_CONFLICT_3SEED_MANIFEST.json").write_text(
        json.dumps(receipt,ensure_ascii=False,indent=2),encoding="utf-8")
    print("G2_CONFLCOV_REAL_SOURCE_20_UCI_3SEED_120_RULESYSTEMS_PASS",len(raw),flush=True)
    print(summary[["system","variant","coverage_pct","active_conflict_pct",
        "shadow_conflict_pct","balanced_accuracy_pct"]].to_string(index=False),flush=True)
if __name__=="__main__":main()
