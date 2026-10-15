"""Record Python/package versions, config and SHA-256 of source/tests as JSON."""
from __future__ import annotations
import hashlib, json, platform, subprocess, sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__ == "__main__":
    out = Path(sys.argv[1])
    src = sorted(ROOT.glob("roughset/*.py")) + [ROOT / "main.py", ROOT / "config.json"]
    tests = sorted(ROOT.glob("tests/*.py"))
    pkgs = {}
    for name in ["numpy", "pandas", "openpyxl", "xlrd", "ucimlrepo", "pytest"]:
        try: pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError: pkgs[name] = None
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    state = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_head": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "git_status_porcelain": git("status", "--porcelain"),
        "python": sys.version, "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": pkgs,
        "config": json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig")),
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in src},
        "test_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in tests},
        "reference_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / "reference").glob("*.py"))},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: state[k] for k in ("timestamp_utc", "git_head", "python", "packages")}, indent=1))
