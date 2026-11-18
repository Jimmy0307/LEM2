"""Elementary formal bounds for local-to-global rule certainty.

The Dirichlet-multinomial probability function applies ONLY to an explicit
client-iid label-generation model p_c ~ Dirichlet(alpha), y_i ~ Categorical(p_c).
It does NOT describe roughset.federated.partition_clients, whose mechanism
allocates class-conditional samples across clients using Dirichlet weights.
No distribution-free theorem of B2 accuracy dominance is claimed.
"""
from __future__ import annotations

from math import exp, isfinite, lgamma
from typing import Sequence


def any_pure_client_label_probability(n: int, alphas: Sequence[float]) -> float:
    """P(one class for all n observations), under a Dirichlet-multinomial model.

    Conditional on p ~ Dirichlet(alphas), labels iid Multinomial(p).
    For n>=1: sum_k E[p_k**n]
      = sum_k Gamma(A)*Gamma(a_k+n)/(Gamma(A+n)*Gamma(a_k)).
    Not a probability under the actual class-wise Dirichlet allocation code.
    """
    if int(n) != n or n < 1:
        raise ValueError("n must be a positive integer")
    a = [float(v) for v in alphas]
    if len(a) < 2 or any(not isfinite(v) or v <= 0 for v in a):
        raise ValueError("at least two positive finite Dirichlet parameters")
    total = sum(a)
    ans = sum(exp(lgamma(total) - lgamma(total+n) + lgamma(v+n) - lgamma(v))
              for v in a)
    return min(1.0, max(0.0, ans))


def global_confidence_bounds(local_positive: int, local_matching: int,
                             external_matching_upper: int) -> tuple[float, float]:
    """Sharp bounds given ONLY local support/match and a cap on external matches.

    If remote matches may all be negative, lower bound is
      s_local / (m_local + m_external_max).
    If remote matches may all be positive, upper bound is
      (s_local + m_external_max) / (m_local + m_external_max).
    Assumes total matching denominator>0, fixed rule semantics, no row duplication.
    This says nothing about BA and cannot certify any nontrivial universal
    accuracy benefit for TRUE-rule demotion.
    """
    vals = (local_positive, local_matching, external_matching_upper)
    if any(int(v) != v or v < 0 for v in vals):
        raise ValueError("support/match counts must be nonnegative integers")
    s, m, u = vals
    if s > m or m + u == 0:
        raise ValueError("local support must <= local matching and total matching nonzero")
    lower = s / (m+u)
    upper = (s+u) / (m+u)
    return lower, upper
