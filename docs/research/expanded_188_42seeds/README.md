# 188 datasets x 42 seeds (expanded_42seeds_20261120) - incremental results

Status: **in progress** until STATUS.json says COMPLETE. Do not present partial
paired summaries as a 42-seed result.

* Code: experiments/expanded_42seeds_20261120 at 56e293c (tree 3dc3d175, identical to
  original 3566580). Contract migration evidence: REVISION_COMPATIBILITY.json;
  original manifest and source records: ORIGINAL_3566580/.
* Fidelity gate: all 1,559 checkpoints produced under 3566580 were recomputed
  bit-identically (rows, source SHA, partition, feature typing) before resuming.
* Execution: WSL2 Ubuntu, Python 3.12.3, numpy 2.3.5, pandas 2.2.3, unmodified
  run.py per (dataset, seed chunk) under an external memory-aware scheduler.
* checkpoints/<dataset>/ is pushed only when all 168 models have a decision
  (result JSON or recorded failure such as TIMEOUT). Raw third-party data is
  never published. RESULTS.csv / PAIRED_COMPARISONS.csv are omitted for size
  (GitHub 100 MB limit); regenerate with
  `python -m experiments.expanded_42seeds_20261120.run --audit --output <dir>`.
* Summary CSV/JSON files reflect the latest periodic audit at commit time.
