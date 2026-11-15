"""Gate 3 analysis: noise sensitivity (Classical vs VPRS) and its link to federated conflict;
six-policy five-way outcome decomposition on fixed rules (from Gate 1)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .common import OUT, bootstrap_path

bootstrap_path()
from fedrs.provenance import write_manifest  # noqa: E402
from fedrs.stats import paired_compare  # noqa: E402

SIX = ("FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL")


def noise(prefix: str):
    c = pd.read_csv(OUT / f"{prefix}_CONFIG.csv")
    s = pd.read_csv(OUT / f"{prefix}_STRUCTURE.csv")
    p = pd.read_csv(OUT / f"{prefix}_POLICIES.csv")
    for df in (c, s, p):
        df["induction_label"] = df.induction + np.where(df.induction == "VPRS", "_b" + df.beta.astype(str), "")
    keys = ["dataset", "seed", "regime", "discretizer", "label_noise", "induction_label"]
    st = s[(s.split == "test") & (s.rule_variant == "B2_TRUE_AS_FALLBACK")]
    vb = p[(p.rule_variant == "B2_TRUE_AS_FALLBACK") & (p.method == "VALIDATION_BEST")]
    m = c.merge(st[keys + ["coverage", "conflict_rate", "truth_in_candidates_rate"]], on=keys) \
         .merge(vb[keys + ["test_ba"]], on=keys)
    m = m.merge(s[(s.split == "test") & (s.rule_variant == "A_ALL_RULES")][keys + ["conflict_rate", "coverage"]]
                .rename(columns={"conflict_rate": "conflict_rate_A", "coverage": "coverage_A"}), on=keys)
    grp = ["regime", "discretizer", "induction_label", "label_noise"] + (["dataset"] if "synthetic" in prefix.lower() else [])
    summ = m.groupby(grp)[["test_ba", "dev_pos_fraction", "mean_local_pos_fraction", "global_rules", "mean_rule_length",
                            "true_rules", "coverage", "conflict_rate", "conflict_rate_A", "coverage_A",
                            "truth_in_candidates_rate", "empty_reduct_clients"]].mean().reset_index()
    summ.to_csv(OUT / f"G3_{prefix.split('_')[-1]}_NOISE_SUMMARY.csv", index=False)
    # VPRS vs Classical paired, per noise level.  Real: dataset is the unit.  Synthetic: only
    # two generators exist, so the replicate unit is (generator, generator_seed) and the
    # result is a synthetic-replicate analysis, not a cross-dataset generalisation test.
    if "synthetic" in prefix.lower():
        m["unit"] = m["dataset"] + "#" + m["source_generator_seed"].astype(str)
        unit = "unit"
    else:
        unit = "dataset"
    tests = []
    for b in ("VPRS_b0.8", "VPRS_b0.6"):
        t = paired_compare(m, unit, "induction_label", "CLASSICAL", b, "test_ba",
                           strata=("regime", "label_noise", "discretizer"))
        tests.append(t)
    pd.concat(tests).to_csv(OUT / f"G3_{prefix.split('_')[-1]}_VPRS_VS_CLASSICAL.csv", index=False)
    # noise -> structure -> conflict association (Spearman across configs, per induction)
    assoc = []
    for (ind, regime), g in m.groupby(["induction_label", "regime"]):
        for x, y in (("label_noise", "mean_local_pos_fraction"), ("label_noise", "global_rules"),
                     ("label_noise", "conflict_rate"), ("label_noise", "coverage"), ("label_noise", "test_ba"),
                     ("mean_local_pos_fraction", "conflict_rate")):
            r = stats.spearmanr(g[x], g[y])
            assoc.append({"induction": ind, "regime": regime, "x": x, "y": y, "spearman_rho": r.statistic,
                          "p_descriptive_only_pseudoreplicated": r.pvalue, "n_configs": len(g)})
    pd.DataFrame(assoc).to_csv(OUT / f"G3_{prefix.split('_')[-1]}_ASSOCIATIONS.csv", index=False)
    return summ


def policy_decomposition():
    s = pd.read_csv(OUT / "REDESIGN_G1_DEGENERACY_STRUCTURE.csv")
    p = pd.read_csv(OUT / "REDESIGN_G1_DEGENERACY_POLICIES.csv")
    keys = ["dataset", "seed", "regime", "partition_mode", "rule_variant"]
    st = s[s.split == "test"][keys + ["no_hit_rate", "single_rate", "conflict_rate", "single_precision",
                                       "multi_truth_in_candidates"]]
    m = p[p.partition_mode == "ORIGINAL"].merge(st, on=keys)
    m["multi_truth_in"] = m.conflict_rate * m.multi_truth_in_candidates.fillna(0)
    m["resolved_correct"] = m.multi_truth_in * m.test_multi_resolution_given_truth_in.fillna(0)
    m["resolved_wrong_truth_present"] = m.multi_truth_in - m.resolved_correct
    m["multi_truth_absent"] = m.conflict_rate - m.multi_truth_in
    m["single_wrong_truth_absent"] = m.single_rate * (1 - m.single_precision.fillna(1))
    cols = ["no_hit_rate", "single_rate", "conflict_rate", "resolved_correct", "resolved_wrong_truth_present",
            "multi_truth_absent", "single_wrong_truth_absent", "test_ba"]
    out = m.groupby(["regime", "rule_variant", "method"])[cols].mean().reset_index()
    # oracle headroom: share of rows a perfect resolver could still fix
    out["oracle_headroom_rows"] = out.resolved_wrong_truth_present
    out.to_csv(OUT / "G3_POLICY_FIVE_WAY_DECOMPOSITION.csv", index=False)
    return out


def main():
    real = noise("REDESIGN_G3_NOISE_REAL")
    syn = noise("REDESIGN_G3_NOISE_SYNTHETIC")
    dec = policy_decomposition()
    write_manifest(OUT / "G3_ANALYSIS_MANIFEST.json", {"status": "EXPLORATORY", "unit": "dataset"})
    pd.set_option("display.width", 250)
    r = real[real.discretizer == "EQUAL_WIDTH_3"]
    print(r.pivot_table(index=["regime", "label_noise"], columns="induction_label",
                        values=["test_ba", "mean_local_pos_fraction", "conflict_rate"]).round(3).to_string())
    sy = syn[syn.discretizer == "MDLP_HIST"].groupby(["dataset", "regime", "induction_label", "label_noise"]).mean(numeric_only=True).reset_index()
    print(sy.pivot_table(index=["dataset", "regime", "label_noise"], columns="induction_label",
                         values=["test_ba", "dev_pos_fraction", "conflict_rate"]).round(3).to_string())
    print(dec[dec.method.isin(["SIMPLE_VOTING", "GLOBAL_STRENGTH"])].round(3).to_string())


if __name__ == "__main__":
    main()
