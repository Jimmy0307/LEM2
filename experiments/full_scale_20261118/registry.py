"""Read the frozen source lists and plan deterministic dataset shards."""
from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "docs/research/teacher_dashboard/data/TEACHER_DATASET_MASTER_20261114.csv"
G5 = ROOT / "docs/research/redesign_20261116/data/CONFIRMATORY_SOURCE_REGISTRY.csv"
PMLB_COMMIT = "7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68"
COHORTS = {"PMLB_117": "PMLB", "UCI_NEW20": "UCI20", "UCI_NEXT12": "NEXT12",
           "UCI_EXTREME7": "EXT7", "UCI_COMMERCE_TECH2": "COMMERCE2", "UCI_BASE3": "O3"}
SAME_SOURCE = {
    "adult": "UCI20:adult_income", "mushroom": "UCI20:mushroom",
    "agaricus_lepiota": "UCI20:mushroom", "iris": "UCI20:iris",
    "wine_recognition": "UCI20:wine", "sonar": "UCI20:sonar",
    "spambase": "UCI20:spambase", "magic": "UCI20:magic_gamma",
    "credit_approval_germany": "UCI20:german_credit", "haberman": "UCI20:haberman",
    "breast_cancer_wisconsin_diagnostic": "UCI20:breast_diagnostic",
    "balance_scale": "O3:Balance Scale", "car_evaluation": "O3:Car Evaluation",
    "hayes_roth": "O3:Hayes-Roth", "contraceptive_method": "EXT7:cmc",
    "nursery": "EXT7:nursery", "tic_tac_toe": "EXT7:tictactoe",
    "congressional_voting_records": "EXT7:voting_records",
    "breast_cancer_wisconsin_original": "EXT7:wisconsin_original",
    "ionosphere": "NEXT12:ionosphere", "yeast": "NEXT12:yeast_localization",
    "segmentation": "NEXT12:image_segmentation", "vehicle": "NEXT12:vehicle_silhouettes",
    "heart_disease_cleveland": "NEXT12:heart_disease",
}


def source_registry():
    master = pd.read_csv(MASTER, keep_default_na=False)
    rows = []
    for r in master.itertuples():
        cohort = COHORTS[r.cohort]
        same = SAME_SOURCE.get(r.id, "") if cohort == "PMLB" else ""
        related = "EXT7:glass" if cohort == "PMLB" and r.id == "glass2" else (
            "PMLB:glass2" if cohort == "EXT7" and r.id == "glass" else "")
        key = r.name if cohort == "O3" else r.id
        rows.append(dict(cohort=cohort, dataset=f"{cohort}:{key}", name=r.id,
                         source_url=r.source_url, upstream_commit=PMLB_COMMIT if cohort == "PMLB" else "",
                         original_rows=int(r.original_rows), same_source_as=same, related_source=related,
                         status="EXCLUDED_SAME_SOURCE" if same else "PENDING"))
    g5 = pd.read_csv(G5, keep_default_na=False)
    for r in g5[g5.status == "ELIGIBLE_PREPARED"].itertuples():
        rows.append(dict(cohort="OML51", dataset=f"OML51:openml_{int(r.did)}", name=r.name,
                         did=int(r.did), source_url=r.parquet_url, upstream_commit="",
                         original_rows=int(float(r.openml_rows)), same_source_as="", related_source="",
                         status="PENDING"))
    registry = pd.DataFrame(rows)
    if registry.dataset.duplicated().any():
        raise ValueError("Duplicate registry keys")
    return registry


def assign_shards(registry, shard_count):
    if shard_count < 11:
        raise ValueError("At least 11 shards are required to isolate the ten largest sources")
    out = registry.copy()
    out["shard"] = -1
    eligible = out[out.status == "PENDING"].sort_values(["original_rows", "dataset"], ascending=[False, True])
    largest = eligible.head(10)
    for shard, idx in enumerate(largest.index):
        out.loc[idx, "shard"] = shard
    for idx, row in eligible.iloc[10:].iterrows():
        digest = hashlib.sha256(row.dataset.encode("utf-8")).digest()
        out.loc[idx, "shard"] = 10 + int.from_bytes(digest[:8], "big") % (shard_count - 10)
    if (eligible.iloc[10:].original_rows > 500_000).any():
        raise ValueError("More than ten >500,000-row sources require additional isolated shards")
    return out
