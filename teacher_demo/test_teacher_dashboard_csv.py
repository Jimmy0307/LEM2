"""CI smoke: custom CSV must genuinely run the original LEM2, not just preview splitting."""
from __future__ import annotations
import json
import runpy
from pathlib import Path

ENGINE=Path("docs/research/teacher_dashboard/runtime/engine.py")

def evaluate(payload):
    scope=runpy.run_path(str(ENGINE),init_globals={"__USER_INPUT_JSON__":json.dumps(payload)})
    return json.loads(scope["__USER_RESULT_JSON__"])

def example():
    rows=[]
    for lw in range(1,4):
        for ld in range(1,4):
            for rw in range(1,4):
                for rd in range(1,4):
                    a=lw*ld;b=rw*rd
                    rows.append([str(lw),str(ld),str(rw),str(rd),"B" if a==b else "L" if a>b else "R"])
    return {"columns":["left_weight","left_distance","right_weight","right_distance","class"],
        "rows":rows,"target":"class","seed":42,"clients":0,"split":"HOLDOUT_80_20"}

def main():
    base=example()
    a=evaluate(base)
    assert a["dataset_rows"]==81
    assert a["train_rows"]+a["test_rows"]==81
    assert a["rule_count"]>0
    assert len(a["metrics"])==6 and len(a["cases"])==a["test_rows"]
    assert all(0<=v["accuracy"]<=1 for v in a["metrics"].values())
    assert sum(v["n"] for v in a["classes"])==a["test_rows"]
    assert all(c["row_id"]>=0 for c in a["cases"])
    assert a["provenance"].startswith("CANONICAL_PYTHON")
    full=example();full["split"]="FULL_DATA";b=evaluate(full)
    assert b["train_rows"]==81 and b["test_rows"]==81
    fed=example();fed["clients"]=2;c=evaluate(fed)
    assert len(c["local_rule_counts"])==2
    assert len(c["classes"])>0
    outcomes=a["cases"][0]["outcomes"]
    assert set(outcomes)==set(a["metrics"])
    for policy in outcomes:
        assert outcomes[policy]["error_type"] in {
          "NO_MATCH_FALLBACK_CORRECT","NO_MATCH_FALLBACK_WRONG",
          "TRUE_CLASS_NOT_CANDIDATE","CANDIDATE_SELECTED_CORRECT",
          "CANDIDATE_PRESENT_BUT_SELECTED_WRONG"
        }
    print("TEACHER_DASHBOARD_CSV_CANONICAL_SMOKE=PASS",flush=True)

if __name__=="__main__":
    main()
