"""Merge the dedicated 42742 no-limit lane into the no-limit supplementary directory (same contract).

Never overwrites: an existing file must be identical (timing may differ), otherwise it is reported.
Appends every merged file to PROVENANCE.json.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/lem2_accel")
sys.path.insert(0, "/mnt/d/Desk/LEM2_expanded_resume/tools")
from experiments.expanded_42seeds_20261120.run import validate_record  # noqa: E402
from orchestrate import same_result  # noqa: E402

RUNS = Path("/home/user/lem2_runs")
LANE, NOL = RUNS / "expanded_accel_nolimit_42742", RUNS / "expanded_accel_nolimit"
DS, DSDIR = "OML51:openml_42742", "OML51__openml_42742"
assert json.loads((LANE / "RUN_MANIFEST.json").read_text()) == json.loads((NOL / "RUN_MANIFEST.json").read_text())
src, dst = LANE / "checkpoints" / DSDIR, NOL / "checkpoints" / DSDIR
dst.mkdir(parents=True, exist_ok=True)
merged, identical, conflicts = [], 0, []
for f in sorted(src.glob("seed??__*.json")):
    seed, scenario = int(f.name[4:6]), f.name.split("__")[1].split(".")[0]
    record = json.loads(f.read_text())
    if not f.name.endswith(".failure.json"):
        validate_record(record, DS, seed, scenario)
    target = dst / f.name
    if target.exists():
        if same_result(target, f):
            identical += 1
        else:
            conflicts.append(f.name)
        continue
    shutil.copy2(f, target)
    merged.append({"dataset": DS, "file": f.name, "origin": "lane:expanded_accel_nolimit_42742"})
prov_path = NOL / "PROVENANCE.json"
prov = json.loads(prov_path.read_text())
prov.setdefault("merged_lanes", []).extend(merged)
prov_path.write_text(json.dumps(prov, indent=1))
print(f"merged={len(merged)} identical={identical} conflicts={conflicts}")
print("42742 in no-limit dir:", len(list(dst.glob("seed??__*.json"))), "decided /168")
