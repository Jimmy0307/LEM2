"""Gate 5 analysis exactly as preregistered (PREREGISTRATION_CONFIRMATORY_20261116.md)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .common import OUT, bootstrap_path

bootstrap_path()
from fedrs.provenance import write_manifest  # noqa: E402
from fedrs.stats import friedman, holm, paired_compare  # noqa: E402

P = "REDESIGN_G5_CONFIRMATORY_"
ARMS = {  # code -> (discretizer, rule_variant, method)
    "M0": ("EQUAL_WIDTH_3", "A_ALL_RULES"), "M1": ("EQUAL_WIDTH_3", "B2_TRUE_AS_FALLBACK"),
    "M2": ("FED_MD_HIST", "B2_TRUE_AS_FALLBACK"), "M3": ("FED_MD_XC", "B2_TRUE_AS_FALLBACK"),
    "R1": ("RS_DISCERNIBILITY_CENTRAL", "B2_TRUE_AS_FALLBACK"), "R2": ("MDLP_HIST", "B2_TRUE_AS_FALLBACK"),
    "R3": ("EQUAL_WIDTH_5", "B2_TRUE_AS_FALLBACK"),
}
SIX = ("FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL")


def arms(p: pd.DataFrame, method: str) -> pd.DataFrame:
    parts = []
    for code, (disc, var) in ARMS.items():
        g = p[(p.discretizer == disc) & (p.rule_variant == var) & (p.method == method)]
        parts.append(g.assign(arm=code))
    for cart in ("CART_CENTRAL", "CART_FED_VOTE"):
        parts.append(p[(p.discretizer == "CART") & (p.method == cart)].assign(arm={"CART_CENTRAL": "C1", "CART_FED_VOTE": "C2"}[cart]))
    return pd.concat(parts, ignore_index=True)


def passed(row) -> bool:
    return bool(row.holm_p < 0.05 and row.mean_diff > 0 and row.ci95_low > 0)


def main():
    p = pd.read_csv(OUT / f"{P}POLICIES.csv", keep_default_na=False, na_values=[""])
    c = pd.read_csv(OUT / f"{P}CONFIG.csv")
    s = pd.read_csv(OUT / f"{P}STRUCTURE.csv")
    f = pd.read_csv(OUT / f"{P}FAILURES.csv") if (OUT / f"{P}FAILURES.csv").stat().st_size > 5 else pd.DataFrame()
    reg = pd.read_csv(OUT / "CONFIRMATORY_SOURCE_REGISTRY.csv")
    fam = {f"openml_{int(r.did)}": r.family for r in reg.itertuples()}

    vb = arms(p, "VALIDATION_BEST")
    # H1
    h1 = paired_compare(vb, "dataset", "arm", "M0", "M2", "test_ba", strata=("regime",))
    h1["holm_p"] = holm(h1.wilcoxon_p.tolist())
    h1["hypothesis"] = "H1"
    # H2
    h2 = paired_compare(vb[vb.regime == "NONIID_01"], "dataset", "arm", "M0", "M1", "test_ba", strata=("regime",))
    h2["holm_p"] = h2.wilcoxon_p
    h2["hypothesis"] = "H2"
    primary = pd.concat([h1, h2], ignore_index=True)
    primary["passed"] = [passed(r) for r in primary.itertuples()]
    primary.to_csv(OUT / "G5_PRIMARY_HYPOTHESES.csv", index=False)

    # family-level sensitivity for H1
    vbf = vb.assign(family=vb.dataset.map(fam))
    fam_h1 = paired_compare(vbf, "family", "arm", "M0", "M2", "test_ba", strata=("regime",))
    fam_h1["holm_p"] = holm(fam_h1.wilcoxon_p.tolist())
    fam_h1.to_csv(OUT / "G5_H1_FAMILY_SENSITIVITY.csv", index=False)

    # secondary (descriptive)
    sec = []
    for method in ("VALIDATION_BEST", "SIMPLE_VOTING", "CONFLICT_BUCKET_ROUTER_V1"):
        a = arms(p, method) if method == "VALIDATION_BEST" else arms(p, method)[lambda d: ~d.arm.isin(["C1", "C2"])]
        if method != "VALIDATION_BEST":
            a = pd.concat([a, arms(p, "VALIDATION_BEST")[lambda d: d.arm.isin(["C1", "C2"])]])
        for base, treat in (("M2", "M3"), ("M2", "R1"), ("M2", "R2"), ("M2", "R3"), ("M2", "C1"), ("M2", "C2"),
                            ("M0", "M1"), ("M1", "M2"), ("M0", "C2")):
            t = paired_compare(a, "dataset", "arm", base, treat, "test_ba", strata=("regime",))
            t.insert(0, "policy_method", method)
            sec.append(t)
    secondary = pd.concat(sec, ignore_index=True)
    secondary.to_csv(OUT / "G5_SECONDARY_DESCRIPTIVE.csv", index=False)

    means = vb.groupby(["regime", "arm"]).test_ba.mean().unstack()
    means.to_csv(OUT / "G5_ARM_MEANS.csv")

    # structure decomposition for M0 vs M2
    keys = ["dataset", "seed", "regime", "discretizer"]
    st = s[s.split == "test"].groupby(["regime", "discretizer", "rule_variant"])[
        ["coverage", "conflict_rate", "truth_in_candidates_rate", "single_precision", "coverage_only_from_true_rules",
         "conflict_created_by_true"]].mean().reset_index()
    st.to_csv(OUT / "G5_STRUCTURE.csv", index=False)
    cfg = c[c.discretizer != "CART"].groupby(["regime", "discretizer"])[
        ["global_rules", "true_rules", "single_class_clients", "mean_effective_intervals", "mean_rule_length",
         "binning_fit_seconds", "reduct_seconds", "lem2_seconds", "binning_communication_numbers_per_client"]].mean().reset_index()
    cfg.to_csv(OUT / "G5_COST_AND_RULES.csv", index=False)

    # policy Friedman under B2 vs A (EW3)
    fr = []
    for var in ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK"):
        for regime in ("IID", "NONIID_05", "NONIID_01"):
            g = p[(p.discretizer == "EQUAL_WIDTH_3") & (p.rule_variant == var) & (p.regime == regime)]
            r = friedman(g, "dataset", "method", "test_ba", SIX)
            m = g[g.method.isin(SIX)].groupby("method").test_ba.mean()
            fr.append({"rule_variant": var, "regime": regime, "spread_pp": 100 * (m.max() - m.min()),
                       "friedman_p": r.get("friedman_p"), "n_datasets": r.get("n_datasets"),
                       "mean_rank_json": json.dumps(r.get("mean_rank", {}))})
    pd.DataFrame(fr).to_csv(OUT / "G5_POLICY_FRIEDMAN.csv", index=False)

    n_tasks = len(c) + len(f)
    fail = {"tasks_total": int(n_tasks), "tasks_failed": int(len(f)),
            "failure_rate": float(len(f) / n_tasks) if n_tasks else float("nan"),
            "failures_by_error": f.error.str[:80].value_counts().to_dict() if len(f) else {}}
    write_manifest(OUT / "G5_ANALYSIS_MANIFEST.json", {"status": "CONFIRMATORY (preregistered)", **fail,
                                                        "datasets": int(vb.dataset.nunique())})
    pd.set_option("display.width", 250)
    print(primary[["hypothesis", "regime", "n_datasets", "mean_baseline", "mean_treatment", "mean_diff", "median_diff",
                   "ci95_low", "ci95_high", "wins", "ties", "losses", "wilcoxon_p", "holm_p", "rank_biserial", "passed"]].round(4).to_string())
    print(fam_h1[["regime", "n_datasets", "mean_diff", "ci95_low", "ci95_high", "holm_p"]].round(4).to_string())
    print(means.mul(100).round(2).to_string())
    print(secondary[secondary.policy_method == "VALIDATION_BEST"][["baseline", "treatment", "regime", "mean_diff", "ci95_low", "ci95_high", "wins", "losses", "wilcoxon_p"]].round(4).to_string())
    print(pd.DataFrame(fr).round(4).to_string())
    print(fail)


if __name__ == "__main__":
    main()
