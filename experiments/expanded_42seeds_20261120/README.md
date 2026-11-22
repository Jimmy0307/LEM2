# 188-source, 42-seed matched centralized/federated extension

Scope: the frozen full-scale registry has 188 eligible entries plus 24 explicitly excluded same-source duplicates. Seeds are **1 through 42**, not seed 42 alone and not the earlier seeds 1001–1005.

Unmodified scientific path: `full_scale_20261118.sources` → `full_scale_20261118.model.run_model`. Full source rows; existing first-six feature contract and rare-class exclusion retained. Nested 64/16/20 split; centralized and federated C=3 under IID, Dirichlet alpha=0.5, alpha=0.1; six resolvers; both A_ALL_RULES and B2_TRUE_AS_FALLBACK. No training-time or test-time source sampling was added. Original three-dataset factorial results are a different protocol and must not be pooled with this extension.

Expected: 188 × 42 × 4 = **31,584 model fits**, producing **379,008 metric rows** (six policies × two variants). Matched federation-minus-centralization differences use the same dataset, seed, rule variant, resolver and prepared-source hash. This is 188 registry tasks, not 188 independent domains.

```bash
python -m experiments.expanded_42seeds_20261120.run --workers 4
python -m experiments.expanded_42seeds_20261120.run --audit
```

Successful models checkpoint atomically. Restarting the exact same command validates and skips completed models and recorded failures. The run manifest rejects changed contracts. To retry a failed model, inspect and remove only its `seedNN__SCENARIO.failure.json`, then resume. Source failures retry on the next launch. No GitHub Actions workflow is changed or triggered by this runner.

`STATUS.json` and `COMPLETENESS.csv` are authoritative completion gates. `MISSING.csv` explicitly lists every uncompleted model, including source failures, model failures and not-run jobs. No status is COMPLETE unless all 31,584 models have completed. Partial paired summaries must not be presented as a 42-seed result. Source exclusions/failures remain denominator entries; no failed dataset is silently omitted. Raw third-party sources stay in the local cache and are excluded from result delivery.

For a small actual computation check, use a separate directory:

```bash
python -m experiments.expanded_42seeds_20261120.run --dataset UCI20:iris --seeds 42 --workers 1 --output outputs/expanded_188_smoke
```

The main run preserves the upstream 2,700-second per-model deadline. Sources larger than 500,000 rows execute alone after the smaller datasets. Actual runtime depends on exact reduct/LEM2 complexity; the runner does not substitute approximations when a model is slow.
