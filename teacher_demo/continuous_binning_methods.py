"""Experimental continuous-feature discretizers for SAME source/split LEM2.

The canonical roughset/preprocessing.py is not modified. The wrapper is
activated in a scoped unittest.mock.patch of roughset.app.fit_shared_preprocessor.
No TEST/Validation values or labels are read to fit edges.

Strategies:
 - EW2/EW3/EW5: canonical equal-width (EW3 = exact original)
 - EQ3/EQ5: DEVELOPMENT pooled quantile boundaries, duplicates collapsed
 - ROBUST3: DEVELOPMENT 1st..99th percentile clipped equal-width edges

Critical limitation: pooled quantiles require access to client values or an
aggregation protocol NOT modeled here; this research implementation is not
privacy-preserving federated quantile estimation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from roughset.preprocessing import fit_shared_preprocessor as canonical_fit

MODES={
 "EQUAL_WIDTH_2":("equal_width",2),
 "EQUAL_WIDTH_3":("equal_width",3),
 "EQUAL_WIDTH_5":("equal_width",5),
 "EQUAL_FREQUENCY_3":("equal_frequency",3),
 "EQUAL_FREQUENCY_5":("equal_frequency",5),
 "ROBUST_WIDTH_3":("robust_width",3),
}

def fit_mode(clients,features,target,continuous,categorical,requested_bins,*,mode):
    if mode not in MODES:raise ValueError("Unknown discretizer mode: "+str(mode))
    method,nbins=MODES[mode]
    base=canonical_fit(clients,features,target,continuous,categorical,nbins)
    assert set(base["continuous_columns"])==set(continuous)
    if method=="equal_width" or not continuous:
        base["research_method"]=mode
        base["quantiles_use_centrally_pooled_client_values"]=False
        return base
    for f in continuous:
        arrays=[pd.to_numeric(table[f],errors="raise").to_numpy(dtype=float)
                for table in clients.values()]
        values=np.concatenate(arrays)
        if not len(values) or not np.isfinite(values).all():
            raise ValueError("Invalid or missing numerical value for "+f)
        lo=float(values.min());hi=float(values.max())
        if np.isclose(lo,hi):
            edges=np.array([lo-.5,hi+.5],dtype=float)
            labels=["Constant"]
        elif method=="equal_frequency":
            edges=np.unique(np.quantile(values,np.linspace(0,1,nbins+1)))
            # Highly tied sparse values can collapse requested quantiles.
            if len(edges)<2:
                edges=np.array([lo-.5,hi+.5],dtype=float)
                labels=["Constant"]
            else:
                labels=[f"QBin_{i+1}" for i in range(len(edges)-1)]
        elif method=="robust_width":
            qlo,qhi=np.quantile(values,[.01,.99])
            if np.isclose(qlo,qhi):
                # Tied 98% percentiles: revert to canonical EW3; never emit
                # invalid zero-width bins or claim robust winsorization occurred.
                edges=np.linspace(lo,hi,nbins+1)
            else:
                edges=np.linspace(float(qlo),float(qhi),nbins+1)
            labels=[f"RBin_{i+1}" for i in range(len(edges)-1)]
        else:raise AssertionError(method)
        assert len(edges)>=2 and np.all(np.diff(edges)>0),(f,mode,edges)
        assert len(labels)==len(edges)-1,(mode,f)
        base["bin_edges"][f]=np.asarray(edges,dtype=float)
        base["bin_labels"][f]=list(labels)
    base["research_method"]=mode
    base["quantiles_use_centrally_pooled_client_values"]=True
    return base
