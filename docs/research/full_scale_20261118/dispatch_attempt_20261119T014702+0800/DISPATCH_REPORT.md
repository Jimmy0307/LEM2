# Smoke workflow 觸發失敗

直接對指定研究分支執行 workflow_dispatch 時，GitHub 回傳：

```text
HTTP 404: Not Found (https://api.github.com/repos/Jimmy0307/LEM2/actions/workflows/full-scale-six-policy-20261118.yml)
```

沒有建立 workflow run；未啟動全量實驗。GitHub 規定 workflow_dispatch 的檔案須存在於預設分支，但此任務禁止修改 main。

https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch
