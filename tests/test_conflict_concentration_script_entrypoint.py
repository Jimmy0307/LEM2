from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_conflict_concentration_script_runs_from_repo_root():
    root = Path(__file__).resolve().parents[1]
    script = root / "tools" / "analyze_conflict_concentration.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Analyze concentration" in completed.stdout
