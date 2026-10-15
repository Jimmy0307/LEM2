from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Mapping, Sequence
import json
import math

import numpy as np
import pandas as pd

from .adapters import DatasetBundle, load_local_file, load_uci_dataset_by_id
from .evaluation import run_centralized
from .federated import partition_clients, run_federated
from .preprocessing import detect_feature_types, fit_shared_preprocessor, apply_preprocessor
from .sources import discover_local_files, parse_uci_sources, resolve_uci_doi
from .splitting import stratified_train_test_split, stratified_kfold_splits
from .paper import run_paper_protocol, published_comparison
from .environment import environment_manifest
from .pipeline import build_rule_system, evaluate_resolvers


def _deep_defaults(config: Mapping[str, Any]) -> Dict[str, Any]:
    defaults = {
        "input": {
            "mode": "AUTO",
            "local_folder": "./real_data/local",
            "schemas_folder": "./real_data/schemas",
            "uci_sources_file": "./real_data/uci_sources.txt",
            "run_local_files": True,
            "run_uci_sources": True,
            "sheet_name": 0,
            "uci_drop_missing_target": True,
        },
        "experiment": {
            "run_centralized": True,
            "run_federated": True,
            "prediction_policy": "FIRST_MATCH",
        },
        "evaluation": {"mode": "HOLDOUT", "test_ratio": 0.20, "cv_folds": 10, "seed": 42},
        "preprocessing": {"auto_discretize": True, "unique_numeric_threshold": 10, "n_bins": 3},
        "federated": {
            "n_clients": 5,
            "partition": "STRATIFIED",
            "dirichlet_alpha": 0.5,
            "dirichlet_max_retries": 100,
            "run_client_sweep": True,
            "client_counts": [2, 3, 4, 5],
            "order_sensitivity_max_permutations": 120,
        },
        "paper": {"enabled": False, "reference": "WANG_2007", "cv_folds": 10},
        "reduct": {
            "enabled": True,
            "method": "MINIMUM_CARDINALITY",
            "selection": "LEXICOGRAPHIC_FIRST",
            "record_all_candidates": True,
        },
        "report": {"outputs_folder": "./outputs", "show_rules": True, "show_rule_limit": 10},
    }
    out = deepcopy(defaults)
    for section, values in config.items():
        if isinstance(values, Mapping) and isinstance(out.get(section), Mapping):
            out[section].update(values)
        else:
            out[section] = values
    return out


def validate_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    cfg = _deep_defaults(config)
    mode = str(cfg["input"]["mode"]).upper()
    if mode not in {"AUTO", "LOCAL", "UCI"}:
        raise ValueError("input.mode must be AUTO, LOCAL, or UCI.")
    emode = str(cfg["evaluation"]["mode"]).upper()
    if emode not in {"HOLDOUT", "K_FOLD_CV"}:
        raise ValueError("evaluation.mode must be HOLDOUT or K_FOLD_CV.")
    policy = str(cfg["experiment"]["prediction_policy"]).upper()
    if policy not in {"FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"}:
        raise ValueError("Unsupported prediction policy.")
    if not (cfg["experiment"]["run_centralized"] or cfg["experiment"]["run_federated"]):
        raise ValueError("Enable at least one of run_centralized/run_federated.")
    if int(cfg["preprocessing"]["n_bins"]) < 2:
        raise ValueError("preprocessing.n_bins must be >= 2.")
    reduct_cfg = cfg["reduct"]
    if str(reduct_cfg["method"]).upper() != "MINIMUM_CARDINALITY":
        raise ValueError("reduct.method must be MINIMUM_CARDINALITY.")
    if str(reduct_cfg["selection"]).upper() != "LEXICOGRAPHIC_FIRST":
        raise ValueError("reduct.selection must be LEXICOGRAPHIC_FIRST.")
    if not isinstance(reduct_cfg["enabled"], bool):
        raise ValueError("reduct.enabled must be a boolean.")
    if not isinstance(reduct_cfg["record_all_candidates"], bool):
        raise ValueError("reduct.record_all_candidates must be a boolean.")
    return cfg


def _schema_path_for(file_path: Path, schemas_folder: Path) -> Path | None:
    candidate = schemas_folder / f"{file_path.stem}.schema.json"
    return candidate if candidate.exists() else None


