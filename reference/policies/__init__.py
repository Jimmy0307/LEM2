"""Separated teaching/reference versions of six Prediction Policies.

The first four are literature-grounded baselines. ``POPULATION_STANDARD`` and
``POPULATION_GLOBAL`` are project-defined experimental variants added from the
2026-10-22 research meeting. These modules are reference-only and are not
imported by the production runtime.
"""

from .first_match import predict_first_match
from .simple_voting import predict_simple_voting
from .standard_voting import predict_standard_voting
from .global_strength import predict_global_strength
from .population_standard import predict_population_standard
from .population_global import predict_population_global

__all__ = [
    "predict_first_match",
    "predict_simple_voting",
    "predict_standard_voting",
    "predict_global_strength",
    "predict_population_standard",
    "predict_population_global",
]
