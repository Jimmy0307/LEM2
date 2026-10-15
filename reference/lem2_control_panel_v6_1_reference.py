# -*- coding: utf-8 -*-
"""
LEM2 中文教學版 V6.1：數學一致性修正版 + Federated Conflict Audit + Client Sweep
==========================================================================

【這支程式的設計目的】
平常使用時，原則上只修改最上面的 USER_SETTINGS。
真正的 LEM2 演算法核心放在最下面，資料來源、Federated、Cross Validation、
Rule Conflict Resolution、Paper Comparison 都放在 LEM2 外面。

整體邏輯：
    USER CONTROL PANEL
            ↓
       INPUT ADAPTER
            ↓
    SPLIT / PREPROCESS
            ↓
   ┌────────┴────────┐
   ↓                 ↓
CENTRALIZED       FEDERATED
   ↓                 ↓
 LEM2          CLIENTS → LOCAL LEM2 → RULE UNION
   └────────┬────────┘
            ↓
  PREDICTION / CONFLICT RESOLUTION
            ↓
        EVALUATION
            ↓
   CONFLICT / CLIENT SWEEP AUDIT
            ↓
        CLEAN REPORT

另外還有一條獨立的 Paper Replication Lane：
    完整標記資料
        ↓
    Minimal Reduct
        ↓
       LEM2
        ↓
   Global Strength
        ↓
    10-Fold CV
        ↓
   與 Wang et al. (2007) 公開結果比較

【重要觀念】
1. LEM2 本身只負責從 decision table 產生規則。
2. FIRST_MATCH / VOTING / GLOBAL_STRENGTH 是規則衝突處理，不是 LEM2 本體。
3. Federated 是外層架構，不應寫死在 LEM2 裡。
4. HOLDOUT / K-FOLD 是評估方式，也不應寫死在 LEM2 裡。
5. Paper Replication 是獨立驗證線，不應拿一般 Holdout 結果直接跟舊 paper 比。
6. V6.1 保留 LEM2 Core，不改核心數學；新增完整 rule provenance、client-order 分布與 Dirichlet label-skew partition。

因此這份程式的核心原則就是：
「設定放最上面、流程放中間、核心演算法放最下面。」
"""

from __future__ import annotations

from collections import Counter, defaultdict
import itertools
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd


# =============================================================================
# 0. USER CONTROL PANEL -- normally edit ONLY this section
# =============================================================================

USER_SETTINGS: Dict[str, Any] = {
    # -------------------------------------------------------------------------
    # ① 資料來源 INPUT
    # -------------------------------------------------------------------------
    # UCI_ALL：自動從 UCI API 抓 Hayes-Roth、Car Evaluation、Balance Scale 三筆資料。
    # UCI：只跑 dataset_key 指定的一筆 UCI 資料。
    # CSV / EXCEL / DATAFRAME：未來換自己資料時使用。
    "input_mode": "UCI_ALL",

    # 只有 input_mode="UCI" 時會用到。
    # 可選：hayes_roth / car_evaluation / balance_scale
    "dataset_key": "balance_scale",

    # 自訂資料才需要設定；跑 UCI_ALL 時都不用改。
    "data_path": None,
    "sheet_name": 0,
    "target": None,
    "drop_columns": [],
    "feature_columns": None,
    "dataframe": None,

    # -------------------------------------------------------------------------
    # ② 主實驗要跑哪一條 EXECUTION PATH
    # -------------------------------------------------------------------------
    # Centralized：所有 training data 放在一起跑一個 LEM2。
    "run_centralized": True,

    # Federated：training data 切成多個 clients，各自跑 LEM2，再聚合規則。
    "run_federated": False,

    # -------------------------------------------------------------------------
    # ③ 規則衝突怎麼解 PREDICTION / CONFLICT RESOLUTION
    # -------------------------------------------------------------------------
    # FIRST_MATCH：
    #   規則依順序檢查，第一條符合就直接決定。
    #
    # SIMPLE_VOTING：
    #   所有符合的規則一條算一票，票最多的 class 勝出。
    #
    # STANDARD_VOTING：
    #   規則依 training support 加權，不是每條 rule 都只有一票。
    #
    # GLOBAL_STRENGTH：
    #   對每個 decision class 計算 matching rules 所覆蓋的 training objects 聯集比例。
    #   Wang et al. (2007) benchmark lane 使用這個方式。
    "prediction_policy": "FIRST_MATCH",

    # -------------------------------------------------------------------------
    # ④ 模型怎麼驗證 EVALUATION
    # -------------------------------------------------------------------------
    # HOLDOUT：例如 80% train / 20% test，只切一次。
    # K_FOLD_CV：例如 10-fold，每個 fold 都重新訓練，再取平均。
    "evaluation_mode": "HOLDOUT",
    "run_evaluation": True,

    # HOLDOUT only：0.20 代表 20% 留作 test。
    "test_ratio": 0.20,

    # K_FOLD_CV only：10 代表 10-fold cross-validation。
    "cv_folds": 10,

    # 固定亂數種子，讓資料切分可重現。
    "seed": 42,

    # -------------------------------------------------------------------------
    # ⑤ 前處理 PREPROCESSING
    # -------------------------------------------------------------------------
    # LEM2 需要離散條件。
    # 目前三筆 UCI 資料依官方語意當 categorical，因此不需要亂切 continuous bins。
    # 未來若換自己的連續資料，auto_discretize=True 時才會做 shared discretization。
    "auto_discretize": True,

    # 若自動判斷不正確，可以手動指定欄位型態。
    "continuous_columns": [],
    "categorical_columns": [],

    # Numeric 欄位的 unique values 超過這個值時，才傾向判成 continuous。
    # 這可避免 Balance Scale 的 1~5 category code 被誤當連續數值。
    "unique_numeric_threshold": 10,

    # 真正 continuous feature 做 Equal-Width discretization 時切成幾箱。
    "n_bins": 3,

    # -------------------------------------------------------------------------
    # ⑥ Federated 設定
    # -------------------------------------------------------------------------
    # training data 要切成幾個 clients。
    "n_clients": 5,

    # 是否額外掃描不同 client 數量，觀察 client fragmentation 對 rules / conflict / performance 的影響。
    # 這個 sweep 是獨立診斷，不會改掉上面的主實驗 n_clients。
    "run_client_sweep": True,
    "client_counts": [2, 3, 4, 5],

    # FIRST_MATCH 的結果可能受 client 到達順序影響。
    # C<=5 時最多 120 種排列，這裡預設全部檢查；較大 C 時會固定 seed 抽樣。
    "order_sensitivity_max_permutations": 120,

    # STRATIFIED：盡量維持各 client 的 class distribution。
    # DIRICHLET_LABEL_SKEW：對每個 class 從 Dirichlet(alpha) 抽 client proportions，
    # 形成可重現的 label-skew non-IID partition。alpha 越小，異質性通常越高。
    "federated_partition": "STRATIFIED",
    "dirichlet_alpha": 0.5,
    "dirichlet_max_retries": 100,

    # UNION：把各 client 的 local rules 做去重後聯集。
    "federated_aggregation": "UNION",

    # -------------------------------------------------------------------------
    # ⑦ 顯示哪種報告 REPORT
    # -------------------------------------------------------------------------
    # CLEAN：只顯示你目前 Control Panel 設定的主實驗結果。
    # PAPER：只顯示 published paper replication 對照。
    # BOTH：兩種都顯示。
    # NONE：結果仍保留在 result 變數，但不印 summary。
    "report_style": "BOTH",

    # 目前內建 Wang et al. (2007) benchmark。
    "paper_reference": "WANG_2007",

    # Paper lane 使用幾 fold；原 benchmark 是 10-fold。
    "paper_cv_folds": 10,

    # -------------------------------------------------------------------------
    # ⑧ 教學 / Debug 顯示
    # -------------------------------------------------------------------------
    # 正式報告時建議全部 False，輸出才不會被大量 intermediate object 淹沒。
    "show_internal_steps": False,
    "show_data_info": False,
    "show_rules": True,
    "show_rule_limit": 10,
    "show_fold_details": False,
    "verbose_lem2": False,

    # 自訂資料可填顯示名稱。
    "name": None,
}


# Handy presets (copy values into USER_SETTINGS if wanted):
#
# Federated-paper style:
#   run_centralized=True/False
#   run_federated=True
#   prediction_policy="FIRST_MATCH"
#   evaluation_mode="HOLDOUT"
#
# Classical / RSES-style benchmark:
#   run_centralized=True
#   run_federated=False
#   prediction_policy="STANDARD_VOTING"
#   evaluation_mode="K_FOLD_CV"
#   cv_folds=10


DATASET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "hayes_roth": {
        "uci_id": 44,
        "name": "Hayes-Roth",
        "target": "class",
        "drop_columns": ["name"],
        "drop_missing_target": True,
        "doi": "10.24432/C5501T",
        "note": "Condition attributes are treated as categorical codes in the LEM2 view.",
    },
    "car_evaluation": {
        "uci_id": 19,
        "name": "Car Evaluation",
        "target": "class",
        "drop_columns": [],
        "doi": "10.24432/C5JP48",
        "note": "Six native categorical condition attributes.",
    },
    "balance_scale": {
        "uci_id": 12,
        "name": "Balance Scale",
        "target": "class",
        "drop_columns": [],
        "doi": "10.24432/C5488X",
        "note": "Values 1-5 are treated as category codes in the classical LEM2 view.",
    },
}


# Published benchmark values used only for comparison/reporting.
# Wang et al. (2007), Pattern Recognition Letters, Table 2.
# The paper reports LEM2 rule extraction, global-strength rule negotiation,
# and 10-fold cross-validation classification accuracy.
PAPER_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "WANG_2007": {
        "title": "Feature Selection based on Rough Sets and Particle Swarm Optimization",
        "doi": "10.1016/j.patrec.2006.09.003",
        "protocol": "LEM2 + global strength + 10-fold CV",
        "datasets": {
            "hayes_roth": {
                "features": 4,
                "instances": 132,
                "reduct_size": 3,
                "rules": 15,
                "accuracy_pct": 89.5,
                "psorsfs_time_s": 95.422,
            },
            "car_evaluation": None,  # not reported in Wang et al. Table 2
            "balance_scale": {
                "features": 4,
                "instances": 625,
                "reduct_size": 4,
                "rules": 207,
                "accuracy_pct": 88.5,
                "psorsfs_time_s": 3001.1,
            },
        },
    }
}


@dataclass
class ControlPanel:
    # Input
    input_mode: str = "UCI_ALL"
    dataset_key: str = "balance_scale"
    data_path: Optional[str] = None
    sheet_name: Union[str, int] = 0
    target: Optional[str] = None
    drop_columns: List[str] = field(default_factory=list)
    feature_columns: Optional[List[str]] = None
    dataframe: Optional[pd.DataFrame] = None

    # Execution
    run_centralized: bool = True
    run_federated: bool = False

    # Prediction
    prediction_policy: str = "FIRST_MATCH"

    # Evaluation
    evaluation_mode: str = "HOLDOUT"
    run_evaluation: bool = True
    test_ratio: float = 0.20
    cv_folds: int = 10
    seed: int = 42

    # Preprocessing
    auto_discretize: bool = True
    continuous_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    unique_numeric_threshold: int = 10
    n_bins: int = 3

    # Federated
    n_clients: int = 5
    run_client_sweep: bool = True
    client_counts: List[int] = field(default_factory=lambda: [2, 3, 4, 5])
    order_sensitivity_max_permutations: int = 120
    federated_partition: str = "STRATIFIED"
    dirichlet_alpha: float = 0.5
    dirichlet_max_retries: int = 100
    federated_aggregation: str = "UNION"

    # Output / report
    report_style: str = "BOTH"
    paper_reference: str = "WANG_2007"
    paper_cv_folds: int = 10
    show_internal_steps: bool = False
    show_data_info: bool = False
    show_rules: bool = True
    show_rule_limit: int = 10
    show_fold_details: bool = False
    verbose_lem2: bool = False

    # Optional label
    name: Optional[str] = None

    def input_mode_normalized(self) -> str:
        return str(self.input_mode).strip().upper()

    def evaluation_mode_normalized(self) -> str:
        return str(self.evaluation_mode).strip().upper()

    def prediction_policy_normalized(self) -> str:
        return str(self.prediction_policy).strip().upper()


# 【中文說明｜Pipeline Router】
# 這一層只負責「決定要走哪條路」，不做 LEM2 數學。
# 主要工作：
#   1) 驗證 Control Panel 設定是否合法。
#   2) 決定一次跑三筆 UCI，還是單一資料集。
#   3) 決定 HOLDOUT 或 K_FOLD_CV。
#   4) 將每個 split 送進 Centralized / Federated module。
#
# 觀念：Router = 實驗流程控制器；LEM2 = 規則學習器。兩者要分開。
#
# =============================================================================
# 1. PIPELINE ROUTER
# =============================================================================


def control_from_dict(values: Mapping[str, Any]) -> ControlPanel:
    allowed = set(ControlPanel.__dataclass_fields__)
    clean = {k: v for k, v in values.items() if k in allowed}
    return ControlPanel(**clean)


