# Windows 工作樹完整性與未提交刪除：安全處理紀錄（2026-11-16）

## 已知事實、尚未驗證部分

Claude 回報 `D:\Desk\LEM2` 的 `git status` 出現**1,339個已追蹤檔案的未提交刪除**，同時在獨立工作樹 `D:\Desk\LEM2-worktrees\degeneracy-20261116` 成功提交 Gate 0–6、推送PR #6。這個回報不是遠端GitHub儲存庫刪除了1,339個檔案。PR #6目前以研究分支為base，原基線與報告檔案仍在遠端Git中。

ChatGPT與本次GitHub連接器**無法直接讀取或修改個人的Windows本機磁碟**，故不能宣稱已修復這1,339個本機刪除，也不可用GitHub端遠端提交推斷本機已恢復。

## 只讀診斷（PowerShell 5.1可用；勿在 C:\Users\user 的錯誤Git根目錄下執行）

```powershell
$main = "D:\Desk\LEM2"
$work = "D:\Desk\LEM2-worktrees\degeneracy-20261116"

Write-Host "=== Paths ==="
@($main,$work) | ForEach-Object { "$_ : $(Test-Path -LiteralPath $_)" }

Write-Host "=== Main exact git root / upstream / index and deleted files ==="
git -C $main rev-parse --show-toplevel
git -C $main rev-parse HEAD
git -C $main branch --show-current
git -C $main remote -v
git -C $main worktree list --porcelain
git -C $main status --short
$deleted = @(git -C $main ls-files --deleted)
"Tracked missing files: $($deleted.Count)"
$deleted | Select-Object -First 30

Write-Host "=== Isolated worktree state ==="
git -C $work rev-parse --show-toplevel
git -C $work branch --show-current
git -C $work status --short
```

如果 `git -C $main` 報錯或 `$main` 不存在，應先人工確認新搬移路徑是否正確；不可在未知Git根目錄使用復原指令。若有意保留本機刪除、尚未推送的工作或資料，應先建立**檔案級備份**與差異清單。

## 復原政策

- **預設 STOP**：在確認刪除是否屬於預期操作前，**不執行** `git restore`、`git reset --hard`、`git clean`、`Remove-Item`。
- 本次PR所有修正都在GitHub獨立研究分支進行，與主工作樹無依賴；不透過切換分支強迫覆蓋本機損失檔案。
- 復原只應針對確認為意外刪除、且沒有未備份本機修改的檔案進行；使用者應先審核完整 `git diff --name-status`、`git status --short` 與檔案清單，再決定何時恢復。
- 建議分離乾淨的研究工作樹與需要修復的主工作樹；不以PR合併替代本機文件恢復。

## 研究版控

- 原始研究分支：`research/report-ready-dashboard-20261109`
- 新方法分支：`research/federated-rule-degeneracy-redesign-20261116`
- 審閱PR：`https://github.com/Jimmy0307/LEM2/pull/6`，保持Draft，未授權合併。
