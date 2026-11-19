"""Validation and aggregation of full-scale shard artifacts."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import pandas as pd
from fedrs.predict import POLICIES
from experiments.full_scale_20261118.analysis import dataset_best, scenario_of, summary
from experiments.full_scale_20261118.model import SCENARIOS
from experiments.full_scale_20261118.registry import G5, ROOT, source_registry
from experiments.full_scale_20261118.shard import FULL19, SMOKE

REGISTRY_COLUMNS = ["cohort", "dataset", "source_url", "upstream_commit", "raw_sha256", "prepared_sha256",
                    "original_rows", "used_rows", "original_features", "used_features", "used_feature_names",
                    "n_classes", "dropped_classes", "minority_share", "continuous_fraction", "feature_type",
                    "size_class", "same_source_as", "related_source", "status"]


def check_19(data):
    if data.empty:
        return
    percentages = ["test_coverage_pct", "candidate_coverage_pct", "accuracy_pct", "balanced_accuracy_pct", "conflict_rate_pct"]
    if data[percentages].isna().any().any() or not ((data[percentages] >= 0) & (data[percentages] <= 100)).all().all():
        raise ValueError("Percentages must be finite and within 0–100")
    if not (data.covered_count + data.no_match_count == data.test_rows).all():
        raise ValueError("covered_count + no_match_count must equal test_rows")
    if not ((data.true_in_candidate_count >= 0) & (data.true_in_candidate_count <= data.covered_count)).all():
        raise ValueError("true_in_candidate_count exceeds covered_count")
    if not ((data.test_rows > 0) & (data.covered_count >= 0) & (data.no_match_count >= 0)).all():
        raise ValueError("Invalid test or coverage counts")
    if not ((data.test_coverage_pct - 100.0 * data.covered_count / data.test_rows).abs() <= 1e-6).all():
        raise ValueError("Invalid test coverage percentage")
    if not ((data.candidate_coverage_pct - 100.0 * data.true_in_candidate_count / data.test_rows).abs() <= 1e-6).all():
        raise ValueError("Invalid candidate coverage percentage")
    if not set(data.distribution).issubset({"IID", "DIRICHLET_NONIID"}):
        raise ValueError("Invalid distribution")
    if "split_mode" in data and not (data.split_mode == "NESTED_64_16_20").all():
        raise ValueError("Invalid split_mode")
    rows = data.copy()
    rows["scenario"] = [scenario_of(r) for r in rows.itertuples()]
    for key, group in rows.groupby(["dataset", "seed", "scenario"], sort=False):
        if len(group) != 6 or set(group.selection_policy) != set(POLICIES):
            raise ValueError(f"Invalid six-policy configuration {key}")
        for col in ("test_rows", "covered_count", "no_match_count", "true_in_candidate_count", "conflict_rate_pct"):
            if group[col].nunique(dropna=False) != 1:
                raise ValueError(f"Inconsistent {col} for {key}")
        spread = group.accuracy_pct.max() - group.accuracy_pct.min()
        if spread > group.conflict_rate_pct.iloc[0] + 1e-6:
            raise ValueError(f"CONFLICT_BOUND {key}: spread={spread}, conflict={group.conflict_rate_pct.iloc[0]}")


def _read_artifacts(directory, prefix):
    files = sorted(Path(directory).rglob(f"{prefix}_*.csv"))
    parts = [pd.read_csv(path) for path in files]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _keys(data):
    if data.empty:
        return set()
    return {(r.dataset, int(r.seed), scenario_of(r)) for r in data.itertuples()}


def _write_csv(path, data, columns=None):
    if columns is not None:
        for col in columns:
            if col not in data:
                data[col] = pd.Series(dtype=object)
        data = data[columns]
    data.to_csv(path, index=False)


def _markdown_table(frame):
    if frame.empty:
        return "（尚無資料）"
    cols = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def validate_g5_rows(primary, seeds):
    g5reg = pd.read_csv(G5)
    g5reg = g5reg[(g5reg.status == "ELIGIBLE_PREPARED") & (g5reg.row_capped.astype(str) == "False") & (g5reg.prepared_rows <= 1800)]
    ref = pd.read_csv(ROOT / "docs/research/redesign_20261116/data/REDESIGN_G5_CONFIRMATORY_POLICIES.csv")
    required = set(range(1001, 1006))
    complete = required.issubset(seeds)
    for item in g5reg.itertuples():
        did = int(item.did)
        for seed in sorted(required):
            actual = primary[(primary.dataset == f"OML51:openml_{did}") & (primary.seed == seed)
                             & (primary.system == "FEDERATED") & (primary.distribution == "IID")]
            old = ref[(ref.did == did) & (ref.seed == seed) & (ref.regime == "IID")
                      & (ref.discretizer == "EQUAL_WIDTH_3") & (ref.rule_variant == "A_ALL_RULES")]
            if len(actual) != 6 or len(old[old.method.isin(POLICIES)]) != 6:
                complete = False
                continue
            for policy in POLICIES:
                now = float(actual[actual.selection_policy == policy].accuracy_pct.iloc[0]) / 100.0
                prev = float(old[old.method == policy].test_accuracy.iloc[0])
                if abs(now-prev) > 1e-12:
                    raise ValueError(f"G5_MISMATCH did={did} seed={seed} policy={policy} expected={prev} actual={now}")
    return complete


def aggregate(artifacts, output, seeds, smoke=False, run_url="", smoke_url="",
              history_dir=None, retry_of_url="", retry_jobs=()):
    """retry_jobs: (dataset, scenario) pairs rerun in this run, replacing their artifacts from
    the run at retry_of_url. history_dir holds earlier failure logs (defaults to output)."""
    output = Path(output)
    history = Path(history_dir) if history_dir else output
    retry_jobs = {(str(d), str(sc)) for d, sc in retry_jobs}
    output.mkdir(parents=True, exist_ok=True)
    names = ["FULL_SCALE_19COL.csv", "FULL_SCALE_19COL_B2.csv", "REGISTRY.csv", "DATASET_BEST.csv",
             "SUMMARY.csv", "SCALE_LADDER.csv", "FAILURES.csv", "TIMINGS.csv", "MANIFEST.json", "FULL_SCALE_REPORT.md"]
    present = [name for name in names if (output / name).exists()]
    if present:
        raise FileExistsError(f"Refusing to overwrite output files: {present}")
    registry = source_registry()
    planned = registry[registry.status == "PENDING"]
    if smoke:
        planned = planned[planned.dataset.isin(SMOKE)]
        seeds = seeds[:1]
    datasets = set(planned.dataset)
    expected = {(d, int(seed), scenario) for d in datasets for seed in seeds for scenario in SCENARIOS}
    result = _read_artifacts(artifacts, "shard")
    failures = _read_artifacts(artifacts, "failures")
    timing = _read_artifacts(artifacts, "timings")
    metadata = _read_artifacts(artifacts, "registry")
    ladder = _read_artifacts(artifacts, "ladder")
    if not result.empty:
        if not set(result.dataset).issubset(datasets):
            raise ValueError("Artifact contains an unexpected dataset")
        primary = result[result.rule_variant == "A_ALL_RULES"].copy()
        b2 = result[result.rule_variant == "B2_TRUE_AS_FALLBACK"].copy()
        if len(primary) + len(b2) != len(result):
            raise ValueError("Unknown rule variant in artifacts")
    else:
        primary = pd.DataFrame(columns=FULL19)
        b2 = pd.DataFrame(columns=FULL19)
    try:
        check_19(primary)
        check_19(b2)
        primary_keys, b2_keys = _keys(primary), _keys(b2)
        if not primary_keys.issubset(expected) or primary_keys != b2_keys:
            raise ValueError("Model configurations or rule variants do not agree")
    except ValueError as exc:
        failures = pd.concat([failures, pd.DataFrame([dict(phase="VALIDATION", status="FAILED", error=str(exc))])], ignore_index=True)
        _write_csv(output / "FAILURES.csv", failures)
        (output / "FULL_SCALE_REPORT.md").write_text(f"# 全量實驗驗證中止\n\n驗證失敗：`{exc}`。未產生可視為完成的統計結果。\n", encoding="utf-8")
        raise
    if failures.empty:
        failures = pd.DataFrame(columns=["dataset", "seed", "scenario", "phase", "status", "error"])
    failure_keys = {(str(r.dataset), int(r.seed), str(r.scenario)) for r in failures.itertuples()
                    if pd.notna(getattr(r, "dataset", None)) and pd.notna(getattr(r, "seed", None))
                    and pd.notna(getattr(r, "scenario", None)) and r.scenario in SCENARIOS
                    and getattr(r, "phase", None) in ("MODEL", "SOURCE", "SHARD")}
    missing = sorted(expected - primary_keys - failure_keys)
    if missing:
        failures = pd.concat([failures, pd.DataFrame([dict(dataset=d, seed=s, scenario=sc, phase="SHARD",
                                                            status="MISSING_ARTIFACT_OR_EVENT", error="No model result or failure artifact")
                                                     for d, s, sc in missing])], ignore_index=True)
    prior = ROOT / "experiments/full_scale_20261118/FAILURES.csv"
    previous_logs = (([prior] if prior.exists() else []) + sorted(history.glob("g5_stop_*/FAILURES.csv"))
                     + sorted(history.glob("conflict_stop_*/FAILURES.csv")) + sorted(history.glob("dispatch_attempt_*/FAILURES.csv")))
    for log in previous_logs:
        old = pd.read_csv(log)
        old["phase"] = "PRELIMINARY_" + old["phase"].fillna("").astype(str)
        failures = pd.concat([failures, old], ignore_index=True)
    if retry_jobs:
        # Keep the replaced run's failure rows for the rerun jobs, marked so they are not
        # counted as current model failures (their configurations were rerun in this run).
        base = history / "FAILURES.csv"
        if not base.exists():
            raise FileNotFoundError(f"Retry mode needs the earlier run's failure log: {base}")
        old = pd.read_csv(base)
        old = old[~old.phase.fillna("").astype(str).str.startswith("PRELIMINARY_")]
        hit = [(str(d), str(sc)) in retry_jobs for d, sc in zip(old.dataset, old.scenario)]
        old = old[hit].copy()
        old["phase"] = "RETRIED_" + old["phase"].fillna("").astype(str)
        old["error"] = old["error"].astype(str) + f" [replaced by rerun; earlier run {retry_of_url}]"
        failures = pd.concat([failures, old], ignore_index=True)
    if not metadata.empty and metadata.dataset.duplicated().any():
        raise ValueError("Duplicate source metadata across shard artifacts")
    if not metadata.empty:
        enrichment = metadata.set_index("dataset").to_dict("index")
        for idx, row in registry.iterrows():
            if row.dataset in enrichment:
                for key, value in enrichment[row.dataset].items():
                    registry.loc[idx, key] = value
    for idx, row in registry.iterrows():
        if row.dataset in datasets:
            configs = {(row.dataset, int(s), scenario) for s in seeds for scenario in SCENARIOS}
            if row.status != "EXCLUDED_TOO_FEW_CLASSES":
                registry.loc[idx, "status"] = "SUCCESS" if configs <= primary_keys else "PARTIAL_OR_FAILED"
        elif smoke and row.status == "PENDING":
            registry.loc[idx, "status"] = "NOT_IN_SMOKE"
    try:
        if "status" in failures and (failures.status == "ConflictBoundViolation").any():
            raise ValueError("CONFLICT_BOUND: a model reported a violation; see FAILURES.csv")
        if not ladder.empty:
            if not set(ladder.scenario).issubset({"FED_IID", "FED_A01"}):
                raise ValueError("Invalid scale-ladder scenario")
            if not (ladder.seed == 1001).all() or any(scenario_of(r) != r.scenario for r in ladder.itertuples()):
                raise ValueError("Invalid scale-ladder seed or scenario")
            for _, part in ladder.groupby(ladder.scale.astype(str)):
                check_19(part)
        g5_ok = False if smoke else validate_g5_rows(primary, seeds)
    except ValueError as exc:
        failures = pd.concat([failures, pd.DataFrame([dict(phase="VALIDATION", status="FAILED", error=str(exc))])], ignore_index=True)
        _write_csv(output / "FAILURES.csv", failures)
        (output / "FULL_SCALE_REPORT.md").write_text(f"# 全量實驗驗證中止\n\n驗證失敗：`{exc}`。未產生可視為完成的統計結果。\n", encoding="utf-8")
        raise
    ladder_expected = set()
    if not smoke:
        large = registry[registry.dataset.isin(datasets) & (pd.to_numeric(registry.original_rows, errors="coerce") >= 20_000)]
        ladder_expected = {(d, sc, scale) for d in large.dataset for sc in ("FED_IID", "FED_A01")
                           for scale in ("1800", "10000", "FULL")}
    ladder_found = {(r.dataset, r.scenario, str(r.scale)) for r in ladder.itertuples()} if not ladder.empty else set()
    if not ladder_found.issubset(ladder_expected):
        error = "Unexpected configuration in scale ladder"
        failures = pd.concat([failures, pd.DataFrame([dict(phase="VALIDATION", status="FAILED", error=error)])], ignore_index=True)
        _write_csv(output / "FAILURES.csv", failures)
        (output / "FULL_SCALE_REPORT.md").write_text(f"# 全量實驗驗證中止\n\n{error}\n", encoding="utf-8")
        raise ValueError(error)
    ladder_missing = ladder_expected - ladder_found
    failed_ladders = {(str(r.dataset), str(r.scenario), str(r.scale)) for r in failures.itertuples()
                      if getattr(r, "phase", None) == "SCALE_LADDER" and pd.notna(getattr(r, "dataset", None))
                      and pd.notna(getattr(r, "scenario", None)) and pd.notna(getattr(r, "scale", None))}
    unreported_ladder = ladder_missing - failed_ladders
    if unreported_ladder:
        failures = pd.concat([failures, pd.DataFrame([dict(dataset=d, seed=1001, scenario=sc, scale=scale,
                                                           phase="SCALE_LADDER", status="MISSING_LADDER_OUTPUT",
                                                           error="No ladder result or failure artifact")
                                                      for d, sc, scale in sorted(unreported_ladder)])], ignore_index=True)
    _write_csv(output / "FULL_SCALE_19COL.csv", primary.copy(), FULL19)
    _write_csv(output / "FULL_SCALE_19COL_B2.csv", b2.copy(), FULL19)
    for col in REGISTRY_COLUMNS:
        if col not in registry:
            registry[col] = pd.Series(dtype=object)
    registry = registry[REGISTRY_COLUMNS + [col for col in registry.columns if col not in REGISTRY_COLUMNS]]
    _write_csv(output / "REGISTRY.csv", registry)
    _write_csv(output / "FAILURES.csv", failures)
    _write_csv(output / "TIMINGS.csv", timing, list(timing.columns) if len(timing.columns) else ["dataset", "seed", "scenario", "wall_seconds"])
    _write_csv(output / "SCALE_LADDER.csv", ladder, list(ladder.columns) if len(ladder.columns) else FULL19 + ["scenario", "scale", "scale_rows"])
    best = dataset_best(primary, registry, seeds)
    summary_data = summary(best)
    _write_csv(output / "DATASET_BEST.csv", best, list(best.columns) if len(best.columns) else ["dataset", "scenario"])
    _write_csv(output / "SUMMARY.csv", summary_data, list(summary_data.columns) if len(summary_data.columns) else ["scenario", "stratum", "stratum_value", "policy"])
    prepared = registry[registry.dataset.isin(datasets) & registry.get("feature_type", pd.Series(index=registry.index, dtype=object)).notna()]
    cross = pd.crosstab(prepared.feature_type, prepared.size_class).reset_index() if not prepared.empty else pd.DataFrame()
    overall = summary_data[summary_data.stratum == "ALL"] if not summary_data.empty else pd.DataFrame()
    wins = overall[["scenario", "policy", "datasets", "wins"]] if not overall.empty else pd.DataFrame()
    model_failures = len(expected - primary_keys)
    g5_detail = "smoke 不驗收 G5 全範圍" if smoke else ("完整通過" if g5_ok else "未完成：至少一個必要配置或種子缺失")
    run_ref = run_url or "未提供"
    smoke_ref = smoke_url or (run_ref if smoke else "未提供")
    quantiles = timing.wall_seconds.quantile([0, .5, .9, 1]).round(3).to_dict() if not timing.empty and "wall_seconds" in timing else {}
    failure_counts = failures.groupby("status", dropna=False).size().reset_index(name="次數") if not failures.empty else pd.DataFrame()
    completed_names = {d for d in datasets if all((d, int(s), sc) in primary_keys for s in seeds for sc in SCENARIOS)}
    complete_meta = registry[registry.dataset.isin(completed_names)]
    feature_counts = complete_meta.feature_type.value_counts().to_dict() if not complete_meta.empty else {}
    type_targets = {name: int(feature_counts.get(name, 0)) for name in ("連續", "混合", "類別/離散")}
    unresolved_fraction = int(complete_meta.continuous_fraction.isna().sum()) if not complete_meta.empty else 0
    unresolved_type = int(complete_meta.feature_type.isna().sum()) if not complete_meta.empty else 0
    coverage_ok = len(completed_names) >= 100 and all(n >= 20 for n in type_targets.values())
    acceptance = {"all_models_completed": model_failures == 0,
                  "scale_ladder_completed": not ladder_missing,
                  "dataset_and_feature_minima": coverage_ok,
                  "registry_feature_types_complete": unresolved_fraction == 0 and unresolved_type == 0,
                  "g5": g5_ok,
                  "run_urls_present": bool(run_url and smoke_url)}
    retry_note = ("" if not retry_jobs else
                  "\n" + f"本結果為補跑合併版：原全量 workflow {retry_of_url} 中，下列因資料下載中斷（IncompleteRead）而失敗的"
                  f"資料集／情境 job 已重跑並以本次結果取代，其餘 job 沿用原 run 的 artifact：{sorted(retry_jobs)}。"
                  f"原 run 對這些 job 的失敗紀錄以 `RETRIED_` 開頭保留於 FAILURES.csv，不計入模型失敗數。原 run 的輸出檔保持不變。" + "\n")
    report = f"""# 全量六策略實驗報告

