"""Stable algorithm-independent research API v1; implementation bundles are versioned separately."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence, runtime_checkable
import pandas as pd

@dataclass(frozen=True)
class Capabilities:
    algorithm: str
    api_version: str = "1.0"
    federated_modes: tuple[str, ...] = ("CENTRALIZED",)
    missing_values: str = "REJECT"
    ordered_decision_required: bool = False
    supports_rules: bool = False
    rule_semantics: str = "UNAVAILABLE"

@dataclass(frozen=True)
class FitRequest:
    train: pd.DataFrame
    clients: Mapping[str, pd.DataFrame]
    features: tuple[str, ...]
    target: str
    mode: str
    seed: int
    options: Mapping[str, object] = field(default_factory=dict)
    ordinal_directions: Mapping[str, int] = field(default_factory=dict)

@dataclass
class Predictions:
    labels: Sequence[str]
    covered: Sequence[bool] | None = None
    candidates: Sequence[Sequence[str]] | None = None

    def validate(self, n: int):
        if len(self.labels) != n:
            raise ValueError("prediction length mismatch")
        if self.covered is not None and len(self.covered) != n:
            raise ValueError("coverage length mismatch")
        if self.candidates is not None and len(self.candidates) != n:
            raise ValueError("candidates length mismatch")
        if self.covered is not None and self.candidates is not None:
            for hit, choices in zip(self.covered, self.candidates):
                if bool(hit) != bool(choices):
                    raise ValueError("coverage and candidates disagree")

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
    if cap.api_version != "1.0":
        raise ValueError("unsupported API version")
    if request.mode not in cap.federated_modes:
        raise ValueError(f"{cap.algorithm} does not support {request.mode}; refusing LEM2 fallback")
    if not request.features or len(set(request.features)) != len(request.features):
        raise ValueError("features empty/duplicated")
    if request.target in request.features:
        raise ValueError("target leakage")
    req = set(request.features) | {request.target}
    if not req.issubset(request.train.columns) or not request.clients:
        raise ValueError("invalid train/client schema")
    if any(not req.issubset(df.columns) for df in request.clients.values()):
        raise ValueError("client schema mismatch")
    if sum(len(c) for c in request.clients.values()) != len(request.train):
        raise ValueError("client partitions do not cover training rows")
    if cap.ordered_decision_required:
        if not request.ordinal_directions:
            raise ValueError("DRSA ordered criterion directions required")
        if not request.options.get("decision_order"):
            raise ValueError("DRSA ordered decision classes required")
    if cap.missing_values == "REJECT":
        for df in [request.train, *request.clients.values()]:
            if df[list(req)].isna().any().any():
                raise ValueError("missing values require explicit validated preprocessing")
