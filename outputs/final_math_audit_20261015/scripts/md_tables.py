"""Render the UCI3 result CSVs as Markdown tables (used for 05_UCI3_RESULTS.md)."""
import sys
from pathlib import Path
import pandas as pd

A = Path(sys.argv[1])
SHORT = {"FIRST_MATCH": "FM", "SIMPLE_VOTING": "SV", "STANDARD_VOTING": "STD", "GLOBAL_STRENGTH": "GS"}

def md(df, fmt="{:.4f}"):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(fmt.format(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)

s = pd.read_csv(A / "uci3_structural_table.csv")
s1 = s[["dataset", "client_count", "central_reduct_size", "central_dependency", "mean_local_reduct_size", "reduct_instability",
        "mean_local_central_reduct_jaccard", "rule_heterogeneity", "central_rule_count", "mean_local_rule_count", "global_rule_count",
        "coverage", "pre_resolution_conflict_case_rate", "covered_conflict_rate", "exact_conflict_antecedent_rate", "conflict_cases_count"]].copy()
s1.columns = ["dataset", "C", "central reduct size", "γ_C", "mean local reduct size", "RI", "mean J(R_c,R_central)", "H_rule", "central rules",
              "mean local rules", "global rules", "coverage", "conflict rate", "covered-conflict rate", "exact-antecedent conflict rate", "conflict cases"]
for c in ["central reduct size", "global rules", "central rules", "conflict cases", "C"]:
    s1[c] = s1[c].astype(int)
print("## STRUCT\n" + md(s1))
s2 = s[["dataset", "client_count", "central_reduct", "local_reducts", "local_rule_counts"]].copy()
s2["local_reducts"] = s2["local_reducts"].str.replace(" | ", "; ", regex=False)
s2["local_rule_counts"] = s2["local_rule_counts"].str.replace(" | ", ", ", regex=False)
s2.columns = ["dataset", "C", "central reduct", "local reducts (Client_1; …; Client_C)", "local rule counts"]
print("## REDUCTS\n" + md(s2))
r = pd.read_csv(A / "uci3_resolver_table.csv")
r["policy"] = r["policy"].map(SHORT)
r1 = r[["dataset", "client_count", "policy", "accuracy", "balanced_accuracy", "macro_f1", "coverage",
        "conflict_resolution_accuracy", "conflict_balanced_accuracy", "conflict_macro_f1",
        "disagreement_vs_first_match", "conflict_disagreement_vs_first_match"]].copy()
r1.columns = ["dataset", "C", "policy", "acc", "BA", "macro-F1", "coverage", "conflict acc", "conflict BA", "conflict macro-F1",
              "disagree vs FM", "conflict disagree vs FM"]
print("## RESOLVER\n" + md(r1))
r2 = r[r.policy == "FM"][["dataset", "client_count", "balanced_accuracy", "order_sensitivity_rate", "order_balanced_accuracy_mean",
                          "order_balanced_accuracy_std", "order_balanced_accuracy_min", "order_balanced_accuracy_max"]].copy()
r2.columns = ["dataset", "C", "nominal BA", "OSR", "order BA mean", "order BA std", "order BA min", "order BA max"]
print("## ORDER\n" + md(r2))
c = r[r.policy == "FM"][["dataset", "client_count", "central_accuracy", "central_balanced_accuracy", "central_macro_f1", "central_coverage"]].drop_duplicates("dataset").drop(columns="client_count")
c.columns = ["dataset", "central acc", "central BA", "central macro-F1", "central coverage"]
print("## CENTRAL_FM\n" + md(c))
w = pd.read_csv(A / "resolver_winners.csv")
for col in [x for x in w.columns if x.startswith("winners_")]:
    w[col] = w[col].map(lambda v: "+".join(SHORT[p] for p in v.split("+")))
w.columns = ["dataset", "C", "best BA", "BA winner", "best conflict BA", "conflict BA winner", "best macro-F1", "macro-F1 winner"]
print("## WINNERS\n" + md(w))
o = pd.read_csv(A / "old_vs_new.csv")
o = o[o.policy.isin(["STANDARD_VOTING", "GLOBAL_STRENGTH"])].copy()
o["policy"] = o["policy"].map(SHORT)
o1 = o[["dataset", "client_count", "policy", "accuracy_old", "accuracy_new", "balanced_accuracy_old", "balanced_accuracy_new",
        "balanced_accuracy_delta", "macro_f1_old", "macro_f1_new", "conflict_balanced_accuracy_old", "conflict_balanced_accuracy_new",
        "conflict_balanced_accuracy_delta", "coverage_delta"]].copy()
o1.columns = ["dataset", "C", "policy", "acc old", "acc new", "BA old", "BA new", "ΔBA", "F1 old", "F1 new", "cBA old", "cBA new", "ΔcBA", "Δcoverage"]
print("## OLDNEW\n" + md(o1, "{:+.4f}").replace("+0.", "0.").replace("+1.", "1."))
