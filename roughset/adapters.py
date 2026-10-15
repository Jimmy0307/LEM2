from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import pandas as pd
from .schema import DatasetSchema, clean_column_name, resolve_schema

KNOWN_UCI_PROFILES = {
    44: {"target": "class", "drop_columns": ["name"], "force_categorical": True},
    19: {"target": "class", "drop_columns": [], "force_categorical": True},
    12: {"target": "class", "drop_columns": [], "force_categorical": True},
}


@dataclass
class DatasetBundle:
    name: str
    frame: pd.DataFrame
    features: List[str]
    target: str
    schema: DatasetSchema
    source: str


def prepare_custom_frame(df: pd.DataFrame, target: str, drop_columns=None, feature_columns=None, name: Optional[str]=None):
    if df is None or len(df)==0: raise ValueError("Input data is empty.")
    out=df.copy(); out.columns=[clean_column_name(c) for c in out.columns]; target=clean_column_name(target)
    if target not in out.columns: raise KeyError(f"Target column '{target}' not found.")
    drop={clean_column_name(c) for c in (drop_columns or [])}; drop.discard(target)
    out=out.drop(columns=[c for c in out.columns if c in drop],errors="ignore")
    if feature_columns:
        features=[clean_column_name(c) for c in feature_columns]
        missing=set(features)-set(out.columns)
        if missing: raise KeyError(f"Requested feature columns not found: {sorted(missing)}")
    else:
        features=[c for c in out.columns if c!=target]
    if not features: raise ValueError("No condition attributes remain after input preparation.")
    selected=out[features+[target]].copy()
    if selected.isna().any().any():
        bad=selected.columns[selected.isna().any()].tolist(); raise ValueError(f"Missing values detected in columns: {bad}")
    return {"key":None,"config":{"name":name or "Custom Dataset","target":target,"drop_columns":sorted(drop),"doi":None,"note":"Custom input"},"dataset":None,"df":selected,"features":features,"target":target}


def load_local_file(path: Path, schema_path: Optional[Path]=None, sheet_name=0) -> DatasetBundle:
    path=Path(path)
    suffix=path.suffix.lower()
    if suffix=='.csv': df=pd.read_csv(path)
    elif suffix in {'.xlsx','.xls'}: df=pd.read_excel(path,sheet_name=sheet_name)
    else: raise ValueError(f"Unsupported local file type: {path.suffix}")
    normalized=df.copy(); normalized.columns=[clean_column_name(c) for c in normalized.columns]
    schema=resolve_schema(normalized,schema_path=schema_path)
    prepared=prepare_custom_frame(normalized,schema.target,drop_columns=schema.ignore,feature_columns=schema.features,name=path.stem)
    return DatasetBundle(path.stem,prepared['df'],prepared['features'],prepared['target'],schema,str(path))


def load_uci_dataset_by_id(uci_id: int, fetcher=None, drop_missing_target: bool = True) -> DatasetBundle:
    if fetcher is None:
        try:
            from ucimlrepo import fetch_ucirepo
        except ImportError as exc:
            raise ImportError("Install ucimlrepo first: pip install ucimlrepo") from exc
        fetcher = fetch_ucirepo
    uci_id = int(uci_id)
    dataset = fetcher(id=uci_id)
    X = dataset.data.features.copy()
    y = dataset.data.targets.copy()
    X.columns = [clean_column_name(c) for c in X.columns]
    profile = KNOWN_UCI_PROFILES.get(uci_id, {})
    for col in profile.get("drop_columns", []):
        X = X.drop(columns=[clean_column_name(col)], errors="ignore")

    if isinstance(y, pd.Series):
        target_name = clean_column_name(profile.get("target") or y.name or "target")
        y = y.to_frame(name=target_name)
    else:
        y = y.copy(); y.columns = [clean_column_name(c) for c in y.columns]
        wanted = clean_column_name(profile.get("target")) if profile.get("target") else None
        if wanted and wanted in y.columns:
            target_name = wanted
        elif y.shape[1] == 1:
            target_name = y.columns[0]
        else:
            raise ValueError(
                f"UCI dataset {uci_id} has {y.shape[1]} target columns; create a local export/schema to choose one explicitly."
            )
    frame = pd.concat([X.reset_index(drop=True), y[[target_name]].reset_index(drop=True)], axis=1)
    if drop_missing_target or profile.get("drop_missing_target", uci_id == 44):
        frame = frame.loc[frame[target_name].notna()].reset_index(drop=True)
    if frame[X.columns.tolist()].isna().any().any():
        bad = frame[X.columns.tolist()].columns[frame[X.columns.tolist()].isna().any()].tolist()
        raise ValueError(f"Missing feature values detected in UCI dataset {uci_id}: {bad}")
    if frame[target_name].isna().any():
        raise ValueError(f"Missing target values detected in UCI dataset {uci_id}.")
    features = list(X.columns)
    metadata = getattr(dataset, "metadata", None)
    name = getattr(metadata, "name", None) or f"UCI_{uci_id}"
    schema = DatasetSchema(
        target=target_name,
        features=features,
        categorical=list(features) if profile.get("force_categorical") else [],
    )
    return DatasetBundle(str(name), frame, features, target_name, schema, f"uci_id:{uci_id}")