執行模式：{'smoke' if smoke else '全量'}。去重後預定來源 {len(datasets)} 個；有完整四種情境及全部指定種子的來源 {sum(all((d, int(s), sc) in primary_keys for s in seeds for sc in SCENARIOS) for d in datasets)} 個。
預定模型 {len(expected)} 個，成功 {len(primary_keys)} 個，未成功 {model_failures} 個。歷次重試失敗也列於 FAILURES.csv，與模型失敗數分開計算。
完整來源的特徵型態數：{type_targets}；另有 {unresolved_type} 個來源的型態、{unresolved_fraction} 個來源的連續比例因跨種子變動無法以單一值表示。至少 100 個來源且每種型態至少 20 個的條件：{'通過' if coverage_ok else '未達或尚未完成'}。

## 型態 × 規模（已準備來源）

{_markdown_table(cross)}

## 四種情境的最佳方法次數（完整種子組）

{_markdown_table(wins)}

## 失敗摘要

{_markdown_table(failure_counts)}

## 運算時間與驗收

模型 wall time 秒數分位數：`{quantiles}`。G5 對照：{g5_detail}。規模階梯缺少 {len(ladder_missing)} 個資料集／情境／規模組合。未完成種子的資料集與情境不列入 DATASET_BEST 與 SUMMARY。
Smoke workflow：{smoke_ref}；全量 workflow：{run_ref if not smoke else '尚未執行'}。Artifact：{run_ref + '#artifacts' if run_url else '未提供'}。
{retry_note}
## 限制

