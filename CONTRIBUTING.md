# Contributing to Federated Decision Making (FDM)

Thank you for improving this **research platform**. This guide applies to the modular FDM SDK and its algorithm adapters; the legacy LEM2 study and its frozen 188×42 results must not be changed by adapter PRs.

## Start here

1. Read [the FDM API guide](docs/research/expanded_188_42seeds/handover/FDM_PIP_ADAPTER_GUIDE_ZH.md), [research comparison contract](docs/research/expanded_188_42seeds/handover/FDM_RESEARCH_ACCEPTANCE_GATE.md), and [security rules](SECURITY.md).
2. Fork the repository, or create a feature branch if explicitly granted write permission. **Do not commit to `main` or the shared research branch directly.**
3. From the research branch, run:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e '.[test]'
   python -m pip install -e ./examples/fdm_lookup_adapter
   python -m pytest -q tests/test_federated_decision_making_package.py
   fdm algorithms
   ```

4. For a new algorithm, start from [adapters/_template](adapters/_template/README.md) or the runnable [lookup example](examples/fdm_lookup_adapter/README.md). Prefer a separate Python distribution/adapter; use the `federated_decision_making.algorithms` entry-point group.
5. Push the branch and open a **Pull Request targeting `research/modular-platform-handover-20261123`**, not `main`. Fill in the checklist and attach non-sensitive reproducibility evidence. Wait for CODEOWNERS review and CI.

## API v1 contract

- Every plugin declares `Capabilities`, implements `fit(FitRequest)`, and returns a model with `predict(features_only)` and `diagnostics()`.
- No adapter may read Test targets, search Test labels for a winning strategy, silently impute missing data, or change the shared dataset/split/seed contract.
- Explicitly declare supported scenarios and features. A centralized-only algorithm MUST NOT masquerade as federated. DRSA requires explicit preference directions and ordered decision classes.
- Report `covered` and `candidates` only where mathematically defined; use `None` for unsupported Coverage/Conflict rather than fabricating a zero.
- Do not reuse LEM2's reduct, rule union or six decision policies unless the proposed algorithm scientifically requires the same semantics.
- No silent fallbacks: missing algorithm plugins must raise a clear error.
- Include the paper/algorithm version, runtime package versions and citation(s); describe deviations from the reference algorithm, and provide a small deterministic example.
- Keep one `dataset_id × seed × scenario × split × features × target × source hash` per paired comparison; name the baseline explicitly and show both absolute Accuracies plus the difference in percentage points.

## Required adapter test evidence

- Import and discover the plugin **as a separately installed wheel** using `fdm algorithms`.
- Fit on a small synthetic or redistributable dataset; predict exactly `len(X)` labels from features-only inputs.
- Test unsupported modes, null/unknown features, missing-value behavior and (for DRSA) incomplete ordinal metadata.
- Verify determinism for fixed seeds when claimed, plus no data leakage across train/val/test.
- For federated claims, verify client-level learning and aggregate behavior rather than merely dividing the dataset.
- Exercise `fdm batch`, resuming a checkpoint, and `fdm compare --baseline majority`.
- Benchmark realistic runtime, memory usage, timeouts and failure rates; disclose unsupported scenarios.
- Never upload raw third-party datasets, source.pkl, corporate data, credentials, `.env`, internal hostnames or private SSH keys.

## Review / acceptance

All PRs require passing GitHub Actions and review by a code owner. Research methods must be independently checked for source/target leakage and pairable baselines. API-breaking changes require a versioned proposal; do not update `API_VERSION` in an algorithm PR without migration review.

**License and ownership gate:** The repository does not yet have a verified repository-wide license. The FDM-specific license decision is documented in [LICENSE_DECISION.md](LICENSE_DECISION.md). Until approved, do not represent the whole repository (or third-party datasets) as MIT-licensed; ask the maintainer about redistribution rights before reusing code outside this collaboration.

Maintainer: [@Jimmy0307](https://github.com/Jimmy0307). Collaboration is through PRs; see [CODEOWNERS](.github/CODEOWNERS).
