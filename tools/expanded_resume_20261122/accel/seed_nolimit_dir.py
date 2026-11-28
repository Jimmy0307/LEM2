"""Seed the no-limit supplementary directory (run inside the accel worktree, WSL).

* RUN_MANIFEST.json = the 14,400 s supplementary contract with timeout_seconds = 1e9 (same code 805ade0).
* SOURCE.json / source.pkl copied from the main run (run.py re-verifies the SHA).
* Completed (non-failure) checkpoints from the 14,400 s supplementary run, its unmerged shards and the
  parity runs are carried over after run.validate_record. A model that finished under a finite deadline
  produces the same deterministic result without one; failures are NOT carried (they are re-run).
* Writes PROVENANCE.json listing every carried file and its origin.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/lem2_accel")
from experiments.expanded_42seeds_20261120.run import validate_record  # noqa: E402

RUNS = Path("/home/user/lem2_runs")
MAIN = RUNS / "expanded_188_42seeds" / "checkpoints"
EXT = RUNS / "expanded_accel_ext"
NOL = RUNS / "expanded_accel_nolimit"
DATASETS = ["OML51:openml_41027", "OML51:openml_42734", "OML51:openml_41162", "OML51:openml_4135",
            "OML51:openml_42733", "OML51:openml_42742", "OML51:openml_1169", "OML51:openml_42732"]

contract = json.loads((EXT / "RUN_MANIFEST.json").read_text())
assert contract["git_revision"] == "805ade097fdd3d9f9c5ef234f3e9277f41798712"
contract["timeout_seconds"] = 1e9
NOL.mkdir(parents=True, exist_ok=True)
manifest = NOL / "RUN_MANIFEST.json"
if manifest.exists():
    assert json.loads(manifest.read_text()) == contract, "existing no-limit manifest differs"
else:
    manifest.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
(NOL / "ORCHESTRATOR_CONTROL.json").write_text(
    json.dumps({"max_jobs": 6, "max_heavy": 6, "mem_budget_gb": 8, "mem_reserve_gb": 2.5}) + "\n")

origins = [("supplementary_14400_merged", EXT / "checkpoints")]
origins += [(f"supplementary_14400_shard:{p.parent.name}/{p.name}", p / "checkpoints")
            for p in sorted((RUNS / "shards_accel").glob("*/s??-??"))]
origins += [(f"parity:{p.name}", p / "checkpoints") for p in sorted((RUNS / "accel_parity").glob("*_s??"))]
carried, skipped = [], []
for ds in DATASETS:
    dsdir = ds.replace(":", "__")
    dest = NOL / "checkpoints" / dsdir
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("SOURCE.json", "source.pkl"):
        if not (dest / name).exists():
            shutil.copy2(MAIN / dsdir / name, dest / name)
    src_sha = json.loads((dest / "SOURCE.json").read_text()).get("prepared_sha256")
    for origin, root in origins:
        for f in sorted((root / dsdir).glob("seed??__*.json")):
            if f.name.endswith(".failure.json") or (dest / f.name).exists():
                continue
            seed, scenario = int(f.name[4:6]), f.name.split("__")[1][:-5]
            record = json.loads(f.read_text())
            try:
                validate_record(record, ds, seed, scenario)
                assert record.get("source_prepared_sha256") in (None, src_sha)
            except Exception as exc:  # report, never hide
                skipped.append({"file": str(f), "error": repr(exc)})
                continue
            shutil.copy2(f, dest / f.name)
            carried.append({"dataset": ds, "file": f.name, "origin": origin})
(NOL / "PROVENANCE.json").write_text(json.dumps({
    "contract": "accel 805ade0, timeout 1e9 s (no practical limit)",
    "carried_completed_models": carried, "skipped_invalid": skipped,
    "rule": "only completed models are carried; failures/timeouts are recomputed without a deadline"}, indent=1))
print(f"carried={len(carried)} skipped={len(skipped)}")
for ds in DATASETS:
    n = len(list((NOL / "checkpoints" / ds.replace(":", "__")).glob("seed??__*.json")))
    print(f"  {ds:22s} completed models carried: {n}")
