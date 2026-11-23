> **2026-11-24 最新狀態（此條優先於以下11/23歷史紀錄）**：完整 Python 套件原始碼、`pyproject.toml`、外部 Adapter 範例、`fdm batch`／`fdm compare`、CI 及 Dockerfile 已同步至本 GitHub 隔離分支；可由 Git 直接 pip 安裝，不再需要先解壓舊版 ZIP 才能取得源碼。舊下文提到「ZIP 尚未同步此 Git 分支」是 **11/23 的歷史狀態**，已不適用。已完成 GitHub wheel build／external adapter／Docker 煙霧測試；實際合作者 SSH 與 Spark 叢集尚未驗收。以 [新版繁體中文安裝與 API 指南](FDM_PIP_ADAPTER_GUIDE_ZH.md) 為準。

# 多演算法研究平台交接｜Algorithm API + SSH + Spark

**2026-11-23｜負責人：跨演算法實驗整合｜狀態：API v1 介面已在隔離分支建立；全套可執行程式與測試以本次對話交付的 ZIP 擴充包發行，尚未全部寫回此 Git 分支。**

## 目標

1. 交接目前 188 資料集 × 42 Seeds 的 LEM2 研究，不覆蓋原 Checkpoint／原發表結果／現有自動發布。
2. 跨演算法統一輸入、分割、配對指標、來源 hash、執行日誌、結果收斂與檢查點。
3. **LEM2 只是第一個 Adapter**，PRISM、RIPPER、DRSA/DOMLEM 需各自實作 Fit/Predict；不可以把 LEM2 Reduct、Rule Union 或 FM/SV/STV 強灌給其他演算法。
4. 讓經授權的研究合作者在 Linux 終端／Docker／SSH 遠端／Spark 叢集執行多個實驗工作。

## 本次交付狀態（驗證與未驗證嚴格分開）

| 項目 | 狀態 | 證據 |
|---|---|---|
| `research_platform.api` FitRequest / Capabilities / Predictions / FittedPredictor | **GitHub 可讀 API v1** | `research_platform/api.py` |
| `research_platform.registry` 外部可信插件註冊 | **GitHub 可讀 API v1** | `research_platform/registry.py` |
| 完整 Runner、算法 Adapter、CLI、Dockerfile、SSH、Spark 調度、回歸測試 | **在 ChatGPT 交接 ZIP 中**，尚未完整同步此 Git 分支 | `LEM2_Modular_Research_Platform_Handover_20261123.zip`（對話附件） |
| 本機 Majority-only 共用API煙霧測試 | **PASS**：正常寫入 checkpoint；重跑會 SKIPPED_VERIFIED | 本次交付環境 |
| Python 快速單元測試 | **9 passed，3 deselected**（未包含需完整原倉庫的 LEM2 相容性／Legacy parity 測試） | 本次交付環境 |
| 在實際 LEM2 Repo 上的CI／Docker | **尚未驗收** | 需解壓交接ZIP後用 Github Actions 執行 |
| 真實 Spark 主機 SSH／Spark Executors | **尚未執行**：缺合作方主機／權限／部署環境 | 不得宣稱已部署 |
| PRISM、RIPPER、DRSA | **預留接口，尚未實作算法本體** | Registry 對未安裝方法會明確報錯 |

交接 ZIP SHA-256（當次上傳版本）：`caf64866438d4234db03869a4e6940b9d7dedd00da1edbca8675365a4cbe7d58`。

## API 容器無關契約

```python
class MyPlugin:
    @property
    def capabilities(self) -> Capabilities: ...
    def fit(self, request: FitRequest) -> FittedPredictor: ...

class MyModel:
    def predict(self, X: pandas.DataFrame) -> Predictions: ...
    def diagnostics(self) -> dict: ...
```

- FitRequest = Development（train）＋可選的同構 Clients＋目標欄＋明確 Features＋Seed＋參數＋可選序準則方向。
- Predict 只接到 **Features**，不帶真實 Test Label，杜絕由策略選法偷看 Test。
- Predictions = 預測 Labels；Coverage、Candidates 為可選欄，不能以0冒充不適用。
- Capabilities = 支援的聯邦模式、缺失值能力、決策序需求、規則可解釋性等。
- Output Receipt = Dataset ID、SHA256、Code Revision、Algorithm／Version、Feature Budget、Split、Seed、Accuracy／Balanced Accuracy／Macro-F1、Coverage／Conflict（若適用）、耗時及 Majority-only Baseline。
- 不會預設只選六個 Features：每次任務必須顯式指定。舊188×42的六 Features 仍留在原流程，兩者不可混成同一個比較結果。

