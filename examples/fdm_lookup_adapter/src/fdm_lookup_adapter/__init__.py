"""Independent adapter example: categorical exact-match lookup (NOT PRISM)."""
from collections import defaultdict, Counter
import pandas as pd
from federated_decision_making.api import Capabilities, FitRequest, Predictions, validate_request

class LookupModel:
    def __init__(self,features,lookup,default):
        self.features,self.lookup,self.default=features,lookup,default
    def predict(self,X: pd.DataFrame) -> Predictions:
        if not set(self.features).issubset(X.columns):raise ValueError('missing features')
        labels=[];covered=[];candidates=[]
        for values in X[list(self.features)].astype(str).itertuples(index=False,name=None):
            classes=self.lookup.get(tuple(values),{})
            if classes:
                winning=max(classes.values())
                label=sorted(c for c,n in classes.items() if n==winning)[0]
                labels.append(label);covered.append(True);candidates.append(tuple(sorted(classes)))
            else:
                labels.append(self.default);covered.append(False);candidates.append(())
        return Predictions(labels,covered,candidates)
    def diagnostics(self) -> dict:
        return {'lookup_patterns':len(self.lookup),'rule_semantics':'categorical_exact_match',
                'not_a_prism_implementation':True}

class LookupPlugin:
    @property
    def capabilities(self):
        return Capabilities(algorithm='lookup_example', federated_modes=('CENTRALIZED',),
            supports_rules=True,rule_semantics='CATEGORICAL_LOOKUP_EXAMPLE')
    def fit(self,request: FitRequest) -> LookupModel:
        validate_request(self.capabilities,request)
        lookup=defaultdict(Counter)
        for values in request.train[list(request.features)+[request.target]].astype(str).itertuples(index=False,name=None):
            lookup[values[:-1]][values[-1]]+=1
        all_counts=Counter(request.train[request.target].astype(str))
        best=max(all_counts.values())
        default=sorted(k for k,v in all_counts.items() if v==best)[0]
        return LookupModel(request.features,dict(lookup),default)
