# License decision / 授權決策（送審前 Gate）

**Status: APPROVAL REQUIRED — 2026-11-24.** This repository currently has NO recognized repository-wide LICENSE. The maintainers must verify ownership and third-party provenance before choosing a license. A public GitHub repository is not automatically open-source merely because its source is visible.

## Why we did not add an unqualified repository-wide MIT LICENSE

This monorepo contains legacy LEM2 code, research references, third-party data loaders and derived results. Licensing all of it under MIT without confirming legal rights and prior contributors would be misleading. A blanket license MUST NOT be assumed to cover OpenML/UCI/PMLB source data or other independent work.

## Recommendation

If each relevant copyright owner agrees, license the *new independently developed FDM SDK and example adapter* under **MIT**, with a file-scope statement covering only:
- `src/federated_decision_making/**`
- `examples/fdm_lookup_adapter/**`
- `adapters/_template/**`
- `FDM_PACKAGE_README.md`, `Dockerfile.fdm`, `scripts/fdm_ssh_run.sh`

The legacy `fedrs/**`, `roughset/**`, `experiments/**`, downloaded data, earlier research artifacts and third-party software remain under their own rights until separately verified.

## Maintainer action before external redistribution

1. Confirm ownership/permission for the FDM files and any contributed source code.
2. Choose MIT, Apache-2.0 or another explicit approved SPDX license **for FDM only**; this is a legal choice, not an engineering default.
3. Add a final `LICENSE-FDM` (not this policy file) with the appropriate copyright notice and scope, update `pyproject.toml` package license metadata, and run the wheel CI.
4. State the legacy code's redistribution permissions, or keep legacy components out of shared distributions. Do not publish legacy LEM2 engine as a bundled wheel until its rights are clear.
5. Publish to PyPI only after the name/owner and license gates are approved. `pip install federated-decision-making` from PyPI is **not yet** available.

Until final approval: internal collaborative review and PR development may proceed under the contributor's existing access rights; this is NOT an open-source-license grant for unrestricted third-party redistribution.
