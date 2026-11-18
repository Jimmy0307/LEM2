"""Post-hoc G4–G8 reanalysis of PUBLISHED Gate 5 CSVs, without OpenML cache.

Derives paired B2-vs-ALL policy suitability, source-level policy spread, and
the decomposed meaning of Coverage/Conflict. Never selects treatment using Test;
test-score range is reported explicitly as non-deployable oracle diagnostic.

Not a new confirmatory analysis. Writes only to a caller-specified scratch path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fedrs.experiment import DEFAULT_BASE
from fedrs.predict import POLICIES

ROOT = Path(__file__).resolve().parents[2]
IN = ROOT / "docs/research/redesign_20261116/data"
PREFIX = "REDESIGN_G5_CONFIRMATORY_"
IDENT = ["dataset", "seed", "regime", "discretizer", "rule_variant"]


def input_csv(name):
    path = IN / (PREFIX + name + ".csv")
    if not path.exists():
        raise FileNotFoundError(f"Published input missing: {path}")
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_unique(frame, cols, what):
    if frame.duplicated(cols).any():
        raise AssertionError(f"Duplicate keys in {what}: {cols}")


def analyze(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    raw = input_csv("POLICIES")
    structure = input_csv("STRUCTURE")
    config = input_csv("CONFIG")
    reg = pd.read_csv(IN / "CONFIRMATORY_SOURCE_REGISTRY.csv")
    selected = reg.loc[reg.status == "ELIGIBLE_PREPARED", "did"].astype(int)
    expected = {f"openml_{d}" for d in selected}
    assert len(expected) == 51, "Never silently downsample confirmatory source set"
    regimes = {"IID", "NONIID_05", "NONIID_01"}
    assert set(config.loc[config.discretizer == "EQUAL_WIDTH_3", "dataset"]) == expected
    assert set(config.regime) == regimes
    assert set(config.seed.astype(int)) == set(range(1001, 1011))
    assert_unique(config, ["dataset", "seed", "regime", "discretizer"], "CONFIG")
    assert_unique(raw, IDENT + ["method"], "POLICIES")
    assert_unique(structure, IDENT + ["split"], "STRUCTURE")
    # Compare ONE IDENTICAL rule set among policy options, only for EW3 and FED_MD.
    raw = raw.loc[raw.discretizer.isin(["EQUAL_WIDTH_3", "FED_MD_HIST"])]
    six = raw[raw.method.isin(POLICIES)].copy()
    n_six = six.groupby(IDENT).method.nunique()
    assert (n_six == 6).all(), "Not all six policies available per configuration"
    paired = six.pivot(index=IDENT, columns="method", values="test_ba")
    paired["test_oracle_spread"] = paired.max(axis=1) - paired.min(axis=1)
    # Validation-best is fit on validation scores; Test is ONLY the reported outcome.
    chosen = raw[raw.method == "VALIDATION_BEST"][IDENT + ["test_ba", "selected_policy"]]
    assert_unique(chosen, IDENT, "VALIDATION_BEST")
    tbl = paired.reset_index()[IDENT + ["test_oracle_spread"]].merge(
        chosen, on=IDENT, how="left", validate="one_to_one"
    )
    if tbl.test_ba.isna().any():
        raise AssertionError("Missing VALIDATION_BEST outcome")
    fixed = six.loc[six.apply(
        lambda r: r.method == DEFAULT_BASE[str(r.regime)], axis=1
    ), IDENT + ["test_ba"]].rename(columns={"test_ba": "fixed_test_ba"})
    assert_unique(fixed, IDENT, "FIXED")
    tbl = tbl.merge(fixed, on=IDENT, how="left", validate="one_to_one")
    if tbl.fixed_test_ba.isna().any():
        raise AssertionError("Missing pre-specified fixed comparator")
    tbl["val_selected_minus_fixed"] = tbl.test_ba - tbl.fixed_test_ba
    tbl["selection_changed"] = tbl.apply(
        lambda r: r.selected_policy != DEFAULT_BASE[str(r.regime)], axis=1
    )
    # Repeated seeds are not independent; group by dataset before mean across sources.
    dataset_summary = tbl.groupby(["dataset", "regime", "discretizer", "rule_variant"], as_index=False).agg(
        test_oracle_spread=("test_oracle_spread", "mean"),
        val_selected_minus_fixed=("val_selected_minus_fixed", "mean"),
        selection_changed=("selection_changed", "mean"),
        seed_count=("seed", "nunique"),
    )
    assert (dataset_summary.seed_count == 10).all(), "Incomplete paired seed blocks"
    summary = dataset_summary.groupby(["regime", "discretizer", "rule_variant"], as_index=False).agg(
        n_sources=("dataset", "nunique"),
        policy_spread_pp=("test_oracle_spread", lambda x: 100 * float(x.mean())),
        validation_selected_minus_fixed_pp=("val_selected_minus_fixed", lambda x: 100 * float(x.mean())),
        fraction_changed_from_fixed=("selection_changed", "mean"),
    )
    assert (summary.n_sources == 51).all()

    # Pair A vs B2 without refitting: same source, seed, regime and discretizer.
    b2 = dataset_summary.pivot(
        index=["dataset", "regime", "discretizer"], columns="rule_variant",
        values=["test_oracle_spread", "val_selected_minus_fixed"]
    )
    if not {("test_oracle_spread", "A_ALL_RULES"),
            ("test_oracle_spread", "B2_TRUE_AS_FALLBACK")}.issubset(b2.columns):
        raise AssertionError("B2/A paired arms missing")
    diff = (b2["test_oracle_spread"]["B2_TRUE_AS_FALLBACK"] -
            b2["test_oracle_spread"]["A_ALL_RULES"]).rename("B2_minus_A_spread")
    diff_source = diff.reset_index().groupby(["regime", "discretizer"]).agg(
        n_sources=("dataset", "nunique"),
        B2_minus_A_policy_spread_pp=("B2_minus_A_spread", lambda x: 100 * float(x.mean()))
    ).reset_index()

    # Structure: distinguish exact rule coverage from TRUE-only effective coverage.
    st = structure.loc[(structure.split == "test") &
                       structure.discretizer.isin(["EQUAL_WIDTH_3", "FED_MD_HIST"])]
    metrics = ["coverage", "conflict_rate", "truth_in_candidates_rate",
               "coverage_only_from_true_rules", "conflict_created_by_true"]
    st = st[IDENT + metrics].copy()
    st = st.merge(config[["dataset", "seed", "regime", "discretizer",
                           "single_class_clients", "true_rules"]],
                  on=["dataset", "seed", "regime", "discretizer"], validate="many_to_one")
    sds = st.groupby(["dataset", "regime", "discretizer", "rule_variant"], as_index=False)[
        metrics + ["single_class_clients", "true_rules"]].mean()
    stsum = sds.groupby(["regime", "discretizer", "rule_variant"], as_index=False)[
        metrics + ["single_class_clients", "true_rules"]].mean()
    audit = {
        "designation": "EXPLORATORY_POST_HOC_ONLY",
        "input_commit_policy": "frozen PR #6 data; source-level aggregation, no test-based method selection",
        "source_count": len(expected), "seeds": list(range(1001, 1011)),
        "regimes": sorted(regimes), "method_count": 6,
        "used_inputs_sha256": {n: sha256(IN / (PREFIX+n+".csv")) for n in
                               ("POLICIES", "STRUCTURE", "CONFIG")},
        "registry_sha256": sha256(IN / "CONFIRMATORY_SOURCE_REGISTRY.csv"),
    }
    summary.to_csv(out / "G4_POLICY_SUITABILITY_EXPLORATORY.csv", index=False)
    diff_source.to_csv(out / "G4_TRUE_EFFECT_PAIRED_EXPLORATORY.csv", index=False)
    stsum.to_csv(out / "G5_COVERAGE_STRUCTURE_EXPLORATORY.csv", index=False)
    (out / "AUDIT_MANIFEST.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    md = [
        "# G4-G8 歷史驗證資料重新解讀（探索性，非新的確認性實驗）",
        "",
        "以下皆由原 Gate5 已發布逐任務 CSV 計算，未更動預註冊、原始數據或重新訓練。",
        "只使用 51 來源×10 Seeds，對每一來源先跨 Seeds 平均，再對來源等權描述。",
        "**ValidationBest** 只用內層 Validation 選法；**test_oracle_spread** 使用 Test 找最大最小值，",
        "因此純屬事後診斷，不可用於正式可部署政策選擇。",
        "",
        "## G4：六策略在固定規則集合的表現",
        "",
        summary.round(5).to_markdown(index=False),
        "",
        "## G4：B2 相對 A 的六策略離散幅度（pp）",
        "",
        diff_source.round(5).to_markdown(index=False),
        "",
        "## G5／G6：Coverage、Candidate、Conflict 來源診斷",
        "",
        stsum.round(5).to_markdown(index=False),
        "",
        "注意：A_ALL_RULES的 Coverage 可能被TRUE規則充滿；B2 並非 Reject。",
        "沒有匹配規則時核心仍使用預設多數類別。該數字不能被稱為 Abstention Rate。",
        "",
        "## 推論限制",
        "1. 同一份 G5 資料曾參與模型設計與分析，這裡不是新預註冊確認。",
        "2. 這些數據可以定位錯誤機制，不能證明任何 Router 或補充規則的因果優勢。",
        "3. 同源資料（例如 ada/gina）仍有獨立性疑慮。",
        "4. 只有前6個特徵、3 Client、最多1800列；高維／多Client另需實驗。",
        "5. 若某種方法獲利0.1pp，不代表其在實務上具重要意義。",
    ]
    (out / "EXPLORATORY_REPORT.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    print("G4_G8_EXPLORATORY_REANALYSIS_PASS")
    print("SOURCES=51 SEEDS=10 METHODS=6 MODELS_PAIRED=A/B2")
    print("G4_POLICY_SUMMARY_BEGIN")
    print(summary.round(4).to_string(index=False))
    print("G4_POLICY_SUMMARY_END")
    print("G5_STRUCTURE_BEGIN")
    print(stsum.round(4).to_string(index=False))
    print("G5_STRUCTURE_END")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True, help="Scratch output directory, NEVER published data/")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(IN.resolve()):
        raise SystemExit("Refusing to write exploratory outputs to published Gate 5 evidence directory")
    analyze(args.output)


if __name__ == "__main__":
    main()