def discover_datasets(config: Mapping[str, Any], fetcher=None) -> Sequence[DatasetBundle]:
    cfg = validate_config(config)
    inp = cfg["input"]
    mode = str(inp["mode"]).upper()
    bundles = []
    if mode in {"AUTO", "LOCAL"} and bool(inp["run_local_files"]):
        local_folder = Path(inp["local_folder"])
        schemas_folder = Path(inp["schemas_folder"])
        for path in discover_local_files(local_folder):
            bundles.append(load_local_file(path, _schema_path_for(path, schemas_folder), inp.get("sheet_name", 0)))
    if mode in {"AUTO", "UCI"} and bool(inp["run_uci_sources"]):
        cache_file = Path(inp["uci_sources_file"]).parent / ".cache" / "uci_doi_map.json"
        for source in parse_uci_sources(Path(inp["uci_sources_file"])):
            uci_id = int(source.value) if source.kind == "uci_id" else resolve_uci_doi(source.value, cache_file)
            bundles.append(load_uci_dataset_by_id(uci_id, fetcher=fetcher, drop_missing_target=bool(inp.get("uci_drop_missing_target", True))))
    if not bundles:
        raise ValueError(
            "No datasets found. Put CSV/XLSX files in real_data/local, or add uci_id:/doi: entries to real_data/uci_sources.txt."
        )
    return bundles


def _feature_types(bundle: DatasetBundle, raw_train: pd.DataFrame, prep_cfg: Mapping[str, Any]):
    schema = bundle.schema
    explicit_cont = list(schema.continuous)
    explicit_cat = list(schema.categorical) + list(schema.ordinal.keys())
    explicit = set(explicit_cont) | set(explicit_cat)
    remaining = [f for f in bundle.features if f not in explicit]
    auto_cont, auto_cat = detect_feature_types(
        raw_train,
        remaining,
        unique_numeric_threshold=int(prep_cfg["unique_numeric_threshold"]),
    ) if remaining else ([], [])
    continuous = explicit_cont + auto_cont
    categorical = explicit_cat + auto_cat
    return continuous, categorical


def _run_split(
    bundle: DatasetBundle,
    raw_train: pd.DataFrame,
    raw_test: pd.DataFrame,
    cfg: Mapping[str, Any],
    quiet: bool = True,
    prediction_policies: Sequence[str] | None = None,
    fold: int = 1,
):
    structural_started = perf_counter()
    target = bundle.target
    prep_cfg = cfg["preprocessing"]
    fed_cfg = cfg["federated"]
    exp_cfg = cfg["experiment"]
    continuous, categorical = _feature_types(bundle, raw_train, prep_cfg)
    if continuous and not bool(prep_cfg["auto_discretize"]):
        raise ValueError("Continuous features detected but preprocessing.auto_discretize=false.")

    raw_clients = None
    if exp_cfg["run_federated"]:
        raw_clients = partition_clients(
            raw_train,
            target_col=target,
            n_clients=int(fed_cfg["n_clients"]),
            seed=int(cfg["evaluation"]["seed"]),
            strategy=str(fed_cfg["partition"]),
            dirichlet_alpha=float(fed_cfg["dirichlet_alpha"]),
            dirichlet_max_retries=int(fed_cfg["dirichlet_max_retries"]),
        )
    prep_source = raw_clients if raw_clients is not None else {"Training": raw_train}
    preprocessor = fit_shared_preprocessor(
        prep_source,
        bundle.features,
        target,
        continuous,
        categorical,
        int(prep_cfg["n_bins"]),
    )
    train = apply_preprocessor(raw_train, preprocessor, target)
    test = apply_preprocessor(raw_test, preprocessor, target)
    condition_columns = list(preprocessor["condition_columns"])

    clients = (
        {name: apply_preprocessor(df, preprocessor, target) for name, df in raw_clients.items()}
        if raw_clients is not None
        else None
    )
    artifact = build_rule_system(
        train,
        test,
        condition_columns,
        target,
        clients=clients,
        reduct_enabled=bool(cfg["reduct"]["enabled"]),
        reduct_selection=str(cfg["reduct"]["selection"]),
        run_central=bool(exp_cfg["run_centralized"]),
        run_federated=bool(exp_cfg["run_federated"]),
        metadata={
            "dataset": bundle.name,
            "source": bundle.source,
            "evaluation_mode": str(cfg["evaluation"]["mode"]).upper(),
            "fold": fold,
            "seed": int(cfg["evaluation"]["seed"]),
            "client_count": len(clients or {}),
        },
        order_sensitivity_max_permutations=int(fed_cfg["order_sensitivity_max_permutations"]),
    )
    structural_elapsed = perf_counter() - structural_started
    structural_metrics = dict(artifact.structural_metrics)
    structural_metrics["rule_system_build_seconds"] = structural_metrics.get(
        "structural_build_seconds"
    )
    structural_metrics["structural_build_seconds"] = structural_elapsed
    artifact = replace(
        artifact,
        structural_build_seconds=structural_elapsed,
        structural_metrics=structural_metrics,
    )
    selected_policies = list(prediction_policies or [exp_cfg["prediction_policy"]])
    policy_results = evaluate_resolvers(artifact, selected_policies)
    active_policy = str(exp_cfg["prediction_policy"]).upper()
    if active_policy not in policy_results:
        active_policy = selected_policies[0]
    central = policy_results[active_policy]["centralized"]
    federated = policy_results[active_policy]["federated"]
    if federated is not None:
        federated["partition_strategy"] = str(fed_cfg["partition"]).upper()
    return {
        "preprocessor": preprocessor,
        "train": train,
        "test": test,
        "centralized": central,
        "federated": federated,
        "structural_artifact": artifact,
        "central_reduct_result": artifact.central_reduct_result,
        "local_reduct_results": artifact.local_reduct_results,
        "policy_results": policy_results,
        "structural_metrics": artifact.structural_metrics,
        "structural_tables": artifact.tables,
    }