def validate_control(control: ControlPanel) -> None:
    if not control.run_centralized and not control.run_federated:
        raise ValueError("At least one of run_centralized / run_federated must be True.")

    if control.prediction_policy_normalized() not in {
        "FIRST_MATCH",
        "SIMPLE_VOTING",
        "STANDARD_VOTING",
        "GLOBAL_STRENGTH",
    }:
        raise ValueError(
            "prediction_policy must be FIRST_MATCH, SIMPLE_VOTING, "
            "STANDARD_VOTING, or GLOBAL_STRENGTH."
        )

    if control.evaluation_mode_normalized() not in {"HOLDOUT", "K_FOLD_CV"}:
        raise ValueError("evaluation_mode must be HOLDOUT or K_FOLD_CV.")

    if control.evaluation_mode_normalized() == "K_FOLD_CV" and not control.run_evaluation:
        raise ValueError("K_FOLD_CV requires run_evaluation=True.")

    if control.run_client_sweep:
        if not control.client_counts:
            raise ValueError("client_counts must contain at least one client count when run_client_sweep=True.")
        if any(int(c) < 2 for c in control.client_counts):
            raise ValueError("Every client_counts value must be >= 2.")

    if int(control.order_sensitivity_max_permutations) < 1:
        raise ValueError("order_sensitivity_max_permutations must be >= 1.")

    partition = str(control.federated_partition).strip().upper()
    if partition not in {"STRATIFIED", "DIRICHLET_LABEL_SKEW"}:
        raise ValueError(
            "federated_partition must be STRATIFIED or DIRICHLET_LABEL_SKEW."
        )
    if float(control.dirichlet_alpha) <= 0:
        raise ValueError("dirichlet_alpha must be > 0.")
    if int(control.dirichlet_max_retries) < 1:
        raise ValueError("dirichlet_max_retries must be >= 1.")


def run_pipeline(
    control: ControlPanel | Mapping[str, Any] = USER_SETTINGS,
    fetcher: Callable[..., Any] | None = None,
):
    """Main public entry point."""
    if not isinstance(control, ControlPanel):
        control = control_from_dict(control)

    validate_control(control)

    if control.input_mode_normalized() == "UCI_ALL":
        results: Dict[str, Any] = {}
        summary_rows: List[Dict[str, Any]] = []

        for key in ["hayes_roth", "car_evaluation", "balance_scale"]:
            child_values = dict(control.__dict__)
            child_values.update({"input_mode": "UCI", "dataset_key": key})
            child = ControlPanel(**child_values)
            result = _run_single_dataset(child, fetcher=fetcher)
            results[key] = result
            summary_rows.append(_summary_row(result))

        summary = pd.DataFrame(summary_rows)
        if control.show_internal_steps and control.show_data_info:
            print("\n" + "=" * 110)
            print("FINAL SUMMARY | Three UCI Datasets")
            print("=" * 110)
            print(summary.to_string(index=False))

        return {"datasets": results, "summary": summary}

    return _run_single_dataset(control, fetcher=fetcher)


def _run_single_dataset(control: ControlPanel, fetcher=None):
    loaded = load_input(control, fetcher=fetcher)
    raw_df = loaded["df"].copy().reset_index(drop=True)
    raw_df["__row_id__"] = np.arange(len(raw_df), dtype=int)

    if control.evaluation_mode_normalized() == "HOLDOUT":
        result = _run_holdout_dataset(control, loaded, raw_df)
    else:
        result = _run_kfold_dataset(control, loaded, raw_df)

    # Client-count sweep 是額外診斷支線：同一資料、同一 seed、同一 evaluation protocol，
    # 只改 C，讓我們能觀察 C -> rule diversity -> conflict -> performance。
    if control.run_client_sweep:
        result["client_sweep"] = _run_client_count_sweep(control, loaded, raw_df)

    return result


