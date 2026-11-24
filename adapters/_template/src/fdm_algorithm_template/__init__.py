"""UNIMPLEMENTED skeleton. Do not use as a research result."""
from federated_decision_making.api import Capabilities, FitRequest, Predictions

class _NotImplementedModel:
    def predict(self, X):
        raise NotImplementedError("Replace this with an actual algorithm-specific predictor")

    def diagnostics(self):
        return {"implementation_status": "NOT_IMPLEMENTED"}

class AlgorithmTemplatePlugin:
    @property
    def capabilities(self):
        return Capabilities(
            algorithm="algorithm_template",
            federated_modes=("CENTRALIZED",),
            missing_values="REJECT",
            ordered_decision_required=False,
            supports_rules=False,
            rule_semantics="UNAVAILABLE",
        )

    def fit(self, request: FitRequest):
        raise NotImplementedError("Implement a scientifically valid algorithm before running experiments")