## 安裝順序（需解壓 ChatGPT ZIP；不得用GitHub此分支當成完整可執行平台）

```bash
git clone --branch research/modular-platform-handover-20261123 https://github.com/Jimmy0307/LEM2.git
cd LEM2
# 從對話下載的 ZIP 裡解出 research_platform/、tests/、Dockerfile.research-platform 等到Repo根目錄：
unzip /path/to/LEM2_Modular_Research_Platform_Handover_20261123.zip -d .
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-core.txt scipy==1.16.3 pytest==9.0.2
python -m pytest -q tests/test_research_platform_api.py
python -m research_platform.cli list
docker build -f Dockerfile.research-platform -t research-platform:v1 .
```

實際 SSH／Spark 範例與共享 Data Mount 要求詳見解壓後的 `research_platform/README.md`。注意：根目錄需要 **完整既有 fedrs/、roughset/**，單獨下載交接ZIP不能執行 LEM2 Adapter。

## SSH 與 Spark 的精確定義

- SSH：指以經授權的研究者帳號登入遠端 Linux，先完成Clone、依賴與只讀資料掛載，再調用同一研究 CLI。SSH不是API，不要把任何私鑰、密碼、Host Config寫進Repo。
- Spark RDD：把 Dataset×Seed×Scenario×Algorithm **不同任務**分到 Executor，每個 Executor 仍然執行一個完整模型；目前**不是單一 LEM2 模型的 intra-model 分散式加速**，也不是替代精確約簡的CUDA實作。
- Spark各Executor需要同一套Python依賴與能存取的共享資料，不能假設 `--py-files` 會裝好 numpy/pandas/scipy或把CSV同步。
- 本ZIP只附原始程式／示例 CSV，不附188資料集原始第三方檔、source.pkl或現行大量checkpoint。

## 舊研究交接不可繞過的 Gate

1. 固定舊版主執行 `RUN_MANIFEST.json` 與 Git Revision；現有模型 SHA / SOURCE metadata 需驗證。檔案 `source.pkl` 是Pickle、需信任來源，不安全的共用檔不得直接載入。
2. 將舊主批 `checkpoints/` 與有效Manifest在相同的遠端運算目錄重建，先執行 `python -m experiments.expanded_42seeds_20261120.run --audit --output <path>`，取得完整性與缺漏表。
3. 若 `RUN_MANIFEST` 拒絕版本轉移，依既有 `tools/expanded_resume_20261122/README_TOOLS.md` 的 controlled migration，不修改/偽造Manifest來繞過。
4. 多個合作者不能同時寫入同一個舊checkpoint主目錄；採單一發表者／單一Merge Owner的結果治理。
5. 新演算法必須建立另外的輸出命名空間，**不得重用原19欄總表或偽裝成同一個LEM2檢查點**。

## 後續執行清單

- [x] 訂立 Algorithm API / Registry 和隔離分支
- [x] 交付本機可使用的擴充 ZIP，含 LEM2 / Majority-only plugin、CLI、Spark派工碼、Docker與SSH示例
- [x] Majority-only CLI 小樣、原子 checkpoint、重跑去重煙霧測試
- [ ] 將 ZIP 全部程式檔同步 GitHub 並執行完整版 CI、Docker/LEM2 parity gate
- [ ] 由遠端運算持有者提供 SSH Host Alias、Spark Master、Python/Java版本、部署模式、可用CPU/RAM、共享磁碟與安全要求
- [ ] 選定 PRISM、RIPPER、DRSA 的可再現實作與合法資料條件，補各算法 plugin
- [ ] 確認老師指定的缺失值論文與允許的 imputing protocol；不可使用未確認的替代方案
- [ ] 演算法合併評比資料表需固定同來源、同Seed、同Test、明確Baseline、失敗與TIMEOUT比例