def _finite_summary(values, prefix):
    arr=np.asarray(values,dtype=float); arr=arr[np.isfinite(arr)]
    if not len(arr): return {f"{prefix}_mean":float("nan"),f"{prefix}_std":float("nan"),f"{prefix}_min":float("nan"),f"{prefix}_max":float("nan")}
    return {f"{prefix}_mean":float(arr.mean()),f"{prefix}_std":float(arr.std(ddof=0)),f"{prefix}_min":float(arr.min()),f"{prefix}_max":float(arr.max())}


def _aggregate_cv(folds, key):
    modules=[f[key] for f in folds if f.get(key) is not None]
    if not modules: return None
    diagnostic_fields=[
        "avg_local_rule_count","total_local_rule_count","global_rule_count",
        "pairwise_jaccard_antecedent","pairwise_jaccard_full_rule",
        "conflict_group_count","conflict_antecedent_rate","conflict_rule_share",
        "conflict_case_count","conflict_case_rate","conflict_resolution_accuracy",
        "pre_resolution_conflict_case_rate","conflict_cases_count","non_conflict_cases_count",
        "conflict_balanced_accuracy","conflict_macro_f1","order_sensitivity_rate",
        "order_sensitivity_conflict_rate","order_balanced_accuracy_mean",
        "order_balanced_accuracy_std","order_balanced_accuracy_min","order_balanced_accuracy_max",
        "all_case_disagreement_rate_vs_first_match","conflict_case_disagreement_rate_vs_first_match",
    ]
    rows=[]
    for i,r in enumerate(modules,1):
        rules=r.get("rules",r.get("global_rules",[]))
        row={"fold":i,"accuracy":r.get("accuracy"),"balanced_accuracy":r.get("balanced_accuracy"),"macro_f1":r.get("macro_f1"),"coverage":r.get("coverage"),"rule_count":len(rules)}
        for field in diagnostic_fields: row[field]=r.get(field)
        rows.append(row)
    table=pd.DataFrame(rows)
    out={"accuracy":float(table.accuracy.mean()),"accuracy_std":float(table.accuracy.std(ddof=0)),"balanced_accuracy":float(table.balanced_accuracy.mean()),"balanced_accuracy_std":float(table.balanced_accuracy.std(ddof=0)),"macro_f1":float(table.macro_f1.mean()),"macro_f1_std":float(table.macro_f1.std(ddof=0)),"coverage":float(table.coverage.mean()),"coverage_std":float(table.coverage.std(ddof=0)),"mean_rule_count":float(table.rule_count.mean()),"fold_metrics":table,"prediction_policy":modules[0].get("prediction_policy")}
    for field in ("accuracy", "balanced_accuracy", "macro_f1", "coverage", "rule_count"):
        out.update(_finite_summary(table[field].tolist(), field))
    out["mean_rule_count"] = out["rule_count_mean"]
    for field in diagnostic_fields:
        out.update(_finite_summary(pd.to_numeric(table[field],errors="coerce").tolist(), field))
    if key=="federated":
        out["client_count"]=modules[0].get("client_count")
        out["order_invariant_by_design"] = modules[0].get("order_invariant_by_design", False)
        out["order_sensitivity_status"] = modules[0].get("order_sensitivity_status", "MEASURED")
        order_tables=[]
        for fold_no,module in enumerate(modules,1):
            t=module.get("order_distribution_table")
            if isinstance(t,pd.DataFrame) and not t.empty:
                x=t.copy(); x.insert(0,"fold",fold_no); order_tables.append(x)
        if order_tables:
            pooled=pd.concat(order_tables,ignore_index=True); out["order_distribution_table"]=pooled
            out["orderings_checked_per_fold"]=max(len(t) for t in order_tables); out["orderings_checked_total"]=len(pooled)
            for col,prefix in [("accuracy","order_accuracy"),("balanced_accuracy","order_balanced_accuracy"),("macro_f1","order_macro_f1"),("coverage","order_coverage"),("conflict_resolution_accuracy","order_conflict_resolution_accuracy")]:
                out.update(_finite_summary(pooled[col].tolist(),prefix))
    return out


