"""Offline checks that the image contains a runnable, correctly pinned LEM2 code base."""
import importlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_registry_has_188_datasets_and_both_experiment_modules_import():
    for module in ("experiments.expanded_42seeds_20261120.run", "experiments.protocol_compare_20261128.run"):
        run = importlib.import_module(module)
        _, chosen = run.selected_registry()
        assert len(chosen) == 188


def test_pinned_runtime_versions():
    import numpy
    import pandas
    assert numpy.__version__ == "2.3.5" and pandas.__version__ == "2.2.3"


def test_git_revision_available_for_run_contract():
    rev = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert len(rev) == 40


def test_reference_results_are_bundled():
    for exp in ("expanded", "protocol"):
        files = list((ROOT / "docker" / "reference" / exp).glob("*/seed01__*.json"))
        assert len(files) == 4, exp
        for f in files:
            assert json.loads(f.read_text())["rows"]
