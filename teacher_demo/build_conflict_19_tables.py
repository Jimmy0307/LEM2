"""Build exactly 19 audit-friendly Conflict Rate (%) tables from frozen 42-seed evidence.

Every structural conflict observation comes from selection_policy=NONE. Never
multiply counts by six policies. We retain integer case/test denominators and
distinguish per-seed equal-weight means from pooled-object ratios.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path("docs/research/teacher_dashboard")
OUT=ROOT/"conflict_19"
BASE=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
NONIID=ROOT/"data/NONIID_42_RESULTS.csv"
POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL")
FACTORS=["dataset","seed","split_mode","system","client_count"]
METRIC=["conflict_case_count","evaluation_rows","conflict_rate_pct"]

def check(condition, why):
    if not bool(condition):raise AssertionError(why)

def load():
    b=pd.read_csv(BASE)
    check(len(b)==8820,"Canonical baseline must contain exactly 8820 rows")
    check(set(b.seed.astype(int))==set(range(1,43)),"Baseline missing seeds")
    check(b[b.selection_policy.eq("NONE")].shape[0]==1260,"Baseline must contain 1260 NONE rows")
    check(b[b.selection_policy.ne("NONE")].shape[0]==7560,"Baseline must contain 7560 policy rows")
    # Other six policies were evaluated on the SAME rule set, not six independent conflicts.
    b=b[b.selection_policy.eq("NONE")].copy()
    check(not b.duplicated(FACTORS).any(),"Nonunique canonical rule-set configuration")
    check(b.groupby("seed").size().eq(30).all(),"Not 30 canonical structural results per seed")
    check(b[["conflict_case_count","evaluation_rows"]].notna().all().all(),"Missing count denominator")
    check((b.conflict_case_count.astype(float)<=b.evaluation_rows.astype(float)).all(),"Impossible conflict rate")
    b["regime"]="STRATIFIED_IID"
    b["alpha"]=np.nan
    b["conflict_rate_pct"]=100*b["conflict_case_count"]/b["evaluation_rows"]
    check(np.allclose(b.conflict_rate_pct/100,b.conflict_case_rate,rtol=0,atol=1e-10),"Baseline count/rate mismatch")
    n=pd.read_csv(NONIID)
    check(len(n)==7056,"Non-IID 42-seed evidence must have 7056 rows (fully complete)")
    n=n[n.selection_policy.eq("NONE")].copy()
    check(len(n)==1008,"Expected 1008 distinct non-IID rule-set configurations")
    check(set(n.seed.astype(int))==set(range(1,43)),"Non-IID missing seeds")
    check(set(n.dirichlet_alpha.round(2))=={0.1,0.5},"Missing planned non-IID alpha")
    check(n.groupby(["seed","dirichlet_alpha"]).size().eq(12).all(),"Non-IID rows per alpha/seed must be 12")
    check(not n.duplicated(FACTORS+["dirichlet_alpha"]).any(),"Non-IID structural duplicates")
    n["regime"]="DIRICHLET_NON_IID"
    n["alpha"]=n["dirichlet_alpha"]
    n["conflict_rate_pct"]=100*n["conflict_case_count"]/n["evaluation_rows"]
    check(np.allclose(n.conflict_rate_pct/100,n.conflict_case_rate,rtol=0,atol=1e-10),"Non-IID count/rate mismatch")
    return b,n

def grouped(df, by, name):
    if df.empty:raise ValueError("Empty group "+name)
    # Each row is a rule-set config with a unique conflict/test denominator.
    t=(df.groupby(by,dropna=False,sort=True).agg(
       configuration_count=("conflict_case_count","size"),
       conflict_cases=("conflict_case_count","sum"),
       evaluation_cases=("evaluation_rows","sum"),
       mean_conflict_rate_pct=("conflict_rate_pct","mean"),
       sd_conflict_rate_pp=("conflict_rate_pct",lambda s:float(s.std(ddof=1)) if len(s)>1 else float("nan"))
     ).reset_index())
    t["pooled_conflict_rate_pct"]=100*t["conflict_cases"]/t["evaluation_cases"]
    t["source_method"]="CLASSICAL_POSITIVE_REGION_REDUCT_LEM2"
    return t

def write(name, frame, detail, rows):
    filename=f"{len(rows)+1:02d}_{name}.csv"
    # Consistent numeric percentage units; full numbers kept for re-audit.
    frame.to_csv(OUT/filename,index=False,float_format="%.10f")
    rows.append({"number":len(rows)+1,"file":filename,"description":detail,
                 "rows":len(frame),"validity":"MEASURED_42_SEEDS",
                 "scope":"Classical reduct + LEM2; percent=100*conflict_cases/evaluation_cases"})

def main():
    b,n=load()
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    both=pd.concat([b,n],ignore_index=True)
    keys=["dataset","seed","split_mode","system","client_count"]
    # 1 baseline + 3 datasets + 5 architectures + 2 splits + 2 non-IID alpha
    # + 4 seed-prefix stability tables + 2 paired IID/non-IID = EXACTLY 19.
    write("IID_ALL_CONFIGS",grouped(b,["dataset","seed","split_mode","system","client_count"],"all"),"All Classical IID rule-set configurations; policy-independent conflict",rows)
    for dataset,suffix in [("Balance Scale","BALANCE"),("Car Evaluation","CAR"),("Hayes-Roth","HAYES")]:
        d=b[b.dataset.eq(dataset)]
        write("IID_"+suffix,grouped(d,["seed","split_mode","system","client_count"],suffix),"IID "+dataset+" by Seed, split, topology",rows)
    for c in [0,2,3,4,5]:
        d=b[b.client_count.eq(c)]
        write("IID_C"+str(c),grouped(d,["dataset","seed","split_mode"],"C"+str(c)),"IID configuration C"+str(c)+" (C0 = Centralized)",rows)
    for mode,suffix in [("FULL_DATA","IN_SAMPLE"),("HOLDOUT_80_20","HOLDOUT")]:
        d=b[b.split_mode.eq(mode)]
        write("IID_"+suffix,grouped(d,["dataset","seed","system","client_count"],mode),"IID "+mode+"; never conflate Full Data with holdout",rows)
    for alpha,label in [(0.1,"01"),(0.5,"05")]:
        d=n[np.isclose(n.alpha,alpha)]
        write("NONIID_ALPHA_"+label,grouped(d,["dataset","seed","client_count"],"alpha"),"Dirichlet label skew alpha="+str(alpha)+" (complete 42 Seeds)",rows)
    hold=b[b.split_mode.eq("HOLDOUT_80_20")]
    for N in (1,7,21,42):
        d=hold[hold.seed.le(N)]
        write("IID_SEEDPREFIX_"+str(N).zfill(2),
              grouped(d,["dataset","system","client_count"],"seed"),
              "First "+str(N)+" seeds; same three datasets; SD is resampling sensitivity",rows)
    for alpha,label in [(0.1,"01"),(0.5,"05")]:
        nn=n[np.isclose(n.alpha,alpha)]
        iid=hold[hold.system.eq("FEDERATED")]
        merged=nn.merge(iid,on=["dataset","seed","client_count"],how="left",
                         suffixes=("_nonIID","_IID"),validate="one_to_one",indicator=True)
        check(merged._merge.eq("both").all(),"Missing exact IID match")
        # Paired rows explicitly retain both numerator and denominator.
        raw=pd.DataFrame({
           "dataset":merged.dataset,"seed":merged.seed,"client_count":merged.client_count,
           "alpha":alpha,
           "nonIID_conflict_cases":merged.conflict_case_count_nonIID,
           "nonIID_evaluation_cases":merged.evaluation_rows_nonIID,
           "nonIID_conflict_rate_pct":merged.conflict_rate_pct_nonIID,
           "IID_conflict_cases":merged.conflict_case_count_IID,
           "IID_evaluation_cases":merged.evaluation_rows_IID,
           "IID_conflict_rate_pct":merged.conflict_rate_pct_IID,
           "paired_difference_pp":merged.conflict_rate_pct_nonIID-merged.conflict_rate_pct_IID,
           "source_method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2"
        })
        write("PAIRED_IID_VS_NONIID_"+label,raw,"Exact same seed/dataset/C paired percent-point contrast; alpha="+str(alpha),rows)
    check(len(rows)==19,"Expected exactly 19 distinct tables")
    for rec in rows:
        check(rec["rows"]>0,"Empty table")
    catalog={
      "schema_version":1,"method":"CLASSICAL_POSITIVE_REGION_REDUCT_LEM2",
      "source_canonical":str(BASE),"source_noniid":str(NONIID),
      "raw_iid_rule_sets":int(len(b)),"raw_noniid_rule_sets":int(len(n)),
      "random_seeds":list(range(1,43)),"unit":"percent (0-100); paired delta is pp",
      "metric":"100 * pre-resolution conflict_case_count / evaluation_rows",
      "policy_independent":True,
      "note":"19 requested Conflict Rate Percentage analytical views; explicit table index, NOT 19 independent datasets or 19 classification algorithms",
      "tables":rows
    }
    (OUT/"manifest.json").write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding="utf-8")
    md=["# 19 張 Conflict Rate (%) 正式資料表","",
        "方法：Classical Rough Set 正域約簡 + LEM2；聯邦式為本地歸納後合併。",
        "只讀取 NONE 結構診斷；不把六策略重複計算成六份 Conflict。"
        "Conflict Rate (%) = 衝突物件數 / 全部評估物件數 × 100；pp = 兩個百分率直接相減。"
        "跨 Seed 的 Mean 與 pooled ratio 可能不同；每表同時保留分母與兩種均值。","",
        "| # | CSV | 列數 | 內容 |","|---:|---|---:|---|"]
    md.extend(f"| {r['number']:02} | [{r['file']}]({r['file']}) | {r['rows']} | {r['description']} |" for r in rows)
    md+=["","主矩陣 42 Seeds + IID/non-IID；本報表不代表新增外部 UCI 實驗已完成。"]
    (OUT/"README.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("CONFLICT_19_TABLES_PASS",len(rows),len(b),len(n),flush=True)

if __name__=="__main__":
    main()
