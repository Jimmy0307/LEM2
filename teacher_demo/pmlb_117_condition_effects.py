"""Evidence-only conditional effects across PMLB 109 x 3 seeds x 3 regimes.

All grouping features derived from induction data or inner validation; labels
of outer Test used ONLY to calculate held-out evaluation, not selection.
Group counts, independent family counts and source-variant caveats attached.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
D=Path("docs/research/teacher_dashboard/data")
WANTED=("FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING","VALIDATION_BEST",
        "GUARDED_SKEW_V1","LOFO_META_KNN7","TEST_ORACLE_DIAGNOSTIC")
def main():
    receipt=json.loads((D/"PMLB_117_3SEED_MANIFEST.json").read_text(encoding="utf-8"))
    assert receipt["status"]=="PASS_OVER_100_PUBLIC_BENCHMARK_TABLES" and receipt["seeds"]==[1,7,42]
    raw=pd.read_csv(D/"PMLB_117_3SEED_POLICY_SELECTIONS.csv")
    a=raw[raw.objective.eq("balanced_accuracy")&raw.method.isin(WANTED)].copy()
    assert a.groupby(["dataset","seed","scenario"]).size().eq(len(WANTED)).all()
    a["class_imbalance"]=np.where(a.train_minority_share<.1,"minority<10%",
       np.where(a.train_minority_share<.25,"10%-25%","minority>=25%"))
    a["client_divergence"]=np.where(a.client_label_js<.05,"JS<0.05",
       np.where(a.client_label_js<.15,"JS 0.05-0.15","JS>=0.15"))
    a["conflict_band"]=np.where(a.validation_conflict<.1,"conflict<10%",
       np.where(a.validation_conflict<.4,"conflict 10%-40%","conflict>=40%"))
    a["coverage_band"]=np.where(a.validation_coverage<.3,"coverage<30%",
       np.where(a.validation_coverage<.8,"coverage 30%-80%","coverage>=80%"))
    a["feature_mode"]=np.where(a.train_continuous_fraction==0,"categorical",
       np.where(a.train_continuous_fraction>.999,"numeric","mixed"))
    a["target_classes"]=np.where(a.train_num_classes==2,"binary",
       np.where(a.train_num_classes<=5,"three_to_five","six_plus"))
    groups=[]
    for field in ("scenario","class_imbalance","client_divergence","conflict_band",
                  "coverage_band","feature_mode","target_classes","source_kind"):
        for (scenario,value),g in a.groupby(["scenario",field]):
            mat=g.pivot_table(index=["dataset","family","seed"],columns="method",values="test_score_pct")
            if not set(WANTED).issubset(mat.columns):continue
            n=len(mat)
            # Family-level summary to reduce overweighting closely related variants
            fam=mat.groupby(level="family").mean()
            rows={
             "scenario":scenario,"group_by":field,"group_value":value,
             "comparisons":n,"datasets":mat.index.get_level_values("dataset").nunique(),
             "provisional_families":len(fam),
             "mean_JS":float(g.client_label_js.mean()),
             "mean_conflict_pct":100*float(g.validation_conflict.mean()),
             "mean_coverage_pct":100*float(g.validation_coverage.mean()),
            }
            for k in WANTED:
                rows["BA_"+k]=float(mat[k].mean())
            for k in ("VALIDATION_BEST","GUARDED_SKEW_V1","LOFO_META_KNN7"):
                rows["delta_"+k+"_vs_SV_pp"]=float((mat[k]-mat["FIXED_SIMPLE_VOTING"]).mean())
                rows["delta_"+k+"_vs_GS_pp"]=float((mat[k]-mat["FIXED_GLOBAL_STRENGTH"]).mean())
            rows["oracle_gain_over_best_fixed_pp"]=float((mat["TEST_ORACLE_DIAGNOSTIC"]-mat[["FIXED_GLOBAL_STRENGTH","FIXED_SIMPLE_VOTING"]].max(axis=1)).mean())
            if n>=5:groups.append(rows)
    out=pd.DataFrame(groups)
    out.to_csv(D/"PMLB_117_3SEED_CONDITIONAL_EFFECTS.csv",index=False,float_format="%.10f")
    print("PMLB_117_CONDITIONAL_EFFECTS_PASS",len(out),"seeds",receipt["seeds"],flush=True)
    for x in out[(out.group_by=="client_divergence") & (out.comparisons>=15)].to_dict("records"):
        print("CONDITION",x["scenario"],x["group_value"],"n",x["comparisons"],
              "VALBEST_VS_SV",round(x["delta_VALIDATION_BEST_vs_SV_pp"],3),
              "VALBEST_VS_GS",round(x["delta_VALIDATION_BEST_vs_GS_pp"],3),flush=True)
if __name__=="__main__":main()
