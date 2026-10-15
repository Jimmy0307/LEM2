"""UCI3 HOLDOUT seed-42 STRATIFIED C=2..5 four-policy rerun using the frozen UCI snapshot.

Usage: python run_uci3.py <outputs_folder> <run_id> <snapshot_dir>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).parent))
from roughset.batch import run_policy_matrix  # noqa: E402
from uci_snapshot import replay_fetcher  # noqa: E402

if __name__ == "__main__":
    out, run_id, snap = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
    assert cfg["evaluation"]["mode"] == "HOLDOUT" and cfg["evaluation"]["seed"] == 42
    assert cfg["federated"]["partition"] == "STRATIFIED" and cfg["federated"]["client_counts"] == [2, 3, 4, 5]
    assert cfg["reduct"]["enabled"] is True
    cfg["report"]["outputs_folder"] = str(out)
    cfg["input"]["run_local_files"] = False  # local folder holds only a placeholder; UCI3 only
    import os; os.chdir(ROOT)
    result = run_policy_matrix(cfg, run_id=run_id, fetcher=replay_fetcher(snap))
    print(result["summary"].to_string(index=False))
    print("ROOT_OUTPUT", result["root_output"])
