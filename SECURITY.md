# Security policy — FDM research collaboration

## Scope / trust boundary

The current FDM platform is an **offline horizontal-federation simulation**, not a cryptographically protected federated protocol. It can calculate pooled Development supports; do NOT infer that connecting actual organizations is private or approved.

- **Python plugins are executable code.** Installing a wheel or discovering entry points can run third-party code. Review adapter sources/dependencies before installation or execution.
- **SSH and Spark:** collaborator nodes require their own authorized accounts, approved network routes, data-permission controls, host-key verification and least-privilege credentials. Do not embed access tokens, passwords or SSH private keys into repo, examples, PRs or container images.
- **Runs:** use isolated Linux containers or constrained Spark queues, CPU/RAM/time quotas, and a single owner for merging shared checkpoints. No unreviewed PR code on privileged Spark workers or research-production hosts.
- **Data:** only use redistributable synthetic/public example data in PRs. Respect UCI/OpenML/PMLB and employer data terms. Never include `source.pkl` or private corpora in pull requests. Untrusted pickles are unsafe to load.
- **CI:** triggered by `pull_request` with read-only contents permission; do not use `pull_request_target` for testing untrusted branch code; do not expose environment secrets to forks.
- **Research integrity:** validation selection must not use Test. Versioned hashes and fixed splits are scientific controls, not a security audit.

## Report a vulnerability

For security issues, do **not** post exploitation details or credentials in a public issue. Contact the repository owner [@Jimmy0307](https://github.com/Jimmy0307) privately via a GitHub-supported private vulnerability reporting channel if enabled. If private reporting is unavailable, ask the maintainer for a secure disclosure route without sharing sensitive exploit details publicly.

FDM 0.1.0 is a research Alpha, not approved for production customer/medical use.
