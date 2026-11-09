"""Browser-compatible adapter around the ORIGINAL roughset LEM2 implementation.

Input: global __USER_INPUT_JSON__ (str, JSON with columns/rows/target/seed/split/clients).
Output: global __USER_RESULT_JSON__ (JSON string).
Do not put predictions, rules, or metrics into the 42-seed baseline evidence file.
"""
import json
import math
from copy import deepcopy

import numpy as np
import pandas as pd

from roughset.adapters import DatasetBundle
from roughset.schema import DatasetSchema, clean_column_name
from roughset.app import _run_split
from roughset.splitting import stratified_train_test_split
from roughset.evaluation import matching_rules, population_support_summary
from roughset.federated import partition_clients

POLICIES = (
    "FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING",
    "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL",
)

def finite(x):
    try:
        f = float(x)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None

def safe_str(x):
    return str(x) if pd.notna(x) else ""

def prepare(raw):
    orig = [str(x) for x in raw["columns"]]
    cols = [clean_column_name(x) for x in orig]
    if len(set(cols)) != len(cols):
        raise ValueError("欄位名稱標準化後重複（例如 A-B 與 A B）。請重新命名。")
    target = clean_column_name(raw["target"])
    if target not in cols:
        raise ValueError("找不到指定決策欄位。")
    if not orig or len(orig) < 2 or len(orig) > 40:
        raise ValueError("CSV 至多支援 40 欄，請先排除識別欄與不必要欄位。")
    values = raw["rows"]
    if len(values) < 4 or len(values) > 2500:
        raise ValueError("瀏覽器試算支援 4～2,500 筆；更大資料請使用 GitHub 原始 CLI。")
    if any(len(row) != len(cols) for row in values):
        raise ValueError("CSV 各列欄位數量不一致。")
    df = pd.DataFrame(values, columns=cols, dtype=str)
    if df.isna().any().any() or (df.astype(str).apply(lambda col: col.str.strip()) == "").any().any():
        raise ValueError("資料有缺值／空字串；此版本不自行補值，請先處理。")
    df = df.apply(lambda col: col.str.strip())
    if df[target].nunique() < 2:
        raise ValueError("決策欄至少要有兩種不同類別。")
    ignore = {clean_column_name(x) for x in raw.get("ignore", [])}
    if target in ignore:
        raise ValueError("決策欄位不能排除。")
    unknown=ignore-set(cols)
    if unknown:
        raise ValueError("排除欄位不存在："+",".join(sorted(unknown)))
    features = [x for x in cols if x != target and x not in ignore]
    if not features:
        raise ValueError("排除後沒有剩餘條件特徵。")
    if len(features) > 8:
        raise ValueError("啟用最小基數 Reduct 時，瀏覽器最多支援 8 個條件屬性，避免指數級搜尋。")
    return DatasetBundle(
        name="Custom CSV", frame=df, features=features, target=target,
        schema=DatasetSchema(target=target, features=features, ignore=sorted(ignore)), source="user-browser-memory"
    )

