"""Gate 2 + Gate 4 analysis: every discretizer vs EQUAL_WIDTH_3 on identical configs.

Dataset = unit (seeds averaged), Wilcoxon + Holm within table, 10k bootstrap CI.
Also: cut position vs interval count decomposition, feature-type strata, cost table.
"""
from __future__ import annotations

import pandas as pd

from .common import OUT, bootstrap_path

bootstrap_path()
from fedrs.provenance import write_manifest  # noqa: E402
from fedrs.stats import paired_compare  # noqa: E402

KEYS = ["dataset", "seed", "regime"]


def load(table):
    a = pd.read_csv(OUT / f"REDESIGN_G2_DISCRETIZATION_{table}.csv")
    b = pd.read_csv(OUT / f"REDESIGN_G4_PROTOTYPES_{table}.csv")
    return pd.concat([a, b], ignore_index=True)


def main():
    c, s, p = load("CONFIG"), load("STRUCTURE"), load("POLICIES")
    methods = sorted(set(p.discretizer) - {"EQUAL_WIDTH_3"})
    out = []
    for variant in ("A_ALL_RULES", "B_DROP_TRUE", "B2_TRUE_AS_FALLBACK"):
        for method in ("SIMPLE_VOTING", "VALIDATION_BEST", "CONFLICT_BUCKET_ROUTER_V1"):
            g = p[(p.rule_variant == variant) & (p.method == method)]
            for m in methods:
                t = paired_compare(g, "dataset", "discretizer", "EQUAL_WIDTH_3", m, "test_ba", strata=("regime",))
                t.insert(0, "rule_variant", variant); t.insert(1, "policy_method", method)
                out.append(t)
    paired = pd.concat(out, ignore_index=True)
    paired.to_csv(OUT / "G2G4_PAIRED_VS_EW3.csv", index=False)

    # position vs count (same per-feature interval count as MDLP_HIST)
    g = p[(p.rule_variant == "B2_TRUE_AS_FALLBACK") & (p.method == "VALIDATION_BEST")]
    dec = pd.concat([
        paired_compare(g, "dataset", "discretizer", "EW_COUNT_MATCHED_MDLP_HIST", "MDLP_HIST", "test_ba", strata=("regime",)).assign(effect="POSITION_supervised_vs_EW_same_count"),
        paired_compare(g, "dataset", "discretizer", "EF_COUNT_MATCHED_MDLP_HIST", "MDLP_HIST", "test_ba", strata=("regime",)).assign(effect="POSITION_supervised_vs_EF_same_count"),
        paired_compare(g, "dataset", "discretizer", "EQUAL_WIDTH_3", "EW_COUNT_MATCHED_MDLP_HIST", "test_ba", strata=("regime",)).assign(effect="COUNT_EW3_to_MDLP_count"),
        paired_compare(g, "dataset", "discretizer", "EQUAL_WIDTH_3", "EQUAL_WIDTH_5", "test_ba", strata=("regime",)).assign(effect="COUNT_EW3_to_EW5"),
        paired_compare(g, "dataset", "discretizer", "EQUAL_WIDTH_5", "RS_DISCERNIBILITY_CENTRAL", "test_ba", strata=("regime",)).assign(effect="POSITION_RSMD_vs_EW5_similar_count"),
    ], ignore_index=True)
    dec.to_csv(OUT / "G2_POSITION_VS_COUNT.csv", index=False)

    # structure + cost per method x regime (B2 for structure, test split)
    st = s[(s.split == "test")].pivot_table(index=["discretizer", "regime"], columns="rule_variant",
                                            values=["coverage", "conflict_rate", "truth_in_candidates_rate", "single_precision"],
                                            aggfunc="mean")
    st.columns = [f"{a}__{b}" for a, b in st.columns]
    cost = c.groupby(["discretizer", "regime"])[["mean_effective_intervals", "global_rules", "true_rules", "mean_rule_length",
                                                  "max_rule_length", "dev_pos_fraction", "dev_boundary_fraction",
                                                  "binning_fit_seconds", "reduct_seconds", "lem2_seconds",
                                                  "match_seconds_dev_val_test", "binning_communication_numbers_per_client"]].mean()
    trainval = s[s.rule_variant == "B2_TRUE_AS_FALLBACK"].pivot_table(index=["discretizer", "regime"], columns="split",
                                                                       values="coverage", aggfunc="mean")
    trainval.columns = [f"exact_coverage_{x}" for x in trainval.columns]
    pol = p[p.rule_variant == "B2_TRUE_AS_FALLBACK"].pivot_table(index=["discretizer", "regime"], columns="method",
                                                                  values="test_ba", aggfunc="mean")
    pol.columns = [f"test_ba__{x}" for x in pol.columns]
    summary = cost.join(trainval).join(st).join(pol).reset_index()
    summary.to_csv(OUT / "G2G4_METHOD_SUMMARY.csv", index=False)

    # feature-type strata (VALIDATION_BEST, B2)
    ft = c[KEYS + ["discretizer", "feature_type"]].drop_duplicates()
    gft = g.merge(ft, on=KEYS + ["discretizer"])
    strat = pd.concat([paired_compare(gft, "dataset", "discretizer", "EQUAL_WIDTH_3", m, "test_ba",
                                      strata=("feature_type", "regime")) for m in methods], ignore_index=True)
    strat.to_csv(OUT / "G2G4_FEATURE_TYPE_STRATA.csv", index=False)

    # LOCO selections
    loco = c[c.discretizer.str.startswith("LOCO")][["discretizer", "regime", "cut_model_extra_json"]].copy()
    loco["chosen"] = loco.cut_model_extra_json.str.extract(r'"chosen": "([A-Z_0-9]+)"')
    loco.groupby(["discretizer", "regime", "chosen"]).size().rename("n").reset_index().to_csv(OUT / "G4_LOCO_CHOICES.csv", index=False)

    write_manifest(OUT / "G2G4_ANALYSIS_MANIFEST.json", {"status": "EXPLORATORY", "unit": "dataset",
                                                          "inputs": ["REDESIGN_G2_DISCRETIZATION_*", "REDESIGN_G4_PROTOTYPES_*"]})
    view = paired[(paired.rule_variant == "B2_TRUE_AS_FALLBACK") & (paired.policy_method == "VALIDATION_BEST")]
    pd.set_option("display.width", 250)
    print(view.pivot_table(index="treatment", columns="regime", values="mean_diff").mul(100).round(2).sort_values("NONIID_01").to_string())
    print(view.pivot_table(index="treatment", columns="regime", values="holm_p_within_table").round(3).to_string())
    print(dec[["effect", "regime", "mean_diff", "ci95_low", "ci95_high", "wilcoxon_p"]].round(4).to_string())
    print(loco.groupby(["discretizer", "chosen"]).size().to_string())


if __name__ == "__main__":
    main()
