from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

POLICIES = [
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
    "POPULATION_STANDARD",
    "POPULATION_GLOBAL",
]
SHORT = {
    "FIRST_MATCH": "FIRST",
    "SIMPLE_VOTING": "SIMPLE",
    "STANDARD_VOTING": "STD",
    "GLOBAL_STRENGTH": "GS",
    "POPULATION_STANDARD": "PS",
    "POPULATION_GLOBAL": "PG",
}
REGIMES = [
    ("CENTRALIZED", "FULL_DATA", "Centralized\nFull"),
    ("CENTRALIZED", "HOLDOUT_80_20", "Centralized\n80/20"),
    ("FEDERATED", "FULL_DATA", "Federated\nFull"),
    ("FEDERATED", "HOLDOUT_80_20", "Federated\n80/20"),
]


def _savefig(figures: Path, name: str) -> None:
    plt.tight_layout()
    plt.savefig(figures / name, dpi=300, bbox_inches="tight")
    plt.savefig(figures / name.replace(".png", ".svg"), bbox_inches="tight")
    plt.close()


def _regime_series(base: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows: list[tuple[str, int, float]] = []
    for split in ["FULL_DATA", "HOLDOUT_80_20"]:
        c = base[(base.system == "CENTRALIZED") & (base.split_mode == split)][metric].mean()
        rows.append((split, 0, float(c)))
        f = (
            base[(base.system == "FEDERATED") & (base.split_mode == split)]
            .groupby("client_count")[metric]
            .mean()
        )
        rows.extend((split, int(client_count), float(value)) for client_count, value in f.items())
    return pd.DataFrame(rows, columns=["split_mode", "client_count", metric])


def _heatmap(means: pd.DataFrame, metric: str, title: str, filename: str, figures: Path) -> None:
    matrix = np.zeros((len(POLICIES), len(REGIMES)))
    for i, policy in enumerate(POLICIES):
        for j, (system, split, _) in enumerate(REGIMES):
            matrix[i, j] = means[
                (means.system == system)
                & (means.split_mode == split)
                & (means.selection_policy == policy)
            ][metric].iloc[0]

    plt.figure(figsize=(8.6, 5.8))
    image = plt.imshow(
        matrix,
        aspect="auto",
        vmin=max(0, float(matrix.min()) - 0.03),
        vmax=min(1, float(matrix.max()) + 0.03),
    )
    plt.colorbar(image, format=PercentFormatter(1.0))
    plt.xticks(np.arange(len(REGIMES)), [regime[2] for regime in REGIMES])
    plt.yticks(np.arange(len(POLICIES)), [SHORT[policy] for policy in POLICIES])
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            plt.text(j, i, f"{matrix[i, j] * 100:.1f}%", ha="center", va="center")
    plt.xlabel("Experimental regime")
    plt.ylabel("Selection policy")
    plt.title(title)
    _savefig(figures, filename)


def build_figures(base: pd.DataFrame, policy: pd.DataFrame, figures: Path) -> None:
    figures.mkdir(parents=True, exist_ok=True)

    conflict = _regime_series(base, "conflict_case_rate")
    plt.figure(figsize=(8.4, 5.2))
    for split, label in [("FULL_DATA", "Full data"), ("HOLDOUT_80_20", "80/20 holdout")]:
        group = conflict[conflict.split_mode == split].sort_values("client_count")
        plt.plot(group.client_count, group.conflict_case_rate, marker="o", label=label)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.xticks([0, 2, 3, 4, 5], ["Centralized", "C=2", "C=3", "C=4", "C=5"])
    plt.xlabel("System / client count")
    plt.ylabel("Conflict rate")
    plt.title("Conflict Emerges After Holdout Splitting or Federated Rule Union")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    _savefig(figures, "fig01_conflict_rate_by_regime.png")

    centralized = base[base.system == "CENTRALIZED"].pivot(
        index="dataset", columns="split_mode", values="conflict_case_rate"
    )
    centralized = centralized.reindex(["Balance Scale", "Car Evaluation", "Hayes-Roth"])
    x = np.arange(len(centralized.index))
    width = 0.36
    plt.figure(figsize=(8.4, 5.2))
    plt.bar(x - width / 2, centralized["FULL_DATA"], width=width, label="Full data")
    plt.bar(x + width / 2, centralized["HOLDOUT_80_20"], width=width, label="80/20 holdout")
    plt.xticks(x, centralized.index)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.ylabel("Conflict rate")
    plt.title("Centralized LEM2: Full-Data Run vs 80/20 Holdout")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    _savefig(figures, "fig02_centralized_conflict_by_dataset.png")

    fed_holdout = base[(base.system == "FEDERATED") & (base.split_mode == "HOLDOUT_80_20")]
    plt.figure(figsize=(8.4, 5.2))
    for dataset in ["Balance Scale", "Car Evaluation", "Hayes-Roth"]:
        group = fed_holdout[fed_holdout.dataset == dataset].sort_values("client_count")
        plt.plot(group.client_count, group.conflict_case_rate, marker="o", label=dataset)
    plt.xticks([2, 3, 4, 5])
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.xlabel("Federated client count")
    plt.ylabel("Conflict rate")
    plt.title("Federated 80/20: Conflict Rate by Dataset and Client Count")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    _savefig(figures, "fig03_federated_holdout_conflict_by_dataset.png")

    coverage = _regime_series(base, "coverage")
    plt.figure(figsize=(8.4, 5.2))
    for split, label in [("FULL_DATA", "Full data"), ("HOLDOUT_80_20", "80/20 holdout")]:
        group = coverage[coverage.split_mode == split].sort_values("client_count")
        plt.plot(group.client_count, group.coverage, marker="o", label=label)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.xticks([0, 2, 3, 4, 5], ["Centralized", "C=2", "C=3", "C=4", "C=5"])
    plt.ylim(0.65, 1.03)
    plt.xlabel("System / client count")
    plt.ylabel("Rule coverage")
    plt.title("Rule Coverage Across Centralized and Federated Regimes")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    _savefig(figures, "fig04_rule_coverage_by_regime.png")

    means = (
        policy.groupby(["system", "split_mode", "selection_policy"])[
            ["accuracy", "balanced_accuracy", "macro_f1"]
        ]
        .mean()
        .reset_index()
    )
    _heatmap(means, "accuracy", "Mean Accuracy Across Three Datasets", "fig05_policy_accuracy_heatmap.png", figures)
    _heatmap(
        means,
        "balanced_accuracy",
        "Mean Balanced Accuracy Across Three Datasets",
        "fig06_policy_balanced_accuracy_heatmap.png",
        figures,
    )
    _heatmap(means, "macro_f1", "Mean Macro-F1 Across Three Datasets", "fig07_policy_macro_f1_heatmap.png", figures)

    fed_policy = policy[(policy.system == "FEDERATED") & (policy.split_mode == "HOLDOUT_80_20")]
    accuracy = fed_policy.groupby(["client_count", "selection_policy"])["accuracy"].mean().reset_index()
    plt.figure(figsize=(9.2, 5.6))
    for selection_policy in POLICIES:
        group = accuracy[accuracy.selection_policy == selection_policy].sort_values("client_count")
        plt.plot(group.client_count, group.accuracy, marker="o", label=SHORT[selection_policy])
    plt.xticks([2, 3, 4, 5])
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.xlabel("Federated client count")
    plt.ylabel("Mean accuracy")
    plt.title("Federated 80/20 Accuracy: Sensitivity to Client Count")
    plt.legend(ncol=3)
    plt.grid(axis="y", alpha=0.25)
    _savefig(figures, "fig08_federated_holdout_accuracy_by_client_count.png")

    candidate = _regime_series(base, "true_in_candidate_rate")
    plt.figure(figsize=(8.4, 5.2))
    for split, label in [("FULL_DATA", "Full data"), ("HOLDOUT_80_20", "80/20 holdout")]:
        group = candidate[candidate.split_mode == split].sort_values("client_count")
        plt.plot(group.client_count, group.true_in_candidate_rate, marker="o", label=label)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1.0))
    plt.xticks([0, 2, 3, 4, 5], ["Centralized", "C=2", "C=3", "C=4", "C=5"])
    plt.ylim(0.55, 1.03)
    plt.xlabel("System / client count")
    plt.ylabel("True class present in candidate set")
    plt.title("Candidate Recall Before Selection Policy")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    _savefig(figures, "fig09_true_in_candidate_by_regime.png")


