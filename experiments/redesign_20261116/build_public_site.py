"""Build the public GitHub Pages artifact from an explicit WHITELIST (never the whole docs/ tree).

What is published:
  docs/index.html                                  site entry (redirects to the dashboard)
  docs/research/teacher_dashboard/**               original dashboard + redesign page + site data copies
  docs/research/full_factorial_20261029/figures/** SVG figures embedded by the dashboard
  docs/research/public_datasets/                   README + two public stratified subsets used by a page
  docs/research/public_datasets_20/**              prepared UCI tables linked from the public20 page

Not published (still in the public Git repository, but not on the website): internal audit notes
(docs/*.md, docs/reviews, docs/superpowers, docs/final_math_audit_*), the 228 MB raw research CSVs
in docs/research/redesign_20261116/, and every other docs/research/* study folder.

Checks (any failure -> exit 1):
  1. every redesign site CSV equals the research table of the same name (LF-canonical SHA-256)
     and the hash recorded in REDESIGN_SITE_MANIFEST.json;
  2. every relative link / asset / fetch() target of the entry page and the redesign page resolves
     inside the artifact (other pages: broken links are reported, not fatal — they pre-date this build);
  3. value-free privacy audit of the artifact: no CRITICAL / HIGH / MEDIUM findings;
  4. artifact size well below the 1 GB Pages limit.

Usage: python -m experiments.redesign_20261116.build_public_site --out _site
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .evidence_index import canonical_sha256
from .public_release_audit import RANK, scan_text

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
WHITELIST = (
    "index.html",
    "research/teacher_dashboard/**",
    "research/full_factorial_20261029/figures/**",
    "research/public_datasets/README.md",
    "research/public_datasets/*_public_stratified_subset.csv",
    "research/public_datasets_20/**",
)
STRICT_PAGES = ("index.html", "research/teacher_dashboard/index.html", "research/teacher_dashboard/redesign/index.html")
SITE_DATA = "research/teacher_dashboard/data/redesign_20261116"
RESEARCH_DATA = DOCS / "research" / "redesign_20261116" / "data"
MAX_BYTES = 300_000_000
REF = re.compile(r'''(?:href|src)\s*=\s*["']([^"'#?]+)|fetch\(\s*(?:D\s*\+\s*)?["'`]([^"'`?$]+)["'`]''')


def tracked() -> set[str]:
    out = subprocess.run(["git", "ls-files", "-z", "docs"], cwd=ROOT, capture_output=True, check=True).stdout
    return {p for p in out.decode("utf-8").split("\0") if p}


def select() -> list[Path]:
    keep = tracked()
    chosen: set[Path] = set()
    for pattern in WHITELIST:
        for path in DOCS.glob(pattern):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and rel in keep:  # only committed files; never local scratch
                chosen.add(path)
    return sorted(chosen)


def add_directory_indexes(out: Path) -> list[str]:
    """Jekyll used to render README.md as a directory index; recreate a plain index where needed."""
    made = []
    for readme in out.rglob("README.md"):
        index = readme.parent / "index.html"
        if index.exists():
            continue
        files = sorted(p.name for p in readme.parent.iterdir() if p.is_file() and p.name != "index.html")
        rel = readme.parent.relative_to(out).as_posix()
        items = "".join(f'<li><a href="./{n}">{n}</a></li>' for n in files)
        index.write_text(
            '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{rel}</title></head><body><main style=\"max-width:900px;margin:auto;padding:16px;"
            'font:15px/1.7 system-ui,sans-serif"><h1>' + rel + "</h1>"
            f"<p>原始研究公開資料（未修改）。說明請看 <a href=\"./README.md\">README.md</a>。</p><ul>{items}</ul>"
            "</main></body></html>\n", encoding="utf-8", newline="\n")
        made.append(rel)
    return made


def check_site_data(out: Path) -> list[str]:
    errors = []
    manifest = json.loads((out / SITE_DATA / "REDESIGN_SITE_MANIFEST.json").read_text(encoding="utf-8"))
    for name, expected in manifest["published_sha256"].items():
        site_file = out / SITE_DATA / name
        if not site_file.exists():
            errors.append(f"site data missing: {name}")
            continue
        actual = canonical_sha256(site_file)
        if actual != expected:
            errors.append(f"site data hash != manifest: {name}")
        research = RESEARCH_DATA / name
        if research.exists() and canonical_sha256(research) != actual:
            errors.append(f"site data differs from research table: {name}")
    return errors


def check_links(out: Path) -> tuple[list[str], list[str]]:
    fatal, warn = [], []
    for page in sorted(out.rglob("*.html")):
        rel_page = page.relative_to(out).as_posix()
        text = page.read_text(encoding="utf-8", errors="ignore")
        data_base = "../data/redesign_20261116/" if rel_page.endswith("redesign/index.html") else ""
        for m in REF.finditer(text):
            target = m.group(1) or m.group(2)
            if not target or target.startswith(("http:", "https:", "mailto:", "data:", "javascript:", "//", "#")):
                continue
            if m.group(2) and data_base and "/" not in target:
                target = data_base + target  # fetch(D + "file.csv") on the redesign page
            resolved = (page.parent / target).resolve()
            ok = resolved.exists() and (resolved.is_file() or (resolved / "index.html").exists())
            try:
                resolved.relative_to(out.resolve())
            except ValueError:
                ok = False
            if not ok:
                (fatal if rel_page in STRICT_PAGES else warn).append(f"{rel_page} -> {target}")
    return fatal, warn


def audit(out: Path) -> list[str]:
    problems = []
    for path in out.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".js", ".json", ".csv", ".md", ".txt", ".svg", ".css"}:
            for (level, name), n in scan_text(path.read_text(encoding="utf-8", errors="ignore")).items():
                if RANK[level] >= 1:
                    problems.append(f"{level} {name} x{n} {path.relative_to(out).as_posix()}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="whitelisted public site builder")
    ap.add_argument("--out", type=Path, default=ROOT / "_site")
    a = ap.parse_args(argv)
    out = a.out.resolve()
    if out == DOCS.resolve() or DOCS.resolve() in out.parents:
        raise SystemExit("--out must not be inside docs/")
    if out.exists():
        shutil.rmtree(out)
    files = select()
    for src in files:
        dst = out / src.relative_to(DOCS)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    indexes = add_directory_indexes(out)
    errors = check_site_data(out)
    fatal, warn = check_links(out)
    privacy = audit(out)
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    published = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(out.rglob("*")) if p.is_file()}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    report = {"git_commit": commit, "whitelist": list(WHITELIST), "files": len(published), "bytes": size,
              "generated_directory_indexes": indexes, "site_data_errors": errors, "strict_link_errors": fatal,
              "nonstrict_broken_links": warn, "privacy_findings_medium_or_higher": privacy, "sha256": published}
    (out / "PUBLICATION_MANIFEST.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"files={len(published)} bytes={size} indexes={indexes}")
    print(f"site_data_errors={len(errors)} strict_link_errors={len(fatal)} nonstrict_broken_links={len(warn)} "
          f"privacy_medium_plus={len(privacy)}")
    for line in errors + fatal + privacy:
        print("  FAIL", line)
    for line in warn[:30]:
        print("  warn", line)
    return 1 if (errors or fatal or privacy or size > MAX_BYTES) else 0


if __name__ == "__main__":
    sys.exit(main())
