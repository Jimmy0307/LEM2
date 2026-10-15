# RoughSet Research Software V1

這是一個把原本 V6.1 單檔研究程式拆成可維護軟體架構的版本。

## 最簡單的使用方式

1. 把資料放進 `real_data/local/`
2. 如果 target 欄不是 `target / class / label / decision`，請建立 schema
3. 若要跑 UCI，把 `UCI ID` 或 `DOI` 貼到 `real_data/uci_sources.txt`
4. 雙擊 `run.bat`
5. 結果會分資料集輸出到 `outputs/`

---

## 目錄

```text
RoughSet_Software_V1/
├─ run.bat
├─ config.json
├─ main.py
├─ requirements.txt
├─ real_data/
│  ├─ local/          # 放 CSV / XLSX / XLS
│  ├─ schemas/        # 可選 sidecar schema
│  └─ uci_sources.txt # UCI ID / DOI
├─ roughset/
│  ├─ core.py         # Rough Set / LEM2 數學核心
│  ├─ reduct.py       # minimum-cardinality reduct search
│  ├─ sources.py      # local / UCI source discovery, DOI resolver
│  ├─ adapters.py     # raw data -> DatasetBundle
│  ├─ schema.py       # target / continuous / categorical / ordinal / ignore
│  ├─ splitting.py    # Holdout / K-Fold
│  ├─ preprocessing.py# train-only discretization
│  ├─ evaluation.py   # prediction policies / metrics / centralized
│  ├─ federated.py    # partition / UNION / provenance / conflict / order
│  ├─ paper.py        # Wang-2007-style replication lane
│  └─ app.py          # orchestration + outputs
├─ reference/
│  └─ lem2_control_panel_v6_1_reference.py
├─ tests/
└─ docs/
```

---


## Environment / 依賴管理

這一版把執行環境拆成 **Core / Excel Adapter / UCI Adapter**，不再要求每次只跑 CSV 也先安裝全部套件。

### Python 版本

目前 canonical 鎖定環境要求 **Python 3.11–3.13**；驗證環境為 CPython 3.13.5。

> **Python 3.14 注意：** 這個 release 刻意不讓 `pandas==2.2.3` 在 Python 3.14 上從 source build。若電腦只有 Python 3.14，請先雙擊 `install_python_313.bat` 安裝 Python 3.13；Python 3.14 可以保留，兩者可共存。`run.bat` 會明確選 3.13。

### 第一次安裝

最簡單：

```text
雙擊 setup_environment.bat
```

預設 `full` 模式會建立 `.venv`，並依 `requirements-lock.txt` 安裝鎖定版本。安裝器會優先選 Python 3.13 → 3.12 → 3.11，**不再使用未限定版本的 `py -3`**。

若只想先建立最小環境：

```bat
setup_environment.bat core
```

只安裝：

- `numpy==2.3.5`
- `pandas==2.2.3`

### run.bat 會自動補需要的 Adapter

`run.bat` 會先確保 Core，再依目前 `config.json + real_data/` 自動判斷：

- 只有 CSV → Core 即可
- 出現 `.xlsx` → 補 Excel adapter
- 出現 `.xls` → 補 Excel adapter
- `uci_sources.txt` 有有效來源 → 補 UCI adapter

所以 Local CSV 不會因為沒有 `ucimlrepo` 而整包不能跑。

### 鎖定版本

完整 top-level runtime pin set：

```text
requirements-lock.txt
```

目前直接依賴鎖定：

```text
numpy==2.3.5
pandas==2.2.3
openpyxl==3.1.5
xlrd==2.0.2
ucimlrepo==0.0.7
```

另有：

```text
requirements-core.txt
requirements-excel.txt
requirements-uci.txt
requirements-dev.txt
```

### 環境檢查

可直接雙擊：

```text
check_environment.bat
```

它會依目前資料來源檢查真正需要的 dependencies。

每次研究輸出也會把 Python / OS / package versions 寫進：

```text
outputs/run_manifest.json
outputs/<dataset>/dataset_manifest.json
```

因此未來可以回溯某次結果是在哪一組 runtime 跑出來。注意：`requirements-lock.txt` 鎖的是本專案直接依賴；實際執行 manifest 會記錄本專案關注套件的實際版本。若要做完全離線且 byte-for-byte 可重建的環境，建議搭配固定的 `wheels/` wheelhouse。

### 沒有安裝 Python 的電腦

若 Windows 本身沒有 Python 3.11–3.13，可先雙擊：

```text
install_python_313.bat
```