def write_core_summary(base: pd.DataFrame, path: Path) -> None:
    rows: list[dict[str, object]] = []
    for system, split, label in [
        ("CENTRALIZED", "FULL_DATA", "Centralized + Full"),
        ("CENTRALIZED", "HOLDOUT_80_20", "Centralized + 80/20"),
    ]:
        group = base[(base.system == system) & (base.split_mode == split)]
        rows.append(
            {
                "regime": label,
                "client_count": 0,
                "mean_conflict_rate": group.conflict_case_rate.mean(),
                "mean_coverage": group.coverage.mean(),
                "mean_true_in_candidate_rate": group.true_in_candidate_rate.mean(),
            }
        )
    for split, label in [("FULL_DATA", "Federated + Full"), ("HOLDOUT_80_20", "Federated + 80/20")]:
        for client_count, group in base[(base.system == "FEDERATED") & (base.split_mode == split)].groupby("client_count"):
            rows.append(
                {
                    "regime": label,
                    "client_count": int(client_count),
                    "mean_conflict_rate": group.conflict_case_rate.mean(),
                    "mean_coverage": group.coverage.mean(),
                    "mean_true_in_candidate_rate": group.true_in_candidate_rate.mean(),
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


def write_docs(root: Path) -> None:
    readme = """# LEM2 Full Factorial Experiment — Canonical Package (2026-10-29)

這個資料夾是本次老師討論用的 **唯一正式結果入口**。

## 實驗矩陣

- Datasets: Balance Scale / Car Evaluation / Hayes-Roth
- Split modes:
  - `FULL_DATA`: 同一份完整資料建規則並做 resubstitution 檢查
  - `HOLDOUT_80_20`: 80% 建規則、20% unseen holdout 評估
- Systems:
  - `CENTRALIZED`
  - `FEDERATED`, client count C = 2, 3, 4, 5
- Selection layer:
  - `NONE`: 不選 winner，只看 rules / coverage / candidates / conflict
  - `FIRST_MATCH`
  - `SIMPLE_VOTING`
  - `STANDARD_VOTING`
  - `GLOBAL_STRENGTH`
  - `POPULATION_STANDARD`
  - `POPULATION_GLOBAL`

總共 **210 rows = 30 baseline rows + 180 policy rows**。

## 最重要的概念

`conflict_case_rate` 是在六種 selection policy **之前**計算。

因此：**六種方法不是 conflict 的來源。**

它們只是在同一筆 object 已經 match 到多個不同 decision candidates 之後，決定最後 winner。

本實驗最乾淨的結果是：

- Centralized + FULL_DATA：三資料集 conflict = 0%
- Centralized + 80/20：平均 conflict = 11.77%
- Federated + FULL_DATA：C=2 → C=5 平均 conflict 由 17.93% 上升到 59.99%
- Federated + 80/20：C=2 → C=5 平均 conflict 由 24.47% 上升到 63.98%

## Directory

- `tables/`：正式 CSV，`FULL_FACTORIAL_RESULTS.csv` 為 canonical master table
- `figures/`：SVG + 300 dpi PNG，由同一支 script 產生
- `FINDINGS.md`：研究結果與解釋邊界
- `MANIFEST_SHA256.txt`：檔案完整性

## Figure index

1. `fig01_conflict_rate_by_regime` — FULL_DATA / 80-20 與 client count 對 conflict 的影響
2. `fig02_centralized_conflict_by_dataset` — centralized full-data 0 conflict，但 80/20 暴露 conflict
3. `fig03_federated_holdout_conflict_by_dataset` — 三資料集 client-count sensitivity
4. `fig04_rule_coverage_by_regime` — coverage 與 conflict 不是同一件事
5. `fig05_policy_accuracy_heatmap` — 六方法 Accuracy
6. `fig06_policy_balanced_accuracy_heatmap` — 六方法 Balanced Accuracy
7. `fig07_policy_macro_f1_heatmap` — 六方法 Macro-F1
8. `fig08_federated_holdout_accuracy_by_client_count` — federated 80/20 下 policy 對 C 的敏感度
9. `fig09_true_in_candidate_by_regime` — selection 前正確類別是否存在 candidate set

所有圖都從 canonical CSV 自動重建，不使用 PPT 手抄數字。
"""
    (root / "README.md").write_text(readme, encoding="utf-8")

    findings = """# LEM2 Full Factorial — Key Findings

## Scope

Canonical matrix: 3 datasets × 2 split modes × (centralized + federated C=2/3/4/5) × (NONE + 6 selection policies) = **210 rows**.

`NONE` is the pure rule-set / candidate baseline. It deliberately has no Accuracy / Balanced Accuracy / Macro-F1 because no unique winner is selected.

## Main empirical findings

1. **Centralized + FULL_DATA has zero conflict on all three datasets.**
   - Balance Scale: 0%
   - Car Evaluation: 0%
   - Hayes-Roth: 0%

2. **Centralized + 80/20 exposes conflict even without federation.**
   - Balance Scale: 8.73%
   - Car Evaluation: 15.03%
   - Hayes-Roth: 11.54%
   - Three-dataset mean: 11.77%

3. **Federated partition + rule UNION creates conflict even under FULL_DATA resubstitution.**
   - Mean conflict rate: C=2 17.93% → C=3 36.28% → C=4 51.56% → C=5 59.99%.

4. **Federated + 80/20 is the strongest conflict setting.**
   - Mean conflict rate: C=2 24.47% → C=3 47.26% → C=4 48.68% → C=5 63.98%.

5. **The six policies do not create conflict.**
   Conflict is measured before policy selection. The policies only choose a winner after multiple candidate decisions exist.

6. **Policy ranking depends on metric and regime.**
   - Centralized 80/20: highest mean Accuracy / Macro-F1 = STANDARD_VOTING and POPULATION_STANDARD (80.93% / 67.13%); highest BA = GLOBAL_STRENGTH and POPULATION_GLOBAL (66.75%).
   - Federated FULL_DATA: highest Accuracy = STANDARD_VOTING (90.53%); highest BA / Macro-F1 = GLOBAL_STRENGTH (83.08% / 81.02%).
   - Federated 80/20: highest Accuracy = STANDARD_VOTING (78.53%); highest BA / Macro-F1 = GLOBAL_STRENGTH (67.25% / 65.23%).

## Interpretation boundary

The experiment supports the statement that **holding out unseen objects and federated local-rule union both change the rule-matching candidate structure**. It does not, by itself, establish a universal causal law for every Rough Set / LEM2 implementation or dataset.
"""
    (root / "FINDINGS.md").write_text(findings, encoding="utf-8")


def write_manifest(root: Path) -> None:
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish(source: Path, destination: Path) -> None:
    tables = destination / "tables"
    figures = destination / "figures"
    if destination.exists():
        shutil.rmtree(destination)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    canonical_files = [
        "FULL_FACTORIAL_RESULTS.csv",
        "FULL_FACTORIAL_BASELINES.csv",
        "FULL_FACTORIAL_POLICY_RESULTS.csv",
        "FULL_FACTORIAL_POLICY_MEANS.csv",
        "FULL_FACTORIAL_POLICY_MEANS_BY_CLIENT_COUNT.csv",
        "FULL_FACTORIAL_BASELINE_MEANS.csv",
    ]
    for name in canonical_files:
        shutil.copy2(source / name, tables / name)

    base = pd.read_csv(tables / "FULL_FACTORIAL_BASELINES.csv")
    policy = pd.read_csv(tables / "FULL_FACTORIAL_POLICY_RESULTS.csv")
    assert len(pd.read_csv(tables / "FULL_FACTORIAL_RESULTS.csv")) == 210
    assert len(base) == 30
    assert len(policy) == 180

    write_core_summary(base, tables / "CORE_REGIME_SUMMARY.csv")
    build_figures(base, policy, figures)
    write_docs(destination)
    write_manifest(destination)

    legacy_note = """# Teacher demo / runner code

這個資料夾只保留可重跑的 demo、full-factorial runner 與 tests。

正式結果、圖、結論與 canonical CSV 已統一移到：

`docs/research/full_factorial_20261029/`

請不要再使用舊的 `CENTRALIZED_VS_FEDERATED.csv`、`CENTRALIZED_CONFLICT_STRUCTURE.csv`、`THREE_DATASET_METRIC_MEANS.csv` 當正式結果來源。
"""
    Path("teacher_demo/README_TEACHER_DEMO.md").write_text(legacy_note, encoding="utf-8")

    print("PUBLISH_VERDICT=PASS")
    print("DESTINATION=", destination)
    print("FIGURES_PNG=", len(list(figures.glob("*.png"))))
    print("FIGURES_SVG=", len(list(figures.glob("*.svg"))))
    print("TABLES=", len(list(tables.glob("*.csv"))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="outputs/teacher_full_factorial_20261029")
    parser.add_argument("--destination", default="docs/research/full_factorial_20261029")
    args = parser.parse_args()
    publish(Path(args.source), Path(args.destination))


if __name__ == "__main__":
    main()