def _run_dataset(
    bundle: DatasetBundle,
    cfg: Mapping[str, Any],
    prediction_policies: Sequence[str] | None = None,
) -> Dict[str, Any]:
    raw=bundle.frame.copy().reset_index(drop=True); raw["__row_id__"]=np.arange(len(raw),dtype=int)
    ev=cfg["evaluation"]
    selected_policies=list(prediction_policies or [cfg["experiment"]["prediction_policy"]])
    if str(ev["mode"]).upper()=="HOLDOUT":
        train,test=stratified_train_test_split(raw,bundle.target,float(ev["test_ratio"]),int(ev["seed"]))
        split=_run_split(bundle,train,test,cfg,quiet=True,prediction_policies=selected_policies,fold=1)
        result={"name":bundle.name,"source":bundle.source,"rows":len(raw),"features":bundle.features,"target":bundle.target,"schema":{"continuous":list(bundle.schema.continuous),"categorical":list(bundle.schema.categorical),"ordinal":dict(bundle.schema.ordinal),"ignore":list(bundle.schema.ignore)},"evaluation_mode":"HOLDOUT",**split}
        result["structural_artifacts"]=[split["structural_artifact"]]
        result["artifact_policy_results"]=[split["policy_results"]]
    else:
        splits=stratified_kfold_splits(raw,bundle.target,int(ev["cv_folds"]),int(ev["seed"]))
        folds=[_run_split(bundle,tr,te,cfg,quiet=True,prediction_policies=selected_policies,fold=fold_no) for fold_no,(tr,te) in enumerate(splits,1)]
        policy_results={}
        for policy in selected_policies:
            policy_results[policy]={}
            for key in ("centralized","federated"):
                modules=[fold["policy_results"][policy].get(key) for fold in folds]
                policy_results[policy][key]=_aggregate_cv(
                    [{key:module} for module in modules if module is not None],key
                ) if any(module is not None for module in modules) else None
        active_policy=str(cfg["experiment"]["prediction_policy"]).upper()
        if active_policy not in policy_results: active_policy=selected_policies[0]
        result={"name":bundle.name,"source":bundle.source,"rows":len(raw),"features":bundle.features,"target":bundle.target,"schema":{"continuous":list(bundle.schema.continuous),"categorical":list(bundle.schema.categorical),"ordinal":dict(bundle.schema.ordinal),"ignore":list(bundle.schema.ignore)},"evaluation_mode":"K_FOLD_CV","fold_results":folds,"policy_results":policy_results,"centralized":policy_results[active_policy]["centralized"],"federated":policy_results[active_policy]["federated"],"structural_artifacts":[fold["structural_artifact"] for fold in folds],"artifact_policy_results":[fold["policy_results"] for fold in folds]}
        result["central_reduct_result"]=[fold["central_reduct_result"] for fold in folds]
        result["local_reduct_results"]=[fold["local_reduct_results"] for fold in folds]
        result["structural_metrics"]=[fold["structural_metrics"] for fold in folds]
    if bool(cfg["federated"]["run_client_sweep"]):
        rows=[]
        artifacts=list(result.get("structural_artifacts",[]))
        artifact_policy_results=list(result.get("artifact_policy_results",[]))
        for c in sorted(set(int(x) for x in cfg["federated"]["client_counts"])):
            if c==int(cfg["federated"]["n_clients"]):
                child_result=result
            else:
                child=deepcopy(cfg); child["experiment"]["run_federated"]=True; child["federated"]["n_clients"]=c; child["federated"]["run_client_sweep"]=False
                child_result=_run_dataset(bundle,child,selected_policies)
            if c != int(cfg["federated"]["n_clients"]):
                artifacts.extend(child_result.get("structural_artifacts",[]))
                artifact_policy_results.extend(child_result.get("artifact_policy_results",[]))
            for artifact, policy_outputs in zip(
                child_result.get("structural_artifacts", []),
                child_result.get("artifact_policy_results", []),
            ):
                struct=artifact.structural_metrics
                for policy in selected_policies:
                    fed=(policy_outputs.get(policy) or {}).get("federated") or {}
                    rows.append({"dataset":bundle.name,"fold":artifact.fold,"clients":c,"prediction_policy":policy,"mean_local_reduct_size":struct.get("mean_local_reduct_size"),"std_local_reduct_size":struct.get("std_local_reduct_size"),"mean_reduct_jaccard":struct.get("mean_reduct_jaccard"),"reduct_instability":struct.get("reduct_instability"),"mean_local_central_reduct_jaccard":struct.get("mean_local_central_reduct_jaccard"),"mean_feature_selection_frequency":struct.get("mean_feature_selection_frequency"),"feature_selection_frequency_std":struct.get("feature_selection_frequency_std"),"rule_jaccard_antecedent":struct.get("pairwise_jaccard_antecedent"),"rule_jaccard_full":struct.get("pairwise_jaccard_full_rule"),"global_rules":fed.get("global_rule_count",fed.get("mean_rule_count")),"pre_resolution_conflict_case_rate":fed.get("pre_resolution_conflict_case_rate",fed.get("conflict_case_rate")),"balanced_accuracy":fed.get("balanced_accuracy"),"conflict_balanced_accuracy":fed.get("conflict_balanced_accuracy"),"all_case_disagreement_rate_vs_first_match":fed.get("all_case_disagreement_rate_vs_first_match"),"conflict_case_disagreement_rate_vs_first_match":fed.get("conflict_case_disagreement_rate_vs_first_match"),"order_invariant_by_design":fed.get("order_invariant_by_design"),"order_sensitivity_rate":fed.get("order_sensitivity_rate"),"order_balanced_accuracy_mean":fed.get("order_balanced_accuracy_mean")})
        result["client_sweep"]=pd.DataFrame(rows)
        result["structural_artifacts"]=artifacts
        result["artifact_policy_results"]=artifact_policy_results
    if bool(cfg.get("paper", {}).get("enabled", False)):
        protocol = run_paper_protocol(
            bundle,
            cv_folds=int(cfg["paper"].get("cv_folds", 10)),
            seed=int(cfg["evaluation"]["seed"]),
        )
        result["paper_protocol"] = protocol
        result["paper_comparison"] = published_comparison(
            bundle, protocol, reference=str(cfg["paper"].get("reference", "WANG_2007"))
        )
    return result


