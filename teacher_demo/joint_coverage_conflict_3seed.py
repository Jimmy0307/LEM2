"""Prospective three-seed replication of 20 UCI coverage/conflict gated supplement pilot.

Reuses SAME earlier source-locked 64/16/20 pipeline and fixed gate;
does not retune thresholds after seeing test. Separates original Exact
Coverage from augmented Effective Coverage. NoMatch != actual rejection.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from teacher_demo import conflict_aware_coverage_pilot as pilot
from teacher_demo.public_20_registry import REGISTRY

SEEDS=(1,7,42)
def run(name,output):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    for seed in SEEDS:
        pilot.SEED=seed
        pilot.INNER_SEED=1000+seed
        tmp=root/f"tmp_seed{seed}"
        pilot.one(name,str(tmp))
        cats={"RESULTS":"CONFLICT_AWARE_RESULTS_",
              "EVENTS":"CONFLICT_AWARE_GATE_EVENTS_",
              "AUDIT":"CONFLICT_AWARE_AUDIT_"}
        for kind,prefix in cats.items():
            f=tmp/(prefix+name+".csv")
            assert f.exists(),f
            values=pd.read_csv(f)
            if kind=="RESULTS":
                assert values.seed.eq(seed).all()
                assert values.groupby(["system"]).size().eq(3).all()
                assert set(values.variant)=={
                    "BASE_LEM2","ALL_TRAIN_SUPPLEMENTS","VALIDATION_GATED_CONFLICT_AWARE"}
                for _,x in values.groupby("system"):
                    base=x[x.variant.eq("BASE_LEM2")].iloc[0]
                    for _,r in x.iterrows():
                        assert r.coverage_pct>=base.coverage_pct-1e-9
                        assert r.active_conflict_count<=r.covered_count
                        assert r.covered_count+r.no_match_count==r.n
                        assert 0<=r.candidate_coverage_pct<=100
            dest=root/f"JOINT_{kind}_{name}_seed{seed}.csv"
            dest.write_bytes(f.read_bytes())
        print("JOINT_COVERAGE_CONFLICT_SOURCE_SEED_PASS",name,seed,flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--dataset",choices=sorted(REGISTRY),required=True)
    p.add_argument("--output",default="outputs/joint_coverage_conflict")
    a=p.parse_args();run(a.dataset,a.output)
if __name__=="__main__":main()
