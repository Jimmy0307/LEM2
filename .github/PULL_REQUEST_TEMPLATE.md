## Summary / 摘要

**Algorithm / Adapter name:**
**Reference paper, version, DOI / source:**
**Base branch:** `research/modular-platform-handover-20261123`
**Changes:**  

## Research contract / 研究契約

- [ ] This change is isolated to the new adapter or explicitly reviewed SDK API changes.
- [ ] Data splits, source SHA, seed, target and features are unchanged and documented.
- [ ] `fit` never sees Test labels; `predict` receives only features.
- [ ] Federated capability reflects **actual** implementation, not simulation-only or automatic fallback.
- [ ] Missing values, ordinal criteria and unsupported metrics are explicitly declared.
- [ ] No LEM2-specific reduct/rule semantics forced on other algorithms.
- [ ] Same-source/seed/scenario/split Test comparisons state the **named baseline**, absolute accuracies and pp difference.
- [ ] No real/private datasets, `source.pkl`, keys, tokens or SSH hosts are committed.

## CI and proof / 驗收

- [ ] Plugin installs separately and is discoverable with `fdm algorithms`.
- [ ] Synthetic/redistributable smoke data plus deterministic tests attached.
- [ ] Tests include invalid feature, missing data and unsupported mode scenarios.
- [ ] Checkpoint retry and `fdm compare` validated when relevant.
- [ ] `pip-wheel-and-external-plugin`, `docker-smoke`, `governance-checks` all PASS (or an explained scoped exception).

**Exact commands run:**

```bash
# paste reproducible commands
```

**Results (both absolute Accuracy values, baseline, environment, known limitations):**

| Dataset / seed | Scenario / split | Candidate | Baseline | Candidate Acc | Baseline Acc | Δ pp |
|---|---|---|---|---|---|---|
|  |  |  | majority |  |  |  |

## Review / risk

- [ ] Maintainer approval requested via CODEOWNERS.
- [ ] Any licensing or third-party code provenance questions are disclosed; not asserting repository-wide MIT.
- [ ] Existing 188×42 research manifests/checkpoints and running jobs are untouched.
