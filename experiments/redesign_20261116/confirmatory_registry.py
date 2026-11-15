"""Gate 5 source registry: OpenML-CC18 (study 99) + AutoML Benchmark classification (study 271).

Eligibility rules are applied MECHANICALLY and every candidate (eligible or not)
is written to CONFIRMATORY_SOURCE_REGISTRY.csv with a status and reason.

E1  not the same source family as any of the 161 sources already used by this
    research (PMLB-117, UCI base3/commerce2/extreme7/new20/next12) - curated alias map;
E2  2 <= classes <= 12;   E3  rows >= 300;   E4  features <= 2000 (parse feasibility);
E5  download succeeds.  NOTE (corrected after code review, 2026-11-16): OpenML's published
    md5_checksum refers to the ARFF file, while this builder downloads the parquet file, so the
    MD5 is STORED but NOT compared; integrity is instead fixed by the recorded parquet SHA-256 and
    prepared-table SHA-256.  Any download/HTTP error is also labelled EXCLUDED_E5_E6 (e.g. albert,
    HTTP 500) - it is a transient failure, not a rule exclusion, and is kept as a failure (not
    retried or replaced) because the registry was frozen with it;
    candidates come from OpenML data/list (active datasets): all 112 suite ids were returned;
E6  prepared table: first 6 non-target, non-id, non-ignored features in OpenML order;
    identifier-like columns (integer-valued numeric with >= 95% distinct values) are
    skipped BEFORE taking the first 6 (rule E6b, fixed before any confirmatory run);
    categorical missing -> '__MISSING__'; rows with numeric missing dropped if <= 5% of
    rows else EXCLUDED; cap 1800 rows by class-stratified sample (seed 20261116);
    classes with < 10 rows after capping are dropped (recorded); >= 2 classes must remain.
Raw files are cached under data_cache/ (git-ignored; not redistributed). Only hashes,
metadata and per-run metrics are committed.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .common import OUT, ROOT

CACHE = ROOT / "data_cache" / "openml"
SUITES = (99, 271)
MAX_ROWS, MAX_FEATURES_USED, CAP_SEED = 1800, 6, 20261116
UA = {"User-Agent": "research-client/1.0"}

# OpenML name -> family already used in this research (E1).  Curated by hand.
USED_FAMILY_ALIASES = {
    "kr-vs-kp": "chess_kr_vs_kp (PMLB)", "letter": "letter (UCI20/PMLB)", "balance-scale": "balance (UCI base3)",
    "mfeat-factors": "mfeat (PMLB)", "mfeat-fourier": "mfeat (PMLB)", "mfeat-karhunen": "mfeat (PMLB)",
    "mfeat-morphological": "mfeat (PMLB)", "mfeat-zernike": "mfeat (PMLB)", "mfeat-pixel": "mfeat (PMLB)",
    "breast-w": "wisconsin original (UCI extreme7/PMLB)", "cmc": "contraceptive (UCI extreme7/PMLB)",
    "optdigits": "optdigits (PMLB)", "credit-approval": "credit approval / Australian (PMLB)",
    "Australian": "credit approval / Australian (PMLB)", "credit-g": "german credit (UCI20/PMLB)",
    "pendigits": "pendigits (PMLB)", "sick": "thyroid Garavan family (PMLB allbp/dis/...)",
    "spambase": "spambase (UCI20/PMLB)", "splice": "splice (PMLB)", "tic-tac-toe": "tic-tac-toe (extreme7/PMLB)",
    "vehicle": "vehicle (next12/PMLB)", "yeast": "yeast (next12/PMLB)", "satimage": "satimage (PMLB)",
    "Satellite": "satimage-derived (PMLB satimage)", "vowel": "vowel (PMLB)",
    "analcatdata_authorship": "PMLB", "analcatdata_dmft": "PMLB", "mnist_784": "mnist (PMLB)",
    "bank-marketing": "bank marketing (UCI20)", "banknote-authentication": "banknote (UCI20)",
    "blood-transfusion-service-center": "blood donation (next12)", "phoneme": "phoneme (PMLB)",
    "wdbc": "breast diagnostic (UCI20/PMLB)", "adult": "adult (UCI20/PMLB)", "covertype": "covertype (UCI20)",
    "PhishingWebsites": "phishing (UCI20)", "wine-quality-white": "wine quality (next12/PMLB)",
    "texture": "texture (PMLB)", "connect-4": "connect-4 (PMLB)", "dna": "dna (PMLB)", "shuttle": "shuttle (PMLB)",
    "churn": "churn (PMLB)", "car": "car (UCI base3/PMLB)", "segment": "segmentation (next12/PMLB)",
    "KDDCup99": "kddcup (PMLB pool)",
}
# Same-origin groups INSIDE the confirmatory pool (kept, but marked for family-level sensitivity).
FAMILY = {"pc1": "nasa_mdp", "pc3": "nasa_mdp", "pc4": "nasa_mdp", "kc1": "nasa_mdp", "kc2": "nasa_mdp",
          "jm1": "nasa_mdp", "christine": "automl_challenge", "jasmine": "automl_challenge",
          "madeline": "automl_challenge", "philippine": "automl_challenge", "sylvine": "automl_challenge",
          "albert": "automl_challenge", "dilbert": "automl_challenge", "fabert": "automl_challenge",
          "volkert": "automl_challenge", "jannis": "automl_challenge", "ada": "automl_challenge",
          "gina": "automl_challenge"}


def _json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180))


def candidates() -> pd.DataFrame:
    ids = set()
    for s in SUITES:
        ids |= {int(x) for x in _json(f"https://www.openml.org/api/v1/json/study/{s}")["study"]["data"]["data_id"]}
    rows = []
    ids = sorted(ids)
    for i in range(0, len(ids), 50):
        chunk = ",".join(map(str, ids[i:i + 50]))
        for x in _json(f"https://www.openml.org/api/v1/json/data/list/data_id/{chunk}/limit/100")["data"]["dataset"]:
            q = {qq["name"]: qq["value"] for qq in x.get("quality", [])}
            rows.append({"did": int(x["did"]), "name": x["name"], "version": int(x["version"]),
                         "openml_rows": float(q.get("NumberOfInstances", 0)),
                         "openml_features": float(q.get("NumberOfFeatures", 0)),
                         "openml_classes": float(q.get("NumberOfClasses", 0)),
                         "openml_missing_values": float(q.get("NumberOfMissingValues", 0))})
    return pd.DataFrame(rows).sort_values("did").reset_index(drop=True)


def screen(df: pd.DataFrame) -> pd.DataFrame:
    status, reason = [], []
    for r in df.itertuples():
        if r.name in USED_FAMILY_ALIASES:
            status.append("EXCLUDED_E1_USED_FAMILY"); reason.append(USED_FAMILY_ALIASES[r.name])
        elif not 2 <= r.openml_classes <= 12:
            status.append("EXCLUDED_E2_CLASSES"); reason.append(f"classes={r.openml_classes:g}")
        elif r.openml_rows < 300:
            status.append("EXCLUDED_E3_ROWS"); reason.append(f"rows={r.openml_rows:g}")
        elif r.openml_features > 2000:
            status.append("EXCLUDED_E4_FEATURES"); reason.append(f"features={r.openml_features:g}")
        else:
            status.append("ELIGIBLE_PENDING_DOWNLOAD"); reason.append("")
    out = df.copy()
    out["status"], out["reason"] = status, reason
    out["family"] = [FAMILY.get(n, n) for n in out["name"]]
    return out


def _download(did: int):
    desc = _json(f"https://www.openml.org/api/v1/json/data/{did}")["data_set_description"]
    feats = _json(f"https://www.openml.org/api/v1/json/data/features/{did}")["data_features"]["feature"]
    folder = CACHE / str(did)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"dataset_{did}.pq"
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(desc["parquet_url"], headers=UA), timeout=600) as resp:
            path.write_bytes(resp.read())
    (folder / "description.json").write_text(json.dumps(desc), encoding="utf-8")
    (folder / "features.json").write_text(json.dumps(feats), encoding="utf-8")
    return desc, feats, path


def prepare(did: int):
    """Returns (prepared frame, meta).  Raises with an explicit reason on exclusion."""
    desc, feats, path = _download(did)
    raw_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = pd.read_parquet(path)
    target = str(desc["default_target_attribute"]).split(",")[0]
    drop = set()
    for key in ("row_id_attribute", "ignore_attribute"):
        v = desc.get(key)
        if v:
            drop |= set(v if isinstance(v, list) else [v])
    ordered = sorted(feats, key=lambda f: int(f["index"]))
    usable = [f for f in ordered if f["name"] != target and f["name"] not in drop
              and str(f.get("is_ignore", "false")) != "true" and str(f.get("is_row_identifier", "false")) != "true"]
    id_like = []
    for f in usable:
        if f["data_type"] == "numeric" and f["name"] in raw:
            v = pd.to_numeric(raw[f["name"]], errors="coerce").dropna()
            if len(v) and (v == np.round(v)).all() and v.nunique() >= 0.95 * len(raw):
                id_like.append(f["name"])
    usable = [f for f in usable if f["name"] not in id_like]
    chosen = usable[:MAX_FEATURES_USED]
    names = [f["name"] for f in chosen]
    frame = raw[names + [target]].copy()
    frame = frame[frame[target].notna()]
    continuous, categorical = [], []
    for f in chosen:
        col = f["name"]
        if f["data_type"] == "numeric" and pd.to_numeric(frame[col], errors="coerce").nunique() > 10:
            continuous.append(col)
        else:
            categorical.append(col)
    numeric_missing = frame[continuous].isna().any(axis=1) if continuous else pd.Series(False, index=frame.index)
    if numeric_missing.mean() > 0.05:
        raise RuntimeError(f"EXCLUDED_E6_NUMERIC_MISSING_GT5PCT({numeric_missing.mean():.3f})")
    dropped_missing = int(numeric_missing.sum())
    frame = frame[~numeric_missing]
    for col in categorical:
        frame[col] = frame[col].astype("string").fillna("__MISSING__").astype(str).str.strip()
    for col in continuous:
        frame[col] = pd.to_numeric(frame[col]).astype(float)
    frame[target] = frame[target].astype(str).str.strip()
    capped = len(frame) > MAX_ROWS
    if capped:
        rng = np.random.default_rng(CAP_SEED)
        share = MAX_ROWS / len(frame)
        keep = []
        for _, g in frame.groupby(target, sort=True):
            k = max(1, int(round(len(g) * share)))
            keep.extend(rng.choice(g.index.to_numpy(), size=min(k, len(g)), replace=False).tolist())
        frame = frame.loc[sorted(keep)]
    counts = frame[target].value_counts()
    small = counts[counts < 10].index.tolist()
    frame = frame[~frame[target].isin(small)]
    if frame[target].nunique() < 2:
        raise RuntimeError("EXCLUDED_E6_FEWER_THAN_2_CLASSES_AFTER_PREP")
    frame = frame.rename(columns={target: "class"}).reset_index(drop=True)
    prep_sha = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    meta = {"did": did, "target": target, "features": names, "continuous": continuous, "categorical": categorical,
            "raw_sha256": raw_sha, "openml_md5": desc.get("md5_checksum"), "prepared_sha256": prep_sha,
            "prepared_rows": len(frame), "prepared_classes": int(frame["class"].nunique()),
            "dropped_numeric_missing_rows": dropped_missing, "row_capped": capped, "dropped_small_classes": small,
            "categorical_missing_cells": int((frame[categorical] == "__MISSING__").sum().sum()) if categorical else 0,
            "imbalance_ratio": float(frame["class"].value_counts().max() / frame["class"].value_counts().min()),
            "skipped_identifier_like_columns": id_like,
            "licence": desc.get("licence"), "openml_version": desc.get("version"),
            "parquet_url": desc.get("parquet_url")}
    return frame, meta


def build():
    reg = screen(candidates())
    metas = []
    for i, r in reg.iterrows():
        if r.status != "ELIGIBLE_PENDING_DOWNLOAD":
            continue
        try:
            frame, meta = prepare(int(r.did))
            folder = CACHE / str(r.did)
            frame.to_csv(folder / "prepared.csv", index=False)
            (folder / "prepared_meta.json").write_text(json.dumps(meta, default=str), encoding="utf-8")
            reg.loc[i, "status"] = "ELIGIBLE_PREPARED"
            metas.append({"did": int(r.did), **{k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                                                 for k, v in meta.items() if k != "did"}})
            print("PREPARED", r.did, r["name"], meta["prepared_rows"], meta["continuous"], flush=True)
        except Exception as exc:
            reg.loc[i, "status"] = "EXCLUDED_E5_E6"
            reg.loc[i, "reason"] = f"{type(exc).__name__}: {exc}"[:300]
            print("EXCLUDED", r.did, r["name"], exc, flush=True)
    reg = reg.merge(pd.DataFrame(metas), on="did", how="left") if metas else reg
    reg.to_csv(OUT / "CONFIRMATORY_SOURCE_REGISTRY.csv", index=False)
    return reg


if __name__ == "__main__":
    build()