它使用 `winget` 安裝 Python 3.13 x64，不會移除既有 Python 3.14。若不想安裝系統 Python，也可把支援 `venv` 與 `pip` 的 portable Python 3.11–3.13 放在：

```text
runtime/python.exe
```

`setup_environment.bat` 會優先使用它。Release ZIP **不直接夾帶第三方 Python binary**；`runtime/README.txt` 有說明。

### 離線安裝

如果目標電腦不能連 PyPI，可以先把與目標 Windows / Python 版本相容的 wheel 檔放入：

```text
wheels/
```

當 `wheels/` 內存在 `.whl` 時，installer 會優先使用 `--no-index --find-links wheels`，不再連外下載。Release 不直接夾帶第三方 wheels；詳見 `wheels/README.txt`。

---

## Local 資料

支援：

- `.csv`
- `.xlsx`
- `.xls`

例如：

```text
real_data/local/
├─ company_8d.csv
├─ medical.xlsx
└─ housing.csv
```

程式會全部批次跑，不會只取第一個。

輸出：

```text
outputs/
├─ company_8d/
├─ medical/
└─ housing/
```

---

## Schema

假設資料：

```text
real_data/local/company_8d.csv
```

可建立：

```text
real_data/schemas/company_8d.schema.json
```

範例：

```json
{
  "target": "class",
  "continuous": ["age", "income"],
  "categorical": ["department", "product_type"],
  "ordinal": {
    "severity": ["low", "medium", "high"]
  },
  "ignore": ["id", "name"]
}
```

規則：

- `target`：decision attribute
- `continuous`：需 training-only discretization
- `categorical`：symbolic condition
- `ordinal`：目前 classical LEM2 當 discrete symbolic values，但順序 metadata 保留給未來 DRSA
- `ignore`：ID / 姓名 / timestamp 等不進模型

若沒有 schema：

- target 只有在欄名**恰好唯一**為 `target / class / label / decision` 時才自動使用
- 不會用「最後一欄」亂猜 target
- 其他 features 再做 conservative auto type detection

---

## Continuous / Categorical / Ordinal 是分開處理的

流程：

```text
Raw Data
   ↓
Schema
   ├─ Continuous
   ├─ Categorical
   ├─ Ordinal
   └─ Ignore
   ↓
Split
   ↓
Fit Preprocessor on TRAIN ONLY
   ↓
Transform Train / Test
   ↓
Decision Table
```

Continuous 的 bin boundary **只用 training data 計算**，避免 test leakage。

---

## UCI Machine Learning Repository

編輯：

```text
real_data/uci_sources.txt
```

可以直接貼：

```text
44
10.24432/C5501T
```

也可以寫明：

```text
uci_id:44
doi:10.24432/C5501T
```

DOI 會：

```text
DOI
 ↓
doi.org redirect
 ↓
UCI dataset page
 ↓
resolve UCI ID
 ↓
cache in real_data/.cache/uci_doi_map.json
```

若離線而 DOI 尚未 cache，會明確報錯；此時可改用 `uci_id:<number>`。

V6.1 已知 benchmark datasets 保留原本語意：

- UCI 44 Hayes-Roth：drop `name`，只保留 labeled rows，conditions 當 categorical codes
- UCI 19 Car Evaluation：categorical
- UCI 12 Balance Scale：1–5 仍當 categorical codes，不偷偷加入 dominance 意義

---

## Split

在 `config.json`：

### Holdout

```json
"evaluation": {
  "mode": "HOLDOUT",
  "test_ratio": 0.2,
  "seed": 42
}
```

### K-Fold

```json
"evaluation": {
  "mode": "K_FOLD_CV",
  "cv_folds": 10,
  "seed": 42
}
```

Split 與 preprocessing 是不同模組。

---

## Federated

```json
"federated": {
  "n_clients": 5,
  "partition": "STRATIFIED",
  "dirichlet_alpha": 0.5,
  "run_client_sweep": true,
  "client_counts": [2, 3, 4, 5]
}
```

Partition：

- `STRATIFIED`
- `DIRICHLET_LABEL_SKEW`

Dirichlet：

\[
\mathbf p_k \sim Dirichlet(\alpha\mathbf 1_C)
\]

並保證：

\[
\bigcup_c U_c=U_{train}
\]

以及 clients pairwise disjoint。

---

## Prediction policies

- `FIRST_MATCH`
- `SIMPLE_VOTING`
- `STANDARD_VOTING`
- `GLOBAL_STRENGTH`

它們都在 evaluation/federated layer，**不是 LEM2 Core**。

---

## 數學 Core

`roughset/core.py` 保留：

