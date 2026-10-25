from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_conflict_concentration_module_runs_from_repo_root():
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "tools.analyze_conflict_concentration", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Analyze concentration" in completed.stdout
