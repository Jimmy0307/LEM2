from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference" / "lem2_control_panel_v6_1_reference.py"

@pytest.fixture(scope="session")
def ref():
    spec = importlib.util.spec_from_file_location("v61_reference", REFERENCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