- equivalence classes
- lower approximation
- LEM2 blocks
- pair selection
- minimal complex
- local covering
- rule induction

`roughset/reduct.py` 保留：

- positive region
- dependency degree
- exhaustive minimum-cardinality reduct search

原 V6.1 canonical reference 保存在 `reference/`，測試會直接做 parity comparison。

---

## Outputs

每個 dataset 會得到例如：

```text
summary.json
summary.csv
centralized_rules.csv
federated_rules.csv
local_metrics.csv
pairwise_jaccard.csv
conflict_groups.csv
conflict_cases.csv
order_distribution.csv
client_sweep.csv
```

啟用 paper lane 時另有：

```text
paper_protocol.json
paper_fold_metrics.csv
paper_comparison.json
```

總覽：

```text
outputs/all_datasets_summary.csv
outputs/run_manifest.json
```

---

## Paper replication lane

預設關閉：

```json
"paper": {
  "enabled": false,
  "reference": "WANG_2007",
  "cv_folds": 10
}
```

這條支線保留 V6.1 的：

```text
Full labeled data
→ minimum-cardinality reduct
→ LEM2
→ Global Strength
→ 10-fold CV
```

這是 historical replication lane；不是推薦的 modern leakage-free evaluation。

---

## 驗證

開發驗證：

```bash
python -m pytest -q
python -m compileall -q roughset main.py
```

V6.1 reference SHA-256：

```text
6dc1732f83944d4b99e36d03f97297e35aaff5fab40c01cc50cdc7d3fb469177
```

## One-click full policy run

`run.bat` is now the default full experiment launcher. It runs **every discovered dataset** through all configured prediction policies while preserving the evaluation mode in `config.json`. The default policy matrix is:

- `FIRST_MATCH`
- `SIMPLE_VOTING`
- `STANDARD_VOTING`
- `GLOBAL_STRENGTH`

The client-count sweep (`2, 3, 4, 5`) remains enabled according to `config.json`. `FIRST_MATCH` receives measured order-sensitivity analysis; `SIMPLE_VOTING`, `STANDARD_VOTING`, and `GLOBAL_STRENGTH` are marked order-invariant by design and are not presented as having empirically measured zero sensitivity. Results are isolated by policy under a timestamped batch folder, so policies do not overwrite one another.

```text
outputs/
  batch_runs/
    YYYYMMDD_HHMMSS/
      batch_summary.csv
      batch_manifest.json
      FIRST_MATCH/
      SIMPLE_VOTING/
      STANDARD_VOTING/
      GLOBAL_STRENGTH/
```

`outputs/latest_batch.txt` points to the most recent batch folder. If you only want the single policy named in `config.json`, use `run_single.bat`.

The batch runner intentionally does **not** force both HOLDOUT and K-fold in one click. It runs the evaluation mode currently selected in `config.json`; this prevents an accidental explosion of `4 policies × 10 folds × client sweep × order permutations`.

## Main strict reduct pipeline

The default main experiment now selects a minimum-cardinality reduct from each training split before LEM2. Centralized induction uses the selected pooled-training reduct; each federated client independently selects a reduct from its local training table and induces local rules using only that reduct. Test rows never enter reduct selection. Set `reduct.enabled` to `false` for the legacy all-condition-features-to-LEM2 ablation.

All minimum-cardinality candidates are retained. Induction uses the deterministic lexicographically first normalized candidate (`reduct_selection_policy: lexicographic_first_among_minimum_cardinality`). Batch execution builds one frozen structural artifact per dataset × fold × client count, then evaluates all configured resolvers against that same artifact.

The batch root now contains one `structural_summary.csv` row per dataset × fold × client count, a separate `resolver_summary.csv` row per resolver, and `research_chain_summary.csv`. Detailed structural tables are under `structural/<dataset>/`; resolver-specific metrics are under `resolver/<policy>/<dataset>/`. Fold aggregates with mean/std/min/max are written to `structural_summary_aggregate.csv` and `resolver_summary_aggregate.csv`. Existing per-policy output directories and CSV names are retained for compatibility.

The main lane is intentionally distinct from the Wang historical replication lane: main uses `split → train-only preprocessing/reduct → LEM2`; Wang keeps its historical full-labeled-data reduct protocol before CV. See [REDUCT_PIPELINE_DESIGN.md](docs/REDUCT_PIPELINE_DESIGN.md), [REDUCT_METRICS.md](docs/REDUCT_METRICS.md), and [BATCH_OUTPUT_SCHEMA.md](docs/BATCH_OUTPUT_SCHEMA.md).
