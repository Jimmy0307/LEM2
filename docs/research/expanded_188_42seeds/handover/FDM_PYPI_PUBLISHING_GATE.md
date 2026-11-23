# PyPI 發布 Gate｜尚未發布

套件註冊名：`federated-decision-making`（`pip install Federated_decision_making` 是同一個正規化名稱），import：`federated_decision_making`。

目前 **只有 Wheel 與 GitHub 研究分支，尚未發佈 PyPI**；上面的 pip install 名稱僅是未來發佈後才可使用的指令。發布前應驗證名稱所有權及相同名稱套件不存在、補齊 LICENSE、發行簽章、SBOM、維護者與研究資料來源，並獲正式授權。

## 不依賴 PyPI 的可立即安裝方式

```bash
python -m pip install ./dist/federated_decision_making-0.1.0-py3-none-any.whl
python -m pip install 'git+https://github.com/Jimmy0307/LEM2.git@research/modular-platform-handover-20261123'
fdm algorithms
```

### 外部 Adapter

```bash
python -m pip install ./examples/lookup_adapter
fdm algorithms
```

GitHub Actions / Docker 僅測試構建與操作，不在推送分支時自動上傳 PyPI。未驗證真實 SSH/Spark cluster，將正式部署另作 Gate。
