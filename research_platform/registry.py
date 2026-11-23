"""Reserved algorithm names and explicit trusted adapter imports.

This file is the source-level contract stub on the isolated branch.
The complete runnable implementation is in the companion handover ZIP.
"""
from __future__ import annotations
import importlib
from research_platform.api import AlgorithmPlugin, Capabilities

BUILTINS = {
    'lem2': 'research_platform.plugins.lem2:LEM2Plugin',
    'majority': 'research_platform.plugins.majority:MajorityPlugin',
}
PLANNED = {'prism','ripper','drsa'}

def load_algorithm(name: str, external: dict[str,str] | None = None) -> AlgorithmPlugin:
    mapping = dict(BUILTINS)
    for key, value in (external or {}).items():
        if key in BUILTINS:
            raise ValueError('cannot replace a built-in adapter')
        if not key.isidentifier() or value.count(':')!=1:
            raise ValueError('explicit trusted plugin path must be name=module:Class')
        mapping[key] = value
    if name not in mapping:
        if name in PLANNED:
            raise NotImplementedError(f'{name} plugin not installed: do not substitute LEM2')
        raise ValueError(f'Unknown algorithm: {name}')
    module, cls = mapping[name].split(':')
    obj = getattr(importlib.import_module(module),cls)()
    if not isinstance(obj,AlgorithmPlugin):
        raise TypeError('Adapter must implement AlgorithmPlugin')
    cap = obj.capabilities
    if not isinstance(cap,Capabilities) or cap.api_version!='1.0' or cap.algorithm!=name:
        raise ValueError('Invalid adapter capabilities')
    return obj
