"""Fit rule-count, memory and time scaling models on all completed models (read-only).

rules  : log10(rules+1) ~ log10(train_rows) + log10(1+category values) + n_categorical + n_continuous
                          + log10(n_classes) + federated
memory : peak_rss_mb ~ a + b*(rules*train_rows/1e6) + c*(train_rows/1e3)          (see FIT.json)
time   : log10(LEM2 s) ~ log10(rules) + log10(train_rows) ;  log10(wall s) likewise
Writes memory_analysis/SCALING_MODELS.json and PROJECTIONS.csv.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("/mnt/d/Desk/LEM2_expanded_resume/memory_analysis")
m = pd.read_csv(OUT / "MODEL_MEASUREMENTS.csv")
d = pd.read_csv(OUT / "DATASET_SUMMARY.csv")
m = m.merge(d[["dataset", "n_classes"]], on="dataset", how="left")
m["federated"] = (m.scenario != "CENTRALIZED").astype(float)


def ols(y, cols, frame, names):
    X = np.c_[np.ones(len(frame)), np.column_stack(cols)]
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    resid_sd = float(np.std(y - pred))
    return dict(zip(["intercept", *names], map(float, coef))), float(r2), resid_sd


def rule_terms(f):
    return [np.log10(f.train_rows), np.log10(1 + f.category_values_total), f.n_categorical,
            f.n_continuous, np.log10(f.n_classes.clip(lower=2)), f.federated]


RULE_NAMES = ["log10_train_rows", "log10_1p_category_values", "n_categorical", "n_continuous",
              "log10_n_classes", "federated"]
rules_fit = m.dropna(subset=["n_classes"])
rc, r2_rules, sd_rules = ols(np.log10(rules_fit.rule_count + 1), rule_terms(rules_fit), rules_fit, RULE_NAMES)

t = m[(m.lem2_seconds > 0.01) & (m.rule_count > 0)]
tc, r2_lem2, sd_lem2 = ols(np.log10(t.lem2_seconds), [np.log10(t.rule_count), np.log10(t.train_rows)], t,
                           ["log10_rules", "log10_train_rows"])
w = m[(m.wall_seconds > 0.05) & (m.rule_count > 0)]
wc, r2_wall, sd_wall = ols(np.log10(w.wall_seconds), [np.log10(w.rule_count), np.log10(w.train_rows)], w,
                           ["log10_rules", "log10_train_rows"])
mem = json.loads((OUT / "FIT.json").read_text())

# feature-count spread (honest check of what the data can identify)
feat_spread = d.n_features.value_counts().sort_index().to_dict()

# projections for the two datasets without results (federated pooled train rows ~ 64 % of used rows)
targets = d[d.dataset.isin(["OML51:openml_1169", "OML51:openml_42732"])]
rows = []
for r in targets.itertuples():
    for fed in (0.0, 1.0):
        f = pd.DataFrame([{"train_rows": 0.64 * r.used_rows, "category_values_total": r.category_values_total,
                           "n_categorical": r.n_categorical, "n_continuous": r.n_continuous,
                           "n_classes": r.n_classes, "federated": fed}])
        x = np.r_[1.0, [float(v.iloc[0]) for v in rule_terms(f)]]
        log_rules = float(x @ np.array(list(rc.values())))
        for label, shift in (("central", 0.0), ("low_1sd", -sd_rules), ("high_1sd", sd_rules)):
            rules = 10 ** (log_rules + shift) - 1
            tr = f.train_rows.iloc[0]
            mem_mb = mem["a"] + mem["b_per_MB_of_rules_x_rows"] * rules * tr / 1e6 + mem["c_per_1000_train_rows"] * tr / 1e3
            lem2_s = 10 ** (tc["intercept"] + tc["log10_rules"] * np.log10(rules) + tc["log10_train_rows"] * np.log10(tr))
            wall_s = 10 ** (wc["intercept"] + wc["log10_rules"] * np.log10(rules) + wc["log10_train_rows"] * np.log10(tr))
            rows.append({"dataset": r.dataset, "scenario": "FEDERATED" if fed else "CENTRALIZED", "estimate": label,
                         "train_rows": round(tr), "rules": round(rules), "memory_gb": round(mem_mb / 1024, 1),
                         "lem2_hours": round(lem2_s / 3600, 1), "wall_hours": round(wall_s / 3600, 1)})
proj = pd.DataFrame(rows)
proj.to_csv(OUT / "PROJECTIONS.csv", index=False)
res = {"n_models": int(len(m)),
       "rules_model": {"coef": rc, "r2": r2_rules, "residual_sd_log10": sd_rules},
       "lem2_time_model": {"coef": tc, "r2": r2_lem2, "residual_sd_log10": sd_lem2, "n": int(len(t))},
       "wall_time_model": {"coef": wc, "r2": r2_wall, "residual_sd_log10": sd_wall, "n": int(len(w))},
       "memory_model": mem, "n_features_distribution_datasets": feat_spread}
(OUT / "SCALING_MODELS.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
print(proj.to_string(index=False))
