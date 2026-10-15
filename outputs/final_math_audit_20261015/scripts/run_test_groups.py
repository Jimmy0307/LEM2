"""Run pytest groups separately and record count/pass/fail/runtime/exit code as JSON.

Usage: python run_test_groups.py <out_json> [group=paths ...]
"""
from __future__ import annotations
import json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GROUPS = {
    "core_math_and_lem2": ["tests/test_math_core.py", "tests/test_reference_ast_parity.py"],
    "reduct": ["tests/test_reduct.py"],
    "pipeline_reduct_integration": ["tests/test_reduct_pipeline.py"],
    "paper_historical": ["tests/test_paper.py"],
    "resolver_semantics_evaluation": ["tests/test_evaluation.py"],
    "federated": ["tests/test_federated.py"],
    "full_suite": ["tests"],
}

def run(paths):
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    summary = next((l for l in reversed(tail) if re.search(r"\d+ (passed|failed|error)", l)), "")
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|deselected)", summary)}
    return {"paths": paths, "exit_code": proc.returncode, "runtime_seconds": round(dt, 3),
            "summary_line": summary, "counts": counts}

if __name__ == "__main__":
    out = Path(sys.argv[1])
    groups = dict(DEFAULT_GROUPS)
    for spec in sys.argv[2:]:
        name, _, paths = spec.partition("=")
        groups[name] = paths.split(",")
    results = {name: run(paths) for name, paths in groups.items()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    for name, r in results.items():
        print(f"{name:34s} exit={r['exit_code']} {r['summary_line']}")
