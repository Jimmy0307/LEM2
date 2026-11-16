"""Independent re-computation of the Gate 5 confirmatory statistics (finalization audit).

Deliberately does NOT import ``fedrs.stats`` or ``analyze_g5``: arm selection, pairing,
Wilcoxon, Holm and bootstrap are re-implemented here from the frozen preregistration text
and applied to the raw per-task file ``REDESIGN_G5_CONFIRMATORY_POLICIES.csv``.

Outputs (new files only; never overwrites published analysis tables):
  data/G5_INDEPENDENT_RECOMPUTATION_20261116.csv
  data/G5_INDEPENDENT_RECOMPUTATION_20261116.json

Usage:  python -m experiments.redesign_20261116.verify_g5_independent [--check]
``--check`` exits non-zero if any recomputed value disagrees with the published tables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "research" / "redesign_20261116" / "data"
RAW = DATA / "REDESIGN_G5_CONFIRMATORY_POLICIES.csv"
OUT_CSV = DATA / "G5_INDEPENDENT_RECOMPUTATION_20261116.csv"
OUT_JSON = DATA / "G5_INDEPENDENT_RECOMPUTATION_20261116.json"
OUT_POSTHOC = DATA / "G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv"
# POST-HOC (not preregistered): sources whose upstream is documented/suspected to overlap historical sources.
# ada / gina: ALvsPK agnostic versions of UCI Adult / MNIST (same 48 / 970 feature representation as
# OpenML 1043 / 1038); sylvine: unverified lead (SYLVA = forest cover type). See SOURCE_INDEPENDENCE_REVIEW.
POSTHOC_EXCLUSIONS = {
    "EXCLUDE_ADA_GINA": ("openml_41156", "openml_41158"),
    "EXCLUDE_ADA_GINA_SYLVINE": ("openml_41156", "openml_41158", "openml_41146"),
}
REGIMES = ("IID", "NONIID_05", "NONIID_01")
SEEDS = tuple(range(1001, 1011))
# Preregistration §3 (frozen at 89fd52b)
ARM_SPEC = {
    "M0": ("EQUAL_WIDTH_3", "A_ALL_RULES", "VALIDATION_BEST"),
    "M1": ("EQUAL_WIDTH_3", "B2_TRUE_AS_FALLBACK", "VALIDATION_BEST"),
    "M2": ("FED_MD_HIST", "B2_TRUE_AS_FALLBACK", "VALIDATION_BEST"),
    "R1": ("RS_DISCERNIBILITY_CENTRAL", "B2_TRUE_AS_FALLBACK", "VALIDATION_BEST"),
    "C1": ("CART", None, "CART_CENTRAL"),
    "C2": ("CART", None, "CART_FED_VOTE"),
}
# (label, minuend, subtrahend, regimes, holm_family)
COMPARISONS = [
    ("H1", "M2", "M0", REGIMES, "H1"),
    ("H2", "M1", "M0", ("NONIID_01",), "H2"),
    ("SEC_M2_minus_R1", "M2", "R1", REGIMES, None),
    ("SEC_M2_minus_C1", "M2", "C1", REGIMES, None),
    ("SEC_M2_minus_C2", "M2", "C2", REGIMES, None),
]
TOL = 1e-9
CRLF, LF = bytes([13, 10]), bytes([10])
RANK_DECIMALS = 12
P_TOL = 0.005  # p-value tolerance for platform tie-handling drift (decisions must still agree)


def sha256(path: Path) -> str:
    """SHA-256 of the Git-canonical (LF) bytes, identical on Windows and Linux checkouts."""
    return hashlib.sha256(path.read_bytes().replace(CRLF, LF)).hexdigest()


def load_arm(raw: pd.DataFrame, arm: str) -> pd.DataFrame:
    disc, variant, method = ARM_SPEC[arm]
    mask = (raw.discretizer == disc) & (raw.method == method)
    if variant is not None:
        mask &= raw.rule_variant == variant
    sub = raw.loc[mask, ["dataset", "seed", "regime", "test_ba"]]
    dup = sub.duplicated(["dataset", "seed", "regime"]).sum()
    if dup:
        raise ValueError(f"{arm}: {dup} duplicated (dataset, seed, regime) rows")
    return sub


def holm_adjust(p: list[float]) -> list[float]:
    order = sorted(range(len(p)), key=lambda i: p[i])
    adjusted, running = [0.0] * len(p), 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[idx]))
        adjusted[idx] = running
    return adjusted


def boot_ci(diff: np.ndarray, seed: int, n: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = diff[rng.integers(0, diff.size, size=(n, diff.size))].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def compare(raw: pd.DataFrame, minuend: str, subtrahend: str, regime: str) -> dict:
    a = load_arm(raw, minuend).query("regime == @regime")
    b = load_arm(raw, subtrahend).query("regime == @regime")
    paired = a.merge(b, on=["dataset", "seed", "regime"], suffixes=("_a", "_b"), validate="one_to_one")
    per = paired.groupby("dataset")[["test_ba_a", "test_ba_b"]].mean()
    diff = (per.test_ba_a - per.test_ba_b).to_numpy()
    lo, hi = boot_ci(diff, seed=20261116)
    alt_lo, alt_hi = boot_ci(diff, seed=7)  # robustness of CI to bootstrap RNG seed
    return {
        "regime": regime, "minuend": minuend, "subtrahend": subtrahend,
        "n_datasets": int(per.shape[0]), "n_paired_replicates": int(len(paired)),
        "seeds_per_dataset_min": int(paired.groupby("dataset").size().min()),
        "mean_minuend": float(per.test_ba_a.mean()), "mean_subtrahend": float(per.test_ba_b.mean()),
        "mean_diff": float(diff.mean()), "median_diff": float(np.median(diff)),
        "ci95_low": lo, "ci95_high": hi, "ci95_low_altseed": alt_lo, "ci95_high_altseed": alt_hi,
        "wins": int((diff > 1e-12).sum()), "ties": int((np.abs(diff) <= 1e-12).sum()),
        "losses": int((diff < -1e-12).sum()),
        # Published method: ranks on unrounded differences. Near-ties (|gap| ~1e-16) make the
        # tie correction depend on platform floating-point summation order, so a tie-robust
        # variant (differences rounded to 1e-12) is reported alongside and only decisions are
        # required to agree (observed: M2-C2 alpha=0.1 p=0.0980 Windows vs 0.0990 Linux).
        "wilcoxon_p_two_sided": float(stats.wilcoxon(diff).pvalue),
        "wilcoxon_p_tie_rounded": float(stats.wilcoxon(np.round(diff, RANK_DECIMALS)).pvalue),
        "sign_test_p": float(stats.binomtest(int((diff > 1e-12).sum()), int((np.abs(diff) > 1e-12).sum())).pvalue),
        "paired_t_p": float(stats.ttest_1samp(diff, 0.0).pvalue),
    }


def recompute(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, m, s, regimes, family in COMPARISONS:
        block = [dict(compare(raw, m, s, r), comparison=label, holm_family=family or "") for r in regimes]
        if family:
            adj = holm_adjust([x["wilcoxon_p_two_sided"] for x in block])
            for x, p in zip(block, adj):
                x["holm_p"] = p
                x["passed_prereg_rule"] = bool(p < 0.05 and x["mean_diff"] > 0 and x["ci95_low"] > 0)
        rows.extend(block)
    return pd.DataFrame(rows)


def check_p(label: str, ours: float, published: float, errors: list[str], warnings: list[str]) -> None:
    """p-values must agree on every decision at alpha=0.05 and within P_TOL; tiny drift is a warning."""
    gap = abs(float(ours) - float(published))
    if gap > P_TOL or (float(ours) < 0.05) != (float(published) < 0.05):
        errors.append(f"{label} p: {ours} vs {published}")
    elif gap > TOL:
        warnings.append(f"{label} p drift {gap:.2e} ({ours} vs {published}); decision unchanged")


def cross_check(rec: pd.DataFrame) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    prim = pd.read_csv(DATA / "G5_PRIMARY_HYPOTHESES.csv")
    for x in prim.itertuples():
        r = rec[(rec.comparison == x.hypothesis) & (rec.regime == x.regime)].iloc[0]
        check_p(f"PRIMARY {x.hypothesis}/{x.regime} wilcoxon", r.wilcoxon_p_two_sided, x.wilcoxon_p, errors, warnings)
        check_p(f"PRIMARY {x.hypothesis}/{x.regime} holm", r.holm_p, x.holm_p, errors, warnings)
        for ours, theirs in (("mean_diff", "mean_diff"), ("ci95_low", "ci95_low"), ("ci95_high", "ci95_high"),
                             ("n_paired_replicates", "n_paired_replicates")):
            if abs(float(r[ours]) - float(getattr(x, theirs))) > TOL * max(1.0, abs(float(r[ours]))):
                errors.append(f"PRIMARY {x.hypothesis}/{x.regime} {ours}: {r[ours]} != {getattr(x, theirs)}")
        if bool(r.passed_prereg_rule) != bool(x.passed):
            errors.append(f"PRIMARY {x.hypothesis}/{x.regime} passed mismatch")
    sec = pd.read_csv(DATA / "G5_SECONDARY_DESCRIPTIVE.csv").query("policy_method == 'VALIDATION_BEST'")
    for other in ("R1", "C1", "C2"):
        for regime in REGIMES:
            r = rec[(rec.comparison == f"SEC_M2_minus_{other}") & (rec.regime == regime)].iloc[0]
            pub = sec[(sec.baseline == "M2") & (sec.treatment == other) & (sec.regime == regime)].iloc[0]
            # published mean_diff is treatment - baseline = other - M2; ours is M2 - other
            if abs(r.mean_diff + pub.mean_diff) > TOL:
                errors.append(f"SEC M2-{other}/{regime}: {r.mean_diff} vs -({pub.mean_diff})")
            check_p(f"SEC M2-{other}/{regime}", r.wilcoxon_p_two_sided, pub.wilcoxon_p, errors, warnings)
    means = pd.read_csv(DATA / "G5_ARM_MEANS.csv").set_index("regime")
    for x in rec.itertuples():
        for arm, val in ((x.minuend, x.mean_minuend), (x.subtrahend, x.mean_subtrahend)):
            if abs(means.loc[x.regime, arm] - val) > TOL:
                errors.append(f"ARM_MEANS {arm}/{x.regime}: {val} vs {means.loc[x.regime, arm]}")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Independent Gate 5 recomputation")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    raw = pd.read_csv(RAW, usecols=["dataset", "seed", "regime", "discretizer", "rule_variant", "method", "test_ba"],
                      keep_default_na=False, na_values=[""])
    datasets = sorted(raw.dataset.unique())
    if len(datasets) != 51:
        raise ValueError(f"expected 51 preregistered sources, found {len(datasets)}")
    if sorted(raw.seed.unique()) != list(SEEDS):
        raise ValueError("unexpected seed set")
    rec = recompute(raw)
    errors, warnings = cross_check(rec)
    rec.to_csv(OUT_CSV, index=False)
    posthoc = pd.concat([recompute(raw[~raw.dataset.isin(ids)]).assign(posthoc_scenario=name, excluded=";".join(ids))
                         for name, ids in POSTHOC_EXCLUSIONS.items()], ignore_index=True)
    posthoc.insert(0, "evidence_level", "POST_HOC_SENSITIVITY_NOT_PREREGISTERED")
    posthoc.to_csv(OUT_POSTHOC, index=False)
    print(posthoc[posthoc.holm_family != ""][["posthoc_scenario", "comparison", "regime", "n_datasets", "mean_diff",
                                               "ci95_low", "holm_p", "passed_prereg_rule"]].round(4).to_string(index=False))
    OUT_JSON.write_text(json.dumps({
        "purpose": "Independent recomputation of preregistered Gate 5 H1/H2 and signed external comparators",
        "raw_input": RAW.relative_to(ROOT).as_posix(), "raw_input_sha256": sha256(RAW),
        "n_datasets": len(datasets), "seeds": list(SEEDS), "direction": "minuend - subtrahend (M2 - comparator)",
        "uses_fedrs_stats": False, "crosscheck_errors": errors, "crosscheck_pass": not errors,
        "p_value_warnings": warnings, "p_value_tolerance": P_TOL,
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
        "secondary_note": "Secondary comparisons are descriptive; p-values are uncorrected; no non-inferiority test was preregistered.",
    }, indent=2), encoding="utf-8")
    view = rec[["comparison", "regime", "mean_diff", "ci95_low", "ci95_high", "wilcoxon_p_two_sided"]].copy()
    view[["mean_diff", "ci95_low", "ci95_high"]] *= 100
    print(view.round(4).to_string(index=False))
    print("CROSSCHECK", "PASS" if not errors else "FAIL", *errors, *warnings, sep="\n")
    return 1 if (args.check and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