def one_case(row, rules, weights, support, sizes, default, predicted, target, features):
    matched = matching_rules(row, rules)
    choices = sorted({safe_str(r.decision) for r in matched})
    truth = safe_str(row[target])
    grouped = {}
    for rule in matched:
        grouped.setdefault(safe_str(rule.decision), []).append(rule)
    pop = population_support_summary(matched, support, sizes)
    scores = []
    for label in sorted(grouped):
        group = grouped[label]
        ctx = pop.get(label, {})
        t = float(ctx.get("total_support_occurrences", 0))
        u = float(ctx.get("unique_population", 0))
        n = float(ctx.get("class_size", 0))
        scores.append({
            "decision": label, "rule_hits": len(group), "T": t, "U": u,
            "N": n, "P": (u / t if t else 0),
            "SIMPLE_VOTING": len(group),
            "STANDARD_VOTING": sum(float(weights.get(rule.key,0)) for rule in group),
            "GLOBAL_STRENGTH": (u/n if n else 0),
            "POPULATION_STANDARD": u,
            "POPULATION_GLOBAL": (u*u/(n*t) if n and t else 0),
        })
    outcomes = {}
    for policy, winner in predicted.items():
        if not matched:
            reason = "NO_MATCH_FALLBACK_CORRECT" if winner == truth else "NO_MATCH_FALLBACK_WRONG"
        elif truth not in choices:
            reason = "TRUE_CLASS_NOT_CANDIDATE"
        elif winner == truth:
            reason = "CANDIDATE_SELECTED_CORRECT"
        else:
            reason = "CANDIDATE_PRESENT_BUT_SELECTED_WRONG"
        outcomes[policy] = {"winner": winner, "correct": winner==truth, "error_type":reason}
    return {
        "row_id": int(row["__row_id__"]), "features": {k:safe_str(row[k]) for k in features},
        "true":truth, "matched_count":len(matched), "candidates":choices,
        "conflict":len(choices)>1, "default_class":safe_str(default),
        "scores": scores,
        "matched_rules":[{"if":[[str(a),safe_str(v)] for a,v in rule.conditions],
            "then":safe_str(rule.decision),
            "weight":finite(weights.get(rule.key,0))} for rule in matched[:50]],
        "matched_rules_truncated":len(matched)>50,
        "outcomes":outcomes,
    }

