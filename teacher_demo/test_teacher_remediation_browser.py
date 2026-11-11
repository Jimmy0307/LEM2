"""Real Chromium quality gate: ranking, exact triage, Hayes protocols, responsive."""
from __future__ import annotations
import http.server
import socketserver
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

class Reuse(socketserver.ThreadingTCPServer):allow_reuse_address=True
def main():
    root=Path("docs").resolve()
    h=lambda *args,**kw:http.server.SimpleHTTPRequestHandler(*args,directory=str(root),**kw)
    server=Reuse(("127.0.0.1",8779),h)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            b=p.chromium.launch(channel="chrome",headless=True,args=["--no-sandbox"])
            page=b.new_page(viewport={"width":1420,"height":960},device_scale_factor=1)
            errs=[]
            page.on("pageerror",lambda x:errs.append(str(x)))
            page.goto("http://127.0.0.1:8779/research/teacher_dashboard/",wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            print("DEBUG_PAGE_ERRORS",errors,flush=True)
            print("DEBUG_HEALTH",page.locator("#remediationHealth").inner_text(),flush=True)
            print("DEBUG_BEST",page.locator("#bestKpis").inner_text()[:800],flush=True)
            print("DEBUG_ROWS",page.locator("#bestRows tr").count(),flush=True)
            page.wait_for_function("document.querySelectorAll('#bestRows tr').length===10",timeout=20000)
            page.wait_for_function("document.querySelectorAll('#triageConflictTable tr').length===3",timeout=60000)
            page.wait_for_function("document.querySelectorAll('#protocolRows tr').length===5",timeout=60000)
            page.wait_for_function("document.querySelectorAll('#seedGridLive button').length===42",timeout=60000)
            assert "70.54%" in page.locator("#bestKpis").inner_text(),page.locator("#bestKpis").inner_text()
            assert "2,520" in page.locator("#protocolSource").inner_text()
            assert page.locator("#bestScatter circle").count()>=30
            assert page.locator("#triageConflictBar .triage-track").count()==3
            assert "統計" in page.locator("#bestInterpretation").inner_text() or "衝突" in page.locator("#bestInterpretation").inner_text()
            page.locator("#bestMetric").select_option("macro_f1")
            assert "集中式" in page.locator("#bestKpis").inner_text()
            page.locator("#gDataset").select_option("Car Evaluation")
            page.locator("#bestMetric").select_option("balanced_accuracy")
            assert "聯邦 C3" in page.locator("#bestKpis").inner_text(),page.locator("#bestKpis").inner_text()
            page.locator("#gDataset").select_option("ALL")
            page.locator("#gSeed").select_option("27")
            page.locator("#gClient").select_option("3")
            assert "Seed 27" not in page.locator("#bestScope").inner_text() # 42-seed rankings by contract
            assert "組相同因素配置" in page.locator("#triageStatus").inner_text()
            page.locator("#protocolMetric").select_option("accuracy")
            assert page.locator("#protocolRows tr").count()==5
            page.locator("#gSplit").select_option("FULL_DATA")
            assert "80/20 排名" in page.locator("#bestScope").inner_text()
            page.locator("#gSplit").select_option("HOLDOUT_80_20")
            assert not errs,errs
            Path("outputs/audit_browser").mkdir(parents=True,exist_ok=True)
            page.screenshot(path="outputs/audit_browser/report_desktop.png",full_page=True)
            print("REPORT_BEST_CONDITION_TRIAGE_HAYES_DESKTOP_PASS",flush=True)
            page.set_viewport_size({"width":390,"height":844})
            page.screenshot(path="outputs/audit_browser/report_mobile.png",full_page=True)
            assert not errs,errs
            print("REPORT_BEST_CONDITION_TRIAGE_HAYES_MOBILE_PASS",flush=True)
            b.close()
    finally:server.shutdown()
if __name__=="__main__":main()