def _run_client_count_sweep(
    control: ControlPanel,
    loaded: Mapping[str, Any],
    raw_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Run federated-only experiments for each requested client count.

    Important: this does not overwrite the main experiment.  It is a diagnostic
    branch that changes only n_clients while keeping dataset, seed, split policy,
    bins and prediction policy fixed.
    """
    sweep_results: Dict[int, Mapping[str, Any]] = {}
    rows: List[Dict[str, Any]] = []

    for c in sorted({int(x) for x in control.client_counts}):
        child_values = dict(control.__dict__)
        child_values.update({
            "n_clients": c,
            "run_centralized": False,
            "run_federated": True,
            "run_client_sweep": False,
            "show_internal_steps": False,
            "show_data_info": False,
            "show_rules": False,
            "show_fold_details": False,
            "verbose_lem2": False,
            "report_style": "NONE",
        })
        child = ControlPanel(**child_values)

        if child.evaluation_mode_normalized() == "HOLDOUT":
            child_result = _run_holdout_dataset(child, loaded, raw_df)
        else:
            child_result = _run_kfold_dataset(child, loaded, raw_df)

        sweep_results[c] = child_result
        fed = child_result.get("federated") or {}
        rows.append({
            "dataset": loaded["config"]["name"],
            "clients": c,
            "avg_local_rules": fed.get("avg_local_rule_count"),
            "total_local_rules": fed.get("total_local_rule_count"),
            "global_rules": fed.get("global_rule_count", fed.get("mean_rule_count")),
            "jaccard_antecedent": fed.get("pairwise_jaccard_antecedent"),
            "jaccard_full_rule": fed.get("pairwise_jaccard_full_rule"),
            "conflict_groups": fed.get("conflict_group_count"),
            "conflict_antecedent_rate": fed.get("conflict_antecedent_rate"),
            "conflict_rule_share": fed.get("conflict_rule_share"),
            "conflict_cases": fed.get("conflict_case_count"),
            "conflict_case_rate": fed.get("conflict_case_rate"),
            "conflict_resolution_accuracy": fed.get("conflict_resolution_accuracy"),
            "order_sensitivity_rate": fed.get("order_sensitivity_rate"),
            "balanced_accuracy": fed.get("balanced_accuracy"),
            "order_balanced_accuracy_mean": fed.get("order_balanced_accuracy_mean"),
            "order_balanced_accuracy_std": fed.get("order_balanced_accuracy_std"),
            "order_balanced_accuracy_min": fed.get("order_balanced_accuracy_min"),
            "order_balanced_accuracy_max": fed.get("order_balanced_accuracy_max"),
            "order_conflict_resolution_accuracy_mean": fed.get("order_conflict_resolution_accuracy_mean"),
            "order_conflict_resolution_accuracy_std": fed.get("order_conflict_resolution_accuracy_std"),
            "macro_f1": fed.get("macro_f1"),
            "coverage": fed.get("coverage"),
            "partition_strategy": child.federated_partition.strip().upper(),
            "dirichlet_alpha": (
                float(child.dirichlet_alpha)
                if child.federated_partition.strip().upper() == "DIRICHLET_LABEL_SKEW"
                else float("nan")
            ),
        })

    return {
        "results": sweep_results,
        "summary": pd.DataFrame(rows),
    }


def _run_holdout_dataset(control: ControlPanel, loaded, raw_df):
    target = loaded["target"]
    raw_train, raw_test = stratified_train_test_split(
        raw_df,
        target_col=target,
        test_ratio=control.test_ratio,
        seed=control.seed,
    )

    split_result = _fit_and_run_split(
        control=control,
        loaded=loaded,
        raw_df=raw_df,
        raw_train=raw_train,
        raw_test=raw_test,
        split_label="Holdout",
        show_output=control.show_internal_steps,
    )

    return {
        "dataset_key": loaded.get("key"),
        "config": loaded["config"],
        "features": loaded["features"],
        "target": target,
        "raw_df": raw_df,
        "evaluation_mode": "HOLDOUT",
        **split_result,
    }


def _run_kfold_dataset(control: ControlPanel, loaded, raw_df):
    target = loaded["target"]
    folds = stratified_kfold_splits(
        raw_df,
        target_col=target,
        n_splits=control.cv_folds,
        seed=control.seed,
    )

    fold_results = []

    if control.show_internal_steps and control.show_data_info:
        print("\n" + "#" * 96)
        print(f"DATASET | {loaded['config']['name']}")
        print("#" * 96)
        print(f"Rows={len(raw_df)}, Features={loaded['features']}, Target={target}")
        print(
            f"Evaluation=K_FOLD_CV ({control.cv_folds} folds) | "
            f"Prediction={control.prediction_policy_normalized()}"
        )

    for fold_no, (raw_train, raw_test) in enumerate(folds, 1):
        if control.show_internal_steps and control.show_fold_details:
            print("\n" + "-" * 80)
            print(f"FOLD {fold_no}/{control.cv_folds}")
            print("-" * 80)

        fold_result = _fit_and_run_split(
            control=control,
            loaded=loaded,
            raw_df=raw_df,
            raw_train=raw_train,
            raw_test=raw_test,
            split_label=f"Fold_{fold_no}",
            show_output=(control.show_internal_steps and control.show_fold_details),
        )
        fold_results.append(fold_result)

    central = _aggregate_cv_module_results(fold_results, "centralized")
    federated = _aggregate_cv_module_results(fold_results, "federated")

    if central and control.show_internal_steps:
        print(
            f"\nCV CENTRALIZED | BA={central['balanced_accuracy']:.4f} "
            f"± {central['balanced_accuracy_std']:.4f} | "
            f"Coverage={central['coverage']:.4f} | "
            f"Mean rules={central['mean_rule_count']:.2f}"
        )

    if federated and control.show_internal_steps:
        print(
            f"CV FEDERATED   | BA={federated['balanced_accuracy']:.4f} "
            f"± {federated['balanced_accuracy_std']:.4f} | "
            f"Coverage={federated['coverage']:.4f} | "
            f"Mean rules={federated['mean_rule_count']:.2f}"
        )

    return {
        "dataset_key": loaded.get("key"),
        "config": loaded["config"],
        "features": loaded["features"],
        "target": target,
        "raw_df": raw_df,
        "evaluation_mode": "K_FOLD_CV",
        "cv_folds": control.cv_folds,
        "fold_results": fold_results,
        "centralized": central,
        "federated": federated,
    }


def _fit_and_run_split(
    control: ControlPanel,
    loaded: Mapping[str, Any],
    raw_df: pd.DataFrame,
    raw_train: pd.DataFrame,
    raw_test: pd.DataFrame,
    split_label: str,
    show_output: bool,
):
    features = list(loaded["features"])
    target = loaded["target"]

    # UCI preconfigured datasets are used in their categorical LEM2 view.
    if control.input_mode_normalized() == "UCI":
        continuous: List[str] = []
        categorical = list(features)
    else:
        continuous, categorical = detect_feature_types(
            raw_train,
            features,
            continuous_columns=control.continuous_columns,
            categorical_columns=control.categorical_columns,
            unique_numeric_threshold=control.unique_numeric_threshold,
        )

    if continuous and not control.auto_discretize:
        raise ValueError(
            "Continuous features detected but auto_discretize=False. "
            "Classical LEM2 requires discrete conditions."
        )

    raw_clients = None
    if control.run_federated:
        raw_clients = partition_clients(
            raw_train,
            target_col=target,
            n_clients=control.n_clients,
            seed=control.seed,
            strategy=control.federated_partition,
            dirichlet_alpha=control.dirichlet_alpha,
            dirichlet_max_retries=control.dirichlet_max_retries,
        )

    # Shared preprocessing is fitted only on training data.
    prep_source = raw_clients if raw_clients is not None else {"Training": raw_train}
    preprocessor = fit_shared_preprocessor(
        clients=prep_source,
        features=features,
        target_col=target,
        continuous_columns=continuous,
        categorical_columns=categorical,
        n_bins=control.n_bins,
    )

    train = apply_preprocessor(raw_train, preprocessor, target)
    test = apply_preprocessor(raw_test, preprocessor, target)
    condition_columns = list(preprocessor["condition_columns"])

    clients = None
    if raw_clients is not None:
        clients = {
            name: apply_preprocessor(df, preprocessor, target)
            for name, df in raw_clients.items()
        }

    if show_output and control.show_data_info:
        print_dataset_info(
            loaded=loaded,
            raw_df=raw_df,
            raw_train=raw_train,
            raw_test=raw_test,
            continuous=continuous,
            categorical=categorical,
            preprocessor=preprocessor,
            control=control,
            split_label=split_label,
        )

    central_result = None
    federated_result = None

    if control.run_centralized:
        central_result = run_centralized(
            train=train,
            test=test,
            condition_columns=condition_columns,
            target=target,
            prediction_policy=control.prediction_policy,
            run_evaluation=control.run_evaluation,
            show_rules=(control.show_rules and show_output),
            show_rule_limit=control.show_rule_limit,
            verbose_lem2=control.verbose_lem2,
            quiet=not show_output,
        )

    if control.run_federated:
        federated_result = run_federated(
            clients=clients,
            test=test,
            condition_columns=condition_columns,
            target=target,
            prediction_policy=control.prediction_policy,
            aggregation=control.federated_aggregation,
            run_evaluation=control.run_evaluation,
            show_rules=(control.show_rules and show_output),
            show_rule_limit=control.show_rule_limit,
            verbose_lem2=control.verbose_lem2,
            order_sensitivity_max_permutations=control.order_sensitivity_max_permutations,
            order_sensitivity_seed=control.seed,
            quiet=not show_output,
        )
        federated_result["partition_strategy"] = control.federated_partition.strip().upper()
        federated_result["dirichlet_alpha"] = (
            float(control.dirichlet_alpha)
            if control.federated_partition.strip().upper() == "DIRICHLET_LABEL_SKEW"
            else float("nan")
        )

    if (
        show_output
        and central_result
        and federated_result
        and control.run_evaluation
    ):
        print("\nCOMPARE | Centralized vs Federated")
        print(f"  Centralized BA = {central_result['balanced_accuracy']:.4f}")
        print(f"  Federated   BA = {federated_result['balanced_accuracy']:.4f}")
        print(
            "  Absolute Δ BA = "
            f"{federated_result['balanced_accuracy'] - central_result['balanced_accuracy']:+.4f}"
        )

    return {
        "raw_train": raw_train,
        "raw_test": raw_test,
        "preprocessor": preprocessor,
        "train": train,
        "test": test,
        "centralized": central_result,
        "federated": federated_result,
    }


def _aggregate_cv_module_results(fold_results, key: str):
    modules = [fold[key] for fold in fold_results if fold.get(key) is not None]
    if not modules:
        return None

    rows = []
    diagnostic_fields = [
        "avg_local_rule_count",
        "total_local_rule_count",
        "global_rule_count",
        "pairwise_jaccard_antecedent",
        "pairwise_jaccard_full_rule",
        "conflict_group_count",
        "conflict_antecedent_rate",
        "conflict_rule_share",
        "conflict_case_count",
        "conflict_case_rate",
        "conflict_resolution_accuracy",
        "order_sensitivity_rate",
        "order_sensitivity_conflict_rate",
    ]

    for i, result in enumerate(modules, 1):
        rule_count = len(result.get("rules", result.get("global_rules", [])))
        row = {
            "fold": i,
            "accuracy": result.get("accuracy"),
            "balanced_accuracy": result.get("balanced_accuracy"),
            "macro_f1": result.get("macro_f1"),
            "coverage": result.get("coverage"),
            "rule_count": rule_count,
        }
        for field_name in diagnostic_fields:
            row[field_name] = result.get(field_name)
        rows.append(row)

    metrics = pd.DataFrame(rows)
    out = {
        "accuracy": float(metrics["accuracy"].mean()),
        "accuracy_std": float(metrics["accuracy"].std(ddof=0)),
        "balanced_accuracy": float(metrics["balanced_accuracy"].mean()),
        "balanced_accuracy_std": float(metrics["balanced_accuracy"].std(ddof=0)),
        "macro_f1": float(metrics["macro_f1"].mean()),
        "macro_f1_std": float(metrics["macro_f1"].std(ddof=0)),
        "coverage": float(metrics["coverage"].mean()),
        "coverage_std": float(metrics["coverage"].std(ddof=0)),
        "mean_rule_count": float(metrics["rule_count"].mean()),
        "fold_metrics": metrics,
        "prediction_policy": modules[0].get("prediction_policy"),
    }

    # Federated diagnostics are averaged across folds when K-Fold CV is used.
    for field_name in diagnostic_fields:
        series = pd.to_numeric(metrics[field_name], errors="coerce")
        if series.notna().any():
            out[field_name] = float(series.mean())
            out[field_name + "_std"] = float(series.std(ddof=0))

    if key == "federated":
        out["client_count"] = modules[0].get("client_count")

        # Pool every checked (fold, client-order) result instead of averaging
        # fold-level standard deviations.  This gives unambiguous CV-wide order
        # distribution summaries.
        order_tables = []
        for fold_no, module in enumerate(modules, 1):
            table = module.get("order_distribution_table")
            if isinstance(table, pd.DataFrame) and not table.empty:
                t = table.copy()
                t.insert(0, "fold", fold_no)
                order_tables.append(t)
        if order_tables:
            pooled_orders = pd.concat(order_tables, ignore_index=True)
            out["order_distribution_table"] = pooled_orders
            out["orderings_checked_per_fold"] = int(
                max(len(t) for t in order_tables)
            )
            out["orderings_checked_total"] = int(len(pooled_orders))
            out.update(_finite_summary(
                pooled_orders["accuracy"].tolist(), "order_accuracy"
            ))
            out.update(_finite_summary(
                pooled_orders["balanced_accuracy"].tolist(),
                "order_balanced_accuracy",
            ))
            out.update(_finite_summary(
                pooled_orders["macro_f1"].tolist(), "order_macro_f1"
            ))
            out.update(_finite_summary(
                pooled_orders["coverage"].tolist(), "order_coverage"
            ))
            out.update(_finite_summary(
                pooled_orders["conflict_resolution_accuracy"].tolist(),
                "order_conflict_resolution_accuracy",
            ))

    return out


def _summary_row(result: Mapping[str, Any]) -> Dict[str, Any]:
    central = result.get("centralized")
    fed = result.get("federated")

    def rules_value(module, federated=False):
        if not module:
            return None
        if "mean_rule_count" in module:
            return module["mean_rule_count"]
        return len(module["global_rules"] if federated else module["rules"])

    return {
        "dataset": result["config"]["name"],
        "rows": len(result["raw_df"]),
        "features": len(result["features"]),
        "evaluation": result["evaluation_mode"],
        "central_rules": rules_value(central),
        "central_ba": central.get("balanced_accuracy") if central else None,
        "federated_rules": rules_value(fed, federated=True),
        "federated_ba": fed.get("balanced_accuracy") if fed else None,
        "federated_coverage": fed.get("coverage") if fed else None,
    }


# 【中文說明｜報告層與 Paper Benchmark】
# 這一層只負責「怎麼呈現結果」，不改任何模型結果。
# CLEAN report：顯示目前主實驗的 Rules / Accuracy / Balanced Accuracy / F1 / Coverage。
# PAPER report：另外跑固定的 published benchmark protocol，再與論文數值逐欄比較。
#
# Paper lane 特別注意：
#   - 不是拿 FIRST_MATCH + HOLDOUT 的結果硬跟 paper 比。
#   - 會另外走 Minimal Reduct → LEM2 → Global Strength → 10-Fold CV。
#   - Car Evaluation 若原 benchmark table 沒有 published target，就只顯示 Our Result，不亂補數字。
#
# =============================================================================
# 1B. CLEAN PRESENTATION + PAPER BENCHMARK REPORTING
# =============================================================================


def _dataset_results_map(result: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    if "datasets" in result:
        return dict(result["datasets"])
    key = result.get("dataset_key") or result.get("config", {}).get("name", "dataset")
    return {str(key): result}


def _module_rule_count(module: Optional[Mapping[str, Any]], federated: bool = False):
    if not module:
        return None
    if module.get("full_data_rule_count") is not None:
        return module["full_data_rule_count"]
    if module.get("mean_rule_count") is not None:
        return module["mean_rule_count"]
    rules_key = "global_rules" if federated else "rules"
    return len(module.get(rules_key, []))


def build_clean_summary(
    result: Mapping[str, Any],
    control: ControlPanel | Mapping[str, Any] = USER_SETTINGS,
) -> pd.DataFrame:
    if not isinstance(control, ControlPanel):
        control = control_from_dict(control)

    rows = []
    for _, ds in _dataset_results_map(result).items():
        base = {
            "Dataset": ds["config"]["name"],
            "Rows": len(ds["raw_df"]),
            "Features": len(ds["features"]),
            "Evaluation": ds["evaluation_mode"],
        }
        central = ds.get("centralized")
        fed = ds.get("federated")

        if control.run_centralized and central:
            if control.run_federated:
                base.update({
                    "Centralized Rules": _module_rule_count(central),
                    "Centralized Accuracy": central.get("accuracy"),
                    "Centralized Balanced Accuracy": central.get("balanced_accuracy"),
                    "Centralized Macro F1": central.get("macro_f1"),
                    "Centralized Coverage": central.get("coverage"),
                })
            else:
                base.update({
                    "Rules": _module_rule_count(central),
                    "Accuracy": central.get("accuracy"),
                    "Balanced Accuracy": central.get("balanced_accuracy"),
                    "Macro F1": central.get("macro_f1"),
                    "Coverage": central.get("coverage"),
                })

        if control.run_federated and fed:
            base.update({
                "Federated Rules": _module_rule_count(fed, federated=True),
                "Federated Accuracy": fed.get("accuracy"),
                "Federated Balanced Accuracy": fed.get("balanced_accuracy"),
                "Federated Macro F1": fed.get("macro_f1"),
                "Federated Coverage": fed.get("coverage"),
                "Conflict Case Rate": fed.get("conflict_case_rate"),
                "Conflict Resolution Accuracy": fed.get("conflict_resolution_accuracy"),
                "Order Sensitivity": fed.get("order_sensitivity_rate"),
            })

        rows.append(base)

    return pd.DataFrame(rows)


def build_federated_diagnostics_summary(result: Mapping[str, Any]) -> pd.DataFrame:
    """One row per dataset with rule-diversity and conflict diagnostics."""
    rows: List[Dict[str, Any]] = []
    for _, ds in _dataset_results_map(result).items():
        fed = ds.get("federated")
        if not fed:
            continue
        rows.append({
            "Dataset": ds["config"]["name"],
            "Clients": fed.get("client_count"),
            "Partition": fed.get("partition_strategy"),
            "Dirichlet Alpha": fed.get("dirichlet_alpha"),
            "Avg Local Rules": fed.get("avg_local_rule_count"),
            "Total Local Rules": fed.get("total_local_rule_count"),
            "Global Rules": fed.get("global_rule_count", fed.get("mean_rule_count")),
            "Jaccard Antecedent": fed.get("pairwise_jaccard_antecedent"),
            "Jaccard Full Rule": fed.get("pairwise_jaccard_full_rule"),
            "Conflict Groups": fed.get("conflict_group_count"),
            "Conflict Antecedent Rate": fed.get("conflict_antecedent_rate"),
            "Conflict Rule Share": fed.get("conflict_rule_share"),
            "Conflict Cases": fed.get("conflict_case_count"),
            "Conflict Case Rate": fed.get("conflict_case_rate"),
            "Conflict Resolution Accuracy": fed.get("conflict_resolution_accuracy"),
            "Order Sensitivity": fed.get("order_sensitivity_rate"),
            "Order Sensitivity (Conflict Only)": fed.get("order_sensitivity_conflict_rate"),
            "Balanced Accuracy": fed.get("balanced_accuracy"),
            "Order-Avg BA": fed.get("order_balanced_accuracy_mean"),
            "Order BA SD": fed.get("order_balanced_accuracy_std"),
            "Order BA Min": fed.get("order_balanced_accuracy_min"),
            "Order BA Max": fed.get("order_balanced_accuracy_max"),
            "Order-Avg CRA": fed.get("order_conflict_resolution_accuracy_mean"),
            "Order CRA SD": fed.get("order_conflict_resolution_accuracy_std"),
            "Coverage": fed.get("coverage"),
        })
    return pd.DataFrame(rows)


def build_client_sweep_summary(result: Mapping[str, Any]) -> pd.DataFrame:
    tables = []
    for _, ds in _dataset_results_map(result).items():
        sweep = ds.get("client_sweep") or {}
        table = sweep.get("summary")
        if isinstance(table, pd.DataFrame) and not table.empty:
            tables.append(table.copy())
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def show_federated_diagnostics_report(result: Mapping[str, Any]) -> pd.DataFrame:
    table = build_federated_diagnostics_summary(result)
    if table.empty:
        return table
    print("\n" + "=" * 150)
    print("FEDERATED DIAGNOSTICS｜Client Rules / Diversity / Conflict")
    print("=" * 150)
    print_plain_table(table)
    return table


def show_client_sweep_report(result: Mapping[str, Any]) -> pd.DataFrame:
    table = build_client_sweep_summary(result)
    if table.empty:
        return table
    print("\n" + "=" * 170)
    print("CLIENT COUNT SWEEP｜C → Rule Diversity → Conflict → Performance")
    print("=" * 170)
    print_plain_table(table)
    return table


def print_plain_table(df: pd.DataFrame, decimals: int = 4) -> None:
    if df.empty:
        print("(no rows)")
        return
    work = df.copy()
    for col in work.select_dtypes(include=["float", "float64", "float32"]).columns:
        work[col] = work[col].map(lambda x: "" if pd.isna(x) else f"{x:.{decimals}f}")
    with pd.option_context("display.max_columns", None, "display.width", 220, "display.max_colwidth", 60):
        print(work.to_string(index=False))


def show_clean_report(
    result: Mapping[str, Any],
    control: ControlPanel | Mapping[str, Any] = USER_SETTINGS,
) -> pd.DataFrame:
    table = build_clean_summary(result, control)
    print("\n" + "=" * 110)
    print("LEM2 RESULT SUMMARY")
    print("=" * 110)
    print_plain_table(table)
    return table


def _print_rules_block(
    rules: Sequence["Rule"],
    support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    limit: int = 10,
    prefix: str = "R",
) -> None:
    """Print a compact, presentation-friendly rule list."""
    rules = list(rules or [])
    support_sets = support_sets or {}
    if not rules:
        print("  （沒有產生可顯示的規則）")
        return

    for i, rule in enumerate(rules[:limit], 1):
        support = support_sets.get(rule.key)
        support_text = f" | support={len(support)}" if support is not None else ""
        print(f"  {prefix}{i:02d}. {rule}{support_text}")

    if len(rules) > limit:
        print(f"  ... 尚有 {len(rules) - limit} 條規則未顯示（可調 show_rule_limit）")


def show_rule_report(
    result: Mapping[str, Any],
    control: ControlPanel | Mapping[str, Any] = USER_SETTINGS,
) -> None:
    """
    顯示主實驗真正使用的 LEM2 rules。

    HOLDOUT 有單一訓練模型，因此直接顯示該模型規則。
    K-FOLD 每一 fold 都會重新學規則，沒有唯一 rule set；為避免誤導，
    只顯示 Fold 1 作為「代表規則」，並明確標示它不是整個 CV 的唯一模型。
    """
    if not isinstance(control, ControlPanel):
        control = control_from_dict(control)
    if not control.show_rules:
        return

    print("\n" + "=" * 110)
    print("LEM2 RULES｜主實驗規則")
    print("=" * 110)

    for _, ds in _dataset_results_map(result).items():
        print(f"\n[{ds['config']['name']}] | Evaluation={ds['evaluation_mode']}")

        # K-fold does not have one unique fitted rule set. Show Fold 1 transparently.
        if ds.get("evaluation_mode") == "K_FOLD_CV":
            folds = ds.get("fold_results") or []
            if not folds:
                print("  （沒有 fold 規則可顯示）")
                continue
            print("  說明：K-Fold 每一 Fold 都會重新學規則；以下只顯示 Fold 1 代表規則。")
            current = folds[0]
            if control.run_centralized and current.get("centralized"):
                module = current["centralized"]
                print(f"  Centralized | Fold 1 代表規則 | total={len(module.get('rules', []))}")
                _print_rules_block(
                    module.get("rules", []),
                    module.get("rule_support_sets"),
                    control.show_rule_limit,
                    prefix="C",
                )
            if control.run_federated and current.get("federated"):
                module = current["federated"]
                print(f"  Federated Global UNION | Fold 1 代表規則 | total={len(module.get('global_rules', []))}")
                _print_rules_block(
                    module.get("global_rules", []),
                    module.get("global_rule_support_sets"),
                    control.show_rule_limit,
                    prefix="G",
                )
            continue

        # Holdout has one fitted model, so these are the actual evaluated rules.
        if control.run_centralized and ds.get("centralized"):
            module = ds["centralized"]
            print(f"  Centralized | total={len(module.get('rules', []))}")
            _print_rules_block(
                module.get("rules", []),
                module.get("rule_support_sets"),
                control.show_rule_limit,
                prefix="C",
            )

        if control.run_federated and ds.get("federated"):
            module = ds["federated"]
            print(f"  Federated Global UNION | total={len(module.get('global_rules', []))}")
            _print_rules_block(
                module.get("global_rules", []),
                module.get("global_rule_support_sets"),
                control.show_rule_limit,
                prefix="G",
            )


def _positive_region_size(df: pd.DataFrame, attrs: Sequence[str], target: str) -> int:
    if not attrs:
        return len(df) if df[target].nunique(dropna=False) == 1 else 0
    grouped = df.groupby(list(attrs), dropna=False)[target].nunique(dropna=False)
    pure_keys = grouped[grouped == 1].index
    if len(pure_keys) == 0:
        return 0
    sizes = df.groupby(list(attrs), dropna=False).size()
    return int(sizes.loc[pure_keys].sum())


def dependency_degree(df: pd.DataFrame, attrs: Sequence[str], target: str) -> float:
    return _positive_region_size(df, attrs, target) / len(df) if len(df) else 0.0


def find_minimal_reducts(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
) -> List[Tuple[str, ...]]:
    """Exhaustive minimal-cardinality reduct search; suitable for these 4-6 feature UCI sets."""
    features = list(features)
    full_gamma = dependency_degree(df, features, target)
    for size in range(1, len(features) + 1):
        found = []
        for combo in itertools.combinations(features, size):
            if np.isclose(dependency_degree(df, combo, target), full_gamma):
                found.append(tuple(combo))
        if found:
            return found
    return [tuple(features)]


def run_paper_protocol(
    loaded: Mapping[str, Any],
    cv_folds: int = 10,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Wang-2007-style benchmark lane:
    minimal rough-set reduct -> LEM2 -> global strength -> stratified K-fold CV.

    Reduct selection is performed once on the full labeled decision table to mirror the
    old benchmark workflow. This is a replication lane, not the recommended modern
    leakage-free evaluation design.
    """
    started = time.perf_counter()
    df = loaded["df"].copy().reset_index(drop=True)
    features = list(loaded["features"])
    target = loaded["target"]
    for col in features + [target]:
        df[col] = df[col].astype(str)
    df["__row_id__"] = np.arange(len(df), dtype=int)

    reduct_candidates = find_minimal_reducts(df, features, target)
    reduct = list(sorted(reduct_candidates, key=lambda x: tuple(map(str, x)))[0])

    full_rules = induce_lem2(
        df,
        condition_cols=reduct,
        decision_col=target,
        source="PaperFullData",
        verbose=False,
    )

    folds = stratified_kfold_splits(df, target, n_splits=cv_folds, seed=seed)
    rows = []
    for fold_no, (train, test) in enumerate(folds, 1):
        rules = induce_lem2(
            train,
            condition_cols=reduct,
            decision_col=target,
            source=f"PaperFold_{fold_no}",
            verbose=False,
        )
        default = majority_class(train, target)
        support_sets, class_sizes = fit_rule_support_sets(train, rules, target)
        metrics = evaluate_rule_model(
            test,
            rules,
            default,
            target,
            prediction_policy="GLOBAL_STRENGTH",
            rule_support_sets=support_sets,
            class_sizes=class_sizes,
        )
        rows.append({
            "fold": fold_no,
            "accuracy": metrics["accuracy"],
            "balanced_accuracy": metrics["balanced_accuracy"],
            "macro_f1": metrics["macro_f1"],
            "coverage": metrics["coverage"],
            "rules": len(rules),
        })

    metrics_df = pd.DataFrame(rows)
    return {
        "reduct": reduct,
        "reduct_candidates": [list(x) for x in reduct_candidates],
        "full_data_rules": full_rules,
        "full_data_rule_count": len(full_rules),
        "accuracy": float(metrics_df["accuracy"].mean()),
        "accuracy_std": float(metrics_df["accuracy"].std(ddof=0)),
        "balanced_accuracy": float(metrics_df["balanced_accuracy"].mean()),
        "macro_f1": float(metrics_df["macro_f1"].mean()),
        "coverage": float(metrics_df["coverage"].mean()),
        "mean_rule_count": float(metrics_df["rules"].mean()),
        "fold_metrics": metrics_df,
        "prediction_policy": "GLOBAL_STRENGTH",
        "evaluation_mode": "K_FOLD_CV",
        "cv_folds": cv_folds,
        "runtime_s": float(time.perf_counter() - started),
    }


def attach_paper_protocol(
    result: Mapping[str, Any],
    cv_folds: int = 10,
    seed: int = 42,
) -> Dict[str, Any]:
    # Mutate the returned result intentionally so the full paper diagnostics stay available.
    for key, ds in _dataset_results_map(result).items():
        loaded = {
            "key": ds.get("dataset_key", key),
            "config": ds["config"],
            "df": ds["raw_df"],
            "features": ds["features"],
            "target": ds["target"],
        }
        ds["paper_protocol"] = run_paper_protocol(loaded, cv_folds=cv_folds, seed=seed)
    return dict(result)


def build_paper_comparison(
    result: Mapping[str, Any],
    reference: str = "WANG_2007",
) -> pd.DataFrame:
    if reference not in PAPER_BENCHMARKS:
        raise KeyError(f"Unknown paper benchmark: {reference}")
    refs = PAPER_BENCHMARKS[reference]["datasets"]

    rows = []
    for key, ds in _dataset_results_map(result).items():
        module = ds.get("paper_protocol") or ds.get("centralized") or {}
        paper = refs.get(key)
        reduct = module.get("reduct")
        our_reduct_size = len(reduct) if reduct is not None else len(ds.get("features", []))
        our_rules = module.get("full_data_rule_count")
        if our_rules is None:
            our_rules = _module_rule_count(module)
        our_acc = module.get("accuracy")
        our_acc_pct = round(float(our_acc) * 100, 4) if our_acc is not None else None

        row = {
            "Dataset": ds["config"]["name"],
            "Instances": len(ds["raw_df"]),
            "Features": len(ds["features"]),
            "Our Reduct Size": our_reduct_size,
            "Our Rules": our_rules,
            "Our Accuracy (%)": our_acc_pct,
            "Paper Reduct Size": paper.get("reduct_size") if paper else None,
            "Paper Rules": paper.get("rules") if paper else None,
            "Paper Accuracy (%)": paper.get("accuracy_pct") if paper else None,
            "Our LEM2 Runtime (s)": module.get("runtime_s"),
            "Paper PSORSFS Time (s)": paper.get("psorsfs_time_s") if paper else None,
        }
        if paper and our_rules is not None:
            row["Rules Δ"] = float(our_rules) - float(paper["rules"])
        else:
            row["Rules Δ"] = None
        if paper and our_acc_pct is not None:
            row["Accuracy Δ (pp)"] = round(our_acc_pct - float(paper["accuracy_pct"]), 4)
        else:
            row["Accuracy Δ (pp)"] = None
        rows.append(row)

    return pd.DataFrame(rows)


def show_paper_comparison(
    result: Mapping[str, Any],
    reference: str = "WANG_2007",
) -> pd.DataFrame:
    table = build_paper_comparison(result, reference=reference)
    meta = PAPER_BENCHMARKS[reference]
    print("\n" + "=" * 130)
    print(f"PUBLISHED PAPER COMPARISON | {reference}")
    print(f"Protocol: {meta['protocol']}")
    print("=" * 130)
    print_plain_table(table, decimals=2)
    print("\nNote: Car Evaluation is not reported in Wang et al. (2007) Table 2; its paper columns are blank.")
    return table


def show_paper_rule_report(
    result: Mapping[str, Any],
    control: ControlPanel | Mapping[str, Any] = USER_SETTINGS,
) -> None:
    """Display the full-data LEM2 rule set used for the published-paper replication lane."""
    if not isinstance(control, ControlPanel):
        control = control_from_dict(control)
    if not control.show_rules:
        return

    print("\n" + "=" * 110)
    print("PAPER REPLICATION RULES｜論文對照用完整資料規則")
    print("=" * 110)

    for _, ds in _dataset_results_map(result).items():
        paper = ds.get("paper_protocol")
        if not paper:
            continue
        rules = paper.get("full_data_rules", [])
        reduct = paper.get("reduct", [])
        print(f"\n[{ds['config']['name']}] | Reduct={reduct} | total={len(rules)}")
        print("  說明：這裡顯示完整 labeled data 在選定 reduct 上誘導出的 LEM2 規則；10-fold 評估時每個 Fold 仍會重新學規則。")
        _print_rules_block(rules, None, control.show_rule_limit, prefix="P")


def run_and_report(
    control: ControlPanel | Mapping[str, Any] = USER_SETTINGS,
    fetcher: Callable[..., Any] | None = None,
):
    if not isinstance(control, ControlPanel):
        control = control_from_dict(control)

    result = run_pipeline(control, fetcher=fetcher)
    style = str(control.report_style).strip().upper()

    if style in {"CLEAN", "BOTH"}:
        show_clean_report(result, control)
        show_rule_report(result, control)
        show_federated_diagnostics_report(result)
        if control.run_client_sweep:
            show_client_sweep_report(result)

    if style in {"PAPER", "BOTH"}:
        if control.input_mode_normalized() not in {"UCI", "UCI_ALL"}:
            print("\nPaper comparison skipped: published targets are defined for the configured UCI datasets.")
        else:
            attach_paper_protocol(result, cv_folds=control.paper_cv_folds, seed=control.seed)
            show_paper_comparison(result, reference=control.paper_reference)
            show_paper_rule_report(result, control)

    return result


# 【中文說明｜Input Adapter】
# 這一層把不同來源統一轉成同一種 decision table 格式：
#   X = condition attributes
#   y = decision attribute
#
# UCI_ALL 會自動抓：Hayes-Roth / Car Evaluation / Balance Scale。
# Hayes-Roth 會排除 ID 欄 name，並只保留有 class label 的資料列。
# 這一層只整理資料，不做 LEM2。
#
# =============================================================================
# 2. INPUT ADAPTER
# =============================================================================


def _clean_column_name(name: Any) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def _clean_name_list(values: Optional[Sequence[Any]]) -> List[str]:
    if not values:
        return []
    return [_clean_column_name(v) for v in values]


def prepare_uci_frame(dataset_key: str, X: pd.DataFrame, y: pd.DataFrame | pd.Series):
    if dataset_key not in DATASET_CONFIGS:
        raise KeyError(f"Unknown dataset key: {dataset_key}")

    config = DATASET_CONFIGS[dataset_key]
    X = X.copy()
    X.columns = [_clean_column_name(c) for c in X.columns]

    if isinstance(y, pd.Series):
        y = y.to_frame(name=config["target"])
    else:
        y = y.copy()
        y.columns = [_clean_column_name(c) for c in y.columns]

    target = _clean_column_name(config["target"])
    drop = {_clean_column_name(c) for c in config.get("drop_columns", [])}
    X = X.drop(columns=[c for c in X.columns if c in drop], errors="ignore")

    if target not in y.columns:
        if y.shape[1] != 1:
            raise ValueError(
                f"Expected one target column for {config['name']}, got {list(y.columns)}"
            )
        y = y.rename(columns={y.columns[0]: target})

    features = list(X.columns)
    df = pd.concat([X.reset_index(drop=True), y[[target]].reset_index(drop=True)], axis=1)

    # Hayes-Roth's UCI package view contains unlabeled rows from the separate
    # test portion.  Published 132-row benchmarks use the labeled rows only.
    if config.get("drop_missing_target", False):
        df = df.loc[df[target].notna()].reset_index(drop=True)

    for col in features + [target]:
        if df[col].isna().any():
            raise ValueError(f"Missing values detected in {config['name']} column '{col}'.")
        df[col] = df[col].astype(str).str.strip()

    return df, features, target


def load_uci_dataset(dataset_key: str, fetcher=None):
    if dataset_key not in DATASET_CONFIGS:
        raise KeyError(f"Unknown dataset key: {dataset_key}")

    config = DATASET_CONFIGS[dataset_key]

    if fetcher is None:
        try:
            from ucimlrepo import fetch_ucirepo
        except ImportError as exc:
            raise ImportError("Install ucimlrepo first: pip install ucimlrepo") from exc
        fetcher = fetch_ucirepo

    dataset = fetcher(id=config["uci_id"])
    df, features, target = prepare_uci_frame(
        dataset_key,
        dataset.data.features,
        dataset.data.targets,
    )

    return {
        "key": dataset_key,
        "config": dict(config),
        "dataset": dataset,
        "df": df,
        "features": features,
        "target": target,
    }


def _prepare_custom_frame(
    df: pd.DataFrame,
    target: str,
    drop_columns=None,
    feature_columns=None,
    name: Optional[str] = None,
):
    if df is None or len(df) == 0:
        raise ValueError("Input data is empty.")

    out = df.copy()
    out.columns = [_clean_column_name(c) for c in out.columns]
    target = _clean_column_name(target)

    if target not in out.columns:
        raise KeyError(f"Target column '{target}' not found.")

    drop = set(_clean_name_list(drop_columns))
    drop.discard(target)
    out = out.drop(columns=[c for c in out.columns if c in drop], errors="ignore")

    if feature_columns:
        features = _clean_name_list(feature_columns)
        missing = set(features) - set(out.columns)
        if missing:
            raise KeyError(f"Requested feature columns not found: {sorted(missing)}")
    else:
        features = [c for c in out.columns if c != target]

    if not features:
        raise ValueError("No condition attributes remain after input preparation.")

    selected = out[features + [target]].copy()
    if selected.isna().any().any():
        bad = selected.columns[selected.isna().any()].tolist()
        raise ValueError(f"Missing values detected in columns: {bad}")

    return {
        "key": None,
        "config": {
            "name": name or "Custom Dataset",
            "target": target,
            "drop_columns": sorted(drop),
            "doi": None,
            "note": "Custom input",
        },
        "dataset": None,
        "df": selected,
        "features": features,
        "target": target,
    }


def load_input(control: ControlPanel, fetcher=None):
    mode = control.input_mode_normalized()

    if mode == "UCI":
        return load_uci_dataset(control.dataset_key, fetcher=fetcher)

    if mode == "CSV":
        if not control.data_path or not control.target:
            raise ValueError("CSV mode requires data_path and target.")
        df = pd.read_csv(control.data_path)
        return _prepare_custom_frame(
            df,
            control.target,
            control.drop_columns,
            control.feature_columns,
            control.name or Path(control.data_path).stem,
        )

    if mode == "EXCEL":
        if not control.data_path or not control.target:
            raise ValueError("EXCEL mode requires data_path and target.")
        df = pd.read_excel(control.data_path, sheet_name=control.sheet_name)
        return _prepare_custom_frame(
            df,
            control.target,
            control.drop_columns,
            control.feature_columns,
            control.name or Path(control.data_path).stem,
        )

    if mode == "DATAFRAME":
        if control.dataframe is None or not control.target:
            raise ValueError("DATAFRAME mode requires dataframe and target.")
        return _prepare_custom_frame(
            control.dataframe,
            control.target,
            control.drop_columns,
            control.feature_columns,
            control.name,
        )

    raise ValueError(f"Unsupported input_mode: {control.input_mode}")


# 【中文說明｜資料切分與前處理】
# HOLDOUT：一次切 Train/Test。
# K-FOLD：切成 K 個 folds，每次 K-1 folds train、1 fold test。
# Federated：training data 再切成多個 clients。
#
# LEM2 需要離散條件：
#   - 原本 categorical → 保留原 category。
#   - 真正 continuous → 只用 training side 計算 shared bins，再套到 test。
# 這樣避免 test leakage。
#
# Balance Scale 的 1~5 在 classical LEM2 view 中仍視為 category code，
# 不在這裡偷偷加入 1<2<3<4<5 的 dominance 意義；那是未來 DRSA 的責任。
#
# =============================================================================
# 3. SPLITTING + PREPROCESSING
# =============================================================================


def stratified_train_test_split(df, target_col, test_ratio=0.20, seed=42):
    if not 0 < test_ratio < 1:
        raise ValueError("test_ratio must be between 0 and 1.")

    rng = np.random.default_rng(seed)
    test_ids: List[int] = []

    for _, group in df.groupby(target_col, sort=False):
        ids = group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        n_test = max(1, int(round(len(ids) * test_ratio)))
        if n_test >= len(ids):
            n_test = len(ids) - 1
        if n_test < 1:
            raise ValueError("Each class needs at least 2 rows for holdout evaluation.")
        test_ids.extend(ids[:n_test].tolist())

    test_id_set = set(test_ids)
    train = df.loc[[i for i in df.index if i not in test_id_set]].copy()
    test = df.loc[sorted(test_id_set)].copy()
    return train, test


def stratified_kfold_splits(df, target_col, n_splits=10, seed=42):
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2.")

    class_counts = df[target_col].value_counts()
    if class_counts.empty:
        raise ValueError("Target column has no classes.")

    if int(class_counts.min()) < n_splits:
        raise ValueError(
            f"n_splits={n_splits} exceeds the smallest class size={int(class_counts.min())}."
        )

    rng = np.random.default_rng(seed)
    fold_test_ids: List[List[int]] = [[] for _ in range(n_splits)]

    for _, group in df.groupby(target_col, sort=False):
        ids = group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        chunks = np.array_split(ids, n_splits)
        for fold_no, chunk in enumerate(chunks):
            fold_test_ids[fold_no].extend(int(x) for x in chunk)

    all_ids = set(int(i) for i in df.index)
    folds = []

    for test_ids in fold_test_ids:
        test_set = set(test_ids)
        train_ids = sorted(all_ids - test_set)
        test_ids = sorted(test_set)
        folds.append((df.loc[train_ids].copy(), df.loc[test_ids].copy()))

    return folds


def stratified_client_partition(train_df, target_col, n_clients=5, seed=42):
    if n_clients < 1:
        raise ValueError("n_clients must be >= 1")

    rng = np.random.default_rng(seed)
    buckets: List[List[int]] = [[] for _ in range(n_clients)]

    for _, group in train_df.groupby(target_col, sort=False):
        ids = group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        for i, row_id in enumerate(ids):
            buckets[i % n_clients].append(int(row_id))

    clients: Dict[str, pd.DataFrame] = {}
    for i, ids in enumerate(buckets, 1):
        if not ids:
            raise ValueError(
                f"Client_{i} received no rows. Reduce n_clients for this dataset/split."
            )
        clients[f"Client_{i}"] = train_df.loc[ids].copy().reset_index(drop=True)

    return clients


def dirichlet_label_skew_partition(
    train_df: pd.DataFrame,
    target_col: str,
    n_clients: int = 5,
    alpha: float = 0.5,
    seed: int = 42,
    max_retries: int = 100,
) -> Dict[str, pd.DataFrame]:
    """Partition training rows with class-conditional Dirichlet label skew.

    For each decision class k:
        p_k ~ Dirichlet(alpha * 1_C)
        n_k1,...,n_kC ~ Multinomial(n_k, p_k)

    Mathematical invariants enforced by construction:
    1) every training row is assigned to exactly one client;
    2) client partitions are pairwise disjoint;
    3) the union of client partitions equals the full training set.

    Empty clients are rejected and the deterministic RNG stream continues to the
    next retry.  Therefore identical (data, seed, alpha, C) gives identical output.
    """
    if n_clients < 1:
        raise ValueError("n_clients must be >= 1")
    if float(alpha) <= 0:
        raise ValueError("alpha must be > 0")
    if int(max_retries) < 1:
        raise ValueError("max_retries must be >= 1")
    if len(train_df) < n_clients:
        raise ValueError(
            f"Cannot create {n_clients} non-empty clients from only {len(train_df)} rows."
        )

    rng = np.random.default_rng(seed)
    client_names = [f"Client_{i}" for i in range(1, n_clients + 1)]

    for _attempt in range(int(max_retries)):
        buckets: Dict[str, List[Any]] = {name: [] for name in client_names}

        for _, group in train_df.groupby(target_col, sort=False, dropna=False):
            row_ids = group.index.to_numpy(copy=True)
            rng.shuffle(row_ids)

            proportions = rng.dirichlet(np.full(n_clients, float(alpha), dtype=float))
            counts = rng.multinomial(len(row_ids), proportions)

            start = 0
            for client_name, count in zip(client_names, counts):
                stop = start + int(count)
                if stop > start:
                    buckets[client_name].extend(row_ids[start:stop].tolist())
                start = stop

            # Multinomial counts must consume the class exactly.
            if start != len(row_ids):
                raise AssertionError("Dirichlet partition failed to consume a class exactly.")

        if all(buckets[name] for name in client_names):
            assigned = [idx for name in client_names for idx in buckets[name]]
            if len(assigned) != len(train_df):
                raise AssertionError("Dirichlet partition lost or duplicated rows by count.")
            if len(set(assigned)) != len(assigned):
                raise AssertionError("Dirichlet partition assigned a row to multiple clients.")
            if set(assigned) != set(train_df.index.tolist()):
                raise AssertionError("Dirichlet partition union does not equal the training set.")

            return {
                name: train_df.loc[buckets[name]].copy().reset_index(drop=True)
                for name in client_names
            }

    raise ValueError(
        "DIRICHLET_LABEL_SKEW could not produce all non-empty clients within "
        f"{max_retries} deterministic retries. Increase alpha, reduce n_clients, "
        "or increase dirichlet_max_retries."
    )


def partition_clients(
    train_df: pd.DataFrame,
    target_col: str,
    n_clients: int = 5,
    seed: int = 42,
    strategy: str = "STRATIFIED",
    dirichlet_alpha: float = 0.5,
    dirichlet_max_retries: int = 100,
) -> Dict[str, pd.DataFrame]:
    """Dispatch a mathematically explicit federated partition strategy."""
    strategy = str(strategy).strip().upper()
    if strategy == "STRATIFIED":
        return stratified_client_partition(
            train_df, target_col=target_col, n_clients=n_clients, seed=seed
        )
    if strategy == "DIRICHLET_LABEL_SKEW":
        return dirichlet_label_skew_partition(
            train_df,
            target_col=target_col,
            n_clients=n_clients,
            alpha=dirichlet_alpha,
            seed=seed,
            max_retries=dirichlet_max_retries,
        )
    raise ValueError(
        "strategy must be STRATIFIED or DIRICHLET_LABEL_SKEW."
    )


def _is_numeric_like(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    return bool(pd.to_numeric(series, errors="coerce").notna().all())


def detect_feature_types(
    df,
    features,
    continuous_columns=None,
    categorical_columns=None,
    unique_numeric_threshold=10,
):
    features = [_clean_column_name(f) for f in features]
    continuous_override = set(_clean_name_list(continuous_columns))
    categorical_override = set(_clean_name_list(categorical_columns))

    overlap = continuous_override & categorical_override
    if overlap:
        raise ValueError(f"Columns cannot be both continuous and categorical: {sorted(overlap)}")

    unknown = (continuous_override | categorical_override) - set(features)
    if unknown:
        raise ValueError(f"Type override columns are not selected features: {sorted(unknown)}")

    continuous = []
    categorical = []

    for feature in features:
        if feature in continuous_override:
            continuous.append(feature)
        elif feature in categorical_override:
            categorical.append(feature)
        elif _is_numeric_like(df[feature]) and df[feature].nunique() > unique_numeric_threshold:
            continuous.append(feature)
        else:
            categorical.append(feature)

    return continuous, categorical


def _bin_labels(n_bins: int) -> List[str]:
    if n_bins < 2:
        raise ValueError("n_bins must be >= 2")
    if n_bins == 3:
        return ["Low", "Medium", "High"]
    return [f"Bin_{i}" for i in range(1, n_bins + 1)]


def fit_shared_preprocessor(
    clients: Mapping[str, pd.DataFrame],
    features: Sequence[str],
    target_col: str,
    continuous_columns: Sequence[str],
    categorical_columns: Sequence[str],
    n_bins: int = 3,
):
    features = list(features)
    continuous = list(continuous_columns)
    categorical = list(categorical_columns)

    if set(continuous) | set(categorical) != set(features):
        raise ValueError("Every feature must be typed exactly once.")

    labels = _bin_labels(n_bins)
    local_min_max: Dict[str, Dict[str, Dict[str, float]]] = {}
    global_min_max: Dict[str, Dict[str, float]] = {}
    bin_edges: Dict[str, np.ndarray] = {}
    bin_labels: Dict[str, List[str]] = {}

    for client_name, client_df in clients.items():
        local_min_max[client_name] = {}
        for feature in continuous:
            numeric = pd.to_numeric(client_df[feature], errors="coerce")
            if numeric.isna().any():
                raise ValueError(f"Continuous column '{feature}' has non-numeric values.")
            local_min_max[client_name][feature] = {
                "min": float(numeric.min()),
                "max": float(numeric.max()),
            }

    for feature in continuous:
        lo = min(stats[feature]["min"] for stats in local_min_max.values())
        hi = max(stats[feature]["max"] for stats in local_min_max.values())
        global_min_max[feature] = {"min": lo, "max": hi}

        if np.isclose(lo, hi):
            bin_edges[feature] = np.array([lo - 0.5, hi + 0.5], dtype=float)
            bin_labels[feature] = ["Constant"]
        else:
            bin_edges[feature] = np.linspace(lo, hi, n_bins + 1)
            bin_labels[feature] = list(labels)

    condition_columns = [
        f"{feature}_bin" if feature in continuous else feature
        for feature in features
    ]

    return {
        "features": features,
        "condition_columns": condition_columns,
        "target": target_col,
        "continuous_columns": continuous,
        "categorical_columns": categorical,
        "n_bins": n_bins,
        "local_min_max": local_min_max,
        "global_min_max": global_min_max,
        "bin_edges": bin_edges,
        "bin_labels": bin_labels,
    }


def apply_preprocessor(df, prep, target_col):
    out = df.copy()

    for feature in prep["categorical_columns"]:
        out[feature] = out[feature].astype(str).str.strip()

    for feature in prep["continuous_columns"]:
        values = pd.to_numeric(out[feature], errors="coerce")
        if values.isna().any():
            raise ValueError(f"Continuous column '{feature}' contains non-numeric values.")

        edges = np.asarray(prep["bin_edges"][feature], dtype=float)
        labels = prep["bin_labels"][feature]
        clipped = values.clip(lower=edges[0], upper=edges[-1])
        out[f"{feature}_bin"] = pd.cut(
            clipped,
            bins=edges,
            labels=labels,
            include_lowest=True,
            right=True,
        ).astype(str)

    out[target_col] = out[target_col].astype(str).str.strip()
    return out


def print_dataset_info(
    loaded,
    raw_df,
    raw_train,
    raw_test,
    continuous,
    categorical,
    preprocessor,
    control,
    split_label,
):
    print("\n" + "#" * 96)
    print(f"DATASET | {loaded['config']['name']} | {split_label}")
    print("#" * 96)
    print(f"Rows={len(raw_df)}, Train={len(raw_train)}, Test={len(raw_test)}")
    print(f"Features={loaded['features']}")
    print(f"Target={loaded['target']}")
    print(f"Categorical={categorical}")
    print(f"Continuous={continuous}")
    print(f"Prediction policy={control.prediction_policy_normalized()}")
    print(f"Evaluation mode={control.evaluation_mode_normalized()}")
    print(f"Class distribution={raw_df[loaded['target']].value_counts().to_dict()}")

    if continuous:
        print("Training-only shared discretization:")
        for feature in continuous:
            mm = preprocessor["global_min_max"][feature]
            edges = np.round(preprocessor["bin_edges"][feature], 4).tolist()
            print(f"  {feature}: min={mm['min']:.4f}, max={mm['max']:.4f}, edges={edges}")


# 【中文說明｜規則衝突與績效】
# LEM2 產生 rules 之後，若一筆新資料同時符合多條規則，必須另外定義 conflict resolution。
# 因此這一層與 LEM2 Core 分開。
#
# FIRST_MATCH      ：第一條符合的 rule 決定結果，會受 rule order 影響。
# SIMPLE_VOTING    ：matching rules 一條一票。
# STANDARD_VOTING  ：matching rules 依 training support 加權。
# GLOBAL_STRENGTH  ：比較各 decision class 被 matching rules 覆蓋的 training-object 比例。
#
# 評估指標：
# Accuracy          = 全部樣本中預測正確比例。
# Balanced Accuracy = 各 class recall 的平均，class imbalance 時比較公平。
# Macro F1          = 各 class F1 的平均。
# Coverage          = 有至少一條規則命中的 test samples 比例。
#
# 另外，Federated 診斷會額外計算：
# - Pairwise Jaccard：client rulesets 的相似度。
# - Conflict Antecedent Rate：相同 antecedent 對應多個 decisions 的比例。
# - Conflict Rule Share：參與 conflict 的 global rules 比例。
# - Conflict Case Rate：test case 同時被不同 decision rules 命中的比例。
# - Conflict Resolution Accuracy：只在 conflict cases 上看最終 prediction 是否正確。
# - Order Sensitivity：改變 client/ruleset arrival order 後，prediction 會改變的 test case 比例。
#
# =============================================================================
# 4. PREDICTION + EVALUATION POLICY
# =============================================================================


def majority_class(df: pd.DataFrame, target_col: str):
    return str(df[target_col].value_counts().idxmax())


def majority_class_from_clients(clients: Mapping[str, pd.DataFrame], target_col: str):
    counts: Counter = Counter()
    for df in clients.values():
        counts.update(df[target_col].astype(str).value_counts().to_dict())
    if not counts:
        raise ValueError("No client labels available for default class.")
    return counts.most_common(1)[0][0]


def _rule_matches(row: pd.Series, rule: Rule) -> bool:
    return all(str(row[attr]) == str(value) for attr, value in rule.conditions)


def matching_rules(row: pd.Series, rules: Sequence[Rule]) -> List[Rule]:
    return [rule for rule in rules if _rule_matches(row, rule)]


def _resolve_vote(votes: Mapping[Any, float], default_class: Any):
    if not votes:
        return default_class
    best = max(votes.values())
    winners = [decision for decision, score in votes.items() if np.isclose(score, best)]
    if default_class in winners:
        return default_class
    return sorted(winners, key=str)[0]


def predict_with_policy(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
    policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    policy = str(policy).strip().upper()

    if policy == "FIRST_MATCH":
        for rule in rules:
            if _rule_matches(row, rule):
                return rule.decision, [rule]
        return default_class, []

    matched = matching_rules(row, rules)
    if not matched:
        return default_class, []

    votes: Dict[Any, float] = defaultdict(float)

    if policy == "SIMPLE_VOTING":
        for rule in matched:
            votes[rule.decision] += 1.0

    elif policy == "STANDARD_VOTING":
        if rule_weights is None:
            raise ValueError("STANDARD_VOTING requires rule_weights.")
        for rule in matched:
            votes[rule.decision] += float(rule_weights.get(rule.key, 0.0))

    elif policy == "GLOBAL_STRENGTH":
        if rule_support_sets is None or class_sizes is None:
            raise ValueError(
                "GLOBAL_STRENGTH requires rule_support_sets and class_sizes."
            )

        matched_by_decision: Dict[Any, List[Rule]] = defaultdict(list)
        for rule in matched:
            matched_by_decision[rule.decision].append(rule)

        for decision, decision_rules in matched_by_decision.items():
            supported_objects: Set[Any] = set()
            for rule in decision_rules:
                supported_objects |= set(rule_support_sets.get(rule.key, set()))

            denominator = int(class_sizes.get(decision, 0))
            votes[decision] = (
                len(supported_objects) / denominator
                if denominator > 0
                else 0.0
            )

    else:
        raise ValueError(
            "policy must be FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING, "
            "or GLOBAL_STRENGTH."
        )

    return _resolve_vote(votes, default_class), matched


def fit_rule_weights(train: pd.DataFrame, rules: Sequence[Rule]) -> Dict[Any, float]:
    """
    Standard-voting weight = number of training objects matching the antecedent.
    """
    weights: Dict[Any, float] = {}

    for rule in rules:
        count = 0
        for _, row in train.iterrows():
            if _rule_matches(row, rule):
                count += 1
        weights[rule.key] = float(count)

    return weights


def fit_rule_support_sets(
    train: pd.DataFrame,
    rules: Sequence[Rule],
    target: str,
    row_prefix: Optional[str] = None,
) -> Tuple[Dict[Any, Set[Any]], Dict[Any, int]]:
    """
    Build the support context required by GLOBAL_STRENGTH.

    For each rule, store training objects that satisfy both its antecedent
    and its decision.  A prefix can be used so federated client row IDs stay
    globally unique without sharing raw rows.
    """
    support_sets: Dict[Any, Set[Any]] = {}
    class_sizes = train[target].astype(str).value_counts().to_dict()

    for rule in rules:
        supported: Set[Any] = set()
        for idx, row in train.iterrows():
            if _rule_matches(row, rule) and str(row[target]) == str(rule.decision):
                object_id = (row_prefix, int(idx)) if row_prefix is not None else int(idx)
                supported.add(object_id)
        support_sets[rule.key] = supported

    return support_sets, {str(k): int(v) for k, v in class_sizes.items()}


def aggregate_rule_support_context(
    local_support_sets: Mapping[str, Mapping[Any, Set[Any]]],
    local_class_sizes: Mapping[str, Mapping[Any, int]],
) -> Tuple[Dict[Any, Set[Any]], Dict[Any, int]]:
    merged_sets: Dict[Any, Set[Any]] = defaultdict(set)
    merged_class_sizes: Counter = Counter()

    for support_sets in local_support_sets.values():
        for key, values in support_sets.items():
            merged_sets[key] |= set(values)

    for class_sizes in local_class_sizes.values():
        merged_class_sizes.update({str(k): int(v) for k, v in class_sizes.items()})

    return dict(merged_sets), dict(merged_class_sizes)


def aggregate_rule_weights(
    local_rule_weights: Mapping[str, Mapping[Any, float]],
) -> Dict[Any, float]:
    """Sum local antecedent-support weights for identical global rules."""
    merged: Dict[Any, float] = defaultdict(float)
    for weights in local_rule_weights.values():
        for key, value in weights.items():
            merged[key] += float(value)
    return dict(merged)


def predict_table(
    df: pd.DataFrame,
    rules: Sequence[Rule],
    default_class: Any,
    prediction_policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    preds = []
    matched_rule_lists = []

    for _, row in df.iterrows():
        pred, matched = predict_with_policy(
            row,
            rules,
            default_class=default_class,
            policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        preds.append(pred)
        matched_rule_lists.append(matched)

    return preds, matched_rule_lists


def balanced_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    recalls = []

    for cls in pd.unique(y_true):
        mask = y_true == cls
        if mask.sum():
            recalls.append(float((y_pred[mask] == cls).mean()))

    return float(np.mean(recalls)) if recalls else 0.0



def classification_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(y_true == y_pred))


def macro_f1_score(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    classes = sorted(set(y_true.tolist()) | set(y_pred.tolist()), key=str)
    if not classes:
        return 0.0

    scores = []
    for cls in classes:
        tp = int(np.sum((y_true == cls) & (y_pred == cls)))
        fp = int(np.sum((y_true != cls) & (y_pred == cls)))
        fn = int(np.sum((y_true == cls) & (y_pred != cls)))
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        scores.append(f1)
    return float(np.mean(scores))

def rule_antecedent_signature(rule: "Rule") -> Tuple[Tuple[str, str], ...]:
    """Canonical antecedent only; used for paper-style Jaccard and conflict grouping."""
    return tuple(sorted((str(a), str(v)) for a, v in rule.conditions))


def rule_full_signature(rule: "Rule") -> Tuple[Tuple[Tuple[str, str], ...], str]:
    """Antecedent + decision; used when full rule identity matters."""
    return (rule_antecedent_signature(rule), str(rule.decision))


def _jaccard(set_a: Set[Any], set_b: Set[Any]) -> float:
    union = set_a | set_b
    if not union:
        return float("nan")
    return float(len(set_a & set_b) / len(union))


def pairwise_rule_jaccard(
    local_rules: Mapping[str, Sequence["Rule"]],
) -> Dict[str, Any]:
    """Compute pairwise client similarity in two ways.

    antecedent: conditions only, matching the healthcare paper's stated set view.
    full_rule:  conditions + decision, stricter and useful for conflict research.
    """
    names = list(local_rules)
    rows: List[Dict[str, Any]] = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            ant_a = {rule_antecedent_signature(r) for r in local_rules[a]}
            ant_b = {rule_antecedent_signature(r) for r in local_rules[b]}
            full_a = {rule_full_signature(r) for r in local_rules[a]}
            full_b = {rule_full_signature(r) for r in local_rules[b]}
            rows.append({
                "client_i": a,
                "client_j": b,
                "jaccard_antecedent": _jaccard(ant_a, ant_b),
                "jaccard_full_rule": _jaccard(full_a, full_b),
            })

    table = pd.DataFrame(rows)
    if table.empty:
        return {
            "pairwise_table": table,
            "pairwise_jaccard_antecedent": float("nan"),
            "pairwise_jaccard_full_rule": float("nan"),
        }

    return {
        "pairwise_table": table,
        "pairwise_jaccard_antecedent": float(table["jaccard_antecedent"].mean(skipna=True)),
        "pairwise_jaccard_full_rule": float(table["jaccard_full_rule"].mean(skipna=True)),
    }


def audit_rule_conflicts(
    rules: Sequence["Rule"],
    rule_sources: Optional[Mapping[Any, Sequence[str]]] = None,
) -> Dict[str, Any]:
    """Audit exact-antecedent conflicts in a global ruleset.

    A conflict group exists when the same antecedent maps to >1 decision.
    This is stricter than case-level conflict; overlapping non-identical rules are
    captured later by conflict_case_rate.  When provenance is supplied, the audit
    reports all clients that produced each conflicting full rule rather than only
    the first client retained by UNION ordering.
    """
    groups: Dict[Any, List["Rule"]] = defaultdict(list)
    for rule in rules:
        groups[rule_antecedent_signature(rule)].append(rule)

    conflicting = {
        ant: rs
        for ant, rs in groups.items()
        if len({str(r.decision) for r in rs}) > 1
    }
    conflict_rule_count = sum(len(rs) for rs in conflicting.values())
    unique_antecedents = len(groups)
    total_rules = len(rules)

    rows = []
    for ant, rs in conflicting.items():
        sources: Set[str] = set()
        for r in rs:
            if rule_sources is not None:
                sources.update(str(x) for x in rule_sources.get(r.key, ()))
            elif r.source:
                sources.add(str(r.source))
        rows.append({
            "antecedent": " AND ".join(f"{a}={v}" for a, v in ant),
            "decisions": sorted({str(r.decision) for r in rs}),
            "rule_count": len(rs),
            "sources": sorted(sources),
        })

    return {
        "conflict_groups_table": pd.DataFrame(rows),
        "unique_antecedent_count": unique_antecedents,
        "conflict_group_count": len(conflicting),
        "conflict_antecedent_rate": (len(conflicting) / unique_antecedents) if unique_antecedents else 0.0,
        "conflict_rule_count": conflict_rule_count,
        "conflict_rule_share": (conflict_rule_count / total_rules) if total_rules else 0.0,
    }


def audit_conflict_cases(
    test: pd.DataFrame,
    rules: Sequence["Rule"],
    predictions: Sequence[Any],
    target: str,
) -> Dict[str, Any]:
    """Measure conflicts that actually occur during inference.

    A test case is conflicting if all matching rules contain >1 distinct decision.
    Conflict resolution accuracy is accuracy restricted to those cases only.
    """
    conflict_flags: List[bool] = []
    rows: List[Dict[str, Any]] = []

    for pos, (_, row) in enumerate(test.iterrows()):
        matched = matching_rules(row, rules)
        decisions = sorted({str(r.decision) for r in matched})
        is_conflict = len(decisions) > 1
        conflict_flags.append(is_conflict)
        if is_conflict:
            rows.append({
                "row_id": int(row["__row_id__"]) if "__row_id__" in row.index else pos,
                "true": str(row[target]),
                "predicted": str(predictions[pos]),
                "matching_rules": len(matched),
                "decisions": decisions,
                "correct": str(predictions[pos]) == str(row[target]),
            })

    n = len(test)
    count = int(sum(conflict_flags))
    resolution_accuracy = (
        float(np.mean([r["correct"] for r in rows])) if rows else float("nan")
    )
    return {
        "conflict_cases_table": pd.DataFrame(rows),
        "conflict_case_flags": conflict_flags,
        "conflict_case_count": count,
        "conflict_case_rate": (count / n) if n else 0.0,
        "conflict_resolution_accuracy": resolution_accuracy,
    }


def _client_orderings(
    client_names: Sequence[str],
    max_permutations: int = 120,
    seed: int = 42,
) -> List[Tuple[str, ...]]:
    names = tuple(client_names)
    if len(names) <= 1:
        return [names]

    factorial = math.factorial(len(names))
    if factorial <= max_permutations:
        return list(itertools.permutations(names))

    # Uniform random permutations with rejection of duplicates.  Do not force the
    # original client order into the sample, because that would overweight one
    # specific ordering when factorial(C) > max_permutations.
    rng = np.random.default_rng(seed)
    seen: Set[Tuple[str, ...]] = set()
    orders: List[Tuple[str, ...]] = []
    attempts = 0
    max_attempts = max_permutations * 100
    while len(orders) < max_permutations and attempts < max_attempts:
        candidate = tuple(rng.permutation(names).tolist())
        if candidate not in seen:
            seen.add(candidate)
            orders.append(candidate)
        attempts += 1
    return orders


def audit_order_sensitivity(
    test: pd.DataFrame,
    local_rules: Mapping[str, Sequence["Rule"]],
    default_class: Any,
    prediction_policy: str,
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
    conflict_case_flags: Optional[Sequence[bool]] = None,
    max_permutations: int = 120,
    seed: int = 42,
) -> Dict[str, Any]:
    """How often predictions change when client arrival order changes."""
    orders = _client_orderings(list(local_rules), max_permutations=max_permutations, seed=seed)
    if not orders or len(test) == 0:
        return {
            "orderings_checked": len(orders),
            "order_sensitivity_rate": 0.0,
            "order_sensitivity_conflict_rate": float("nan"),
        }

    predictions_by_order: List[List[Any]] = []
    for order in orders:
        ordered = {name: local_rules[name] for name in order}
        ordered_global_rules = union_rules(ordered)
        preds, _ = predict_table(
            test,
            ordered_global_rules,
            default_class,
            prediction_policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        predictions_by_order.append([str(x) for x in preds])

    matrix = np.asarray(predictions_by_order, dtype=object)
    sensitive = np.array([len(set(matrix[:, j].tolist())) > 1 for j in range(matrix.shape[1])])
    overall = float(sensitive.mean()) if len(sensitive) else 0.0

    conflict_only = float("nan")
    if conflict_case_flags is not None:
        conflict_mask = np.asarray(conflict_case_flags, dtype=bool)
        if conflict_mask.any():
            conflict_only = float(sensitive[conflict_mask].mean())

    return {
        "orderings_checked": len(orders),
        "order_sensitivity_rate": overall,
        "order_sensitivity_conflict_rate": conflict_only,
    }


def _finite_summary(values: Sequence[float], prefix: str) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            f"{prefix}_mean": float("nan"),
            f"{prefix}_std": float("nan"),
            f"{prefix}_min": float("nan"),
            f"{prefix}_max": float("nan"),
        }
    return {
        f"{prefix}_mean": float(arr.mean()),
        f"{prefix}_std": float(arr.std(ddof=0)),
        f"{prefix}_min": float(arr.min()),
        f"{prefix}_max": float(arr.max()),
    }


def audit_order_distribution(
    test: pd.DataFrame,
    local_rules: Mapping[str, Sequence["Rule"]],
    default_class: Any,
    target: str,
    prediction_policy: str,
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
    max_permutations: int = 120,
    seed: int = 42,
) -> Dict[str, Any]:
    """Evaluate prediction metrics over client-arrival permutations.

    For a fixed client count C and fixed learned local rules, this isolates the
    order effect induced by UNION + FIRST_MATCH from the client-count effect.
    Metrics are recomputed for every checked client order and summarized by
    population mean/std/min/max.  Conflict cases are defined by the order-invariant
    set of all matching global rules; CRA is then evaluated per order.
    """
    orders = _client_orderings(
        list(local_rules), max_permutations=max_permutations, seed=seed
    )
    if not orders or len(test) == 0:
        empty = pd.DataFrame()
        total_possible = math.factorial(len(local_rules)) if len(local_rules) > 1 else 1
        out: Dict[str, Any] = {
            "order_distribution_table": empty,
            "orderings_checked": len(orders),
            "total_possible_orderings": total_possible,
            "order_sampling_complete": len(orders) == total_possible,
            "order_sensitivity_rate": 0.0,
            "order_sensitivity_conflict_rate": float("nan"),
        }
        for name in (
            "order_accuracy",
            "order_balanced_accuracy",
            "order_macro_f1",
            "order_coverage",
            "order_conflict_resolution_accuracy",
        ):
            out.update(_finite_summary([], name))
        return out

    # The set of global full rules is invariant to client order; only ordering changes.
    reference_rules = union_rules(local_rules)
    dummy_predictions = [default_class] * len(test)
    reference_conflicts = audit_conflict_cases(
        test=test,
        rules=reference_rules,
        predictions=dummy_predictions,
        target=target,
    )
    conflict_flags = np.asarray(reference_conflicts["conflict_case_flags"], dtype=bool)

    rows: List[Dict[str, Any]] = []
    predictions_by_order: List[List[str]] = []

    for order in orders:
        ordered_local = {name: local_rules[name] for name in order}
        ordered_rules = union_rules(ordered_local)
        metrics = evaluate_rule_model(
            test=test,
            rules=ordered_rules,
            default_class=default_class,
            target=target,
            prediction_policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        case_audit = audit_conflict_cases(
            test=test,
            rules=ordered_rules,
            predictions=metrics["predictions"],
            target=target,
        )
        predictions_by_order.append([str(x) for x in metrics["predictions"]])
        rows.append({
            "client_order": " -> ".join(order),
            "accuracy": metrics["accuracy"],
            "balanced_accuracy": metrics["balanced_accuracy"],
            "macro_f1": metrics["macro_f1"],
            "coverage": metrics["coverage"],
            "conflict_resolution_accuracy": case_audit["conflict_resolution_accuracy"],
        })

    table = pd.DataFrame(rows)
    matrix = np.asarray(predictions_by_order, dtype=object)
    sensitive = np.array([
        len(set(matrix[:, j].tolist())) > 1
        for j in range(matrix.shape[1])
    ], dtype=bool)
    order_sensitivity_rate = float(sensitive.mean()) if sensitive.size else 0.0
    order_sensitivity_conflict_rate = (
        float(sensitive[conflict_flags].mean())
        if conflict_flags.any()
        else float("nan")
    )

    total_possible = math.factorial(len(local_rules)) if len(local_rules) > 1 else 1
    out = {
        "order_distribution_table": table,
        "orderings_checked": len(orders),
        "total_possible_orderings": total_possible,
        "order_sampling_complete": len(orders) == total_possible,
        "order_sensitivity_rate": order_sensitivity_rate,
        "order_sensitivity_conflict_rate": order_sensitivity_conflict_rate,
    }
    out.update(_finite_summary(table["accuracy"].tolist(), "order_accuracy"))
    out.update(_finite_summary(table["balanced_accuracy"].tolist(), "order_balanced_accuracy"))
    out.update(_finite_summary(table["macro_f1"].tolist(), "order_macro_f1"))
    out.update(_finite_summary(table["coverage"].tolist(), "order_coverage"))
    out.update(_finite_summary(
        table["conflict_resolution_accuracy"].tolist(),
        "order_conflict_resolution_accuracy",
    ))
    return out


def evaluate_rule_model(
    test: pd.DataFrame,
    rules: Sequence[Rule],
    default_class: Any,
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    preds, matched = predict_table(
        test,
        rules,
        default_class,
        prediction_policy=prediction_policy,
        rule_weights=rule_weights,
        rule_support_sets=rule_support_sets,
        class_sizes=class_sizes,
    )

    return {
        "accuracy": classification_accuracy(test[target], preds),
        "balanced_accuracy": balanced_accuracy(test[target], preds),
        "macro_f1": macro_f1_score(test[target], preds),
        "coverage": float(np.mean([len(x) > 0 for x in matched])) if len(test) else 0.0,
        "predictions": preds,
        "matched_rules": matched,
        "prediction_policy": str(prediction_policy).strip().upper(),
    }


# 【中文說明｜Centralized】
# 所有 training data 放在同一張 decision table 中：
#     Train → Preprocess → LEM2 → Rules → Prediction Policy → Test
#
# 這條線是最單純的 baseline。
# 它不做 client partition，也沒有 rule aggregation。
#
# =============================================================================
# 5. CENTRALIZED MODULE
# =============================================================================


def run_centralized(
    train: pd.DataFrame,
    test: pd.DataFrame,
    condition_columns: Sequence[str],
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    run_evaluation: bool = True,
    show_rules: bool = True,
    show_rule_limit: int = 5,
    verbose_lem2: bool = False,
    quiet: bool = False,
):
    if not quiet:
        print("\nCENTRALIZED | LEM2")

    rules = induce_lem2(
        train,
        condition_cols=condition_columns,
        decision_col=target,
        source="Centralized",
        verbose=verbose_lem2,
    )

    default_class = majority_class(train, target)
    rule_weights = fit_rule_weights(train, rules)
    rule_support_sets, class_sizes = fit_rule_support_sets(
        train, rules, target=target
    )

    result: Dict[str, Any] = {
        "rules": rules,
        "rule_weights": rule_weights,
        "rule_support_sets": rule_support_sets,
        "class_sizes": class_sizes,
        "default_class": default_class,
        "prediction_policy": str(prediction_policy).strip().upper(),
        "test_row_ids": test["__row_id__"].astype(int).tolist() if "__row_id__" in test else [],
    }

    if show_rules:
        print(f"  Rules = {len(rules)}")
        for i, rule in enumerate(rules[:show_rule_limit], 1):
            print(f"  C{i:02d}. {rule}")
        if len(rules) > show_rule_limit:
            print(f"  ... {len(rules)-show_rule_limit} more")

    if run_evaluation:
        metrics = evaluate_rule_model(
            test,
            rules,
            default_class,
            target,
            prediction_policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        result.update(metrics)
        if not quiet:
            print(
                f"  Prediction = {metrics['prediction_policy']} | "
                f"Accuracy = {metrics['accuracy']:.4f} | "
                f"Balanced Accuracy = {metrics['balanced_accuracy']:.4f} | "
                f"Macro F1 = {metrics['macro_f1']:.4f} | "
                f"Coverage = {metrics['coverage']:.4f}"
            )

    return result


# 【中文說明｜Federated】
# Federated 不是 LEM2 演算法的一部分，而是外層協作架構：
#
#     Training Data
#          ↓
#     Client Partition
#          ↓
#   Client 1 → Local LEM2 → Rules_1
#   Client 2 → Local LEM2 → Rules_2
#   ...
#          ↓
#        UNION
#          ↓
#     Global Rule Set
#          ↓
#  Prediction Policy / Evaluation
#
# 目前聚合策略是 UNION：相同條件與相同 decision 的 rule 去重後聯集。
# 不把 raw rows 直接集中回 server；Global Strength 所需的是 support context / metadata。
#
# =============================================================================
# 6. FEDERATED MODULE -- outside LEM2 core
# =============================================================================


def union_rules_with_provenance(
    local_rules: Mapping[str, Sequence[Rule]],
) -> Tuple[List[Rule], Dict[Any, Tuple[str, ...]]]:
    """UNION aggregation plus complete source provenance.

    Rule identity remains exactly the existing mathematical/code definition:
        key = (sorted antecedent conditions, decision)

    UNION keeps the first occurrence only to preserve first-match ordering, but
    provenance records *every* client that independently produced the same rule.
    This separates two concepts that must not be conflated:
      - global rule order (needed for FIRST_MATCH), and
      - source multiplicity (needed for later collaborative weighting/auditing).
    """
    merged: List[Rule] = []
    seen: Set[Any] = set()
    source_sets: Dict[Any, Set[str]] = defaultdict(set)

    for client_name, rules in local_rules.items():
        for rule in rules:
            source_sets[rule.key].add(str(client_name))
            if rule.key not in seen:
                seen.add(rule.key)
                merged.append(rule)

    provenance = {
        key: tuple(sorted(values, key=str))
        for key, values in source_sets.items()
    }
    return merged, provenance


def union_rules(local_rules: Mapping[str, Sequence[Rule]]) -> List[Rule]:
    """Backward-compatible UNION rule list without exposing provenance."""
    merged, _ = union_rules_with_provenance(local_rules)
    return merged


def run_federated(
    clients: Mapping[str, pd.DataFrame],
    test: pd.DataFrame,
    condition_columns: Sequence[str],
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    aggregation: str = "UNION",
    run_evaluation: bool = True,
    show_rules: bool = True,
    show_rule_limit: int = 5,
    verbose_lem2: bool = False,
    order_sensitivity_max_permutations: int = 120,
    order_sensitivity_seed: int = 42,
    quiet: bool = False,
):
    if not quiet:
        print("\nFEDERATED | Local LEM2 -> Aggregation")

    local_rules: Dict[str, List[Rule]] = {}
    local_rule_weights: Dict[str, Dict[Any, float]] = {}
    local_rule_support_sets: Dict[str, Dict[Any, Set[Any]]] = {}
    local_class_sizes: Dict[str, Dict[Any, int]] = {}
    local_metrics: List[Dict[str, Any]] = []

    for client_name, client_df in clients.items():
        rules = induce_lem2(
            client_df,
            condition_cols=condition_columns,
            decision_col=target,
            source=client_name,
            verbose=verbose_lem2,
        )
        weights = fit_rule_weights(client_df, rules)
        support_sets, class_sizes = fit_rule_support_sets(
            client_df,
            rules,
            target=target,
            row_prefix=client_name,
        )

        local_rules[client_name] = rules
        local_rule_weights[client_name] = weights
        local_rule_support_sets[client_name] = support_sets
        local_class_sizes[client_name] = class_sizes

        row = {
            "client": client_name,
            "n": len(client_df),
            "rules": len(rules),
            "classes": client_df[target].value_counts().to_dict(),
        }

        if run_evaluation:
            local_default = majority_class(client_df, target)
            row.update(
                evaluate_rule_model(
                    test,
                    rules,
                    local_default,
                    target,
                    prediction_policy=prediction_policy,
                    rule_weights=weights,
                    rule_support_sets=support_sets,
                    class_sizes=class_sizes,
                )
            )

        local_metrics.append(row)

        if show_rules:
            msg = f"  {client_name}: n={len(client_df)}, rules={len(rules)}"
            if run_evaluation:
                msg += f", BA={row['balanced_accuracy']:.4f}, coverage={row['coverage']:.4f}"
            print(msg)

    aggregation = aggregation.strip().upper()
    if aggregation != "UNION":
        raise ValueError("Only federated_aggregation='UNION' is implemented.")

    global_rules, global_rule_sources = union_rules_with_provenance(local_rules)
    global_rule_weights = aggregate_rule_weights(local_rule_weights)
    global_rule_support_sets, global_class_sizes = aggregate_rule_support_context(
        local_rule_support_sets, local_class_sizes
    )
    global_default = majority_class_from_clients(clients, target)

    local_counts = [len(rs) for rs in local_rules.values()]
    jaccard = pairwise_rule_jaccard(local_rules)
    rule_conflicts = audit_rule_conflicts(global_rules, rule_sources=global_rule_sources)

    result: Dict[str, Any] = {
        "clients": dict(clients),
        "client_count": len(clients),
        "local_rules": local_rules,
        "local_rule_weights": local_rule_weights,
        "local_rule_support_sets": local_rule_support_sets,
        "local_class_sizes": local_class_sizes,
        "local_metrics": pd.DataFrame(local_metrics),
        "avg_local_rule_count": float(np.mean(local_counts)) if local_counts else 0.0,
        "total_local_rule_count": int(sum(local_counts)),
        "global_rules": global_rules,
        "global_rule_count": int(len(global_rules)),
        "global_rule_sources": global_rule_sources,
        "global_rule_source_counts": {
            key: len(sources) for key, sources in global_rule_sources.items()
        },
        "global_rule_weights": global_rule_weights,
        "global_rule_support_sets": global_rule_support_sets,
        "global_class_sizes": global_class_sizes,
        "default_class": global_default,
        "prediction_policy": str(prediction_policy).strip().upper(),
        "test_row_ids": test["__row_id__"].astype(int).tolist() if "__row_id__" in test else [],
        **jaccard,
        **rule_conflicts,
    }

    if show_rules:
        print("\n  Aggregation = UNION")
        print(f"  Total local rules = {result['total_local_rule_count']}")
        print(f"  Unique global rules = {len(global_rules)}")
        print(f"  Avg local rules = {result['avg_local_rule_count']:.2f}")
        print(f"  Pairwise Jaccard (antecedent) = {result['pairwise_jaccard_antecedent']:.4f}")
        print(f"  Pairwise Jaccard (full rule) = {result['pairwise_jaccard_full_rule']:.4f}")
        print(
            f"  Conflict groups = {result['conflict_group_count']} | "
            f"Antecedent rate = {result['conflict_antecedent_rate']:.4f} | "
            f"Rule share = {result['conflict_rule_share']:.4f}"
        )
        for i, rule in enumerate(global_rules[:show_rule_limit], 1):
            print(f"  G{i:02d}. {rule}")
        if len(global_rules) > show_rule_limit:
            print(f"  ... {len(global_rules)-show_rule_limit} more")

    if run_evaluation:
        metrics = evaluate_rule_model(
            test,
            global_rules,
            global_default,
            target,
            prediction_policy=prediction_policy,
            rule_weights=global_rule_weights,
            rule_support_sets=global_rule_support_sets,
            class_sizes=global_class_sizes,
        )
        result.update(metrics)

        case_conflicts = audit_conflict_cases(
            test=test,
            rules=global_rules,
            predictions=metrics["predictions"],
            target=target,
        )
        result.update(case_conflicts)

        order_audit = audit_order_distribution(
            test=test,
            local_rules=local_rules,
            default_class=global_default,
            target=target,
            prediction_policy=prediction_policy,
            rule_weights=global_rule_weights,
            rule_support_sets=global_rule_support_sets,
            class_sizes=global_class_sizes,
            max_permutations=order_sensitivity_max_permutations,
            seed=order_sensitivity_seed,
        )
        result.update(order_audit)

        if not quiet:
            cra = result["conflict_resolution_accuracy"]
            cra_text = "NA" if pd.isna(cra) else f"{cra:.4f}"
            print(
                f"  Prediction = {metrics['prediction_policy']} | "
                f"Federated Accuracy = {metrics['accuracy']:.4f} | "
                f"Balanced Accuracy = {metrics['balanced_accuracy']:.4f} | "
                f"Macro F1 = {metrics['macro_f1']:.4f} | "
                f"Coverage = {metrics['coverage']:.4f}"
            )
            print(
                f"  Conflict Case Rate = {result['conflict_case_rate']:.4f} | "
                f"Conflict Resolution Accuracy = {cra_text} | "
                f"Order Sensitivity = {result['order_sensitivity_rate']:.4f} "
                f"({result['orderings_checked']} client orders checked)"
            )
            print(
                f"  Order-averaged BA = {result['order_balanced_accuracy_mean']:.4f} "
                f"± {result['order_balanced_accuracy_std']:.4f} | "
                f"range=[{result['order_balanced_accuracy_min']:.4f}, "
                f"{result['order_balanced_accuracy_max']:.4f}]"
            )

    return result


# 【中文說明｜LEM2 Core】
# 這裡才是真正的 LEM2 演算法，而且它完全不知道 UCI、Federated、CV、Paper 是什麼。
#
# Step 1｜Decision Concept
#   對某一 decision class X，先建立目標集合。
#
# Step 2｜Lower Approximation
#   B = lower_C(X)
#   只保留能由 condition attributes「確定判斷」屬於 X 的 objects。
#
# Step 3｜Local Covering
#   G = B，代表目前尚未被規則 cover 的 target objects。
#
# Step 4｜選最佳 attribute-value pair t=(a,v)
#   優先最大化 |[t] ∩ G|：一次 cover 最多尚未處理的 target objects。
#   若平手，再最小化 |[t]|：偏好更 specific / discriminative 的條件。
#
# Step 5｜建立 complex T
#   不斷加入 pair，直到：
#       非空的 [T] ⊆ B
#   此時 T 已經能形成一條「確定」規則。
#
# Step 6｜Minimal Complex
#   逐一嘗試刪掉多餘條件；若刪掉後仍然 [T] ⊆ B，就把該條件移除。
#
# Step 7｜Local Covering
#   產生 rule 後，把它已 cover 的 objects 從 G 移除，再產生下一條 rule，直到 cover B。
#
# Step 8｜移除 redundant rules
#   若刪掉整條 rule，其他 rules 仍能 cover 同一個 lower approximation，該 rule 就是 redundant。
#
# LEM2 到這裡就結束。
# FIRST_MATCH / Voting / Federated / CV 都是在 Core 外面處理。
#
# =============================================================================
# 7. LEM2 CORE -- algorithm only; no UCI/federated/evaluation knowledge
# =============================================================================


@dataclass(frozen=True)
class Rule:
    conditions: Tuple[Tuple[str, Any], ...]
    decision: Any
    source: str = ""

    def __str__(self):
        lhs = " AND ".join(f"{a}={v}" for a, v in self.conditions)
        src = f" [source={self.source}]" if self.source else ""
        return f"IF {lhs} THEN decision={self.decision}{src}"

    @property
    def key(self):
        return (tuple(sorted(self.conditions)), self.decision)


def equivalence_classes(df: pd.DataFrame, condition_cols: Sequence[str]) -> List[Set[int]]:
    groups = df.groupby(list(condition_cols), sort=False, dropna=False).groups
    return [set(ids) for ids in groups.values()]


def lower_approximation(df, condition_cols, decision_col, decision_value) -> Set[int]:
    concept = set(df.index[df[decision_col] == decision_value])
    lower: Set[int] = set()

    for eq_class in equivalence_classes(df, condition_cols):
        if eq_class <= concept:
            lower |= eq_class

    return lower


def build_blocks(df, condition_cols):
    blocks = {}
    for attr in condition_cols:
        for value in pd.unique(df[attr]):
            blocks[(attr, value)] = set(df.index[df[attr] == value])
    return blocks


def complex_block(conditions, blocks, universe):
    if not conditions:
        return set(universe)

    result = set(universe)
    for pair in conditions:
        result &= blocks[pair]
    return result


def choose_best_pair(blocks, G, used_pairs):
    candidates = []

    for pair, block in blocks.items():
        if pair in used_pairs:
            continue

        overlap = len(block & G)
        if overlap:
            candidates.append((pair, overlap, len(block)))

    if not candidates:
        raise RuntimeError("No candidate pair can cover the remaining target objects.")

    # 1) maximize |[t] ∩ G|
    # 2) tie -> minimize |[t]|
    candidates.sort(key=lambda x: (-x[1], x[2], str(x[0])))
    return candidates[0][0]


def minimize_complex(conditions, B, blocks, universe):
    conditions = list(conditions)
    changed = True

    while changed and len(conditions) > 1:
        changed = False
        for condition in list(conditions):
            trial = [x for x in conditions if x != condition]
            trial_block = complex_block(trial, blocks, universe)
            if trial_block and trial_block <= B:
                conditions = trial
                changed = True
                break

    return conditions


def build_one_complex(B, uncovered, blocks, universe, verbose=False):
    G = set(uncovered)
    T = []
    step = 0

    while True:
        current = complex_block(T, blocks, universe)
        if T and current and current <= B:
            break

        best_pair = choose_best_pair(blocks, G, T)

        if verbose:
            print(
                f"    Step {step+1}: choose {best_pair}, "
                f"|[t]∩G|={len(blocks[best_pair] & G)}, |[t]|={len(blocks[best_pair])}"
            )

        T.append(best_pair)
        G &= blocks[best_pair]
        step += 1

    T = minimize_complex(T, B, blocks, universe)
    return tuple(T), complex_block(T, blocks, universe)


def remove_redundant_complexes(complexes, B):
    complexes = list(complexes)
    changed = True

    while changed and len(complexes) > 1:
        changed = False
        for i in range(len(complexes)):
            covered_by_others: Set[int] = set()
            for j, (_, block) in enumerate(complexes):
                if i != j:
                    covered_by_others |= (block & B)
            if covered_by_others >= B:
                complexes.pop(i)
                changed = True
                break

    return complexes


def induce_lem2(
    df: pd.DataFrame,
    condition_cols: Sequence[str],
    decision_col: str,
    source: str = "",
    verbose: bool = False,
) -> List[Rule]:
    """Classical certain-rule LEM2 local-covering implementation."""
    data = df.reset_index(drop=True).copy()
    universe = set(data.index)
    blocks = build_blocks(data, condition_cols)
    rules: List[Rule] = []

    for decision_value in pd.unique(data[decision_col]):
        B = lower_approximation(data, condition_cols, decision_col, decision_value)

        if verbose:
            print("\n" + "=" * 72)
            print(f"Decision concept: {decision_col}={decision_value}")
            print(f"Lower approximation B = {sorted(B)}")

        if not B:
            continue

        complexes = []
        covered: Set[int] = set()

        while covered != B:
            uncovered = B - covered
            T, T_block = build_one_complex(B, uncovered, blocks, universe, verbose=verbose)
            complexes.append((T, T_block))
            covered |= (T_block & B)

            if verbose:
                readable = " AND ".join(f"{a}={v}" for a, v in T)
                print(f"  Minimal complex = {readable}")
                print(f"  [T] = {sorted(T_block)}")

        complexes = remove_redundant_complexes(complexes, B)

        for T, _ in complexes:
            rules.append(Rule(conditions=T, decision=decision_value, source=source))

    return rules


# =============================================================================
# 8. SCRIPT ENTRY
# =============================================================================


if __name__ == "__main__":
    run_pipeline(USER_SETTINGS)
