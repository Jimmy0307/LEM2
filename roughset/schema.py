from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json
import pandas as pd


def clean_column_name(name) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True)
class DatasetSchema:
    target: str
    features: List[str]
    continuous: List[str] = field(default_factory=list)
    categorical: List[str] = field(default_factory=list)
    ordinal: Dict[str, List[str]] = field(default_factory=dict)
    ignore: List[str] = field(default_factory=list)


def _load_schema(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid schema JSON: {path}: {exc}") from exc


def resolve_schema(df: pd.DataFrame, schema_path: Optional[Path] = None) -> DatasetSchema:
    cols = [clean_column_name(c) for c in df.columns]
    if len(set(cols)) != len(cols):
        raise ValueError("Column names collide after normalization.")

    if schema_path is not None:
        raw = _load_schema(Path(schema_path))
        if not raw.get("target"):
            raise ValueError("Schema requires 'target'.")
        target = clean_column_name(raw["target"])
        continuous = [clean_column_name(x) for x in raw.get("continuous", [])]
        categorical = [clean_column_name(x) for x in raw.get("categorical", [])]
        ordinal = {
            clean_column_name(k): [str(v) for v in values]
            for k, values in (raw.get("ordinal", {}) or {}).items()
        }
        ignore = [clean_column_name(x) for x in raw.get("ignore", [])]
    else:
        candidates = [c for c in cols if c in {"target", "class", "label", "decision"}]
        if len(candidates) != 1:
            raise ValueError(
                "target column cannot be determined safely; provide a schema JSON with 'target'."
            )
        target = candidates[0]
        continuous, categorical, ordinal, ignore = [], [], {}, []

    if target not in cols:
        raise ValueError(f"target column '{target}' not found.")
    roles = continuous + categorical + list(ordinal) + ignore
    if len(set(roles)) != len(roles):
        raise ValueError("A column cannot appear in multiple schema roles.")
    unknown = set(roles) - set(cols)
    if unknown:
        raise ValueError(f"Schema columns not found: {sorted(unknown)}")
    if target in roles:
        raise ValueError("Target cannot also be a feature or ignored column.")

    features = [c for c in cols if c != target and c not in set(ignore)]
    # Features omitted from explicit type roles remain untyped here and are
    # handled by the preprocessing layer's conservative auto detection.
    explicit_feature_roles = set(continuous) | set(categorical) | set(ordinal)
    if not features:
        raise ValueError("No condition attributes remain after schema resolution.")

    return DatasetSchema(
        target=target,
        features=features,
        continuous=continuous,
        categorical=categorical,
        ordinal=ordinal,
        ignore=ignore,
    )
