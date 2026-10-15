# Final mathematical audit evidence (2026-10-15)

Reports: `docs/final_math_audit_20261015/01..08`. Recovery copy of the verdict:
`FINAL_MATHEMATICAL_FREEZE_REPORT.md`. Integrity: `AUDIT_MANIFEST.sha256`.

| Path | Content |
|---|---|
| `baseline/` | unmodified-source state, compileall, pytest (74 passed), test groups |
| `red_green/` | new contract tests on unmodified source (RED) and after the fix (GREEN) |
| `final_regression/` | post-fix compileall, pytest (100 passed), test groups, state |
| `uci_snapshot/` | UCI 44 / 19 / 12 fetched once and frozen (CSV, pickle, `meta.json` with SHA-256) |
| `PRE_FIX_BASELINE/` | UCI3 batch on unmodified source; reproduces `evidence/20261014_162216` exactly |
| `UCI3_HOLDOUT42_FINAL/` | UCI3 batch on audited source (final results) |
| `old_vs_new.csv` | dataset × C × policy, old/new/delta for every metric + structure |
| `uci3_structural_table.csv`, `uci3_resolver_table.csv`, `resolver_winners.csv` | final result tables |
| `structural_associations.csv`, `structural_trajectories.csv` | exploratory descriptive associations (n = 12) |
| `structural_prefix_vs_final_diff.csv` | structural differences pre vs post fix (empty = none) |
| `toy_math_crosscheck.csv` | hand-checkable 3-client support / Global Strength example |
| `uci_distributed_vs_pooled.csv` | distributed = pooled checks on the 12 real UCI3 artifacts |
| `analysis_checks.json` | machine-readable summary of the comparisons |
| `scripts/` | every script used to produce the above |

Reproduce (from the repository root, project `.venv`):

```bash
python -I outputs/final_math_audit_20261015/scripts/run_uci3.py outputs/final_math_audit_20261015/UCI3_HOLDOUT42_FINAL FINAL outputs/final_math_audit_20261015/uci_snapshot
python -I outputs/final_math_audit_20261015/scripts/analyze.py outputs/final_math_audit_20261015
python -I outputs/final_math_audit_20261015/scripts/toy_crosscheck.py outputs/final_math_audit_20261015/toy_math_crosscheck.csv
python -I outputs/final_math_audit_20261015/scripts/uci_distributed_vs_pooled.py outputs/final_math_audit_20261015/uci_snapshot outputs/final_math_audit_20261015/uci_distributed_vs_pooled.csv
```

`AUDIT_MANIFEST.sha256` hashes file content as committed to git (LF line endings for text files),
so it verifies on any checkout via `git show HEAD:<path> | sha256sum`; on Windows with
`core.autocrlf = true` the working-tree bytes of text files differ by CRLF.