def run(raw):
    bundle = prepare(raw)
    seed = int(raw.get("seed",42))
    clients = int(raw.get("clients",0))
    split = str(raw.get("split","HOLDOUT_80_20"))
    if seed not in range(1,43) or clients not in (0,2,3,4,5):
        raise ValueError("Seed 應介於 1～42；Client 僅能為 0 或 2～5。")
    if split not in ("HOLDOUT_80_20","FULL_DATA"):
        raise ValueError("無效切分模式。")
    partition = str(raw.get("partition","STRATIFIED")).upper()
    alpha = float(raw.get("alpha",0.5))
    bins = int(raw.get("bins",3))
    reduct_enabled = bool(raw.get("reduct_enabled",True))
    if partition not in ("STRATIFIED","DIRICHLET_LABEL_SKEW"):
        raise ValueError("未知的 Client 分割方法。")
    if not 0.01 <= alpha <= 10:
        raise ValueError("Dirichlet alpha 請介於 0.01～10。")
    if bins not in (2,3,4,5):
        raise ValueError("離散化 bins 請選 2、3、4 或 5。")
    cfg={
        "evaluation":{"seed":seed,"mode":split,"test_ratio":0.2},
        "preprocessing":{"auto_discretize":True,"unique_numeric_threshold":10,"n_bins":bins},
        "federated":{"n_clients":clients,"partition":partition,
                     "dirichlet_alpha":alpha,"dirichlet_max_retries":100,
                     "run_client_sweep":False,"order_sensitivity_max_permutations":1},
        "experiment":{"run_centralized":clients==0,
                      "run_federated":clients!=0,"prediction_policy":"FIRST_MATCH"},
        "reduct":{"enabled":reduct_enabled,"method":"MINIMUM_CARDINALITY",
                  "selection":"LEXICOGRAPHIC_FIRST","record_all_candidates":True},
    }
    raw_df=bundle.frame.copy().reset_index(drop=True)
    raw_df["__row_id__"]=np.arange(len(raw_df),dtype=int)
    if split=="HOLDOUT_80_20":
        raw_train,raw_test=stratified_train_test_split(raw_df,bundle.target,0.2,seed)
    else:
        raw_train=raw_df.copy();raw_test=raw_df.copy()
    result=_run_split(bundle,raw_train,raw_test,cfg,quiet=True,prediction_policies=POLICIES,fold=1)
    art=result["structural_artifact"]
    key="centralized" if clients==0 else "federated"
    rules=list(art.central_rules if clients==0 else art.global_rules)
    weights=art.central_rule_weights if clients==0 else art.global_rule_weights
    support=art.central_rule_support_sets if clients==0 else art.global_rule_support_sets
    class_sizes=art.central_class_sizes if clients==0 else art.global_class_sizes
    default=art.central_default_class if clients==0 else art.default_class
    outputs={policy:result["policy_results"][policy][key] for policy in POLICIES}
    metrics={}
    for policy,o in outputs.items():
        metrics[policy]={k:finite(o.get(k)) for k in (
            "accuracy","balanced_accuracy","macro_f1","coverage",
            "conflict_resolution_accuracy","target_coverage_macro",
            "target_candidate_coverage_macro")}
    cases=[]
    tests=art.test
    for i,(_,row) in enumerate(tests.iterrows()):
        predictions={name:safe_str(output["predictions"][i]) for name,output in outputs.items()}
        cases.append(one_case(row,rules,weights,support,class_sizes,default,predictions,bundle.target,bundle.features))
    classes=[]
    for label in sorted({x["true"] for x in cases}):
        same=[c for c in cases if c["true"]==label];n=len(same)
        d={"decision":label,"n":n,"coverage":sum(c["matched_count"]>0 for c in same)/n,
           "candidate_coverage":sum(label in c["candidates"] for c in same)/n,
           "conflict_rate":sum(c["conflict"] for c in same)/n}
        for p in POLICIES:
            d["recall_"+p]=sum(c["outcomes"][p]["correct"] for c in same)/n
        classes.append(d)
    failure_counts={}
    for policy in POLICIES:
        counts={}
        for c in cases:
            typ=c["outcomes"][policy]["error_type"]
            counts[typ]=counts.get(typ,0)+1
        failure_counts[policy]=counts
    assigned={}
    if clients:
        original_client_tables=partition_clients(
            raw_train,target_col=bundle.target,n_clients=clients,seed=seed,
            strategy=partition,dirichlet_alpha=alpha,dirichlet_max_retries=100)
        for client_name,frame in original_client_tables.items():
            for row_id in frame["__row_id__"]:
                assigned[int(row_id)]=client_name
    train_ids=set(int(x) for x in raw_train["__row_id__"])
    test_ids=set(int(x) for x in raw_test["__row_id__"])
    assignments=[
        {"row_id":i,"decision":safe_str(raw_df.iloc[i][bundle.target]),
         "in_train":i in train_ids,"in_evaluation":i in test_ids,
         "client":assigned.get(i,"Centralized" if i in train_ids else "Test")}
        for i in range(len(raw_df))
    ]
    return {
        "provenance":"CANONICAL_PYTHON_IN_BROWSER; user CSV; not in frozen 8820",
        "dataset_rows":len(raw_df), "train_rows":len(raw_train),
        "test_rows":len(raw_test), "seed":seed, "split":split, "clients":clients,
        "partition":partition,"alpha":alpha,"bins":bins,"reduct_enabled":reduct_enabled,
        "ignored_columns":sorted({clean_column_name(x) for x in raw.get("ignore", [])}),
        "features":bundle.features, "target":bundle.target,
        "assignments":assignments,
        "condition_columns":list(art.condition_columns),
        "rule_count":len(rules), "rules":[{"if":[[str(k),safe_str(v)] for k,v in r.conditions],
                                          "then":safe_str(r.decision)} for r in rules[:80]],
        "rules_truncated":len(rules)>80,
        "selected_reduct":list(art.central_reduct_result.selected_reduct)
                if clients==0 and art.central_reduct_result is not None else None,
        "client_reducts":{k:list(v.selected_reduct) for k,v in art.local_reduct_results.items() if v},
        "local_rule_counts":{k:len(v) for k,v in art.local_rules.items()},
        "metrics":metrics,"classes":classes,"error_decomposition":failure_counts,
        "cases":cases,
    }

__USER_RESULT_JSON__=json.dumps(run(json.loads(__USER_INPUT_JSON__)),ensure_ascii=False,allow_nan=False)
