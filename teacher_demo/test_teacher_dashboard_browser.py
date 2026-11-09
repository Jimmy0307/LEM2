"""Real-browser test of the teacher dashboard, including a CSV → LEM2 run.

Requires playwright and Chrome on CI; no mock model or fabricated results.
"""
from __future__ import annotations
import contextlib
import http.server
import os
import socketserver
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

class Reuse(socketserver.ThreadingTCPServer):
    allow_reuse_address=True

def main():
    root=Path("docs").resolve()
    handler=lambda *args,**kwargs:http.server.SimpleHTTPRequestHandler(*args,directory=str(root),**kwargs)
    server=Reuse(("127.0.0.1",8777),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel="chrome",headless=True,args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":1366,"height":900},locale="zh-TW")
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            url="http://127.0.0.1:8777/research/teacher_dashboard/"
            page.goto(url,wait_until="domcontentloaded",timeout=45000)
            page.wait_for_function("document.querySelectorAll('#seedGrid .measured').length===42",timeout=35000)
            assert "42/42" in page.locator("#seedStatus").inner_text()
            assert page.locator("#seedChart polyline").count()>=1
            page.locator("#dataset").select_option("Car Evaluation")
            page.locator("#metric").select_option("conflict_case_rate")
            assert page.locator("#seedTable tr").count()==42
            print("BROWSER_SEED_GRID_AND_CHART=PASS",flush=True)
            page.locator("#demoButton").click()
            assert page.locator("#runButton").is_enabled()
            page.locator("#runButton").click()
            page.wait_for_function("!document.getElementById('modelResults').hidden",timeout=240000)
            assert page.locator("#assignmentTable tr").count()==81
            assert page.locator("#assignmentBars .metric").count()>=2
            assert page.locator("#modelPolicies tr").count()==6
            assert page.locator("#modelClasses tr").count()>=2
            assert page.locator("#caseTable tr").count()>=1
            page.locator("#caseFilter").select_option("CONFLICT")
            page.locator("#caseFilter").select_option("ALL")
            page.locator("#caseTable button").first.click()
            assert page.locator("#caseDetail").inner_text().find("Winner")!=-1
            assert page.locator("#downloadModel").is_enabled()
            assert not errors,errors
            print("BROWSER_UPLOAD_LEM2_SIX_POLICIES_CONFLICT=PASS",flush=True)
            browser.close()
    finally:
        server.shutdown()
if __name__=="__main__":
    main()
