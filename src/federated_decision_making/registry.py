"""Algorithm registry: internal adapters plus Python package entry points.

Only *installed trusted Python code* is loaded; a case JSON cannot specify
an import path and there is never a silent fallback to LEM2.
"""
from __future__ import annotations
import importlib
from importlib.metadata import EntryPoint, entry_points
from .api import AlgorithmPlugin, Capabilities

ENTRY_POINT_GROUP = "federated_decision_making.algorithms"
BUILTINS = {
    "majority": "federated_decision_making.plugins.majority:MajorityPlugin",
    "lem2": "federated_decision_making.plugins.lem2:LEM2Plugin",
}
PLANNED = {"prism", "ripper", "drsa"}

def available_plugins(external: dict[str, str] | None = None):
    result: dict[str, str | EntryPoint] = dict(BUILTINS)
    try:
        installed = entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:  # compatibility with older importlib.metadata API
        installed = entry_points().select(group=ENTRY_POINT_GROUP)
    for ep in installed:
        if ep.name in result:
            raise ValueError(f"duplicate plugin name {ep.name}: cannot override a built-in adapter")
        result[ep.name] = ep
    for name, spec in (external or {}).items():
        if name in result:
            raise ValueError(f"cannot override built-in/installed plugin {name}")
        if not name.isidentifier() or not isinstance(spec, str) or spec.count(":") != 1:
            raise ValueError("trusted --plugin must be ALGO=installed.module:Class")
        result[name] = spec
    return result

def load_algorithm(name: str, external: dict[str, str] | None = None) -> AlgorithmPlugin:
    known = available_plugins(external)
    if name not in known:
        if name in PLANNED:
            raise NotImplementedError(f"{name} adapter not installed; install a plugin exposing {ENTRY_POINT_GROUP}")
        raise ValueError(f"Unknown algorithm: {name}; installed={sorted(known)}")
    spec = known[name]
    if isinstance(spec, EntryPoint):
        cls = spec.load()
    else:
        module_name, attr = spec.split(":")
        cls = getattr(importlib.import_module(module_name), attr)
    plugin = cls()
    if not isinstance(plugin, AlgorithmPlugin):
        raise TypeError(f"{name}: algorithm does not implement API v1")
    cap = plugin.capabilities
    if not isinstance(cap, Capabilities) or cap.api_version != "1.0" or cap.algorithm != name:
        raise ValueError(f"{name}: capability contract mismatch")
    return plugin

def plugin_code_fingerprint(name: str, external: dict[str, str] | None = None) -> str:
    """Versioned fingerprints prevent stale checkpoint reuse after adapter upgrades."""
    import hashlib, inspect, json, sys
    plugin = load_algorithm(name, external)
    cls = type(plugin)
    module=sys.modules[cls.__module__]
    source=getattr(module,'__file__',None)
    loader=getattr(module,'__loader__',None)
    try:
        code=loader.get_data(source) if source and hasattr(loader,'get_data') else inspect.getsource(module).encode()
    except (OSError, IOError, TypeError):
        code=inspect.getsource(cls).encode()
    payload = json.dumps({"name": name, "module": cls.__module__, "class": cls.__qualname__,
                          "capabilities": repr(plugin.capabilities)}, sort_keys=True)
    return hashlib.sha256(payload.encode() + code).hexdigest()
