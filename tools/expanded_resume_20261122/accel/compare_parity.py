"""Compare accel parity checkpoints with the main run (results must be identical; timing may differ)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/d/Desk/LEM2_expanded_resume/tools")
from orchestrate import same_result  # noqa: E402

MAIN = Path("/home/user/lem2_runs/expanded_188_42seeds/checkpoints")
PAR = Path("/home/user/lem2_runs/accel_parity")


def seconds(t):
    return {k: round(v, 1) for k, v in t.items() if k.endswith("seconds") and isinstance(v, (int, float))}


for run in sorted(PAR.glob("*_s??")):
    dsdir, seed = run.name.rsplit("_s", 1)
    for sc in ("CENTRALIZED", "FED_IID", "FED_A05", "FED_A01"):
        name = f"seed{seed}__{sc}"
        new_ok, new_fail = run / "checkpoints" / dsdir / f"{name}.json", run / "checkpoints" / dsdir / f"{name}.failure.json"
        old_ok, old_fail = MAIN / dsdir / f"{name}.json", MAIN / dsdir / f"{name}.failure.json"
        new = new_ok if new_ok.exists() else new_fail if new_fail.exists() else None
        old = old_ok if old_ok.exists() else old_fail if old_fail.exists() else None
        if new is None:
            print(f"{run.name:28s} {sc:12s} RUNNING")
            continue
        t_new = json.loads(new.read_text()).get("timing", {})
        state_old = "OK" if old == old_ok else "TIMEOUT"
        state_new = "OK" if new == new_ok else json.loads(new.read_text()).get("status", "FAIL")
        verdict = ("IDENTICAL" if same_result(old, new) else "DIFFERENT") if (old == old_ok and new == new_ok) else "-"
        tot = sum(seconds(t_new).values())
        print(f"{run.name:28s} {sc:12s} main={state_old:7s} accel={state_new:7s} {verdict:9s} accel_total_s={tot:9.1f} predict_s={seconds(t_new).get('predict_seconds')}")
