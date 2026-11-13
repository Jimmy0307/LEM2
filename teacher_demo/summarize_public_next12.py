"""Source-checked and failure-aware aggregation of twelve new UCI LEM2 stress studies.

Failed experiments remain named FAIL (no imputation). Scientific conclusion
cannot include incomplete or source mismatched tasks.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
from teacher_demo.public_next12_registry import REGISTRY

INPUT=Path("next12_incoming")
DATA=Path("docs/research/teacher_dashboard/data")
PREP=Path("docs/research/public_datasets_next12")
REPORT=Path("docs/research/teacher_dashboard/next12")
POLICIES={"FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"}

def validate(key):
    for s in ("PROFILE","BASE","SUPPLEMENT","DATA"):
        assert (INPUT/f"NEXT12_{s}_{key}."+("json" if s=="PROFILE" else "csv")).is_file(),(key,s)
    prof=json.loads((INPUT/f"NEXT12_PROFILE_{key}.json").read_text())
    assert prof["dataset_key"]==key and int(prof["uci_id"])==REGISTRY[key]["id"]
    assert prof["source_url"]==REGISTRY[key]["url"]
    assert prof["status"]=="PILOT_SEED42_SOURCE_ACQUIRED"
    assert int(prof["used_feature_count"])<=6
    assert int(prof["used_rows"])>=50 and int(prof["used_rows"])<=int(prof["source_rows"])
    frame=pd.read_csv(INPUT/f"NEXT12_DATA_{key}.csv")
    assert len(frame)==int(prof["used_rows"]) and frame.columns[-1]=="class"
    assert len(frame.columns)==int(prof["used_feature_count"])+1
    assert frame["class"].nunique()>=2 and frame["class"].value_counts().min()>=2
    assert set(frame["class"].astype(str).unique())==set(prof["class_counts"])
    assert not frame.isna().any().any()
    base=pd.read_csv(INPUT/f"NEXT12_BASE_{key}.csv")
    sup=pd.read_csv(INPUT/f"NEXT12_SUPPLEMENT_{key}.csv")
    assert len(base)==14 and len(sup)==2
    assert set(base.pilot)=={"EXTRA_PUBLIC12_SEED42"}
    assert set(base.selection_policy)=={"NONE"}|POLICIES
    assert set(base.client_count)=={0,3}
    assert not base.duplicated(["client_count","selection_policy"]).any()
    assert set(sup.client_count)=={0,3} and set(sup.seed)=={42}
    for c,d in base.groupby("client_count"):
        assert len(d)==7
        row=d[d.selection_policy=="NONE"].iloc[0]
        assert int(row.train_rows)+int(row.evaluation_rows)==len(frame)
        assert int(row.covered_count)+int(row.no_match_count)==int(row.evaluation_rows)
        assert 0<=int(row.conflict_case_count)<=int(row.covered_count)
        assert 0<=int(row.true_in_candidate_count)<=int(row.covered_count)
        assert np.isclose(row.coverage,row.covered_count/row.evaluation_rows)
        assert np.isclose(row.conflict_case_rate,row.conflict_case_count/row.evaluation_rows)
        assert np.isclose(row.true_in_candidate_rate,row.true_in_candidate_count/row.evaluation_rows)
        z=sup[sup.client_count==c].iloc[0]
        assert np.isclose(z.baseline_test_coverage_pct,100*row.coverage)
        assert z.augmented_test_coverage_pct>=z.baseline_test_coverage_pct-1e-8
    return prof,frame,base,sup

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    PREP.mkdir(parents=True,exist_ok=True)
    REPORT.mkdir(parents=True,exist_ok=True)
    passed=[];failure={};rows=[];supplements=[];catalog=[];classes=[]
    for key,cfg in REGISTRY.items():
        error=INPUT/f"NEXT12_ERROR_{key}.json"
        if error.is_file():
            failure[key]=json.loads(error.read_text(encoding="utf-8"))
            catalog.append({"key":key,"uci_id":cfg["id"],"name":cfg["name"],"status":"FAIL_NOT_IMPUTED",
                            "source":cfg["url"],"trait":cfg["research_trait"],"detail":failure[key]})
            continue
        try:prof,frame,base,sup=validate(key)
        except Exception as exc:
            failure[key]={"error":type(exc).__name__+": "+str(exc),"stage":"VALIDATION"}
            catalog.append({"key":key,"uci_id":cfg["id"],"name":cfg["name"],"status":"FAIL_NOT_IMPUTED",
                            "source":cfg["url"],"trait":cfg["research_trait"],"detail":failure[key]})
            continue
        passed.append(key)
        rows.append(base);supplements.append(sup)
        prepared=PREP/f"{key}_prepared.csv"
        shutil.copy2(INPUT/f"NEXT12_DATA_{key}.csv",prepared)
        counts=frame["class"].astype(str).value_counts().sort_index()
        for label,n in counts.items():
            classes.append({"dataset_key":key,"class_label":str(label),"rows":int(n),
                            "share_pct":100*int(n)/len(frame)})
        catalog.append({"key":key,"uci_id":cfg["id"],"name":cfg["name"],"status":"PASS_ONE_SEED",
            "source":cfg["url"],"license_source_record":cfg["source_license_claim"],
            "domain":cfg["domain"],"trait":cfg["research_trait"],
            "original_rows":int(prof["source_rows"]),"prepared_rows":len(frame),
            "original_features":int(prof["source_feature_count"]),
            "prepared_features":int(prof["used_feature_count"]),
            "class_distribution":{str(k):int(v) for k,v in counts.items()},
            "prepared_file":"docs/research/public_datasets_next12/"+prepared.name,
            "prepared_sha256":hashlib.sha256(prepared.read_bytes()).hexdigest(),
            "transform":cfg.get("label_transform"),
            "limitations":cfg.get("notes","")})
    if rows:
        full=pd.concat(rows,ignore_index=True)
        full.to_csv(DATA/"PUBLIC_NEXT12_BASE_RESULTS.csv",index=False)
        supps=pd.concat(supplements,ignore_index=True)
        supps.to_csv(DATA/"PUBLIC_NEXT12_SUPPLEMENT_RESULTS.csv",index=False)
        full[full.selection_policy.ne("NONE")].to_csv(DATA/"PUBLIC_NEXT12_SIX_POLICIES.csv",index=False)
        pd.DataFrame(classes).to_csv(DATA/"PUBLIC_NEXT12_CLASS_COUNTS.csv",index=False)
        assert len(full)==14*len(passed)
        assert len(supps)==2*len(passed)
    status="PASS_ALL_12_SOURCES" if len(passed)==12 else "PARTIAL_SOURCES_UNAVAILABLE"
    m={"status":status,"registered":12,"passed_count":len(passed),"failed_count":len(failure),
       "failed":failure,"datasets":catalog,"seeds":[42],"protocol":"HOLDOUT_80_20",
       "method":"Classical positive-region reduct + LEM2; C0 and federated C3; six selection policies; supplemental one-condition-drop purity >=.90",
       "scope":"Only first seed; capped/6-feature feasibility. NOT full source scalability or 42-seed evidence.",
       "warn":"Always separate original task class transform, especially Wine Quality >=6 derived binary label.",
       "base_rows":14*len(passed),"supplement_rows":2*len(passed)}
    (DATA/"PUBLIC_NEXT12_MANIFEST.json").write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding="utf-8")
    (PREP/"README.md").write_text(
        "# 12 additional open UCI classification datasets\n\n"+
        "Each prepared subset is source-attributed in the manifest (original UCI ID, URL and class distribution). "+
        "All source licenses are recorded as CC BY 4.0; cite original authors. "+
        "Prepared subsets and altered targets/features are DERIVED research data.\n\n"+
        "First seed 42 only; maximum six selected predictors, no all-row large-scale benchmark. "+
        "The Wine Quality target is explicitly BINARIZED as >=6 for this pilot.\n\n"+
        "Manifest: ../teacher_dashboard/data/PUBLIC_NEXT12_MANIFEST.json\n",encoding="utf-8")
    report=["# 另外 12 個公開資料集（與前 20 個來源不重複）","",
            f"狀態：**{status}**；成功 {len(passed)}/12、失敗 {len(failure)}/12。不可將失敗當成零或成功結果。",
            "第一輪 Seed=42，Classical LEM2 C0/C3，各資料集共 14 列分類／結構結果、2 列 Train-only 補充規則。","",
            "| Dataset | UCI ID | 類型與研究特性 | Source rows | Prepared rows | 資料狀態 |",
            "|---|---:|---|---:|---:|---|"]
    for x in catalog:
        report.append(f"| [{x['name']}]({x['source']}) | {x['uci_id']} | {x['trait']} | {x.get('original_rows','—')} | {x.get('prepared_rows','—')} | {x['status']} |")
    report+=["","### 注意","- 這批 12 份資料是新增來源，不計入前 20 份的 Seed 42 實驗結論。",
             "- 新資料仍為固定欄位與抽樣，不能宣稱原始全量或原始全部特徵已執行。",
             "- Wine Quality 的任務被明確轉成 >=6 二元分類；原本是有序品質標籤。",
             "- Image Segmentation 來源圖像可能重複產生關聯區塊，隨機切分有群組洩漏風險。",
             "- 若有任何來源失敗，記錄其實際原因，待修復後才加入比較。"]
    (REPORT/"README.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print("PUBLIC_NEXT12_AGGREGATE",status,len(passed),len(failure),flush=True)
    for key,info in failure.items():print("PUBLIC_NEXT12_FAILED",key,str(info)[:280])
if __name__=="__main__":main()
