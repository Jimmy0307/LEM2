# UCI3 Ready Run

This package is preconfigured to fetch and run the three UCI datasets used in the earlier benchmark work:

1. Hayes-Roth — UCI ID 44 — DOI 10.24432/C5501T
2. Car Evaluation — UCI ID 19 — DOI 10.24432/C5JP48
3. Balance Scale — UCI ID 12 — DOI 10.24432/C5488X

## Run

Double-click `run.bat`.

The current `config.json` keeps both local and UCI sources enabled. Therefore the input logic is OR/union-style:

- if only the UCI list has entries, the three UCI datasets run;
- if local files are also present in `real_data/local/`, those local datasets run as well;
- local files are not required for this UCI3 package.

The UCI loader already has explicit profiles for IDs 44, 19 and 12. These three datasets are treated as categorical benchmark datasets. Hayes-Roth drops the non-condition `name` field and rows with missing target labels according to the existing V6.1 adapter behavior.

Internet access is required the first time `ucimlrepo` fetches the datasets unless they are already cached by the local environment.