def _jsonable(value):
    if isinstance(value,pd.DataFrame): return value.to_dict(orient="records")
    if isinstance(value,pd.Series): return value.tolist()
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,Path): return str(value)
    if isinstance(value,dict):
        out={}
        for k,v in value.items():
            # rule-key tuples are not JSON object keys; stringify them for reports.
            out[str(k)] = _jsonable(v)
        return out
    if isinstance(value,(list,tuple,set)): return [_jsonable(x) for x in value]
    if hasattr(value,"conditions") and hasattr(value,"decision"): return str(value)
    if isinstance(value,float) and not math.isfinite(value): return None
    return value


def _summary(result):
    c=result.get("centralized") or {}; f=result.get("federated") or {}
    structural=result.get("structural_metrics") or {}
    if isinstance(structural,list):
        numeric_keys={key for row in structural for key,value in row.items() if isinstance(value,(int,float,np.number)) and not isinstance(value,bool)}
        aggregated={}
        for key in numeric_keys:
            values=np.asarray([row.get(key,np.nan) for row in structural],dtype=float)
            finite=values[np.isfinite(values)]
            aggregated[key]=float(finite.mean()) if len(finite) else float("nan")
        structural=aggregated
    return {
        "dataset":result["name"],"source":result["source"],"rows":result["rows"],
        "features":len(result["features"]),"target":result["target"],"evaluation":result["evaluation_mode"],
        "centralized_balanced_accuracy":c.get("balanced_accuracy"),"centralized_coverage":c.get("coverage"),
        "federated_balanced_accuracy":f.get("balanced_accuracy"),"federated_coverage":f.get("coverage"),
        "federated_global_rules":f.get("global_rule_count",f.get("mean_rule_count")),
        "central_reduct_size":structural.get("central_reduct_size"),
        "central_reduct":json.dumps(structural.get("central_reduct", []),ensure_ascii=False),
        "mean_local_reduct_size":structural.get("mean_local_reduct_size"),
        "reduct_instability":structural.get("reduct_instability"),
        "mean_local_central_reduct_jaccard":structural.get("mean_local_central_reduct_jaccard"),
        "rule_heterogeneity":structural.get("rule_heterogeneity"),
        "pre_resolution_conflict_case_rate":f.get("pre_resolution_conflict_case_rate",f.get("conflict_case_rate")),
        "conflict_case_rate":f.get("conflict_case_rate"),
        "order_invariant_by_design":f.get("order_invariant_by_design"),
        "order_sensitivity_rate":f.get("order_sensitivity_rate"),
    }


