from __future__ import annotations
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]


def _imports(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    out=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.ImportFrom): out.append(n.module or '')
        if isinstance(n,ast.Import): out.extend(a.name for a in n.names)
    return out


def test_core_does_not_import_outer_layers():
    imports=' '.join(_imports(ROOT/'roughset'/'core.py'))
    for forbidden in ['adapters','sources','federated','evaluation','app']:
        assert forbidden not in imports


def test_adapter_does_not_import_lem2_or_reduct():
    imports=' '.join(_imports(ROOT/'roughset'/'adapters.py'))
    assert 'core' not in imports
    assert 'reduct' not in imports


def test_split_and_preprocessing_are_separate_modules():
    assert (ROOT/'roughset'/'splitting.py').exists()
    assert (ROOT/'roughset'/'preprocessing.py').exists()
    assert (ROOT/'roughset'/'schema.py').exists()
    assert (ROOT/'roughset'/'sources.py').exists()


def test_windows_bat_is_path_safe_and_propagates_errors():
    text=(ROOT/'run.bat').read_text(encoding='utf-8').lower()
    assert 'cd /d "%~dp0"' in text
    assert '.venv\\scripts\\python.exe' in text
    assert ('exit /b %run_exit%' in text) or ('exit /b !run_exit!' in text)
    assert 'main.py" --config "config.json"' in text
