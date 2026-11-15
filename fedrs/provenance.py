"""Run provenance: git commit, source hashes, environment, manifests."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--", "fedrs", "experiments"], text=True).strip()
        return sha + ("+UNCOMMITTED_FEDRS_CHANGES" if dirty else "")
    except Exception as exc:  # pragma: no cover - recorded, not hidden
        return f"UNKNOWN({type(exc).__name__})"


def environment() -> Dict[str, Any]:
    import numpy, pandas, scipy
    try:
        import sklearn
        skl = sklearn.__version__
    except Exception:
        skl = None
    return {
        "python": sys.version.split()[0], "platform": platform.platform(),
        "numpy": numpy.__version__, "pandas": pandas.__version__, "scipy": scipy.__version__,
        "sklearn": skl,
    }


def write_manifest(path: Path, payload: Dict[str, Any]) -> None:
    body = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "environment": environment(),
        **payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
