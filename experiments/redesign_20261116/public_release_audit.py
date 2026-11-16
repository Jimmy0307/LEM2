"""Pre-publication privacy / secret audit (prints paths, categories and counts only — never values).

Scans tracked files (default) or a built site folder for:
  CRITICAL  credentials: private keys, GitHub/AWS/Slack/OpenAI-style tokens, credentials in URLs
  HIGH      generic secret assignments (password=, api_key=, token=, secret=) with a literal value
  MEDIUM    e-mail addresses whose domain is not on the public allow-list (personal / company mail)
  LOW       local user-profile paths (C:\\Users\\<name>, /home/<name>), private-network IPs

The allow-list contains only domains that are public by design. Company or personal domains
are deliberately NOT written in this file (it is itself published); they surface as MEDIUM.

Usage:
  python -m experiments.redesign_20261116.public_release_audit                 # tracked files
  python -m experiments.redesign_20261116.public_release_audit --root _site    # built site
  ... --json report.json   (machine-readable, still value-free)
Exit code 1 if any CRITICAL/HIGH finding, or any MEDIUM finding inside --root (a site to publish).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".parquet", ".whl", ".pptx", ".xlsx",
          ".docx", ".woff", ".woff2", ".ttf", ".pyc"}
PUBLIC_EMAIL_DOMAINS = {
    "users.noreply.github.com", "noreply.github.com", "anthropic.com", "example.com", "example.org",
}
PATTERNS = [
    ("CRITICAL", "private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("CRITICAL", "github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("CRITICAL", "aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("CRITICAL", "slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("CRITICAL", "api_key_like", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("CRITICAL", "credential_in_url", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@'\"]+:[^\s/@'\"]{3,}@[^\s/'\"]+")),
    ("HIGH", "secret_assignment", re.compile(
        r"(?i)\b(?:password|passwd|pwd|api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
    ("LOW", "user_profile_path", re.compile(r"(?i)\b[A-Z]:\\{1,2}Users\\{1,2}[A-Za-z0-9._-]+|/home/[a-z_][a-z0-9_-]+/")),
    ("LOW", "private_ip", re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
]
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b")
RANK = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}


def files_to_scan(root: Path | None) -> list[Path]:
    if root is not None:
        return [p for p in sorted(root.rglob("*")) if p.is_file()]
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [ROOT / p for p in out.decode("utf-8").split("\0") if p]


def scan_text(text: str) -> Counter:
    hits: Counter = Counter()
    for level, name, rx in PATTERNS:
        n = len(rx.findall(text))
        if n:
            hits[(level, name)] += n
    for m in EMAIL.finditer(text):
        domain = m.group(1).lower()
        if domain in PUBLIC_EMAIL_DOMAINS or domain.endswith((".png", ".jpg", ".svg", ".js", ".css")):
            continue
        hits[("MEDIUM", "email_non_public_domain")] += 1
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="value-free privacy / secret audit")
    ap.add_argument("--root", type=Path, default=None, help="scan this folder instead of tracked files")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    base = a.root.resolve() if a.root else ROOT
    findings = []
    for path in files_to_scan(a.root):
        if path.suffix.lower() in BINARY or path.stat().st_size > 80_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for (level, name), n in scan_text(text).items():
            findings.append({"path": path.relative_to(base).as_posix(), "risk": level, "category": name, "count": n})
    findings.sort(key=lambda f: (-RANK[f["risk"]], f["path"]))
    summary = Counter((f["risk"], f["category"]) for f in findings)
    for f in findings:
        print(f"{f['risk']:8s} {f['category']:24s} x{f['count']:<5d} {f['path']}")
    print("SUMMARY", {f"{k[0]}:{k[1]}": v for k, v in sorted(summary.items())})
    if a.json:
        a.json.write_text(json.dumps({"scope": str(a.root or "tracked files"), "findings": findings}, indent=1),
                          encoding="utf-8")
    blocking = any(RANK[f["risk"]] >= 2 for f in findings) or (a.root is not None and any(f["risk"] == "MEDIUM" for f in findings))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
