# Federated Decision Making | Algorithm-neutral Research SDK

Python package: `federated-decision-making` v0.1.0 (Alpha). Import namespace: `federated_decision_making`.

**Contributor onboarding:** [CONTRIBUTING.md](CONTRIBUTING.md) · [Researcher quick start](docs/research/expanded_188_42seeds/handover/FDM_COLLABORATOR_INVITE_ZH.md) · [FDM API guide](docs/research/expanded_188_42seeds/handover/FDM_PIP_ADAPTER_GUIDE_ZH.md) · [Security](SECURITY.md).

This research platform separates dataset splits, horizontal client allocation, classification metrics, source/code fingerprints, resumable checkpoints, SSH/Spark task dispatch, and experiment comparisons from individual rule-induction algorithms.

## Install from the research branch

```bash
python -m pip install "git+https://github.com/Jimmy0307/LEM2.git@research/modular-platform-handover-20261123"
fdm algorithms
```

Not yet published on PyPI. A bare `pip install federated-decision-making` will work **only after** an authorized PyPI release.

## Execute and compare

```bash
fdm run --case case.json --output ./results
fdm batch --manifest jobs.json --output ./results
fdm compare --results ./results --baseline majority --csv ./paired.csv
```

Scientific comparisons use the **same dataset/seed/scenario/split/features/target/source hash** and report the named baseline's absolute Accuracy alongside the candidate's absolute Accuracy and Δpp. They never select the best algorithm on Test.

## Plug in your algorithm

Add a separately installable Python package with an entry point:

```toml
[project.entry-points."federated_decision_making.algorithms"]
my_algorithm = "my_adapter.plugin:MyAlgorithmPlugin"
```

Implement `Capabilities`, `fit(FitRequest)` → predictor, `predict(X)` and `diagnostics()`. See `adapters/_template/` for an intentionally **unimplemented** skeleton and `examples/fdm_lookup_adapter/` for a runnable, non-PRISM example.

- `majority`: ready as a non-rule negative-control baseline.
- `lem2`: ready as a wrapper only when legacy `fedrs` + `roughset` modules are installed.
- `prism`, `ripper`, `drsa`: **reserved, not implemented**. Each requires its own scientifically validated adapter.
- Federated execution is a **horizontal offline simulation**, not a secure network protocol. Spark distributes independent experiment tasks, not one LEM2 model.

## Collaboration release gates

- [x] API v1, plugin discovery, fixed split/metric contracts, checkpoint and pairing
- [x] Unit tests, Wheel build, external example plugin and core Docker smoke
- [ ] Repository owner approves the [license/ownership decision](LICENSE_DECISION.md). Legacy LEM2 and third-party datasets have separate provenance.
- [ ] Repository owner enables **branch ruleset/required CODEOWNERS review** in GitHub Settings; CODEOWNERS is not protection without that setting.
- [ ] PR-required checks run successfully on the research branch.
- [ ] Real remote SSH/Spark cluster is verified before any credentials/data access.

Use a Fork/feature branch and open PRs against `research/modular-platform-handover-20261123`. Do not merge into `main` or alter the frozen 188×42 research checkpoints through adapter PRs.
