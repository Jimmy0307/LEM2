"""Real-browser acceptance check of the public site (local build or the live URL).

Checks:
  * site entry redirects to the original dashboard, which renders without JS errors;
  * the redesign page loads all 10 research tables with data rows (no "載入中" / "資料未發布");
  * the confirmatory and reproducibility status badges are PASS;
  * no horizontal overflow at 320, 390 and 1366 px viewport widths;
  * the redesign data files served by the site have the SHA-256 recorded in REDESIGN_SITE_MANIFEST.json.

Usage:
  python -m experiments.redesign_20261116.site_browser_check --base http://127.0.0.1:8000/
  python -m experiments.redesign_20261116.site_browser_check --base https://jimmy0307.github.io/LEM2/ --channel msedge
Requires: pip install playwright && python -m playwright install chromium   (or --channel msedge/chrome)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

TABLES = ("prevRows", "decRows", "spreadRows", "dzRows", "nzRows", "confRows", "armRows",
          "secondaryDirectionRows", "recRows", "phRows")
BAD_TEXT = ("載入中", "資料未發布", "未通過", "未載入", "正在核對", "尚未完成")
WIDTHS = (320, 390, 1366)
SITE_DATA = "research/teacher_dashboard/data/redesign_20261116/"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "lem2-site-check/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def check_data_hashes(base: str) -> list[str]:
    manifest = json.loads(fetch(base + SITE_DATA + "REDESIGN_SITE_MANIFEST.json").decode("utf-8"))
    errors = []
    for name, expected in manifest["published_sha256"].items():
        body = fetch(base + SITE_DATA + name).replace(b"\r\n", b"\n")
        if hashlib.sha256(body).hexdigest() != expected:
            errors.append(f"served data hash mismatch: {name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="site acceptance check")
    ap.add_argument("--base", required=True, help="site root URL ending with /")
    ap.add_argument("--channel", default=None, help="e.g. msedge or chrome; default bundled chromium")
    a = ap.parse_args(argv)
    base = a.base if a.base.endswith("/") else a.base + "/"
    errors: list[str] = check_data_hashes(base)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=a.channel) if a.channel else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        js_errors: list[str] = []
        page.on("pageerror", lambda e: js_errors.append(str(e)[:200]))
        resp = page.goto(base, wait_until="networkidle")
        if not resp or resp.status >= 400:
            errors.append(f"entry status {resp.status if resp else 'none'}")
        if "teacher_dashboard" not in page.url:
            errors.append(f"entry did not redirect to dashboard: {page.url}")
        if page.locator("nav a[href='./redesign/']").count() == 0:
            errors.append("dashboard nav lacks redesign link")
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(base + "research/teacher_dashboard/redesign/", wait_until="networkidle")
            page.wait_for_function(
                "ids => ids.every(id => { const e = document.getElementById(id); return e && e.querySelectorAll('tr').length > 0 && !/載入中|正在核對/.test(e.textContent); })",
                arg=list(TABLES), timeout=30000)
            for tid in TABLES:
                body = page.locator(f"#{tid}").inner_text()
                rows = page.locator(f"#{tid} tr").count()
                if rows == 0 or any(t in body for t in BAD_TEXT):
                    errors.append(f"{width}px table {tid} not loaded (rows={rows})")
            for badge in ("confBadge", "recBadge"):
                cls = page.locator(f"#{badge}").get_attribute("class") or ""
                if "s-pass" not in cls:
                    errors.append(f"{width}px badge {badge} not PASS")
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if overflow > 1:
                errors.append(f"{width}px horizontal overflow {overflow}px")
            print(f"width={width}: tables={len(TABLES)} overflow={overflow}")
        errors += [f"js error: {e}" for e in js_errors]
        browser.close()
    print("SITE_CHECK", "PASS" if not errors else "FAIL", *errors, sep="\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
