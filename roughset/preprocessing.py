from __future__ import annotations
from typing import Dict, List, Mapping, Optional, Sequence
import numpy as np
import pandas as pd
from .schema import clean_column_name


def _clean_name_list(values):
    return [clean_column_name(v) for v in values] if values else []


def _is_numeric_like(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    return bool(pd.to_numeric(series, errors="coerce").notna().all())


def detect_feature_types(df, features, continuous_columns=None, categorical_columns=None, unique_numeric_threshold=10):
    features = [clean_column_name(f) for f in features]
    continuous_override = set(_clean_name_list(continuous_columns))
    categorical_override = set(_clean_name_list(categorical_columns))
    overlap = continuous_override & categorical_override
    if overlap:
        raise ValueError(f"Columns cannot be both continuous and categorical: {sorted(overlap)}")
    unknown = (continuous_override | categorical_override) - set(features)
    if unknown:
        raise ValueError(f"Type override columns are not selected features: {sorted(unknown)}")
    continuous=[]; categorical=[]
    for feature in features:
        if feature in continuous_override:
            continuous.append(feature)
        elif feature in categorical_override:
            categorical.append(feature)
        elif _is_numeric_like(df[feature]) and df[feature].nunique() > unique_numeric_threshold:
            continuous.append(feature)
        else:
            categorical.append(feature)
    return continuous, categorical


def _bin_labels(n_bins: int) -> List[str]:
    if n_bins < 2: raise ValueError("n_bins must be >= 2")
    if n_bins == 3: return ["Low", "Medium", "High"]
    return [f"Bin_{i}" for i in range(1, n_bins+1)]


def fit_shared_preprocessor(clients: Mapping[str,pd.DataFrame], features: Sequence[str], target_col: str, continuous_columns: Sequence[str], categorical_columns: Sequence[str], n_bins: int=3):
    features=list(features); continuous=list(continuous_columns); categorical=list(categorical_columns)
    if set(continuous) | set(categorical) != set(features) or set(continuous) & set(categorical):
        raise ValueError("Every feature must be typed exactly once.")
    labels=_bin_labels(n_bins)
    local_min_max={}; global_min_max={}; bin_edges={}; bin_labels={}
    for client_name, client_df in clients.items():
        local_min_max[client_name]={}
        for feature in continuous:
            numeric=pd.to_numeric(client_df[feature], errors="coerce")
            if numeric.isna().any(): raise ValueError(f"Continuous column '{feature}' has non-numeric values.")
            local_min_max[client_name][feature]={"min":float(numeric.min()),"max":float(numeric.max())}
    for feature in continuous:
        lo=min(stats[feature]["min"] for stats in local_min_max.values()); hi=max(stats[feature]["max"] for stats in local_min_max.values())
        global_min_max[feature]={"min":lo,"max":hi}
        if np.isclose(lo,hi):
            bin_edges[feature]=np.array([lo-0.5,hi+0.5],dtype=float); bin_labels[feature]=["Constant"]
        else:
            bin_edges[feature]=np.linspace(lo,hi,n_bins+1); bin_labels[feature]=list(labels)
    condition_columns=[f"{f}_bin" if f in continuous else f for f in features]
    return {"features":features,"condition_columns":condition_columns,"target":target_col,"continuous_columns":continuous,"categorical_columns":categorical,"n_bins":n_bins,"local_min_max":local_min_max,"global_min_max":global_min_max,"bin_edges":bin_edges,"bin_labels":bin_labels}


def apply_preprocessor(df, prep, target_col):
    out=df.copy()
    for feature in prep["categorical_columns"]:
        out[feature]=out[feature].astype(str).str.strip()
    for feature in prep["continuous_columns"]:
        values=pd.to_numeric(out[feature],errors="coerce")
        if values.isna().any(): raise ValueError(f"Continuous column '{feature}' contains non-numeric values.")
        edges=np.asarray(prep["bin_edges"][feature],dtype=float); labels=prep["bin_labels"][feature]
        clipped=values.clip(lower=edges[0],upper=edges[-1])
        out[f"{feature}_bin"]=pd.cut(clipped,bins=edges,labels=labels,include_lowest=True,right=True).astype(str)
    out[target_col]=out[target_col].astype(str).str.strip()
    return out