僅使用前六個符合各來源既有選欄規則的特徵；不同 seed 不是新資料。欄位型態或連續比例若隨 seed 變化，REGISTRY 保留各 seed 的實際值；無法用單一比例表示時留空並記錄失敗，未分類來源不計入三種型態的最低數量。Accuracy 偏向多數類；聯邦式為模擬，沒有隱私保證。結果僅描述成功執行的配置，不以重複來源補數。
"""
    (output / "FULL_SCALE_REPORT.md").write_text(report, encoding="utf-8")
    versions = {}
    for package in ("numpy", "pandas", "scipy", "pyarrow", "scikit-learn"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    tracked_diff = subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=ROOT)
    manifest = dict(commit_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    tracked_worktree_dirty=bool(tracked_diff),
                    tracked_diff_sha256=hashlib.sha256(tracked_diff).hexdigest() if tracked_diff else None,
                    python=platform.python_version(), packages=versions, workflow_run_url=run_url, smoke_run_url=smoke_url,
                    retry_of_run_url=retry_of_url or None, retry_jobs=sorted([list(x) for x in retry_jobs]),
                    expected_models=len(expected), successful_models=len(primary_keys), failed_or_unrun_models=model_failures,
                    g5_validation_passed=g5_ok, smoke_passed=smoke and model_failures == 0,
                    acceptance=acceptance,
                    hashes_exclude_manifest_itself=True,
                    file_sha256={str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(output.rglob("*")) if p.is_file() and p.name != "MANIFEST.json"})
    (output / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifacts", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--seeds", default="1001,1002,1003,1004,1005")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--run-url", default="")
    p.add_argument("--smoke-url", default="")
    p.add_argument("--history-dir", default=None)
    p.add_argument("--retry-of-url", default="")
    p.add_argument("--retry-jobs", default="", help='JSON list of [dataset, scenario] pairs')
    a = p.parse_args()
    retry_jobs = [tuple(x) for x in json.loads(a.retry_jobs)] if a.retry_jobs.strip() else []
    result = aggregate(a.artifacts, a.output, [int(s.strip()) for s in a.seeds.split(",") if s.strip()],
                       a.smoke, a.run_url, a.smoke_url, a.history_dir, a.retry_of_url, retry_jobs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (result["smoke_passed"] if a.smoke else all(result["acceptance"].values())) else 1


if __name__ == "__main__":
    sys.exit(main())
