"""Negative-control baseline: class majority, not a rule learner."""
from __future__ import annotations
import pandas as pd
from federated_decision_making.api import Capabilities, FitRequest, Predictions, validate_request


class MajorityModel:
    def __init__(self, label):
        self.label = label
    def predict(self, X: pd.DataFrame) -> Predictions:
        return Predictions(labels=[self.label] * len(X))
    def diagnostics(self) -> dict:
        return {'n_rules': None, 'prediction_semantics': 'MAJORITY_CLASS', 'rule_coverage': None}


class MajorityPlugin:
    @property
    def capabilities(self):
        return Capabilities(algorithm='majority', federated_modes=('CENTRALIZED', 'FED_IID', 'FED_A05', 'FED_A01'))
    def fit(self, request: FitRequest) -> MajorityModel:
        validate_request(self.capabilities, request)
        counts = request.train[request.target].astype(str).value_counts()
        # deterministic tie: lexical minimum
        score = int(counts.max())
        cls = sorted(str(k) for k, v in counts.items() if int(v) == score)[0]
        return MajorityModel(cls)
