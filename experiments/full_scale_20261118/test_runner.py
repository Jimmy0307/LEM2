import time
from experiments.full_scale_20261118.runner import invoke_with_deadline, collect_events


def _slow():
    time.sleep(1)


def _raise():
    raise MemoryError("synthetic memory failure")


def test_model_deadline_is_enforced():
    result = invoke_with_deadline(_slow, (), 0.05)
    assert result["status"] == "TIMEOUT"


def test_memory_failure_is_recorded():
    result = invoke_with_deadline(_raise, (), 5)
    assert result["status"] == "MEMORY_ERROR"
    assert "synthetic memory failure" in result["error"]


def test_missing_configurations_are_reported_with_source_failure():
    events = [{"kind": "source_failure", "dataset": "UCI20:iris", "status": "HTTPError", "error": "503"}]
    rows, timings, registry, ladder, failures = collect_events(["UCI20:iris"], [1001], events)
    assert not rows and not timings and not registry and not ladder
    assert len(failures) == 4
    assert all(f["status"] == "HTTPError" and "503" in f["error"] for f in failures)


def test_scenario_slices_only_expect_the_requested_configuration():
    events = [{"kind": "source_failure", "dataset": "A", "status": "HTTPError", "error": "503"}]
    _, _, _, _, failures = collect_events(["A"], [1001], events, scenarios=["FED_IID"])
    assert len(failures) == 1
    assert failures[0]["scenario"] == "FED_IID"


def test_ladder_model_timing_is_preserved():
    event = {"kind": "ladder", "dataset": "A", "scenario": "FED_IID", "scale": "1800",
             "scale_rows": 1800, "scale_used_rows": 1790, "dropped_classes": {"rare": 10},
             "rows": [{"selection_policy": "FIRST_MATCH"}], "timing": {"wall_seconds": 3.5}}
    _, timings, _, ladder, _ = collect_events(["A"], [1001], [event], scenarios=["FED_IID"])
    assert timings[0]["phase"] == "SCALE_LADDER"
    assert timings[0]["wall_seconds"] == 3.5
    assert ladder[0]["scale_used_rows"] == 1790
