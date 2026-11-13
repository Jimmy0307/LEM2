"""Execute the existing audited Classical LEM2 protocol on 12 NEW UCI sources.

Avoid copying/rewriting the LEM2 experiment: exact same previously audited
runner, frozen source preprocessing, six policies and Train-only supplement.
Only the family/filename tags change, and source metadata is retained.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from teacher_demo.public_next12_registry import REGISTRY
import teacher_demo.extreme_dataset_runner as source
import teacher_demo.public_20_runner as experiment

def run(key,output):
    if key not in REGISTRY:raise ValueError("Dataset must be in new-12 registry")
    # Imported experiments read their registries when called.
    source.REGISTRY.update(REGISTRY)
    experiment.REGISTRY.update(REGISTRY)
    dest=Path(output)
    dest.mkdir(parents=True,exist_ok=True)
    experiment.run(key,dest)
    for label in ("BASE","SUPPLEMENT","DATA"):
        src=dest/f"PUBLIC20_{label}_{key}.csv"
        if not src.is_file():raise AssertionError("Experiment missing "+str(src))
        target=dest/f"NEXT12_{label}_{key}.csv"
        if label=="BASE":
            df=pd.read_csv(src)
            df["pilot"]="EXTRA_PUBLIC12_SEED42"
            df.to_csv(target,index=False)
            src.unlink()
        else:
            src.rename(target)
    path=dest/f"PUBLIC20_PROFILE_{key}.json"
    if not path.is_file():raise AssertionError("No source provenance for "+key)
    meta=json.loads(path.read_text(encoding="utf-8"))
    meta["experiment_family"]="PUBLIC_NEXT12_INDEPENDENT"
    meta["original_source_is_full_model_training"]=False
    meta["status"]="PILOT_SEED42_SOURCE_ACQUIRED"
    (dest/f"NEXT12_PROFILE_{key}.json").write_text(
        json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    path.unlink()
    print("NEXT12_EXPERIMENT_PASS",key,int(meta["source_rows"]),int(meta["used_rows"]),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--dataset",required=True,choices=sorted(REGISTRY))
    ap.add_argument("--output",default="outputs/next12")
    a=ap.parse_args()
    run(a.dataset,a.output)
