"""LEM2 legacy adapter: API boundary, no modification to frozen algorithm.

Uses existing fit_model and six policy prediction implementation. This adapter
is an OFFLINE pooled-data HFL simulation, not secure federated computation.
"""
from __future__ import annotations
import pandas as pd
from federated_decision_making.api import Capabilities, FitRequest, Predictions, validate_request


class LEM2Model:
    def __init__(self, fm, categorical: list[str], policy: str, variant: str, features: tuple[str, ...]):
        self.fm, self.categorical, self.policy, self.variant, self.features = fm, categorical, policy, variant, features
    def predict(self, X: pd.DataFrame) -> Predictions:
        from fedrs.discretize import apply_cuts
        from fedrs.predict import match_matrix, variant_matrix, resolve_scalable
        if not set(self.features).issubset(X.columns):
            raise ValueError('inference missing required features')
        # Existing apply_cuts writes target even during inference; supply a
        # synthetic placeholder, and NEVER derive training or selection from it.
        source = X[list(self.features)].copy()
        source[self.fm.target] = '__UNKNOWN_TEST_LABEL__'
        transformed = apply_cuts(source, self.fm.cut_model, self.fm.target, self.categorical)
        M = variant_matrix(match_matrix(transformed, self.fm.rules), self.fm.ctx, self.variant)
        labels = resolve_scalable(M, self.fm.ctx, self.policy)
        if len(self.fm.ctx.classes):
            involved = M[:, :].astype(bool)
            decisions = [str(r.decision) for r in self.fm.rules]
            candidates = [tuple(sorted({decisions[j] for j in row.nonzero()[0]})) for row in involved]
            covered = [bool(c) for c in candidates]
        else:
            candidates, covered = [tuple() for _ in range(len(M))], [False] * len(M)
        return Predictions(labels=labels, covered=covered, candidates=candidates)
    def diagnostics(self):
        return {
            'n_rules': len(self.fm.rules), 'rule_variant': self.variant,
            'selection_policy': self.policy, 'federated_semantics': 'OFFLINE_POOLED_DATA_SIMULATION',
            'source': 'fedrs.experiment.fit_model + fedrs.predict.resolve_scalable',
        }


class LEM2Plugin:
    @property
    def capabilities(self):
        return Capabilities(algorithm='lem2', federated_modes=('CENTRALIZED','FED_IID','FED_A05','FED_A01'),
            supports_rules=True, rule_semantics='LEM2_IF_THEN_ANTECEDENT_CLASS')

    def check_engine(self) -> None:
        try:
            import fedrs.experiment
            import roughset.preprocessing
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "LEM2 needs the legacy fedrs/ and roughset/ engine. "
                "Run from a cloned LEM2 repo, install the optional engine package, "
                "or use an externally installed plugin. Missing: " + str(exc)
            ) from exc

    def fit(self, request: FitRequest) -> LEM2Model:
        validate_request(self.capabilities, request)
        self.check_engine()
        from roughset.preprocessing import detect_feature_types
        from fedrs.experiment import fit_model
        from fedrs.predict import POLICIES, RULE_VARIANTS
        policy = str(request.options.get('selection_policy', 'STANDARD_VOTING'))
        variant = str(request.options.get('rule_variant', 'B2_TRUE_AS_FALLBACK'))
        if policy not in POLICIES or variant not in RULE_VARIANTS:
            raise ValueError('unknown LEM2 policy or variant; must be explicit supported value')
        continuous, categorical = detect_feature_types(request.train, request.features,
            continuous_columns=request.options.get('continuous'),
            categorical_columns=request.options.get('categorical'))
        blank = request.train.iloc[:0]
        fm = fit_model(list(request.features), continuous, categorical, request.target,
            request.clients, request.train, blank, blank,
            discretizer=request.options.get('discretizer', 'EQUAL_WIDTH_3'),
            induction=request.options.get('induction', 'CLASSICAL'),
            beta=float(request.options.get('beta', 1.0)))
        return LEM2Model(fm, categorical, policy, variant, request.features)