def _write_dataset_output(result: Mapping[str, Any], folder: Path):
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"summary.json").write_text(json.dumps(_jsonable(_summary(result)),ensure_ascii=False,indent=2),encoding="utf-8")
    pd.DataFrame([_summary(result)]).to_csv(folder/"summary.csv",index=False,encoding="utf-8-sig")
    preprocessor_obj = result.get("preprocessor")
    if result.get("fold_results"):
        preprocessor_obj = [fold.get("preprocessor") for fold in result["fold_results"]]
    manifest = {
        "dataset": result.get("name"),
        "source": result.get("source"),
        "target": result.get("target"),
        "features": result.get("features"),
        "schema": result.get("schema"),
        "evaluation_mode": result.get("evaluation_mode"),
        "preprocessing": preprocessor_obj,
        "reduct_enabled": bool(result.get("config", {}).get("reduct", {}).get("enabled", True)),
        "reduct_method": result.get("config", {}).get("reduct", {}).get("method", "MINIMUM_CARDINALITY"),
        "reduct_selection_policy": "lexicographic_first_among_minimum_cardinality",
        "record_all_candidates": bool(result.get("config", {}).get("reduct", {}).get("record_all_candidates", True)),
        "conflict_rate_definition": "pre-resolution; all matching rules with more than one distinct decision",
        "coverage_is_structural_and_shared_across_policies": True,
        "environment": environment_manifest(),
    }
    (folder/"dataset_manifest.json").write_text(
        json.dumps(_jsonable(manifest),ensure_ascii=False,indent=2),encoding="utf-8"
    )
    for label,key in [("centralized","centralized"),("federated","federated")]:
        module=result.get(key) or {}
        rules=module.get("rules",module.get("global_rules",[]))
        if rules:
            pd.DataFrame([{"rule_no":i,"conditions":" AND ".join(f"{a}={v}" for a,v in r.conditions),"decision":r.decision,"source":r.source} for i,r in enumerate(rules,1)]).to_csv(folder/f"{label}_rules.csv",index=False,encoding="utf-8-sig")
    sweep=result.get("client_sweep")
    if isinstance(sweep,pd.DataFrame): sweep.to_csv(folder/"client_sweep.csv",index=False,encoding="utf-8-sig")
    fed=result.get("federated") or {}
    for filename,field in [
        ("local_metrics.csv","local_metrics"),
        ("pairwise_jaccard.csv","pairwise_table"),
        ("conflict_groups.csv","conflict_groups_table"),
        ("conflict_cases.csv","conflict_cases_table"),
        ("order_distribution.csv","order_distribution_table"),
        ("fold_metrics.csv","fold_metrics"),
    ]:
        table=fed.get(field)
        if isinstance(table,pd.DataFrame) and not table.empty:
            table.to_csv(folder/filename,index=False,encoding="utf-8-sig")
    artifact_tables: dict[str,list[pd.DataFrame]] = {}
    for artifact in result.get("structural_artifacts",[]):
        for key,table in artifact.tables.items():
            if isinstance(table,pd.DataFrame) and not table.empty:
                enriched=table.copy()
                for column,value in (("dataset",artifact.dataset),("fold",artifact.fold),("client_count",artifact.client_count)):
                    if column not in enriched.columns: enriched.insert(0,column,value)
                artifact_tables.setdefault(key,[]).append(enriched)
    table_files={
        "central_reduct":"central_reduct.csv",
        "local_reducts":"local_reducts.csv",
        "reduct_candidates":"reduct_candidates.csv",
        "pairwise_reduct_jaccard":"pairwise_reduct_jaccard.csv",
        "feature_selection_frequency":"feature_selection_frequency.csv",
        "centralized_rules":"centralized_rules.csv",
        "local_rules":"local_rules.csv",
        "federated_rules":"federated_rules.csv",
        "pairwise_rule_jaccard":"pairwise_rule_jaccard.csv",
        "rule_metrics":"rule_metrics.csv",
        "conflict_groups":"conflict_groups.csv",
        "conflict_cases":"conflict_cases.csv",
    }
    for key,filename in table_files.items():
        frames=artifact_tables.get(key,[])
        if frames:
            combined=pd.concat(frames,ignore_index=True)
            combined.to_csv(folder/filename,index=False,encoding="utf-8-sig")
            if key=="pairwise_rule_jaccard":
                combined.to_csv(folder/"pairwise_jaccard.csv",index=False,encoding="utf-8-sig")
    paper=result.get("paper_protocol")
    if paper:
        paper_summary={k:v for k,v in paper.items() if k not in {"full_data_rules","fold_metrics"}}
        (folder/"paper_protocol.json").write_text(json.dumps(_jsonable(paper_summary),ensure_ascii=False,indent=2),encoding="utf-8")
        paper["fold_metrics"].to_csv(folder/"paper_fold_metrics.csv",index=False,encoding="utf-8-sig")
        (folder/"paper_comparison.json").write_text(json.dumps(_jsonable(result.get("paper_comparison",{})),ensure_ascii=False,indent=2),encoding="utf-8")


