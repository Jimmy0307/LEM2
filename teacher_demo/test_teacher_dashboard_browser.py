"""End-to-end browser QA for GitHub Pages: report -> evidence -> methods -> figures -> lab.

Run the real Python LEM2 CSV demo in /lab/, never a mock.
"""
from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

def main():
    root=Path("docs").resolve()
    handler=lambda *args,**kwargs:http.server.SimpleHTTPRequestHandler(*args,directory=str(root),**kwargs)
    server=Server(("127.0.0.1",8777),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel="chrome",headless=True,args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":1366,"height":900},locale="zh-TW")
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            base="http://127.0.0.1:8777/"
            report=base+"research/teacher_dashboard/"

            # The Pages root is a report gateway, NOT the CSV model test app.
            page.goto(base,wait_until="domcontentloaded",timeout=45000)
            page.wait_for_url("**/research/teacher_dashboard/",timeout=15000)
            page.wait_for_function("document.querySelectorAll('#seedGridLive button').length===42",timeout=40000)
            assert "37 欄" in page.locator("#dataState").inner_text()
            assert "互動研究流程" in page.title()
            assert page.locator("button[data-stage]").count()==14
            assert page.locator("#seedScatter circle").count()==42
            assert page.locator("#seedDetailTable tr").count()==42
            assert page.locator("#policyCompareRows tr").count()==6
            assert page.locator("#metricDictionary details").count()>=9
            assert page.locator("#triageFlow .triage-step").count()==4
            page.wait_for_function("document.querySelector('#triageFlow').textContent.includes('逐筆匹配紀錄')",timeout=30000)
            assert "正解在候選" in page.locator("#triageFlow").inner_text()
            print("CONFLICT_EXACT_CANDIDATE_INTERSECTION=PASS",flush=True)
            baseline=page.locator("#finalNarrative").inner_text()
            page.locator("#gSeed").select_option("27")
            assert "Seed 27" in page.locator("#finalNarrative").inner_text()
            assert page.locator("#seedGridLive button[aria-pressed='true']").count()==1
            assert page.locator("#seedDetailTable tr.selected-row").count()==1
            assert page.locator("#finalNarrative").inner_text()!=baseline
            page.locator("button[data-stage='union']").click()
            assert "Rule Union" in page.locator("#stagePanel").inner_text()
            page.locator("#traceMetric").select_option("balanced_accuracy")
            assert page.locator("#seedScatter circle").count()==42
            page.locator("#gSystem").select_option("CENTRALIZED")
            assert page.locator("#gClient").is_disabled()
            page.locator("#flowAll").click()
            assert page.locator("#allStages article").count()==14
            print("REPORT_SEED27_LIVE_NUMBERS_PIPELINE_CHARTS=PASS",flush=True)
            print("REPORT_HOME_42SEEDS_NARRATIVE_CHARTS=PASS",flush=True)

            # Conflict semantics are independently explained and demonstrable.
            assert page.locator('a[href="./conflict/"]').count() >= 1
            page.goto(report+"conflict/",wait_until="domcontentloaded")
            assert "沒有 Conflict 時怎麼選" in page.locator("h1").inner_text()
            assert page.locator(".route").count() == 3
            assert "訓練資料的多數類別" in page.locator("#flow").inner_text()
            assert "Good" in page.locator("#tieResult").inner_text()
            page.locator("#majority").select_option("Medium")
            assert "Bad" in page.locator("#tieResult strong").inner_text()
            page.locator("#scoreBad").fill("12")
            assert "Bad" in page.locator("#tieResult strong").inner_text()
            assert "82%" in page.locator("#accOverall").inner_text()
            assert "60%" in page.locator("#accConflict").inner_text()
            page.locator("#correctC").fill("18")
            assert "88%" in page.locator("#accOverall").inner_text()
            assert "90%" in page.locator("#accConflict").inner_text()
            page.locator("#correctC").fill("21")
            assert "—" in page.locator("#accOverall").inner_text()
            page.locator("#correctC").fill("12")
            assert "82%" in page.locator("#accOverall").inner_text()
            assert not errors, errors
            print("CONFLICT_NO_MATCH_NON_CONFLICT_TIE_METRICS=PASS",flush=True)

            # Independent evidence drilldown: complete matrix with real selectors.
            page.goto(report+"evidence/",wait_until="domcontentloaded")
            page.wait_for_function("document.getElementById('validState').textContent.includes('PASS')",timeout=30000)
            assert "8,820" in page.locator("#totalRows").inner_text()
            page.locator("#seed").select_option("27")
            assert "210" in page.locator("#shownRows").inner_text()
            page.locator("#comparison").select_option("GS_STD_BA")
            assert page.locator("#compareRows tr").count()==42
            assert page.locator("#trend polyline").count()>=1
            print("EVIDENCE_FULL_MATRIX_PAIRED_COMPARISON=PASS",flush=True)

            # Decision-oriented leaderboard uses actual 42-seed data, not invented winners.
            page.goto(report+"ranking/",wait_until="domcontentloaded")
            page.wait_for_function("document.getElementById('evidenceStatus').textContent.includes('PASS')",timeout=30000)
            assert page.locator("#rankTable tr").count()>=6
            assert page.locator("#datasetChampions tr").count()==3
            assert page.locator("#frontier circle").count()>=25
            page.locator("#dataset").select_option("Car Evaluation")
            page.locator("#objective").select_option("accuracy")
            assert "90.10%" in page.locator("#rankTable").inner_text()
            page.locator("#dataset").select_option("Hayes-Roth")
            page.wait_for_function("document.querySelectorAll('#hayesResults tr').length>=2",timeout=20000)
            assert "89.74%" in page.locator("#hayesResults").inner_text()
            print("RANKING_ACTUAL_SEEDS_HAYES_EXTERNAL_PROTOCOLS=PASS",flush=True)

            page.goto(report+"methods/",wait_until="domcontentloaded")
            assert "正域" in page.locator("body").inner_text()
            assert "POPULATION_GLOBAL" in page.locator("body").inner_text()
            print("MATH_AND_INDICATOR_REFERENCE=PASS",flush=True)

            page.goto(report+"figures/",wait_until="domcontentloaded")
            assert page.locator("figure img").count()==9
            page.wait_for_function("Array.from(document.querySelectorAll('figure img')).every(x=>x.complete && x.naturalWidth>0)",timeout=20000)
            print("NINE_ORIGINAL_FIGURES=PASS",flush=True)

            # Canonical LEM2 remains a separate route and still runs real Python.
            page.goto(report+"lab/",wait_until="domcontentloaded")
            page.wait_for_function("document.querySelectorAll('#seedGrid .measured').length===42",timeout=40000)
            assert "42/42" in page.locator("#seedStatus").inner_text()
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
            assert "Winner" in page.locator("#caseDetail").inner_text()
            assert page.locator("#downloadModel").is_enabled()
            assert not errors,errors
            print("LAB_REAL_LEM2_SPLIT_POLICIES_CONFLICT=PASS",flush=True)
            print("TEACHER_MULTI_ROUTE_WEBSITE_VERDICT=PASS",flush=True)
            browser.close()
    finally:
        server.shutdown()

if __name__=="__main__":
    main()
