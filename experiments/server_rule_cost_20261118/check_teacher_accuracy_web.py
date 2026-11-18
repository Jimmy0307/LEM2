"""Playwright acceptance of combined Teacher Dashboard 109+51+161 accuracy/cost page.

Run after building a local whitelist artifact, not against a stale public Pages site.
"""
from __future__ import annotations

import argparse
import sys
from playwright.sync_api import sync_playwright

def run(base: str) -> None:
    root = base.rstrip("/") + "/"
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.on("pageerror", lambda e: errors.append("JS: " + str(e)[:200]))
        page.goto(root + "research/teacher_dashboard/", wait_until="networkidle")
        assert page.locator("nav a[href='./cost_accuracy/']").count() == 1
        target = root + "research/teacher_dashboard/cost_accuracy/"
        for width in (320, 390, 1366):
            page.set_viewport_size({"width": width, "height": 900})
            response = page.goto(target, wait_until="networkidle")
            assert response and response.status == 200
            page.wait_for_function("document.getElementById('dataStatus').textContent === 'PASS'", timeout=40000)
            assert page.locator("#nDatasets").inner_text() == "109"
            assert page.locator("#tableRows tr").count() == 109
            assert page.locator("#tableRows tr").first.locator("td").count() >= 10
            assert page.locator("#tableRows").inner_text().find("%") >= 0
            page.locator("#regime").select_option("NONIID_01")
            page.locator("#method").select_option("FIRST_MATCH")
            assert page.locator("#nDatasets").inner_text() == "109"
            assert page.locator("#tableRows tr").count() == 109
            page.locator("#cohort").select_option("OPENML")
            assert page.locator("#nDatasets").inner_text() == "51"
            assert page.locator("#tableRows tr").count() == 51
            assert page.locator("#method").input_value() == "M2"
            assert page.locator("#tableRows").inner_text().find("%") >= 0
            page.locator("#cohort").select_option("INVENTORY")
            assert page.locator("#nDatasets").inner_text() == "161"
            assert page.locator("#tableRows tr").count() == 161
            page.locator("#search").fill("adult")
            assert 1 <= int(page.locator("#nDatasets").inner_text()) < 161
            page.locator("#search").fill("")
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if overflow > 1:
                errors.append(f"horizontal overflow {width}px = {overflow}px")
            print(f"width={width} PMLB=109 OpenML=51 inventory=161 overflow={overflow}")
        browser.close()
    if errors:
        raise AssertionError("; ".join(errors))
    print("TEACHER_ACCURACY_WEB_PASS")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    args = ap.parse_args()
    try:
        run(args.base)
    except Exception as e:
        print("TEACHER_ACCURACY_WEB_FAIL", str(e))
        sys.exit(1)
