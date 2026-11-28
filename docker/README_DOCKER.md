# LEM2 Docker 重現套件

用一個容器重現 LEM2 聯邦 Rough Set 實驗。映像檔會從 GitHub 取出**固定版本**的程式，並鎖定 Python 3.12.3、numpy 2.3.5、pandas 2.2.3 等套件版本。

**原始資料不包含在映像檔中**：OpenML、PMLB、UCI 的資料在執行時下載，所以第一次跑需要網路。

## 1. 建置
```bash
git clone --branch research/lem2-docker-20261128 https://github.com/Jimmy0307/LEM2.git
cd LEM2
docker build -t lem2:20261128 -f docker/Dockerfile docker/
# 要鎖定到特定 commit：加上 --build-arg LEM2_EXPECT=<commit sha>
```
建置過程會從 GitHub 稀疏下載程式碼與兩份資料來源清單，不需要整個 300 MB 的 repo。

## 2. 先驗證環境
```bash
docker run --rm lem2:20261128 version      # 程式 commit 與套件版本
docker run --rm lem2:20261128 selftest     # 離線測試（約 1 分鐘）
docker run --rm -v "$PWD/lem2-work:/work" lem2:20261128 smoke
```
`smoke` 會用 `UCI20:iris` seed 1 跑兩種實驗，再和映像裡附的已發布結果逐值比對，最後應顯示 `SMOKE PASS`。

## 3. 執行
所有輸出都寫到容器內的 `/work`，請掛載一個主機資料夾（例如 `-v "$PWD/lem2-work:/work"`）。在 Linux 主機上建議加 `--user "$(id -u):$(id -g)"`，避免輸出檔案的權限問題。

```bash
# 單一資料集
docker run --rm -v "$PWD/lem2-work:/work" lem2:20261128 run expanded UCI20:iris 1,2,3
docker run --rm -v "$PWD/lem2-work:/work" lem2:20261128 run protocol EXT7:nursery 1

# 全部資料（有記憶體保護的平行排程）
docker run --rm -v "$PWD/lem2-work:/work" lem2:20261128 run-all expanded --max-jobs 8 --mem-budget-gb 12
docker run --rm -v "$PWD/lem2-work:/work" lem2:20261128 run-all protocol --datasets UCI20:iris,EXT7:nursery

# 進度與比對
docker run --rm -v "$PWD/lem2-work:/work" lem2:20261128 audit expanded
docker run --rm -v "$PWD/lem2-work:/work" -v "$PWD/published:/ref" lem2:20261128 verify /work/expanded /ref
```
- 資料集名稱用 `lem2 list` 查（共 188 份）。
- 已完成的模型會存成檢查點；中斷後重跑同一個指令會自動接續，不會重算。

## 4. 兩個實驗
| 名稱 | 內容 | 已發布結果 |
|---|---|---|
| `expanded` | 188 份資料 × 42 Seeds × 4 情境（集中式、Fed IID、α=0.5、α=0.1）× 6 策略 × 2 規則版本 | 分支 `research/expanded-42seeds-20261120` 的 `docs/research/expanded_188_42seeds/checkpoints/` |
| `protocol` | 同樣的組合，在同一個外層 20% 測試集上比較「80/20」與「80(64/16)/20」 | 執行中（2026-11-28 起） |

預設每個模型上限 2,700 秒，與已發布主實驗的合約相同。若要放寬時限，可傳入第 4 個參數 `TIMEOUT_S`，或在 `run-all` 加 `--timeout`；放寬後結果屬於另一份合約，要和主實驗分開陳述。

## 5. 資源需求與已知限制
- 每個模型只用 1 個 CPU 核心；平行度由 `--max-jobs` 決定。
- 記憶體大致是 **109 MB + 2 bytes × 規則數 × 訓練列數**。180 份資料每個模型都在 1.1 GB 以下。
- `openml_1169`、`openml_42732` 每個模型需要數十 GB 以上的記憶體和超過 30 小時，在一般機器上跑不完，見 `docs/research/expanded_188_42seeds/status_20261128/`。
- **記憶體保護的限制**：排程器讀的是 `/proc/meminfo`。在 Docker 裡它看到的是主機的記憶體，而不是 `--memory` 給容器的上限。如果用 `--memory` 限制容器，請把 `--mem-budget-gb` 和 `--max-jobs` 設得比容器上限小。
- 第一次跑會下載資料；下載失敗時會留下 `SOURCE_FAILURE.json`，重跑即可再試。

## 6. 與已發布結果的關係
- 映像中的預測程式包含「位元集合聯集」加速（`fedrs/predict.py`）。它的分數和預測與原始實作**完全相同**：
  - 隨機比對與真實資料逐值比對都已驗證；
  - `smoke` 也會再驗證一次。
- 執行合約（`RUN_MANIFEST.json`）裡的 `git_revision` 是這個映像的程式 commit，不會和已發布主實驗的 `56e293c` 相同；所以要比對的是**結果**，不是合約。
