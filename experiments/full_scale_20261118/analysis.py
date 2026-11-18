"""Paired, dataset-level summaries for six policy results."""
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon
from fedrs.predict import POLICIES

TIE = 1e-6  # percentage points


def scenario_of(row):
    if row.system not in ("CENTRALIZED", "FEDERATED"):
        raise ValueError("Unrecognized system")
    if hasattr(row, "client_count"):
        expected_clients = 0 if row.system == "CENTRALIZED" else 3
        if int(row.client_count) != expected_clients:
            raise ValueError("Invalid client_count")
    if row.distribution == "IID" and pd.notna(row.dirichlet_alpha):
        raise ValueError("IID must have an empty dirichlet_alpha")
    if row.system == "CENTRALIZED":
        if row.distribution != "IID":
            raise ValueError("CENTRALIZED must use IID")
        return "CENTRALIZED"
    if row.distribution == "IID":
        return "FED_IID"
    if row.distribution != "DIRICHLET_NONIID" or pd.isna(row.dirichlet_alpha):
        raise ValueError("Invalid non-IID distribution or alpha")
    if np.isclose(float(row.dirichlet_alpha), .5):
        return "FED_A05"
    if np.isclose(float(row.dirichlet_alpha), .1):
        return "FED_A01"
    raise ValueError("Unrecognized configuration")


def tied_ranks(values):
    ordered = sorted(POLICIES, key=lambda p: (-values[p], p))
    ranks = {}
    pos = 0
    while pos < len(ordered):
        end = pos + 1
        while end < len(ordered) and values[ordered[pos]] - values[ordered[end]] <= TIE:
            end += 1
        rank = (pos + 1 + end) / 2.0
        for p in ordered[pos:end]:
            ranks[p] = rank
        pos = end
    return ranks


def dataset_best(results, registry, seeds):
    if results.empty:
        return pd.DataFrame()
    data = results.copy()
    data["scenario"] = [scenario_of(r) for r in data.itertuples()]
    metadata = registry.set_index("dataset")
    rows = []
    for (dataset, scenario), group in data.groupby(["dataset", "scenario"], sort=True):
        if set(group.seed.astype(int)) != set(seeds):
            continue
        if group.duplicated(["seed", "selection_policy"]).any() or len(group) != len(seeds)*len(POLICIES):
            raise ValueError(f"Incomplete or duplicate policy results for {dataset} {scenario}")
        if set(group.selection_policy) != set(POLICIES):
            raise ValueError(f"Unexpected policy set for {dataset} {scenario}")
        averages = group.groupby("selection_policy")[["accuracy_pct", "balanced_accuracy_pct"]].mean()
        acc = {p: float(averages.loc[p, "accuracy_pct"]) for p in POLICIES}
        ba = {p: float(averages.loc[p, "balanced_accuracy_pct"]) for p in POLICIES}
        winners = [p for p in POLICIES if max(acc.values()) - acc[p] <= TIE]
        ba_winners = [p for p in POLICIES if max(ba.values()) - ba[p] <= TIE]
        rank = tied_ranks(acc)
        sorted_acc = sorted(acc.values(), reverse=True)
        meta = metadata.loc[dataset]
        row = dict(dataset=dataset, scenario=scenario, n_seeds=len(seeds),
                   feature_type=meta.feature_type, size_class=meta.size_class,
                   accuracy_best_methods=";".join(winners), accuracy_lead_pp=0.0 if len(winners) > 1 else sorted_acc[0]-sorted_acc[1],
                   accuracy_range_pp=sorted_acc[0]-sorted_acc[-1], ba_best_methods=";".join(ba_winners),
                   metric_winners_agree=set(winners) == set(ba_winners))
        for p in POLICIES:
            row.update({f"{p}_accuracy_pct": acc[p], f"{p}_balanced_accuracy_pct": ba[p],
                        f"{p}_rank": rank[p], f"{p}_wins": 1/len(winners) if p in winners else 0.0})
        rows.append(row)
    return pd.DataFrame(rows)


def holm(pairs):
    adjusted, last = {}, 0.0
    for i, (policy, value) in enumerate(sorted(pairs.items(), key=lambda x: x[1])):
        last = max(last, min(1.0, (len(pairs)-i)*value))
        adjusted[policy] = last
    return adjusted


def summary(best):
    if best.empty:
        return pd.DataFrame()
    partitions = []
    for scenario, part in best.groupby("scenario", sort=True):
        partitions.append((scenario, "ALL", "ALL", part))
        for dimension in ("feature_type", "size_class"):
            for label, sub in part.groupby(dimension, sort=True, dropna=False):
                partitions.append((scenario, dimension, "未分類（跨種子變動）" if pd.isna(label) else label, sub))
    output = []
    for scenario, dimension, label, data in partitions:
        rank_mean = {p: float(data[f"{p}_rank"].mean()) for p in POLICIES}
        leader = min(POLICIES, key=lambda p: (rank_mean[p], POLICIES.index(p)))
        arrays = [data[f"{p}_accuracy_pct"].to_numpy(dtype=float) for p in POLICIES]
        p_friedman = float(friedmanchisquare(*arrays).pvalue) if len(data) >= 3 and any(not np.array_equal(arrays[0], a) for a in arrays[1:]) else float("nan")
        comparisons = {}
        for policy in POLICIES:
            if policy == leader:
                continue
            diff = data[f"{leader}_accuracy_pct"].to_numpy() - data[f"{policy}_accuracy_pct"].to_numpy()
            comparisons[policy] = float(wilcoxon(diff).pvalue) if np.any(diff) else 1.0
        corrected = holm(comparisons)
        for p in POLICIES:
            output.append(dict(scenario=scenario, stratum=dimension, stratum_value=label, policy=p,
                               datasets=len(data), wins=float(data[f"{p}_wins"].sum()),
                               average_rank=rank_mean[p], average_accuracy_pct=float(data[f"{p}_accuracy_pct"].mean()),
                               friedman_p=p_friedman, reference_method=leader,
                               wilcoxon_p=comparisons.get(p, float("nan")),
                               wilcoxon_holm_p=corrected.get(p, float("nan"))))
    return pd.DataFrame(output)
