from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_environment_manifest_reports_python_and_package_versions():
    from roughset.environment import environment_manifest

    manifest = environment_manifest()
    assert manifest["python"]["version"]
    assert manifest["python"]["executable"]
    assert manifest["packages"]["numpy"]["installed"] is True
    assert manifest["packages"]["pandas"]["installed"] is True
    assert "version" in manifest["packages"]["numpy"]


def test_dependency_profiles_distinguish_core_excel_and_uci():
    from roughset.environment import DEPENDENCY_PROFILES

    assert DEPENDENCY_PROFILES["core"] == ("numpy", "pandas")
    assert "openpyxl" in DEPENDENCY_PROFILES["excel"]
    assert "xlrd" in DEPENDENCY_PROFILES["excel"]
    assert DEPENDENCY_PROFILES["uci"] == ("ucimlrepo",)


def test_environment_files_exist_and_lock_exact_versions():
    for name in [
        "requirements-core.txt",
        "requirements-excel.txt",
        "requirements-uci.txt",
        "requirements-lock.txt",
        "setup_environment.bat",
        "check_environment.bat",
    ]:
        assert (ROOT / name).exists(), name

    lock_lines = [
        line.strip()
        for line in (ROOT / "requirements-lock.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lock_lines
    assert all("==" in line for line in lock_lines)
    assert any(line.startswith("numpy==") for line in lock_lines)
    assert any(line.startswith("pandas==") for line in lock_lines)


def test_run_bat_uses_setup_and_does_not_require_optional_adapters_upfront():
    text = (ROOT / "run.bat").read_text(encoding="utf-8").lower()
    assert "setup_environment.bat" in text
    assert "check_environment.bat" in text
    # Optional adapters are checked on demand by Python/source type, not mandatory for every run.
    assert 'import numpy,pandas,openpyxl,xlrd,ucimlrepo' not in text


def test_runtime_placeholder_documents_portable_python_option():
    path = ROOT / "runtime" / "README.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8").lower()
    assert "python.exe" in text
    assert "portable" in text

def test_required_profiles_are_inferred_from_current_inputs(tmp_path):
    from roughset.environment import required_profiles_for_config

    local = tmp_path / 'real_data' / 'local'
    local.mkdir(parents=True)
    (local / 'a.csv').write_text('x,class\n1,A\n', encoding='utf-8')
    uci_file = tmp_path / 'real_data' / 'uci_sources.txt'
    uci_file.write_text('# none\n', encoding='utf-8')
    config = {
        'input': {
            'mode': 'AUTO',
            'local_folder': './real_data/local',
            'uci_sources_file': './real_data/uci_sources.txt',
            'run_local_files': True,
            'run_uci_sources': True,
        }
    }
    config_path = tmp_path / 'config.json'
    config_path.write_text(json.dumps(config), encoding='utf-8')
    assert required_profiles_for_config(config_path) == ('core',)

    (local / 'b.xlsx').write_bytes(b'placeholder')
    uci_file.write_text('44\n', encoding='utf-8')
    assert required_profiles_for_config(config_path) == ('core', 'xlsx', 'uci')

def test_pip_command_prefers_local_wheelhouse_when_present(tmp_path):
    from roughset.environment import build_pip_install_command

    wheels = tmp_path / 'wheels'
    wheels.mkdir()
    (wheels / 'dummy-1.0-py3-none-any.whl').write_bytes(b'not-a-real-wheel')
    req = tmp_path / 'requirements-core.txt'
    req.write_text('numpy==2.3.5\n', encoding='utf-8')
    cmd = build_pip_install_command('python.exe', req, tmp_path)
    assert '--no-index' in cmd
    assert '--find-links' in cmd
    assert str(wheels) in cmd

def test_environment_manifest_marks_supported_python():
    from roughset.environment import environment_manifest
    manifest = environment_manifest()
    assert manifest['python']['minimum_supported'] == '3.11'
    assert manifest['python']['supported'] is True

def test_runtime_lock_constant_matches_lock_file():
    from roughset.environment import LOCKED_VERSIONS
    lock = {}
    for line in (ROOT / 'requirements-lock.txt').read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        name, version = line.split('==', 1)
        lock[name] = version
    assert LOCKED_VERSIONS == lock


def test_environment_manifest_reports_lock_compliance_for_core():
    from roughset.environment import environment_manifest
    manifest=environment_manifest()
    assert manifest['packages']['numpy']['expected_version'] == '2.3.5'
    assert manifest['packages']['numpy']['matches_lock'] is True
    assert manifest['packages']['pandas']['matches_lock'] is True

def test_ensure_install_uses_package_root_not_external_config_folder(tmp_path, monkeypatch):
    import roughset.environment as env

    cfg = tmp_path / 'external-config.json'
    cfg.write_text(json.dumps({'input': {'run_local_files': False, 'run_uci_sources': False}}), encoding='utf-8')
    calls=[]
    states=iter([('numpy',), ()])
    monkeypatch.setattr(env, 'missing_packages', lambda profiles: next(states))
    monkeypatch.setattr(env, 'install_profiles', lambda profiles, project_root, python_executable=None: calls.append(Path(project_root)))
    env.ensure_for_config(cfg, install=True)
    assert calls == [ROOT]


def test_locked_environment_rejects_python_314_but_accepts_313():
    from roughset.environment import is_supported_python, MAX_PYTHON_EXCLUSIVE

    assert MAX_PYTHON_EXCLUSIVE == (3, 14)
    assert is_supported_python((3, 11)) is True
    assert is_supported_python((3, 13)) is True
    assert is_supported_python((3, 14)) is False
    assert is_supported_python((3, 15)) is False


def test_setup_bat_prefers_supported_python_minor_versions_and_never_uses_unqualified_py3():
    text = (ROOT / "setup_environment.bat").read_text(encoding="utf-8").lower()
    assert "py -3.13 -m venv" in text
    assert "py -3.12 -m venv" in text
    assert "py -3.11 -m venv" in text
    assert 'py -3 -m venv ".venv"' not in text


def test_setup_bat_rebuilds_existing_venv_when_runtime_is_outside_locked_range():
    text = (ROOT / "setup_environment.bat").read_text(encoding="utf-8").lower()
    assert 'rmdir /s /q ".venv"' in text
    assert "python 3.11-3.13" in text


def test_python_side_installer_refuses_source_builds_for_locked_dependencies(tmp_path):
    from roughset.environment import build_pip_install_command

    req = tmp_path / 'requirements-core.txt'
    req.write_text('numpy==2.3.5\npandas==2.2.3\n', encoding='utf-8')
    cmd = build_pip_install_command('python.exe', req, tmp_path)
    assert '--only-binary=:all:' in cmd


def test_python_313_helper_exists_and_uses_winget_without_removing_python_314():
    path = ROOT / 'install_python_313.bat'
    assert path.exists()
    text = path.read_text(encoding='utf-8').lower()
    assert 'python.python.3.13' in text
    assert 'winget install' in text
    assert 'does not remove python 3.14' in text
