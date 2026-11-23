"""Stable API v1. Algorithms depend on this, not each other's internals.

Predict must work on features-only frames. Train/val/test never overlap.
Per-row coverage/candidates are optional and explicitly unavailable for models
which do not return rule explanations; never fabricate zeros for N/A.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence, runtime_checkable
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Capabilities:
    algorithm: str
    api_version: str = '1.0'
    federated_modes: tuple[str, ...] = ('CENTRALIZED',)
    missing_values: str = 'REJECT'  # explicit policy, never implicit imputation
    ordered_decision_required: bool = False
    supports_rules: bool = False
    rule_semantics: str = 'UNAVAILABLE'  # not all rules are logical IF-THEN conditions


@dataclass(frozen=True)
class FitRequest:
    train: pd.DataFrame
    clients: Mapping[str, pd.DataFrame]
    features: tuple[str, ...]
    target: str
    mode: str
    seed: int
    options: Mapping[str, object] = field(default_factory=dict)
    # Dataset-specific ordinal criterion directions are intentionally required
    # by future DRSA adapters, not guessed by this API.
    ordinal_directions: Mapping[str, int] = field(default_factory=dict)


@dataclass
class Predictions:
    labels: Sequence[str]
    covered: Sequence[bool] | None = None
    candidates: Sequence[Sequence[str]] | None = None

    def validate(self, n: int):
        if len(self.labels) != n:
            raise ValueError(f'prediction length mismatch: {len(self.labels)} != {n}')
        if self.covered is not None and len(self.covered) != n:
            raise ValueError('coverage length mismatch')
        if self.candidates is not None and len(self.candidates) != n:
            raise ValueError('candidates length mismatch')
        if self.covered is not None and self.candidates is not None:
            for hit, choices in zip(self.covered, self.candidates):
                if bool(hit) != bool(choices):
                    raise ValueError('coverage and candidates disagree')


@runtime_checkable
class FittedPredictor(Protocol):
    def predict(self, X: pd.DataFrame) -> Predictions: ...
    def diagnostics(self) -> dict: ...


@runtime_checkable
class AlgorithmPlugin(Protocol):
    @property
    def capabilities(self) -> Capabilities: ...
    def fit(self, request: FitRequest) -> FittedPredictor: ...


def validate_request(cap: Capabilities, request: FitRequest):
    if cap.api_version != '1.0':
        raise ValueError(f'API version unsupported: {cap.api_version}')
    if request.mode not in cap.federated_modes:
        raise ValueError(f'{cap.algorithm} does not support {request.mode}; refusing silent centralized fallback')
    if not request.features or len(set(request.features)) != len(request.features):
        raise ValueError('features empty or duplicated')
    if request.target in request.features:
        raise ValueError('target leakage')
    required = set(request.features) | {request.target}
    if not required.issubset(request.train.columns):
        raise ValueError('training frame missing required columns')
    if not request.clients or any(not required.issubset(df.columns) for df in request.clients.values()):
        raise ValueError('client schema mismatch')
    if sum(len(c) for c in request.clients.values()) != len(request.train):
        raise ValueError('clients do not partition training rows')
    if cap.ordered_decision_required:
        if not request.ordinal_directions:
            raise ValueError('ordered-criterion directions required (DRSA); not inferred')
        if not request.options.get('decision_order'):
            raise ValueError('decision class order required (DRSA); not inferred')
    if cap.missing_values == 'REJECT':
        for df in [request.train, *request.clients.values()]:
            if df[list(required)].isna().any().any():
                raise ValueError('missing values require an explicit imputation adapter; not yet defined')
