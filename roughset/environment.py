from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Dict, Mapping, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 11)
MAX_PYTHON_EXCLUSIVE = (3, 14)

LOCKED_VERSIONS = {
    "numpy": "2.3.5",
    "pandas": "2.2.3",
    "openpyxl": "3.1.5",
    "xlrd": "2.0.2",
    "ucimlrepo": "0.0.7",
}

DEPENDENCY_PROFILES: Dict[str, Tuple[str, ...]] = {
    "core": ("numpy", "pandas"),
    "xlsx": ("openpyxl",),
    "xls": ("xlrd",),
    "excel": ("openpyxl", "xlrd"),
    "uci": ("ucimlrepo",),
}

REQUIREMENT_FILES = {
    "core": "requirements-core.txt",
    "xlsx": "requirements-excel.txt",
    "xls": "requirements-excel.txt",
    "excel": "requirements-excel.txt",
    "uci": "requirements-uci.txt",
    "full": "requirements-lock.txt",
}


def is_supported_python(version: Sequence[int] | Tuple[int, int] | None = None) -> bool:
    """Return True only for Python versions validated by the canonical dependency lock.

    pandas 2.2.3 has binary-wheel support through Python 3.13.  Python 3.14
    therefore uses a different dependency generation and is intentionally rejected
    here rather than falling back to a local source build.
    """
    if version is None:
        version = sys.version_info[:2]
    major_minor = tuple(int(x) for x in version[:2])
    return MIN_PYTHON <= major_minor < MAX_PYTHON_EXCLUSIVE


def _package_status(package: str) -> Dict[str, object]:
    expected = LOCKED_VERSIONS.get(package)
    try:
        version = metadata.version(package)
    except metadata.PackageNotFoundError:
        return {"installed": False, "version": None, "expected_version": expected, "matches_lock": False if expected else None}
    return {
        "installed": True,
        "version": version,
        "expected_version": expected,
        "matches_lock": (version == expected) if expected else None,
    }


def environment_manifest() -> Dict[str, object]:
    packages = sorted({pkg for values in DEPENDENCY_PROFILES.values() for pkg in values})
    return {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "minimum_supported": f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
            "maximum_supported_exclusive": f"{MAX_PYTHON_EXCLUSIVE[0]}.{MAX_PYTHON_EXCLUSIVE[1]}",
            "supported": is_supported_python(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "packages": {pkg: _package_status(pkg) for pkg in packages},
    }


def _load_config(config_path: Path) -> Mapping[str, object]:
    return json.loads(config_path.read_text(encoding="utf-8-sig"))


def required_profiles_for_config(config_path: Path) -> Tuple[str, ...]:
    config_path = Path(config_path).resolve()
    cfg = _load_config(config_path)
    base = config_path.parent
    input_cfg = dict(cfg.get("input", {}))
    mode = str(input_cfg.get("mode", "AUTO")).upper()
    profiles = {"core"}

    run_local = bool(input_cfg.get("run_local_files", True)) and mode in {"AUTO", "LOCAL"}
    run_uci = bool(input_cfg.get("run_uci_sources", True)) and mode in {"AUTO", "UCI"}

    if run_local:
        local_folder = Path(input_cfg.get("local_folder", "./real_data/local"))
        if not local_folder.is_absolute():
            local_folder = base / local_folder
        if local_folder.exists():
            suffixes = {p.suffix.lower() for p in local_folder.iterdir() if p.is_file()}
            if ".xlsx" in suffixes:
                profiles.add("xlsx")
            if ".xls" in suffixes:
                profiles.add("xls")

    if run_uci:
        sources = Path(input_cfg.get("uci_sources_file", "./real_data/uci_sources.txt"))
        if not sources.is_absolute():
            sources = base / sources
        if sources.exists():
            active = [line.strip() for line in sources.read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith("#")]
            if active:
                profiles.add("uci")

    order = ["core", "xlsx", "xls", "uci"]
    return tuple(name for name in order if name in profiles)


def missing_packages(profiles: Sequence[str]) -> Tuple[str, ...]:
    """Return required packages that are missing OR do not match the locked version."""
    packages = []
    for profile in profiles:
        packages.extend(DEPENDENCY_PROFILES[profile])
    unsatisfied = set()
    for pkg in packages:
        status = _package_status(pkg)
        if not status["installed"] or status.get("matches_lock") is False:
            unsatisfied.add(pkg)
    return tuple(sorted(unsatisfied))


def build_pip_install_command(python_executable: str, requirement_file: Path, project_root: Path) -> list[str]:
    project_root = Path(project_root).resolve()
    requirement_file = Path(requirement_file).resolve()
    cmd = [python_executable, "-m", "pip", "install", "--only-binary=:all:"]
    wheelhouse = project_root / "wheels"
    if wheelhouse.exists() and any(wheelhouse.glob("*.whl")):
        cmd.extend(["--no-index", "--find-links", str(wheelhouse)])
    cmd.extend(["-r", str(requirement_file)])
    return cmd


def install_profiles(profiles: Sequence[str], project_root: Path, python_executable: str | None = None) -> None:
    project_root = Path(project_root).resolve()
    python_executable = python_executable or sys.executable
    files = []
    for profile in profiles:
        req = project_root / REQUIREMENT_FILES[profile]
        if req not in files:
            files.append(req)
    for req in files:
        if not req.exists():
            raise FileNotFoundError(f"Requirement file not found: {req}")
        subprocess.run(build_pip_install_command(python_executable, req, project_root), check=True)


def ensure_for_config(config_path: Path, install: bool = False) -> Dict[str, object]:
    if not is_supported_python():
        raise RuntimeError(
            "Canonical locked environment requires Python 3.11-3.13; "
            f"found {platform.python_version()}. Python 3.14+ is intentionally rejected "
            "because pandas==2.2.3 has no matching Python 3.14 wheel. "
            "Install Python 3.13 x64 (recommended) or place a compatible portable runtime in runtime\\python.exe."
        )
    config_path = Path(config_path).resolve()
    profiles = required_profiles_for_config(config_path)
    missing_before = missing_packages(profiles)
    if install and missing_before:
        install_profiles(profiles, PROJECT_ROOT)
    missing_after = missing_packages(profiles)
    return {
        "required_profiles": list(profiles),
        "missing_before": list(missing_before),
        "missing_after": list(missing_after),
        "environment": environment_manifest(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RoughSet environment checker")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--ensure", action="store_true", help="Install missing dependencies required by the configured inputs")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        result = ensure_for_config(Path(args.config), install=args.ensure)
    except Exception as exc:
        print(f"ENVIRONMENT ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Required profiles:", ", ".join(result["required_profiles"]))
        print("Missing / lock mismatch before:", ", ".join(result["missing_before"]) or "none")
        print("Missing / lock mismatch after:", ", ".join(result["missing_after"]) or "none")
    return 0 if not result["missing_after"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
