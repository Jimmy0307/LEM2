"""Rebuild a fully auditable 20-domain Coverage x Conflict atlas and row/column profiles.

Inputs are immutable, validated, published experiment artifacts; this script
never invents outcomes, fits a model on test labels, or calls an LLM.
The 20 new domains have one seed 42; two earlier domain pilots use four seeds.
Published public CSVs represent CAPPED/SUBSET data, not original full raw rows.

Main labels:
- Coverage: P(any antecedent matching).
- Conflict: P(two or more DIFFERENT candidate decisions).
- Conflict-free coverage: P(matched and exactly one decision) = C - K.
- Candidate coverage: P(true class is among matched rule decisions).
- Conflicted among covered: K/C (undefined if C=0).
- Unique correct candidate: needs object-level flags; NOT derivable from C-K.
"""
from __future__ import annotations
import json
import hashlib
import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path("docs/research")
DATA=ROOT/"teacher_dashboard/data"
OUTPUT=ROOT/"teacher_dashboard/conflict_atlas"
INPUT20=ROOT/"public_datasets_20"
INPUT2=ROOT/"public_datasets"
COLS=["dataset_key","family","source_url","source_rows","prepared_rows","source_features",
      "used_features","class_count","minority_class_rows","minority_class_rate_pct",
      "feature_mode","duplicates_full_rows","missing_cells_in_prepared","prepared_file_sha256"]
from teacher_demo.public_20_registry import REGISTRY
from teacher_demo.extreme_dataset_runner import REGISTRY as ALL_REGISTRY

def ensure(q,why):
    if not bool(q):raise AssertionError(why)

def safe(x):return None if x is None or (isinstance(x,float) and not math.isfinite(x)) else x

def profile_one(key,family,cfg,source_rows,source_feats,local_path):
    ensure(local_path.is_file(),"Missing published prepared CSV: "+str(local_path))
    frame=pd.read_csv(local_path,low_memory=False)
    ensure(len(frame)>=2 and frame.columns[-1]=="class","Invalid prepared structure "+key)
    ensure(int(frame["class"].nunique())>=2,"No multiclass target "+key)
    ensure(frame.columns.is_unique,"Duplicate normalized column names "+key)
    feat=[c for c in frame if c!="class"]
    declared=list(cfg["continuous_columns"]) if cfg.get("feature_mode")=="EXPLICIT_MIXED" else (
      feat if cfg["feature_mode"]=="ALL_CONTINUOUS" else [])
    ensure(set(declared).issubset(feat),"Declared continuous columns missing "+key)
    ensure(len(feat)<=10,"Unexpectedly many features in exact-reduct pilot "+key)
    counts=frame["class"].astype(str).value_counts(dropna=False).sort_index()
    ensure(counts.sum()==len(frame),"Class grain broken")
    filehash=hashlib.sha256(local_path.read_bytes()).hexdigest()
    row={
      "dataset_key":key,"family":family,"source_url":cfg["url"],
      "source_rows":int(source_rows),"prepared_rows":len(frame),
      "source_features":int(source_feats) if source_feats is not None else np.nan,
      "used_features":len(feat),"class_count":len(counts),
      "minority_class_rows":int(counts.min()),"minority_class_rate_pct":100*counts.min()/len(frame),
      "feature_mode":cfg["feature_mode"],"duplicates_full_rows":int(frame.duplicated().sum()),
      "missing_cells_in_prepared":int(frame.isna().sum().sum()),
      "prepared_file_sha256":filehash
    }
    labels=[{"dataset_key":key,"family":family,"class_label":str(lbl),
             "class_count":int(n),"class_pct":100*n/len(frame),
             "prepared_total":len(frame)} for lbl,n in counts.items()]
    details=[]
    for featname in feat:
        series=frame[featname]
        numeric=pd.to_numeric(series,errors="coerce")
        is_cont=featname in declared
        # Numeric-looking nominal categories remain categorical when registered as such.
        distinct=int(series.nunique(dropna=True))
        missing=int(series.isna().sum())
        explicit_missing=int(series.astype(str).eq("__MISSING_FEATURE__").sum())
        q10=q50=q90=mn=mx=np.nan
        if is_cont:
            ensure(numeric.notna().all(),"Declared numeric nonnumeric "+key+" "+featname)
            mn=float(numeric.min());mx=float(numeric.max())
            q10=float(numeric.quantile(.1));q50=float(numeric.quantile(.5));q90=float(numeric.quantile(.9))
        top=series.astype(str).value_counts().head(3)
        details.append({"dataset_key":key,"family":family,"column":featname,
          "declared_type":"CONTINUOUS" if is_cont else "CATEGORICAL",
          "pandas_dtype":str(series.dtype),"non_null_rows":int(series.notna().sum()),
          "missing_rows":missing,"explicit_missing_token_rows":explicit_missing,
          "unique_values":distinct,"unique_ratio_pct":100*distinct/len(frame),
          "top_3_values_json":json.dumps({str(v):int(n) for v,n in top.items()},ensure_ascii=False),
          "min_numeric":mn,"p10_numeric":q10,"median_numeric":q50,
          "p90_numeric":q90,"max_numeric":mx})
    return row,labels,details

