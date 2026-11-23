# Federated Decision Making｜pip 安裝與 Adapter 交接指南

**v0.1.0，2026-11-24；研究用途／Alpha 版**。目標：把跨演算法的資料切分、聯邦分配、評估、執行及 Checkpoint 從 LEM2 抽離。

## 1. 套件命名與安裝

- PyPI 預定發行名稱：`federated-decision-making`（大小寫、底線與連字號會被 pip 正規化）。**尚未發布至 PyPI**，不能現在執行 `pip install Federated_decision_making` 並期待從 PyPI 安裝。
- Python 匯入名稱：`federated_decision_making`。
- CLI：`fdm`、`federated-decision-making`。
- **現在可行：** `python -m pip install /path/to/federated_decision_making-0.1.0-py3-none-any.whl`。
- **同步到 GitHub 分支後：** `python -m pip install 'git+https://github.com/Jimmy0307/LEM2.git@research/modular-platform-handover-20261123'`。

## 2. 共用執行 API

```python
from federated_decision_making.api import Capabilities, FitRequest, Predictions

class MyFittedModel:
    def predict(self, X):
        # X 永遠只有 Features，不能偷看 Test target。
        return Predictions(labels=['A']*len(X), covered=None, candidates=None)

    def diagnostics(self):
        return {'n_rules': None}

class MyPlugin:
    @property
    def capabilities(self):
        return Capabilities(algorithm='my_algo', federated_modes=('CENTRALIZED',))

    def fit(self, request: FitRequest):
        # 僅使用 request.train / request.clients 的 Development 資料。
        return MyFittedModel()
```

插件以 `entry_points` 自動註冊，不需要動 core：

```toml
[project.entry-points."federated_decision_making.algorithms"]
my_algo = "my_package.adapter:MyPlugin"
```

安裝 adapter Wheel 後，`fdm algorithms` 自動顯示；未安裝的 PRISM／RIPPER／DRSA 明確標示 **INTERFACE_RESERVED_NOT_INSTALLED**。

一個完整可執行、**非 PRISM** 的自動發現範例位於 `examples/lookup_adapter/`。

## 3. 統一 CLI（同資料集、同 Test、同 Seed 公平比較）

```bash
fdm algorithms
fdm run --case ./case.json --output ./results
fdm batch --manifest ./jobs.json --output ./results
fdm compare --results ./results --baseline majority --csv ./paired.csv
```

`case.json`：

```json
{
  "dataset_id":"housing_case_001",
  "csv":"/data/housing.csv",
  "target":"decision",
  "features":["a","b","c"],
  "algorithm":"lem2",
  "scenario":"FED_A01",
  "seed":1,
  "split":"64_16_20",
  "options":{"selection_policy":"STANDARD_VOTING","rule_variant":"B2_TRUE_AS_FALLBACK"}
}
```

以上 CSV path、target 和 features 只是假例，請依真正資料 schema 改寫。`split` 可選 `80_20`, `64_16_20`, `60_20_20`；三者共用外層 20% Test，同 seed，且不得以 Test 決定最優策略。此 v0.1.0 的 Validation 只是保留，尚未內建六策略Validation-first挑選流程。

輸出每個 model 的 `run_id.json` receipt：dataset、source_sha256、core+plugin code hash、algorithms、version、split、seed、scenario、features、Metrics、MAJORITY_ONLY、runtime、rule diagnostics（若有）。重跑相同 contract 時 `SKIPPED_VERIFIED`；來源或算法版本更動造成不同指紋，拒絕偷換既有結果。`fdm compare` 會明寫被比較的 Accuracy、baseline_accuracy 和 accuracy_difference_pp，而不是只寫差值。

## 4. LEM2 與其他演算法的依賴邊界

平台 wheel **不包含舊版 LEM2 引擎**，才能確保 Core 安裝獨立。`lem2` adapter 懶載入現有 repo 的 `fedrs/` 和 `roughset/`；請在完整 LEM2 git checkout 所在環境執行（或另把舊引擎封裝成獨立 wheel）。單獨安裝平台 wheel，`fdm algorithms` 會正確顯示 LEM2 `MISSING_ENGINE`，不是假裝可以跑。

PRISM、RIPPER 與 DRSA 需自行實作並安裝獨立 plugin wheel。RIPPER Ordered Rules、PRISM Covering Rules 與 DRSA 的 Dominance、單調有序決策不可硬套 LEM2 的六種投票法。對不支援的 Coverage/Conflict，保持 `null`，不要填 0。

目前 Client 都是假設同 Schema/Target 的 **水平聯邦離線模擬**，沒有真實跨機構加密協定或單模型 Spark 分散式學習。

## 5. SSH／Spark／Docker

```bash
# Docker（不含 legacy LEM2 引擎）
docker build -f Dockerfile.fdm -t federated-decision-making:0.1 .
docker run --rm federated-decision-making:0.1 algorithms

# SSH：主機權限／Known Hosts／遠端 Python／資料路徑由研究團隊提供
REMOTE_HOST='researcher@my-spark-login' DRY_RUN=1 bash scripts/fdm_ssh_run.sh \
  /srv/study/case.json /srv/study/results /srv/LEM2

# Spark：獨立 Dataset×Seed×Algorithm 任務，不是分散同一個 LEM2 模型
fdm-spark-bundle --output /tmp/fdm_spark_bundle.zip --legacy-repo /srv/LEM2
spark-submit --master yarn --deploy-mode client \
  --py-files /tmp/fdm_spark_bundle.zip \
  /srv/LEM2/src/federated_decision_making/spark_job.py \
  --manifest /srv/study/jobs.json --output /srv/study/results --partitions 8
```

Spark Python workers須能讀到相同資料路徑，且安裝一致的 numpy、pandas、PySpark 等依賴。第三方 Adapter 必須在每個 Executor 上**安裝同一版本的 Plugin Wheel**，Spark ZIP 本身不會安裝第三方套件。真實 SSH／Spark 遠端尚未驗收。

## 6. 研究封版與安全要求

- 原 `research/expanded-42seeds-20261120` 分支的 188×42實驗、19欄輸出與 Checkpoint不改動；新平台使用獨立輸出資料夾。
- 所有比較固定 source hash、seed、scenario、split、feature columns、Target；不混用已被Test最佳選法的 oracle 與實際固定策略。
- `source.pkl` 是 Python Pickle，不接受未驗證來源；ZIP不包括第三方原始資料、私鑰或公司內部資料。
- 缺失值預設拒絕；老師提到的缺失值方法尚無明確論文前不得冒名替代。
- 每個重型模型的 deadline / memory cap 需在SSH、Docker或 Spark Job層設定，核心CLI尚未內建2700s watchdog。
- 發布PyPI之前仍需確認套件名稱所有權、授權條款、Trusted Publisher、Git Tag、Release與安全掃描。本次沒有對PyPI送出任何發布請求。

## 7. 目前完成度

- Python Core API／Plugin Registry／Entry Points：已實作。
- Wheel build、獨立 Adapter Wheel 自動註冊、CLI batch/compare、Checkpoint Resume：本機驗收。
- LEM2：Adapter已寫，須在完整GitHub Repo做Parity；單獨Wheel預期顯示`MISSING_ENGINE`。
- PRISM/RIPPER/DRSA：接口存在，演算法本體未實作。
- Spark／SSH：腳本有，未登入合作者遠端，尚未端到端驗收。
