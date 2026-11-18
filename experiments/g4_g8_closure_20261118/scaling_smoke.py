"""G8 resource-capped synthetic scalability smoke, NOT real-domain generalisation.

Checks POS exactness and distinguishes exact-minimum reduct from a greedy
train-POS-preserving heuristic at 5/8/12/24 categorical features. Does NOT
present Greedy vs exact Test BA or claim NP-hardness is solved. Outputs scratch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from fedrs.discretize import apply_cuts, condition_columns, fit_equal_width
from fedrs.noise import synthetic_table
from roughset.reduct_fast import exact_cached, greedy_pos


def evaluate_smoke(seed: int = 20261118, n: int = 240):
    rng = np.random.default_rng(seed)
    frame = synthetic_table(n, "balanced", seed)
    m = fit_equal_width({"global": frame}, ["x1","x2","x3"], "class", 3)
    data = apply_cuts(frame, m, "class", ["c1","c2"])
    base = condition_columns(["x1","x2","x3","c1","c2"], ["x1","x2","x3"])
    for i in range(19):
        data[f"noise_{i:02d}"] = rng.integers(0, 3, size=len(data)).astype(str)
    rows = []
    for n_features in (5, 8, 12, 24):
        cols = base + [f"noise_{i:02d}" for i in range(n_features - len(base))]
        assert len(cols) == n_features
        started = perf_counter()
        greedy = greedy_pos(data, cols, "class")
        wall = perf_counter() - started
        if greedy.full_positive_region != greedy.positive_region:
            raise AssertionError("Greedy did not preserve exact Train POS")
        if not (0 <= greedy.reduct_size <= n_features):
            raise AssertionError("Greedy reduct size out of bounds")
        exact = exact_cached(data, cols, "class", max_features=8) if n_features <= 8 else None
        if exact is not None:
            if exact.full_positive_region != greedy.full_positive_region:
                raise AssertionError("Exact and greedy Train POS disagree")
            if greedy.reduct_size < exact.reduct_size:
                raise AssertionError("Greedy cannot be smaller than a verified exact minimum")
        rows.append({
            "seed":seed,"n_rows":len(data),"n_features":n_features,
            "algorithm":"GREEDY_POS",
            "reduct_size":greedy.reduct_size,
            "train_pos":greedy.positive_region,
            "full_train_pos":greedy.full_positive_region,
            "selection_seconds":wall,
            "exact_minimum_verified":exact is not None,
            "exact_minimum_size":exact.reduct_size if exact else None,
            "greedy_equals_exact_selected":(greedy.selected == exact.selected) if exact else None,
        })
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    out=args.output.resolve()
    published=Path(__file__).resolve().parents[2]/"docs/research/redesign_20261116/data"
    if out.is_relative_to(published.resolve()):
        raise SystemExit("Scratch output cannot be inside published evidence")
    out.mkdir(parents=True,exist_ok=True)
    rows=evaluate_smoke()
    pd.DataFrame(rows).to_csv(out/"G8_SYNTHETIC_SCALING_SMOKE.csv",index=False)
    (out/"G8_SYNTHETIC_SCALING_SMOKE_MANIFEST.json").write_text(
        json.dumps({"status":"ENGINEERING_FEASIBILITY_SMOKE_ONLY",
                    "seed":20261118,"n_rows":240,"feature_counts":[5,8,12,24],
                    "max_exact_features":8,"full_lem2_test_not_executed":True,
                    "no_novel_algorithm_claim":True,"no_performance_generalisation":True},
                    indent=2)+"\n",encoding="utf-8")
    print("G8_SYNTHETIC_SCALING_SMOKE_PASS",len(rows))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=="__main__":
    main()
