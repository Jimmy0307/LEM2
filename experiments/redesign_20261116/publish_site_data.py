"""Copy summary CSVs used by teacher_dashboard/redesign/ into the dashboard data folder.

Raw per-config tables stay in docs/research/redesign_20261116/data (linked from the page).
A manifest records the SHA-256 of every published copy.
"""
from __future__ import annotations

import shutil

from .common import OUT, ROOT, bootstrap_path

bootstrap_path()
from fedrs.provenance import sha256_file, write_manifest  # noqa: E402

SITE = ROOT / "docs" / "research" / "teacher_dashboard" / "data" / "redesign_20261116"
FILES = ("G1_DEGENERACY_PREVALENCE.csv", "G1_STRUCTURE_DECOMPOSITION.csv", "G1_POLICY_SPREAD_FRIEDMAN.csv",
         "G1_PAIRED_VARIANT_VS_A.csv", "G1_ALPHA_GAP.csv", "G1_CONTROL_C_VS_ORIGINAL.csv", "G1_CONTROL_C_STRUCTURE.csv",
         "G2G4_PAIRED_VS_EW3.csv", "G2G4_METHOD_SUMMARY.csv", "G2_POSITION_VS_COUNT.csv",
         "G2_COUNTEREXAMPLES_FINER_VS_CONFLICT.csv", "G4_LOCO_CHOICES.csv",
         "G3_REAL_NOISE_SUMMARY.csv", "G3_SYNTHETIC_NOISE_SUMMARY.csv", "G3_POLICY_FIVE_WAY_DECOMPOSITION.csv",
         "G5_PRIMARY_HYPOTHESES.csv", "G5_ARM_MEANS.csv", "G5_SECONDARY_DESCRIPTIVE.csv", "G5_H1_FAMILY_SENSITIVITY.csv",
         "G5_POLICY_FRIEDMAN.csv", "G5_STRUCTURE.csv", "CONFIRMATORY_SOURCE_REGISTRY.csv")


def main():
    SITE.mkdir(parents=True, exist_ok=True)
    published, missing = {}, []
    for name in FILES:
        src = OUT / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copyfile(src, SITE / name)
        published[name] = sha256_file(SITE / name)
    write_manifest(SITE / "REDESIGN_SITE_MANIFEST.json", {"published_sha256": published, "missing": missing,
                                                          "source_folder": "docs/research/redesign_20261116/data"})
    print("published", len(published), "missing", missing)


if __name__ == "__main__":
    main()
