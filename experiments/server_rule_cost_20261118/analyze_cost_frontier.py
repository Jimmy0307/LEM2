"""Cross-source *descriptive* cost frontier: reuse existing frozen evidence, no new model fit.

Never treat post-hoc TEST-based arm ranks as deployable policy choices. Costs
measure original binning / reduct / induction; Server integration cost is NOT measured.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
G5 = ROOT / "docs/research/redesign_20261116/data"
H = ROOT / "docs/research/teacher_dashboard/data"
OUT = ROOT / "docs/research/server_rule_cost_20261118"
ARMS = {"M1": "EQUAL_WIDTH_3", "R3": "EQUAL_WIDTH_5",
        "R2": "MDLP_HIST", "M2": "FED_MD_HIST", "M3": "FED_MD_XC"}
REGIMES = ("IID", "NONIID_05", "NONIID_01")
BUDGETS = (("L0_16", 16), ("L1_512", 512), ("L2_2048", 2048),
           ("L3_10000000", 10000000), ("L4_40000000", 40000000))
KEYS = ["dataset", "seed", "regime", "discretizer"]

def read(name, root=G5):
    return pd.read_csv(root / name, low_memory=False)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((G5 / "REDESIGN_G5_CONFIRMATORY_MANIFEST.json").read_text())
    assert manifest["tasks"] == 10710 and manifest["failed"] == 0
    reg = read("CONFIRMATORY_SOURCE_REGISTRY.csv")
    eligible = reg[reg.status == "ELIGIBLE_PREPARED"]
    assert eligible.did.nunique() == 51
    families = {"openml_" + str(int(r.did)): r.family for r in eligible.itertuples()}
    names = {"openml_" + str(int(r.did)): r.name for r in eligible.itertuples()}
    cfg = read("REDESIGN_G5_CONFIRMATORY_CONFIG.csv")
    pol = read("REDESIGN_G5_CONFIRMATORY_POLICIES.csv")
    st = read("REDESIGN_G5_CONFIRMATORY_STRUCTURE.csv")
    assert len(cfg) == 10710
    c = cfg[cfg.discretizer.isin(ARMS.values())].copy()
    assert len(c) == 7650 and not c.duplicated(KEYS).any()
    c["fit_time_proxy_sec"] = c.binning_fit_seconds + c.reduct_seconds + c.lem2_seconds
    c["comm_numbers"] = c.binning_communication_numbers_per_client
    p = pol[(pol.discretizer.isin(ARMS.values())) &
            (pol.rule_variant == "B2_TRUE_AS_FALLBACK") &
            (pol.method == "VALIDATION_BEST")][KEYS + ["test_ba"]]
    b2 = st[(st.discretizer.isin(ARMS.values())) &
            (st.rule_variant == "B2_TRUE_AS_FALLBACK") &
            (st.split == "test")][KEYS +
                ["coverage", "conflict_rate", "single_precision"]]
    full = st[(st.discretizer.isin(ARMS.values())) &
              (st.rule_variant == "A_ALL_RULES") &
              (st.split == "test")][KEYS + ["coverage_only_from_true_rules"]]
    for key, frame in [("policy", p), ("B2", b2), ("A", full)]:
        assert len(frame) == len(c) and not frame.duplicated(KEYS).any(), key
    m = (c.merge(p, on=KEYS, validate="one_to_one")
           .merge(b2, on=KEYS, validate="one_to_one")
           .merge(full, on=KEYS, validate="one_to_one"))
    assert len(m) == 7650
    for key in ["test_ba", "coverage", "conflict_rate", "global_rules", "comm_numbers"]:
        assert m[key].notna().all(), key
    m["nontrue_coverage_proxy"] = (
        m.coverage - m.coverage_only_from_true_rules.fillna(0)).clip(lower=0)
    m["arm"] = m.discretizer.map({v: k for k, v in ARMS.items()})
    by = m.groupby(["dataset", "regime", "discretizer", "arm"], as_index=False).agg(
        ba=("test_ba", "mean"), coverage=("coverage", "mean"),
        effective_coverage=("nontrue_coverage_proxy", "mean"),
        conflict=("conflict_rate", "mean"), rules=("global_rules", "mean"),
        fit_time_proxy_sec=("fit_time_proxy_sec", "mean"),
        comm_numbers=("comm_numbers", "mean"), seeds=("seed", "nunique"))
    assert len(by) == 765 and by.seeds.eq(10).all()
    by["source_name"] = by.dataset.map(names)
    by["family"] = by.dataset.map(families)
    assert by.family.notna().all() and by.source_name.notna().all()
    by["comm_bytes_float64_proxy"] = by.comm_numbers * 8
    by.to_csv(OUT / "G5_51_SOURCES_PER_DATASET_COST.csv", index=False)

    summary = by.groupby(["regime", "arm", "discretizer"], as_index=False).agg(
        ba=("ba", "mean"), coverage=("coverage", "mean"),
        effective_coverage=("effective_coverage", "mean"),
        conflict=("conflict", "mean"), rules=("rules", "mean"),
        fit_time_proxy_sec=("fit_time_proxy_sec", "mean"),
        comm_numbers=("comm_numbers", "mean"),
        sources=("dataset", "nunique"), families=("family", "nunique"))
    assert summary.sources.eq(51).all()
    # A cap is not hard unless it bounds EVERY observed source and seed task.
    extremes = m.groupby(["regime", "discretizer"], as_index=False).agg(
        max_comm_per_task=("comm_numbers", "max"),
        p90_comm_per_task=("comm_numbers", lambda x: x.quantile(0.90)))
    summary = summary.merge(extremes, on=["regime", "discretizer"],
                            validate="one_to_one")
    summary.to_csv(OUT / "G5_ALL_ARMS_AGGREGATED.csv", index=False)

    frontier = []
    for regime in REGIMES:
        x = summary[summary.regime == regime]
        for label, cap in BUDGETS:
            available = x[x.max_comm_per_task <= cap]
            if len(available) == 0:
                frontier.append(dict(regime=regime, budget=label, cap=cap, arm="NONE"))
                continue
            winner = available.sort_values(
                ["ba", "comm_numbers", "rules"],
                ascending=[False, True, True]).iloc[0].to_dict()
            frontier.append({**winner, "budget": label, "cap": cap})
    result = pd.DataFrame(frontier)
    result.to_csv(OUT / "G5_BUDGET_FRONTIER_POSTHOC.csv", index=False)

    # Dataset-level Pareto: a retrospective diagnostic, NEVER test-set policy selection.
    pareto = []
    for (dataset, regime), g in by.groupby(["dataset", "regime"]):
        options = g.to_dict("records")
        for a in options:
            dominators = []
            for b in options:
                if a["arm"] == b["arm"]:
                    continue
                no_worse = (b["ba"] >= a["ba"] and
                            b["effective_coverage"] >= a["effective_coverage"] and
                            b["conflict"] <= a["conflict"] and
                            b["comm_numbers"] <= a["comm_numbers"] and
                            b["rules"] <= a["rules"])
                better = (b["ba"] > a["ba"] or
                          b["effective_coverage"] > a["effective_coverage"] or
                          b["conflict"] < a["conflict"] or
                          b["comm_numbers"] < a["comm_numbers"] or
                          b["rules"] < a["rules"])
                if no_worse and better:
                    dominators.append(b["arm"])
            pareto.append(dict(dataset=dataset, regime=regime, arm=a["arm"],
                               source_name=a["source_name"], family=a["family"],
                               nondominated_diagnostic=not dominators,
                               dominated_by=";".join(dominators),
                               selection_leakage_warning="TEST_POSTHOC_NOT_DEPLOYABLE"))
    pd.DataFrame(pareto).to_csv(OUT / "G5_SOURCE_PARETO_DIAGNOSTIC.csv", index=False)

    master = read("TEACHER_DATASET_MASTER_20261114.csv", H)
    audit = read("PMLB_117_3SEED_SOURCE_AUDIT.csv", H)
    assert len(master) == 161 and len(audit) == 117
    assert (audit.status == "PASS").sum() == 109
    a = audit[["dataset", "configs_passed", "wall_seconds",
               "actual_sample_rows", "status"]].rename(columns={
                   "dataset": "id", "wall_seconds": "pmlb_9config_wall_seconds",
                   "status": "pmlb_status"})
    historical = master.merge(a, on="id", how="left", validate="many_to_one")
    historical["cpu_scope"] = "9_CONFIG_TOTAL_NOT_SERVER_COST"
    historical.to_csv(OUT / "HISTORICAL_161_SOURCE_INVENTORY.csv", index=False)
    historical["pmlb_passed_with_cpu"] = (
        historical.pmlb_status.eq("PASS") &
        historical.pmlb_9config_wall_seconds.notna())
    hsummary = historical.groupby("cohort", dropna=False).agg(
        sources=("id", "size"),
        pmlb_cpu_recorded=("pmlb_9config_wall_seconds", "count"),
        pmlb_passed_with_cpu=("pmlb_passed_with_cpu", "sum"),
        median_used_rows=("used_rows", "median"),
        median_used_features=("used_features", "median")).reset_index()
    hsummary.to_csv(OUT / "HISTORICAL_COHORT_SUMMARY.csv", index=False)

    staircase = read("PMLB_G8_REAL_CPU_STAIRCASE_36.csv", H)
    assert len(staircase) == 36 and staircase.dataset.nunique() == 4
    scale = staircase.groupby(["rows", "features"], as_index=False).agg(
        n_sources=("dataset", "nunique"),
        median_fit_seconds=("fit_seconds", "median"),
        median_policy_test_seconds=("six_policy_test_seconds", "median"),
        median_rules=("rules", "median"))
    scale.to_csv(OUT / "G8_MEASURED_CPU_STAIRCASE.csv", index=False)

    def f(x):
        return f"{x:.2f}"
    report = [
        "# Federated LEM2: cross-source empirical cost tiers (2026-11-18)", "",
        "**EXPLORATORY DESCRIPTIVE REVIEW, NOT A NEW SERVER RULE ALGORITHM.**",
        "Frozen G5 CSVs are unchanged. Only published aggregates and metadata are read.", "",
        "## Evidence coverage",
        "- Confirmatory cohort: 51 OpenML sources, 37 manually identified families, 10 seeds,",
        "  3 regimes, 5 non-CART arms; 765 source-regime-arm records, 7,650 model tasks.",
        "- All 161 historical source-catalogue rows are included in the inventory.",
        "- All 117 historical PMLB audit candidates, of which 109 passed; CPU records joined.",
        "- Actual CPU staircase: 36 trials from 4 distinct sources.", "",
        "These groups are NOT 51+161 independent datasets; related source families overlap.",
        "Historical PMLB experiments use at most 900 rows and the first 6 features.",
        "G5 uses first 6 features, at most 1,800 rows, and 3 Clients.", "",
        "## Budget frontier (one FIXED arm selected by retrospective aggregate TEST BA)",
        "Caps are HARD per-task maximum numbers per Client across all 51 sources",
        "and 10 seeds in the given regime, not averages. Displayed numbers are means.",
        "The selected fixed arm is a retrospective TEST-based ranking and is",
        "NOT a deployable selection policy. The 512 tier does NOT permit MDLP",
        "on every source; the 10M tier does NOT permit FED_MD on every source.",
        "Intermediate accuracy and communication between roughly 413 and",
        "7.7M mean numbers per Client remain unobserved.", "",
        "| Regime | Hard tier | Arm | Test BA | Non-TRUE coverage | Conflict | Rules | Mean numbers/Client | Max numbers/Client |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in frontier:
        if r["arm"] == "NONE":
            continue
        report.append(f"| {r['regime']} | {r['budget']} | {r['arm']} | "
                      f"{100*r['ba']:.2f}% | {100*r['effective_coverage']:.2f}% | "
                      f"{100*r['conflict']:.2f}% | {r['rules']:.1f} | "
                      f"{r['comm_numbers']:,.1f} | "
                      f"{r['max_comm_per_task']:,.1f} |")
    report += ["", "## Actual CPU time (whole Classical LEM2 fit; NOT Server rule integration)",
               "| Rows | Features | Sources | Median fit seconds | Median 6-policy test seconds | Median rules |",
               "|---:|---:|---:|---:|---:|---:|"]
    for r in scale.to_dict("records"):
        report.append(f"| {int(r['rows'])} | {int(r['features'])} | "
                      f"{int(r['n_sources'])} | {r['median_fit_seconds']:.3f} | "
                      f"{r['median_policy_test_seconds']:.3f} | {r['median_rules']:.1f} |")
    report += ["", "## Interpretation / guardrails",
               "1. Hard budget levels constrain the maximum recorded per-task communication",
               "   over all 51 sources and 10 seeds; observed maxima are not population bounds.",
               "2. Communication numbers are simulated accounting, not network latency",
               "   or actual secure-protocol byte payload. Multiplying by 8 only models float64.",
               "3. Fit time is preprocessing + reduct + induction, NOT Server merge CPU.",
               "4. Non-TRUE coverage subtracts A-only TRUE matches from B2 coverage;",
               "   it is not predictive precision nor a global rule certificate.",
               "5. Per-dataset Pareto uses TEST outcomes: diagnostic only; choosing by it",
               "   for a deployed selector would leak Test labels.",
               "6. Ada/Gina potentially overlap historical upstream sources; 51 and 161",
               "   must never be added into an independence claim.",
               "7. No result here identifies the optimal budget for a new server-side",
               "   coverage/conflict rule subset optimizer: rule antecedents and",
               "   independent validation evidence are absent from stored G5 CSVs.", "",
               "## Next gate: Server-only cost-knee experiment",
               "Freeze each Client rule set once, without any further Client calls.",
               "On identical frozen rules compare UNION, TRUE fallback, exact logical",
               "deduplication, safe subsumption pruning and budgeted rule subsets.",
               "Sweep 25/50/75/100 percent non-TRUE rules and measure server CPU,",
               "peak RAM, serialized rule bytes, validation coverage/conflict/BA,",
               "and held-out Test BA with source-level paired statistics.",
               "Without authorized Server-side validation, restrict objectives to",
               "syntactic rule overlap and potential logical conflict, not observed",
               "global empirical Coverage. Require new preregistration for confirmation.", "",
               "Reproduce: python -m experiments.server_rule_cost_20261118.analyze_cost_frontier",
               ""]
    (OUT / "COST_FRONTIER_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    audit_summary = dict(g5_sources=51, g5_source_regime_arm_records=765,
                         g5_models_analyzed=7650, historical_inventory=161,
                         pmlb_candidates=117, pmlb_successful=109,
                         measured_cpu_trials=36, measured_cpu_sources=4)
    (OUT / "AUDIT_SUMMARY.json").write_text(
        json.dumps(audit_summary, ensure_ascii=False, indent=2) + "\n")
    print("AUDIT", json.dumps(audit_summary))
    print("FRONTIER")
    print(result[["regime", "budget", "arm", "ba", "comm_numbers"]].to_string(index=False))


if __name__ == "__main__":
    main()
