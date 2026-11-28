"""NESTED test rows of the protocol run must equal the published main-run rows (same computation).

Usage: python parity_vs_main.py <protocol_run_dir> [--max N]
Compares every protocol checkpoint that also exists (as a completed model) in the main run.
"""
import json
import math
import sys
from pathlib import Path

MAIN = Path("/home/user/lem2_runs/expanded_188_42seeds/checkpoints")
FIELDS = (("accuracy_pct", "accuracy_pct"), ("balanced_accuracy_pct", "balanced_accuracy_pct"),
          ("coverage_pct", "test_coverage_pct"), ("candidate_coverage_pct", "candidate_coverage_pct"),
          ("conflict_rate_pct", "conflict_rate_pct"), ("rule_count", "rule_count"), ("train_rows", "train_rows"))


def main():
    run = Path(sys.argv[1]) / "checkpoints"
    limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None
    compared = identical = 0
    diffs = []
    for f in sorted(run.glob("*/seed??__*.json")):
        if f.name.endswith(".failure.json"):
            continue
        ref = MAIN / f.parent.name / f.name
        if not ref.exists():
            continue
        new = {(r["rule_variant"], r["selection_policy"]): r for r in json.loads(f.read_text())["rows"]
               if r["protocol"] == "NESTED_64_16_20" and r["split"] == "test"}
        old = {(r["rule_variant"], r["selection_policy"]): r for r in json.loads(ref.read_text())["rows"]}
        compared += 1
        bad = [(k, a) for k in old for a, b in FIELDS
               if not math.isclose(float(new[k][a]), float(old[k][b]), rel_tol=0, abs_tol=1e-9)]
        if bad:
            diffs.append((f"{f.parent.name}/{f.name}", bad[:3]))
        else:
            identical += 1
        if limit and compared >= limit:
            break
    print(f"compared={compared} identical={identical} different={len(diffs)}")
    for d in diffs[:10]:
        print("  DIFF", d)
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
