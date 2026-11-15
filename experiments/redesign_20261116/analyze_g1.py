"""Gate 1 analysis: TRUE-rule decomposition and paired tests (dataset = unit)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .common import OUT, bootstrap_path

bootstrap_path()
from fedrs.provenance import write_manifest  # noqa: E402
from fedrs.stats import friedman, paired_compare  # noqa: E402

P = "REDESIGN_G1_DEGENERACY_"
SIX = ("FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL")


def main():
    c = pd.read_csv(OUT / f"{P}CONFIG.csv")
    s = pd.read_csv(OUT / f"{P}STRUCTURE.csv")
    p = pd.read_csv(OUT / f"{P}POLICIES.csv")
    cl = pd.read_csv(OUT / f"{P}CLIENTS.csv")

    # 1. structural decomposition (ORIGINAL partition)
    so = s[s.partition_mode == "ORIGINAL"]
    cols = ["coverage", "no_hit_rate", "single_rate", "conflict_rate", "truth_in_candidates_rate", "single_precision",
            "multi_truth_in_candidates", "rows_matched_by_true_rule", "coverage_only_from_true_rules",
            "conflict_rate_without_true", "conflict_created_by_true", "conflict_involving_true",
            "truth_in_candidates_only_via_true"]
    dec = so.groupby(["regime", "split", "rule_variant"])[[x for x in cols if x in so]].mean().reset_index()
    dec.to_csv(OUT / "G1_STRUCTURE_DECOMPOSITION.csv", index=False)

    co = c[c.partition_mode == "ORIGINAL"]
    deg = co.groupby("regime").agg(
        configs=("dataset", "size"), configs_with_true_rule=("true_rules", lambda x: float((x > 0).mean())),
        mean_true_rules=("true_rules", "mean"), mean_single_class_clients=("single_class_clients", "mean"),
        mean_empty_reduct_clients=("empty_reduct_clients", "mean"), mean_tiny_clients=("tiny_clients", "mean"),
        mean_global_rules=("global_rules", "mean"), mean_label_skew_tv=("label_skew_tv", "mean"),
        mean_exact_antecedent_conflicts=("exact_antecedent_conflict_groups", "mean"),
        mean_pairwise_antecedent_jaccard=("pairwise_antecedent_jaccard", "mean")).reset_index()
    deg.to_csv(OUT / "G1_DEGENERACY_PREVALENCE.csv", index=False)
    clo = cl[cl.partition_mode == "ORIGINAL"]
    ds = clo.groupby(["dataset", "regime"]).agg(single_class_client_share=("single_class_client", "mean"),
                                                empty_reduct_share=("empty_reduct", "mean"),
                                                mean_client_rows=("client_rows", "mean")).reset_index()
    ds.to_csv(OUT / "G1_DEGENERACY_BY_DATASET.csv", index=False)

    # 2. paired B / B2 vs A on Test BA and structure, per regime x method
    po = p[p.partition_mode == "ORIGINAL"].copy()
    pairs = []
    for variant in ("B_DROP_TRUE", "B2_TRUE_AS_FALLBACK"):
        for metric in ("test_ba", "test_accuracy", "test_macro_f1"):
            pairs.append(paired_compare(po, "dataset", "rule_variant", "A_ALL_RULES", variant, metric,
                                        strata=("regime", "method")))
    paired = pd.concat(pairs, ignore_index=True)
    paired.to_csv(OUT / "G1_PAIRED_VARIANT_VS_A.csv", index=False)

    # 3. policy spread & Friedman within each regime x variant
    spread = []
    for (regime, variant), g in po.groupby(["regime", "rule_variant"]):
        means = g[g.method.isin(SIX)].groupby("method").test_ba.mean()
        fr = friedman(g, "dataset", "method", "test_ba", SIX)
        spread.append({"regime": regime, "rule_variant": variant, "best_policy": means.idxmax(),
                       "worst_policy": means.idxmin(), "spread_pp": 100 * (means.max() - means.min()),
                       **{k: v for k, v in fr.items() if k != "mean_rank"},
                       "mean_rank_json": json.dumps(fr.get("mean_rank", {}))})
    pd.DataFrame(spread).to_csv(OUT / "G1_POLICY_SPREAD_FRIEDMAN.csv", index=False)

    # 4. alpha gap: IID vs NONIID under each variant (same datasets/seeds)
    gaps = []
    for variant in ("A_ALL_RULES", "B_DROP_TRUE", "B2_TRUE_AS_FALLBACK"):
        g = po[po.rule_variant == variant]
        for regime in ("NONIID_05", "NONIID_01"):
            t = paired_compare(g, "dataset", "regime", "IID", regime, "test_ba", strata=("method",))
            t.insert(0, "rule_variant", variant)
            gaps.append(t)
    pd.concat(gaps, ignore_index=True).to_csv(OUT / "G1_ALPHA_GAP.csv", index=False)

    # 5. Control C (different data allocation!) vs ORIGINAL, only configs where C succeeded
    ok = c[c.partition_mode == "CONTROL_C"][["dataset", "seed", "regime"]]
    pc = p.merge(ok, on=["dataset", "seed", "regime"])
    pc = pc[pc.rule_variant == "A_ALL_RULES"]
    cc = paired_compare(pc, "dataset", "partition_mode", "ORIGINAL", "CONTROL_C", "test_ba", strata=("regime", "method"))
    cc.to_csv(OUT / "G1_CONTROL_C_VS_ORIGINAL.csv", index=False)
    cstruct = c.merge(ok, on=["dataset", "seed", "regime"]).groupby(["regime", "partition_mode"])[
        ["true_rules", "single_class_clients", "label_skew_tv", "partition_attempts", "global_rules"]].mean().reset_index()
    cstruct.to_csv(OUT / "G1_CONTROL_C_STRUCTURE.csv", index=False)

    write_manifest(OUT / "G1_ANALYSIS_MANIFEST.json", {
        "inputs": [f"{P}{t}.csv" for t in ("CONFIG", "STRUCTURE", "POLICIES", "CLIENTS")],
        "unit": "dataset (seeds averaged within dataset)", "test": "two-sided Wilcoxon signed-rank; Holm within table",
        "bootstrap": "10000 dataset resamples, percentile 95% CI", "status": "EXPLORATORY",
    })
    print(deg.to_string())
    key = paired[(paired.metric == "test_ba") & paired.method.isin(["SIMPLE_VOTING", "GLOBAL_STRENGTH", "VALIDATION_BEST", "CONFLICT_BUCKET_ROUTER_V1"])]
    print(key[["regime", "method", "treatment", "mean_diff", "ci95_low", "ci95_high", "wins", "ties", "losses", "wilcoxon_p", "holm_p_within_table"]].round(4).to_string())
    print(pd.DataFrame(spread)[["regime", "rule_variant", "best_policy", "spread_pp", "friedman_p"]].round(4).to_string())
    print(cc[cc.method.isin(["SIMPLE_VOTING", "VALIDATION_BEST"])][["regime", "method", "n_datasets", "mean_diff", "ci95_low", "ci95_high", "wilcoxon_p"]].round(4).to_string())
    print(cstruct.round(3).to_string())


if __name__ == "__main__":
    main()