def run_application(
    config: Mapping[str, Any],
    fetcher=None,
    prediction_policies: Sequence[str] | None = None,
) -> Dict[str, Any]:
    cfg=validate_config(config)
    policies = list(dict.fromkeys(
        str(policy).strip().upper()
        for policy in (prediction_policies or [cfg["experiment"]["prediction_policy"]])
    ))
    supported = {"FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"}
    unknown = set(policies) - supported
    if not policies or unknown:
        raise ValueError(f"Unsupported or empty prediction policy list: {sorted(unknown)}")
    bundles=discover_datasets(cfg,fetcher=fetcher)
    outputs=Path(cfg["report"]["outputs_folder"])
    results={}
    summaries=[]
    seen={}
    for bundle in bundles:
        base=bundle.name.strip().replace(" ","_") or "dataset"; n=seen.get(base,0)+1; seen[base]=n; key=base if n==1 else f"{base}_{n}"
        result=_run_dataset(bundle,cfg,policies); result["config"]=cfg; results[key]=result; summaries.append(_summary(result)); _write_dataset_output(result,outputs/key)
    outputs.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(summaries).to_csv(outputs/"all_datasets_summary.csv",index=False,encoding="utf-8-sig")
    (outputs/"run_manifest.json").write_text(json.dumps({"datasets":list(results),"config":_jsonable(cfg),"environment":environment_manifest()},ensure_ascii=False,indent=2),encoding="utf-8")
    return {"datasets":results,"summary":pd.DataFrame(summaries),"config":cfg}
