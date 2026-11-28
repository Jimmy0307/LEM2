"""Compare checkpoint JSONs of a new run with a reference run (results identical; timing ignored).

Usage: python docker/verify_results.py <NEW_DIR> <REFERENCE_DIR>
Both directories may be an experiment output dir (with checkpoints/<dataset>/...) or a plain folder of
<dataset>/seedNN__SCENARIO.json files. Every reference file must exist in NEW_DIR with identical rows,
source hash and partition/feature typing. Exit code 0 = all identical.
"""
import json
import sys
from pathlib import Path

TIMING_KEYS = ("dataset", "seed", "scenario", "partition_status", "partition_attempts",
               "continuous_features", "categorical_features")


def checkpoints(root: Path) -> Path:
    return root / "checkpoints" if (root / "checkpoints").is_dir() else root


def canon(v):
    return json.dumps(v, sort_keys=True)


def same(a: Path, b: Path) -> tuple[bool, str]:
    x, y = json.loads(a.read_text()), json.loads(b.read_text())
    if a.name.endswith(".failure.json"):
        return x.get("status") == y.get("status"), "failure status"
    if canon(x["rows"]) != canon(y["rows"]):
        return False, "rows differ"
    if x.get("source_prepared_sha256") != y.get("source_prepared_sha256"):
        return False, "source hash differs"
    tx, ty = x.get("timing", {}), y.get("timing", {})
    # protocol runs keep partition/feature typing per protocol; compare whatever both records carry
    for k in TIMING_KEYS:
        if k in tx or k in ty:
            if canon(tx.get(k)) != canon(ty.get(k)):
                return False, f"timing.{k} differs"
    for proto in ("NESTED_64_16_20", "HOLDOUT_80_20"):
        if proto in tx or proto in ty:
            for k in ("partition_status", "partition_attempts", "rules", "continuous_features", "categorical_features"):
                if canon(tx.get(proto, {}).get(k)) != canon(ty.get(proto, {}).get(k)):
                    return False, f"timing.{proto}.{k} differs"
    return True, ""


def main() -> int:
    new, ref = checkpoints(Path(sys.argv[1])), checkpoints(Path(sys.argv[2]))
    refs = sorted(ref.glob("*/seed??__*.json"))
    if not refs:
        print(f"no reference checkpoints under {ref}")
        return 2
    ok = bad = missing = 0
    for r in refs:
        n = new / r.parent.name / r.name
        if not n.exists():
            missing += 1
            print(f"  MISSING   {r.parent.name}/{r.name}")
            continue
        good, why = same(n, r)
        if good:
            ok += 1
        else:
            bad += 1
            print(f"  DIFFERENT {r.parent.name}/{r.name}: {why}")
    print(f"identical={ok} different={bad} missing={missing} (of {len(refs)} reference models)")
    return 0 if bad == 0 and missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
