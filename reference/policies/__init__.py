"""Separated teaching/reference versions of the four Prediction Policies.

These modules mirror the frozen semantics in ``roughset.evaluation`` but are
not imported by the production runtime.  They exist so each policy can be
reviewed independently by a reader or instructor.
"""

from .first_match import predict_first_match
from .simple_voting import predict_simple_voting
from .standard_voting import predict_standard_voting
from .global_strength import predict_global_strength

__all__ = [
    "predict_first_match",
    "predict_simple_voting",
    "predict_standard_voting",
    "predict_global_strength",
]
