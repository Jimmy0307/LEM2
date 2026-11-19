"""Summary tables for the professor's six questions (2026-11-19).

Reads only already-published CSVs under docs/research/teacher_dashboard/data/
and writes derived tables to data/six_questions_20261119/.  No model is refit.
Run from the repository root:  python experiments/six_questions_20261119/build_tables.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

D0 = Path("docs/research/teacher_dashboard/data")
OUT = D0 / "six_questions_20261119"
OUT.mkdir(parents=True, exist_ok=True)
P = ["FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH", "POPULATION_STANDARD", "POPULATION_GLOBAL"]
AB = dict(zip(P, ["FM", "SV", "STD", "GS", "PS", "PG"]))
SC = ["CENTRALIZED", "FED_IID", "FED_A05", "FED_A01"]
EPS = 1e-6

fs = D0 / "full_scale_20261118"
best = pd.read_csv(fs / "DATASET_BEST.csv")
reg = pd.read_csv(fs / "REGISTRY.csv")
t19 = pd.read_csv(fs / "FULL_SCALE_19COL.csv")
summ = pd.read_csv(fs / "SUMMARY.csv")
t19["scenario"] = np.where(t19.system == "CENTRALIZED", "CENTRALIZED",
                  np.where(t19.distribution == "IID", "FED_IID",
                  np.where(t19.dirichlet_alpha == 0.5, "FED_A05", "FED_A01")))
diag = (t19[t19.selection_policy == "FIRST_MATCH"]
        .groupby(["dataset", "scenario"])[["conflict_rate_pct", "test_coverage_pct", "candidate_coverage_pct", "rule_count"]]
        .mean().reset_index())
D = best.merge(diag, on=["dataset", "scenario"]).merge(
    reg[["dataset", "cohort", "n_classes", "minority_share", "used_rows"]], on="dataset")
acc = D[[p + "_accuracy_pct" for p in P]].to_numpy()
top = acc.max(axis=1)
for p in P:
    D["loss_" + AB[p]] = top - D[p + "_accuracy_pct"]
D.to_csv(OUT / "DATASET_SCENARIO_WITH_DIAGNOSTICS.csv", index=False)

# Q2: who wins, by how much
rows = []
for sc in SC:
    g = D[D.scenario == sc]
    A = g[[p + "_accuracy_pct" for p in P]].to_numpy()
    srt = np.sort(A, 1)
    b, second = srt[:, -1], srt[:, -2]
    n_top = (A >= b[:, None] - EPS).sum(1)
    for i, p in enumerate(P):
        a = A[:, i]
        sole = (a >= b - EPS) & (n_top == 1)
        lead = (b - second)[sole]
        rows.append(dict(scenario=sc, policy=p, abbr=AB[p], datasets=len(g),
                         wins_fractional=round(float(g[p + "_wins"].sum()), 3),
                         sole_wins=int(sole.sum()), sole_wins_lead_ge_1pp=int((sole & ((b - second) >= 1)).sum()),
                         mean_lead_when_sole_pp=round(float(lead.mean()), 3) if len(lead) else None,
                         mean_loss_vs_best_pp=round(float((b - a).mean()), 3),
                         datasets_loss_ge_5pp=int(((b - a) >= 5).sum())))
q2 = pd.DataFrame(rows)
q2.to_csv(OUT / "Q2_WINS_AND_MARGINS.csv", index=False)

# Q3: federated minus centralized on datasets complete in all four scenarios
common = D.groupby("dataset").scenario.nunique()
common = common[common == 4].index
C = D[D.dataset.isin(common)]
q3 = []
for p in ["STANDARD_VOTING", "SIMPLE_VOTING"]:
    w = C.pivot(index="dataset", columns="scenario", values=p + "_accuracy_pct")
    for sc in SC[1:]:
        d = w[sc] - w["CENTRALIZED"]
        q3.append(dict(policy=p, scenario=sc, datasets=len(d), mean_diff_pp=round(float(d.mean()), 3),
                       median_diff_pp=round(float(d.median()), 3), fed_higher=int((d > EPS).sum()),
                       fed_lower=int((d < -EPS).sum())))
pd.DataFrame(q3).to_csv(OUT / "Q3_FEDERATED_MINUS_CENTRALIZED_FULLSCALE.csv", index=False)

c42 = pd.read_csv(D0 / "CLASSICAL_19_COLUMNS_42SEEDS.csv")
c42["scenario"] = np.where(c42.system == "CENTRALIZED", "CENTRALIZED",
                  np.where(c42.distribution == "STRATIFIED_IID", "FED_IID",
                  np.where(c42.dirichlet_alpha == 0.5, "FED_A05", "FED_A01")))
assert c42.groupby(["dataset", "seed"]).test_rows.nunique().max() == 1  # same test split for every architecture
g42 = (c42.groupby(["dataset", "scenario", "client_count", "selection_policy"])
       [["accuracy_pct", "test_coverage_pct", "conflict_rate_pct"]].mean().reset_index())
g42.to_csv(OUT / "Q3_42SEEDS_MEANS.csv", index=False)

# Q4: per-scenario profile
q4 = []
for sc in SC:
    g = C[C.scenario == sc]
    s = summ[(summ.scenario == sc) & (summ.stratum == "ALL")]
    q4.append(dict(scenario=sc, datasets=len(g),
                   mean_acc_SV=round(float(g.SIMPLE_VOTING_accuracy_pct.mean()), 2),
                   mean_acc_STD=round(float(g.STANDARD_VOTING_accuracy_pct.mean()), 2),
                   mean_acc_best_of_six=round(float(g[[p + "_accuracy_pct" for p in P]].max(axis=1).mean()), 2),
                   median_test_coverage_pct=round(float(g.test_coverage_pct.median()), 1),
                   median_truth_in_candidates_pct=round(float(g.candidate_coverage_pct.median()), 1),
                   median_conflict_pct=round(float(g.conflict_rate_pct.median()), 1),
                   median_rules=round(float(g.rule_count.median()), 1),
                   median_six_policy_range_pp=round(float(g.accuracy_range_pp.median()), 2),
                   best_mean_rank=";".join(s[s.average_rank <= s.average_rank.min() + 1e-9].policy),
                   most_wins=s.sort_values("wins").policy.iloc[-1]))
pd.DataFrame(q4).to_csv(OUT / "Q4_SCENARIO_PROFILE.csv", index=False)

# Q6: where each policy works / fails (mean loss vs the best of six, pp)
non = D[D.scenario.isin(["FED_A05", "FED_A01"])]
groups = [
    ("衝突率 <1%", D[D.conflict_rate_pct < 1]),
    ("衝突率 1–10%", D[(D.conflict_rate_pct >= 1) & (D.conflict_rate_pct < 10)]),
    ("衝突率 10–30%", D[(D.conflict_rate_pct >= 10) & (D.conflict_rate_pct < 30)]),
    ("衝突率 ≥30%", D[D.conflict_rate_pct >= 30]),
    ("聯邦 IID", D[D.scenario == "FED_IID"]),
    ("Non-IID，2–5 類", non[non.n_classes <= 5]),
    ("Non-IID，6 類以上", non[non.n_classes >= 6]),
    ("Non-IID，少數類 <10%", non[non.minority_share < 0.10]),
    ("Non-IID，類別平均（少數類 ≥25%）", non[non.minority_share >= 0.25]),
]
q6 = []
for name, g in groups:
    r = dict(condition=name, configs=len(g), datasets=g.dataset.nunique())
    for p in P:
        r["mean_loss_" + AB[p]] = round(float(g["loss_" + AB[p]].mean()), 2)
        r["share_loss_ge_5pp_" + AB[p]] = round(float((g["loss_" + AB[p]] >= 5).mean() * 100), 1)
    q6.append(r)
pd.DataFrame(q6).to_csv(OUT / "Q6_POLICY_CONDITIONS.csv", index=False)
coh = (D[D.scenario == "FED_A01"].groupby("cohort")[[p + "_wins" for p in P]].sum().round(2)
       .assign(datasets=D[D.scenario == "FED_A01"].groupby("cohort").size()))
coh.to_csv(OUT / "Q6_A01_WINS_BY_COHORT.csv")
print("done", len(D), len(common))