def structural_pairs():
    raw=pd.read_csv(DATA/"PUBLIC20_BASE_RESULTS.csv")
    man=json.loads((DATA/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    ensure(man["status"]=="ALL_20_ONE_SEED_PASS" and man["passed_count"]==20,"20/20 frozen evidence required")
    ensure(len(raw)==280,"280 raw configurations expected")
    none=raw[raw.selection_policy.eq("NONE")].copy()
    ensure(len(none)==40,"40 structural rule systems required")
    ensure(not none.duplicated(["public_dataset_key","seed","client_count"]).any(),"Duplicated structural config")
    ensure(set(none.seed.astype(int))=={42},"Only one Seed 42")
    rows=[]
    for key in sorted(man["passed_keys"]):
        m=[x for x in man["datasets"] if x["key"]==key][0]
        a=none[(none.public_dataset_key==key)&(none.client_count==0)]
        b=none[(none.public_dataset_key==key)&(none.client_count==3)]
        ensure(len(a)==len(b)==1,"Missing source pair "+key)
        c=a.iloc[0];f=b.iloc[0]
        for x in (c,f):
            ensure(int(x.covered_count)+int(x.no_match_count)==int(x.evaluation_rows),"Covered denominator fail "+key)
            ensure(0<=int(x.conflict_case_count)<=int(x.covered_count),"Conflict denominator fail "+key)
            ensure(0<=int(x.true_in_candidate_count)<=int(x.covered_count),"Candidate denominator fail "+key)
        ensure(int(c.evaluation_rows)==int(f.evaluation_rows),"Different test denominator")
        def metrics(x):
            n=int(x.evaluation_rows);hit=int(x.covered_count);conf=int(x.conflict_case_count)
            cand=int(x.true_in_candidate_count)
            return {"coverage":100*hit/n,"conflict":100*conf/n,"candidate":100*cand/n,
                    "unambiguous":100*(hit-conf)/n,
                    "conflict_cond_covered":100*conf/hit if hit else np.nan,
                    "candidate_cond_covered":100*cand/hit if hit else np.nan}
        ca,fb=metrics(c),metrics(f)
        r={
          "dataset_key":key,"uci_id":int(m["uci_id"]),"source_rows":int(m["source_rows"]),
          "prepared_rows":int(m["used_rows"]),"feature_count":int(m["used_feature_count"]),
          "class_count":len(m["observed_classes"]),"feature_mode":m["feature_mode"],
          "minority_share_pct":100*min(m["observed_classes"].values())/int(m["used_rows"]),
          "domain":m["domain"],"seed":42,"test_rows":int(c.evaluation_rows),
          "central_rule_count":int(c.rule_count),"federated_c3_rule_count":int(f.rule_count),
          "delta_rules":int(f.rule_count)-int(c.rule_count),
        }
        for k in ca:
            r["central_"+k+"_pct"]=ca[k]
            r["fed_c3_"+k+"_pct"]=fb[k]
            r["delta_"+k+"_pp"]=fb[k]-ca[k]
        # This delta is a matched C0-vs-C3 ARCHITECTURE contrast, not
        # causal effect of adding a rule to a fixed ruleset.
        ensure(np.isclose(r["delta_unambiguous_pp"],r["delta_coverage_pp"]-r["delta_conflict_pp"]),
            "Unambiguous identity violated")
        r["conflict_cost_per_coverage_gain"]=(
            r["delta_conflict_pp"]/r["delta_coverage_pp"] if r["delta_coverage_pp"]>0 else np.nan)
        r["dominant_tradeoff"]=(
            "CONFLICT_COST_EXCEEDS_COVERAGE_GAIN" if r["delta_unambiguous_pp"]< -1e-9 else
            "NO_CHANGE" if np.isclose(r["delta_unambiguous_pp"],0) else
            "NONCONFLICT_COVERAGE_GAIN")
        rows.append(r)
    pair=pd.DataFrame(rows).sort_values("dataset_key")
    ensure(len(pair)==20,"Expected exactly 20 pairs")
    return pair

def aggregate(df,group_cols):
    agg=[]
    for key,d in df.groupby(group_cols,dropna=False):
        rec=dict(zip(group_cols,key if isinstance(key,tuple) else (key,)))
        rec.update(dataset_count=len(d),
                   mean_delta_coverage_pp=float(d.delta_coverage_pp.mean()),
                   mean_delta_conflict_pp=float(d.delta_conflict_pp.mean()),
                   mean_delta_nonconflict_coverage_pp=float(d.delta_unambiguous_pp.mean()),
                   mean_fed_c3_coverage_pct=float(d.fed_c3_coverage_pct.mean()),
                   mean_fed_c3_conflict_pct=float(d.fed_c3_conflict_pct.mean()),
                   harmed_count=int((d.delta_unambiguous_pp< -1e-9).sum()),
                   improved_count=int((d.delta_unambiguous_pp>1e-9).sum()))
        agg.append(rec)
    return pd.DataFrame(agg)

def run():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    profiles=[];labels=[];columns=[]
    man=json.loads((DATA/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    for m in man["datasets"]:
        if m["status"]!="PASS_ONE_SEED":continue
        k=m["key"];cfg=REGISTRY[k]
        x,y,z=profile_one(k,"NEW_PUBLIC20",cfg,m["source_rows"],m["source_feature_count"] if "source_feature_count" in m else None,INPUT20/f"{k}_prepared.csv")
        ensure(x["prepared_rows"]==m["used_rows"],"Prepared rows mismatch "+k)
        ensure(x["class_count"]==len(m["observed_classes"]),"Class count mismatch "+k)
        ensure({u["class_label"]:u["class_count"] for u in y}=={str(a):int(b) for a,b in m["observed_classes"].items()},
               "Class distribution mismatch "+k)
        profiles.append(x);labels.extend(y);columns.extend(z)
    # Two PREVIOUS domain pilot datasets are append-only: do not count as new 20.
    prior=DATA/"PUBLIC_COMMERCE_TECH_PILOT_MANIFEST.json"
    if prior.is_file():
        m=json.loads(prior.read_text(encoding="utf-8"))
        for key in ["online_shoppers","ai4i_maintenance"]:
            cfg=ALL_REGISTRY[key]
            path=INPUT2/f"{key}_public_stratified_subset.csv"
            if not path.is_file():continue
            x,y,z=profile_one(key,"PREVIOUS_COMMERCE_TECH_4SEEDS",cfg,
                                12330 if key=="online_shoppers" else 10000,
                                17 if key=="online_shoppers" else 6,path)
            profiles.append(x);labels.extend(y);columns.extend(z)
    ensure(len([x for x in profiles if x["family"]=="NEW_PUBLIC20"])==20,"Missing one of 20")
    ensure(len(profiles)>=20,"No data")
    for filename,data in [
      ("DATASET_ROW_COUNTS_AND_TYPES.csv",pd.DataFrame(profiles)),
      ("DATASET_CLASS_COUNTS.csv",pd.DataFrame(labels)),
      ("DATASET_COLUMN_TYPES_AND_STATS.csv",pd.DataFrame(columns))
    ]:data.to_csv(OUTPUT/filename,index=False,float_format="%.10f")
    p=structural_pairs()
    p.to_csv(OUTPUT/"PUBLIC20_COVERAGE_CONFLICT_PAIRS.csv",index=False,float_format="%.10f")
    aggregate(p,["feature_mode"]).to_csv(OUTPUT/"PUBLIC20_BY_FEATURE_TYPE.csv",index=False)
    aggregate(p,["class_count"]).to_csv(OUTPUT/"PUBLIC20_BY_CLASS_COUNT.csv",index=False)
    p.sort_values("delta_unambiguous_pp").to_csv(OUTPUT/"PUBLIC20_CONFLICT_TRADEOFF_RANKED.csv",index=False)
    # One provenance-grounded static visualization payload; JSON preserves
    # categorical labels and quote/comma-containing feature value summaries.
    payload={
        "schema":"PUBLIC20_ATLAS_V1",
        "profiles":json.loads(pd.DataFrame(profiles).to_json(orient="records",force_ascii=False)),
        "class_counts":json.loads(pd.DataFrame(labels).to_json(orient="records",force_ascii=False)),
        "column_details":json.loads(pd.DataFrame(columns).to_json(orient="records",force_ascii=False)),
        "pairs":json.loads(p.to_json(orient="records",force_ascii=False)),
        "evidence":"Seed 42 only, 20 C0/C3 pairs; 2 prior UCI domain sample profiles",
    }
    (OUTPUT/"ATLAS_DATA.json").write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False),
                                           encoding="utf-8")
    # Expose all rule-system row and class denominators to support audit.
    desc={
      "status":"SOURCE_AUDITED_20_EXPERIMENTS","scope":"Seed42 C0/C3; unchanged frozen LEM2 rules; 20 datasets, 2 architectures",
      "profiles":len(profiles),"profile_columns":len(columns),"class_rows":len(labels),
      "matched_pairs":len(p),"source_evidence":["PUBLIC20_BASE_RESULTS.csv","PUBLIC20_MANIFEST.json",
                     "public_datasets_20/*_prepared.csv"],
      "improvement_counts":{
        "coverage_gain":int((p.delta_coverage_pp>1e-9).sum()),
        "conflict_gain":int((p.delta_conflict_pp>1e-9).sum()),
        "conflict_free_coverage_harmed":int((p.delta_unambiguous_pp< -1e-9).sum())},
      "method_limitations":[
        "Training row totals and individual columns refer to published capped prepared subsets, not UCI raw data",
        "Structural data are from Seed 42 only; no confidence interval, no causal claim",
        "C0 and C3 use different fitted rule systems; architecture contrast is NOT a marginal rule-addition effect",
        "Conflict-free coverage = coverage-conflict, not accuracy nor correct-candidate rate",
        "Four-seed commerce/AI4I domain profiles are not in the matched pair analysis",
        "Class proportions are for prepared subsets and may differ from raw source distributions"]
    }
    (OUTPUT/"MANIFEST.json").write_text(json.dumps(desc,indent=2,ensure_ascii=False),encoding="utf-8")
    lines=["# 公開資料集逐 row／逐 column 與 Coverage × Conflict 實驗圖譜","",
     f"- 已驗證：20 個新資料集，20 個相同 Seed 的 C0/C3 配對；實際已發布子集 {len(profiles)} 份，欄位 {len(columns)} 筆，類別統計 {len(labels)} 筆。",
     "- 核心定義：Coverage=P(至少一條規則命中)；Conflict=P(命中規則指向兩種以上類別)；無衝突覆蓋=Coverage−Conflict。",
     "- 實驗僅 Seed 42，80/20；不是 42 Seeds。資料表原始 rows 與 prepared rows 不可混用。",
     "- 本次還保留兩個前期電商／工業資料的 profile；不把它們重新計入「新增 20 資料集」。","",
     "## 20 配對資料集：Coverage vs Conflict（百分點）","",
     "| 資料集 | 原始→實際 rows | C0 Coverage | C3 Coverage | C0 Conflict | C3 Conflict | Δ 無衝突覆蓋 |",
     "|---|---:|---:|---:|---:|---:|---:|"]
    src={x["key"]:x for x in man["datasets"]}
    for _,r in p.iterrows():
        lines.append(f"| [{r.dataset_key}]({src[r.dataset_key]['original_source']}) | {int(r.source_rows):,}→{int(r.prepared_rows):,} | {r.central_coverage_pct:.2f}% | {r.fed_c3_coverage_pct:.2f}% | {r.central_conflict_pct:.2f}% | {r.fed_c3_conflict_pct:.2f}% | {r.delta_unambiguous_pp:+.2f} pp |")
    lines+=["",
      "## 實驗資料下載",
      "- [逐資料集 row 數／類別數與欄位型態](DATASET_ROW_COUNTS_AND_TYPES.csv)",
      "- [每個決策類別的 rows 與比例](DATASET_CLASS_COUNTS.csv)",
      "- [每個因子的欄位型態、缺值、基數、分位數](DATASET_COLUMN_TYPES_AND_STATS.csv)",
      "- [20 配對 Coverage×Conflict 全量資訊](PUBLIC20_COVERAGE_CONFLICT_PAIRS.csv)",
      "- [依特徵型態分組](PUBLIC20_BY_FEATURE_TYPE.csv)",
      "- [依類別數分組](PUBLIC20_BY_CLASS_COUNT.csv)",
      "- [以無衝突覆蓋變化排序](PUBLIC20_CONFLICT_TRADEOFF_RANKED.csv)",
      "- [資料來源與公式稽核](MANIFEST.json)",
      "",
      "## 解讀限制",
      "C0 與 C3 是不同的學習規則集合，不能直接宣稱新增規則造成衝突。對衝突的因果檢驗需使用固定 R 的逐條加入／移除實驗，並以 train/validation 選規則，最後 test 僅評估。",
      "無衝突覆蓋率也不能視為正確覆蓋率，因為單一錯誤候選同樣算在內。"]
    (OUTPUT/"README.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("PUBLIC20_DATA_ATLAS_AUDIT_PASS",len(p),len(profiles),len(columns),len(labels),
          "harmed",int((p.delta_unambiguous_pp< -1e-9).sum()),flush=True)

if __name__=="__main__":run()
