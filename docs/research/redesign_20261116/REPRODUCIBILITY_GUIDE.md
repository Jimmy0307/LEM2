# 重現指南（Reproducibility Guide）

目標：新的研究者能 Clone、建好環境、驗證已發布資料、跑低成本 Smoke Test、重算統計，並核對已發布結果。以下指令在 repo 根目錄執行；Windows 可用 Git Bash 或 PowerShell（把 `export X=Y` 改成 `$env:X="Y"`）。

## 0. 取得程式
```bash
git clone https://github.com/Jimmy0307/LEM2.git
cd LEM2
git checkout research/federated-rule-degeneracy-redesign-20261116
```
Clone 大小約 31 MB（GitHub 壓縮後）；研究 CSV 展開後約 228 MB，最大單檔 52 MB。

## 1. 環境
| 用途 | Python | 套件 |
|---|---|---|
| 重建研究（`fedrs/`、Gate 0–5） | 3.12–3.14 | `numpy>=2`、`pandas>=2.2`、`scipy>=1.13`、`scikit-learn>=1.5`、`pytest` |
| 原始軟體全套測試（含環境鎖定測試） | **3.11–3.13**（3.14 會被原始環境檢查刻意拒絕） | `pip install -r requirements-lock.txt "scipy>=1.13" "scikit-learn>=1.5" pytest` |

已發布資料由 Python 3.14.2、numpy 2.4.6、pandas 3.0.3、scipy 1.17.1、scikit-learn 1.8.0（Windows 11）產生，紀錄在各 `*_MANIFEST.json` 的 `environment` 欄。

```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install "numpy>=2" "pandas>=2.2" "scipy>=1.13" "scikit-learn>=1.5" pytest
```

## 2. 不需要下載原始資料就能完成的驗證（約 1 分鐘）
```bash
# (a) 全部研究資料檔的 SHA-256（LF 正規化，等於 Git blob）
python -m experiments.redesign_20261116.evidence_index
# (b) 從逐任務原始 CSV 獨立重算 H1/H2 與外部對照方向，並與已發布表逐值比對
python -m experiments.redesign_20261116.verify_g5_independent --check
# (c) 發布完整性、資料 Schema、單元與原始管線一致性測試
python -m pytest tests/test_fedrs_publication_integrity.py tests/test_fedrs_data_quality.py \
                 tests/test_fedrs_units.py tests/test_fedrs_parity.py -q
```
預期：`EVIDENCE_INDEX PASS`、`CROSSCHECK PASS`、所有測試通過（`test_fedrs_data_quality.py` 有 2 個 skip，因為記憶體量測只輸出 CONFIG 表）。

`verify_g5_independent` 會重寫 `G5_INDEPENDENT_RECOMPUTATION_20261116.*` 與 `G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv`。不同平台上浮點格式可能有極小差異，判斷依據是 `--check` 的容差比對，不是 `git diff`。

## 3. 原始資料（Gate 5 重新執行才需要）
OpenML 原始資料**不在 Git 內**（`data_cache/` 已 git-ignore，未重新散布）。
```bash
python -m experiments.redesign_20261116.confirmatory_registry
```
- 這個指令會下載並準備 `data_cache/openml/<did>/`。執行時若遇到既有的 `CONFIRMATORY_SOURCE_REGISTRY.csv`，會**拒絕覆寫**（見第 5 節）。正確做法：先把 `LEM2_REDESIGN_RUN_OUT` 設成暫存資料夾。另一個選擇是只用已登錄的 51 份 `parquet_url` 自行下載。
- 每份資料讀入時都會核對 `prepared_sha256`，不一致就停止。
- OpenML 服務可能暫時失敗（例如當初的 `albert` HTTP 500）。依預註冊，失敗的來源保留為失敗，**不替換**。
- 每份資料的授權寫在登錄表的 `licence` 欄。

## 4. 低成本 Smoke Test 與重新執行抽查
```bash
export LEM2_REDESIGN_RUN_OUT=/tmp/lem2_smoke                    # 不可指向已發布資料夾
python -m experiments.redesign_20261116.gate5_confirmatory --limit 14 --jobs 4   # 約 10 秒
python -m experiments.redesign_20261116.spotcheck_g5_rerun --scratch /tmp/lem2_spot --jobs 8   # 126 任務，約 80 秒（16 核）
```
`spotcheck_g5_rerun` 以固定亂數種子 20261116 抽 3 份來源（目前為 1169、1486、42769），取 Seeds 1005、1010，涵蓋三種分布與七種離散化，共 126 個任務。重新執行後，與已發布的 POLICIES／STRUCTURE／CONFIG 逐欄比對（排除計時欄）。2026-11-16 的結果是**全部逐值相同**（`data/G5_RERUN_SPOTCHECK_20261116.csv`）。

## 5. 防止覆寫已發布證據
`experiments/redesign_20261116/common.py` 有寫入保護：輸出目錄預設是已發布資料夾，若對應的 `*_MANIFEST.json` 已存在，執行會直接停止。只有同時符合以下兩點時才可設定 `LEM2_ALLOW_OVERWRITE_PUBLISHED=1`：
1. 有明確、可記錄的重新執行理由；
2. 舊結果會保留（例如改用新檔名，或先在新分支提交差異），並寫進修訂紀錄。

## 6. 完整重跑（成本）
| 實驗 | 指令 | 任務數 | 原始耗時（32 核） |
|---|---|---:|---:|
| Gate 1 | `python -m experiments.redesign_20261116.gate1_degeneracy` | 1,200 | 約 3 分鐘 |
| Gate 2 | `python -m experiments.redesign_20261116.gate2_discretization`（`--memory`） | 5,610 | 約 13 分鐘 |
| Gate 3 | `python -m experiments.redesign_20261116.gate3_noise` | 5,940 | 約 9 分鐘 |
| Gate 4 | `python -m experiments.redesign_20261116.gate2_discretization --p4` | 5,100 | 約 30 分鐘 |
| Gate 5 | `python -m experiments.redesign_20261116.gate5_confirmatory` | 10,710 | 約 50 分鐘 |

分析：`python -m experiments.redesign_20261116.analyze_g1`（`analyze_g2_g4`、`analyze_g3`、`analyze_g5` 同理）。分析程式會在原地重寫分析表，請在乾淨的工作樹執行，然後用 `git diff` 檢查差異。

Gate 1–4 需要 UCI20 原始資料，由原始軟體的 UCI 載入流程取得（`real_data/`、`ucimlrepo`）。

## 7. 核對網站
```bash
cd docs && python -m http.server 8765
# 開啟 http://127.0.0.1:8765/research/teacher_dashboard/redesign/
```
網站所用的 CSV 都在 `docs/research/teacher_dashboard/data/redesign_20261116/`，SHA 列在 `REDESIGN_SITE_MANIFEST.json`，由 `tests/test_fedrs_publication_integrity.py` 檢查。

## 8. 已知的重現限制
- Gate 1–4 的 Manifest `git_commit` 是執行當下的 HEAD；當時 `fedrs/` 尚未提交，因此不能精確指出程式版本。Gate 5 沒有這個問題（`e57e306`）。
- OpenML 資料可能更新或下線；以 `raw_sha256`／`prepared_sha256` 判斷是否為同一份資料。
- 來源獨立性只完成 metadata 與文獻層級（見 `SOURCE_INDEPENDENCE_REVIEW_20261116.md`）。
