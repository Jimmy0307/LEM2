"""Isolated model execution with explicit resource-failure outcomes."""
import multiprocessing as mp
import time
import traceback


def _child(connection, fn, args):
    try:
        connection.send({"status": "OK", "value": fn(*args)})
    except MemoryError as exc:
        connection.send({"status": "MEMORY_ERROR", "error": f"{type(exc).__name__}: {exc}"})
    except BaseException as exc:
        connection.send({"status": type(exc).__name__, "error": f"{exc}\n{traceback.format_exc(limit=8)}"})
    finally:
        connection.close()


def invoke_with_deadline(fn, args, timeout_seconds):
    ctx = mp.get_context("fork")
    receive, send = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(send, fn, args))
    proc.start()
    send.close()
    deadline = time.monotonic() + timeout_seconds
    try:
        while True:
            if receive.poll(min(0.1, max(0, deadline-time.monotonic()))):
                try:
                    result = receive.recv()
                except EOFError:
                    proc.join()
                    return {"status": "PROCESS_KILLED_OR_OOM", "error": f"exit code {proc.exitcode}"}
                proc.join()
                return result
            if time.monotonic() >= deadline:
                proc.kill()
                proc.join()
                return {"status": "TIMEOUT", "error": f"exceeded {timeout_seconds:.2f} seconds"}
            if not proc.is_alive():
                proc.join()
                return {"status": "PROCESS_KILLED_OR_OOM", "error": f"exit code {proc.exitcode}"}
    finally:
        receive.close()
        if proc.is_alive():
            proc.kill()
            proc.join()


def collect_events(datasets, seeds, events, scenarios=None):
    """Materialize finished configurations and explicitly account for gaps."""
    from fedrs.predict import POLICIES
    from experiments.full_scale_20261118.model import SCENARIOS
    scenarios = tuple(scenarios) if scenarios is not None else SCENARIOS
    if not scenarios or not set(scenarios).issubset(SCENARIOS):
        raise ValueError("Invalid scenario slice")
    expected = {(d, int(seed), scenario) for d in datasets for seed in seeds for scenario in scenarios}
    models, model_failures, source_failures = {}, {}, {}
    registry, ladder, failures, timings = [], [], [], []
    for event in events:
        kind = event["kind"]
        if kind == "registry":
            registry.append(event["record"])
        elif kind == "source_failure":
            source_failures[event["dataset"]] = event
        elif kind in ("model", "model_failure"):
            key = (event["dataset"], int(event["seed"]), event["scenario"])
            if key not in expected or key in models or key in model_failures:
                raise ValueError(f"Unexpected or duplicate configuration event: {key}")
            (models if kind == "model" else model_failures)[key] = event
        elif kind == "ladder":
            for row in event["rows"]:
                ladder.append({**row, "scenario": event["scenario"], "scale": event["scale"],
                               "scale_rows": event["scale_rows"], "scale_used_rows": event["scale_used_rows"],
                               "dropped_classes": str(event["dropped_classes"])})
            if event.get("timing"):
                timings.append({**event["timing"], "phase": "SCALE_LADDER", "scale": event["scale"]})
        elif kind == "ladder_failure":
            failures.append({**event, "phase": "SCALE_LADDER"})
        elif kind == "checkpoint_failure":
            failures.append({**event, "phase": "CHECKPOINT"})
        elif kind == "source_retry_failure":
            failures.append({**event, "phase": "SOURCE_RETRY"})
        elif kind == "metadata_failure":
            failures.append({**event, "phase": "REGISTRY"})
        else:
            raise ValueError(f"Unexpected event kind {kind}")
    rows = []
    for key in sorted(expected):
        dataset, seed, scenario = key
        if key in models:
            result = models[key]["record"]
            actual = result["rows"]
            for variant in ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK"):
                subset = [r for r in actual if r["rule_variant"] == variant]
                if len(subset) != len(POLICIES) or {r["selection_policy"] for r in subset} != set(POLICIES):
                    raise ValueError(f"Invalid policy results for {key} {variant}")
            rows.extend(actual)
            timings.append(result["timing"])
        else:
            failure = model_failures.get(key) or source_failures.get(dataset) or {}
            failures.append(dict(dataset=dataset, seed=seed, scenario=scenario,
                                 phase="MODEL" if key in model_failures else "SOURCE" if failure else "SHARD",
                                 status=failure.get("status", "NOT_RUN_SHARD_TERMINATED"),
                                 error=failure.get("error", "No completed model event before shard stopped")))
    return rows, timings, registry, ladder, failures
