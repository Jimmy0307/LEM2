"""G4–G8 new exploratory synthetic interventions, not independent evidence.

Same synthetic source/seed/partition used for S0 B2 baseline and S2 train-only
relaxed supplements. Vary Client 3/5/10 to expose pure-client and rule coverage
effects. Never claim validation on new external domain or privacy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from fedrs.experiment import fit_model, nested_split
from fedrs.noise import synthetic_table
from fedrs.partition import original_partition
from fedrs.supplement_exploratory import supplement_test

REGIMES = ("IID", "NONIID_05", "NONIID_01")
CLIENTS = (3, 5, 10)
SEEDS = (3001, 3002)


def tasks():
    return [(seed, r, k) for seed in SEEDS for r in REGIMES for k in CLIENTS]


def run(seed: int, regime: str, n_clients: int) -> dict:
    frame = synthetic_table(420, "skewed", seed)
    dev, val, test = nested_split(frame, "class", seed)
    clients = original_partition(dev, "class", n_clients, seed, regime)
    if len(clients) != n_clients:
        raise AssertionError("client partition count mismatch")
    fm = fit_model(["x1","x2","x3","c1","c2"], ["x1","x2","x3"], ["c1","c2"],
                   "class", clients, dev, val, test, "EQUAL_WIDTH_3")
    s = supplement_test(fm, min_support=5, min_purity=.90, base_policy="SIMPLE_VOTING")
    if s["augmented_strict_coverage"] < s["strict_nonempty_coverage"] - 1e-9:
        raise AssertionError("augmented strict rule coverage cannot decrease")
    return {
        "seed":seed, "regime":regime, "n_clients":n_clients,
        "pure_clients":sum(m.n_classes==1 for m in fm.local.values()),
        "small_clients":sum(m.rows<20 for m in fm.local.values()),
        "true_rules":sum(not r.conditions for r in fm.rules),
        **s,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    dest=a.output.resolve()
    published=(Path(__file__).resolve().parents[2]/"docs/research/redesign_20261116/data").resolve()
    if dest.is_relative_to(published):
        raise SystemExit("Cannot overwrite confirmation results")
    dest.mkdir(parents=True,exist_ok=True)
    good,bad=[],[]
    for seed,regime,clients in tasks():
        try:
            good.append(run(seed,regime,clients))
        except Exception as exc:
            bad.append({"seed":seed,"regime":regime,"n_clients":clients,
                        "error_type":type(exc).__name__,"error":str(exc)})
    pd.DataFrame(good).to_csv(dest/"G4_G8_CLIENT_SUPPLEMENT_SYNTHETIC.csv",index=False)
    pd.DataFrame(bad,columns=("seed","regime","n_clients","error_type","error")).to_csv(
        dest/"G4_G8_CLIENT_SUPPLEMENT_FAILURES.csv",index=False)
    state={
        "designation":"NEW_EXPLORATORY_SYNTHETIC_ONLY",
        "seed_list":SEEDS,"regimes":REGIMES,"n_clients":CLIENTS,
        "attempted":len(tasks()),"succeeded":len(good),"failed":len(bad),
        "train_only_supplement":True,"test_used_for_selection":False,
        "no_privacy_guarantee":True,"not_full_scale":True,
    }
    (dest/"G4_G8_CLIENT_SUPPLEMENT_MANIFEST.json").write_text(
        json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("G4_G8_SYNTHETIC_INTERVENTION_TASKS",len(tasks()),"PASSED",len(good),"FAILED",len(bad))
    if good:
        print(pd.DataFrame(good).groupby(["regime","n_clients"]).agg(
            mean_strict_coverage=("strict_nonempty_coverage","mean"),
            mean_supplement_coverage=("augmented_strict_coverage","mean"),
            mean_BA_gain_pp=("test_ba_gain_pp","mean"),
            pure_clients=("pure_clients","mean")
        ).round(4).to_string())
    if bad:
        print("FAILED_CASES",bad)
        raise RuntimeError(f"{len(bad)} synthetic intervention tasks failed; failures preserved")
    print("G4_G8_SYNTHETIC_INTERVENTION_PASS")


if __name__=="__main__":
    main()
