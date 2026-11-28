# LEM2 autopilot (2026-11-28): keep the main and protocol runs alive, then finalize and push.
#   * every 30 min: read run state from WSL; relaunch a driver only if its run is incomplete, no driver
#     and no launcher is running, and the last relaunch of that run was > 25 min ago
#   * when both runs are complete: stop the background publisher, publish remaining main datasets once,
#     generate the report data, commit and push (fetch + rebase on conflict, never force), write DONE
# Launch detached (WMI) so it survives the Claude session:  powershell -NoProfile -ExecutionPolicy Bypass
#   -WindowStyle Hidden -File D:\Desk\LEM2_expanded_resume\tools\23_autopilot.ps1
param([switch]$Once)
$ErrorActionPreference = 'Continue'
$Tools   = 'D:\Desk\LEM2_expanded_resume\tools'
$Log     = 'D:\Desk\LEM2_expanded_resume\reports\autopilot.log'
$Done    = 'D:\Desk\LEM2_expanded_resume\reports\AUTOPILOT_DONE'
$WT      = 'D:\Desk\LEM2-worktrees\expanded-42seeds-results'
$Branch  = 'research/expanded-42seeds-20261120'
$MainExpected = 31584      # 188 x 42 x 4 (includes recorded timeouts)
$ProtExpected = 31248      # 186 x 42 x 4 (openml_1169 and openml_42732 excluded)
$lastLaunch = @{ main = [datetime]::MinValue; protocol = [datetime]::MinValue }

function Write-Log([string]$m) { Add-Content -Path $Log -Encoding utf8 -Value ("{0} {1}" -f (Get-Date -Format s), $m) }

function Get-State {
    $raw = & wsl.exe -d Ubuntu --exec bash /mnt/d/Desk/LEM2_expanded_resume/tools/autopilot_state.sh 2>$null
    try { return (($raw | Out-String).Trim() | ConvertFrom-Json) } catch { Write-Log "state parse failed: $raw"; return $null }
}

function Start-Detached([string]$cmd) {
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
    return $r.ReturnValue
}

function Ensure-Running($s, [string]$name, [int]$decided, [int]$expected, [int]$driver, [int]$launcher, [string]$script) {
    if ($decided -ge $expected) { return }
    if ($driver -gt 0 -or $launcher -gt 0) { return }
    if (((Get-Date) - $lastLaunch[$name]).TotalMinutes -lt 25) { return }
    $rc = Start-Detached "wsl.exe -d Ubuntu --exec bash /mnt/d/Desk/LEM2_expanded_resume/tools/$script"
    $lastLaunch[$name] = Get-Date
    Write-Log "RELAUNCH $name (decided $decided/$expected, no driver) rc=$rc"
}

function Invoke-Git([string[]]$GitArgs) {
    $out = & git -C $WT @GitArgs 2>&1
    Write-Log ("git {0} -> {1}" -f ($GitArgs -join ' '), (($out | Out-String).Trim() -replace "`r?`n", ' | '))
    return $LASTEXITCODE
}

function Finalize {
    Write-Log 'FINALIZE start'
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'publish\.py' -and $_.CommandLine -notmatch '--once' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Log "stopped background publisher $($_.ProcessId)" }
    & python -I "$Tools\publish.py" --main '\\wsl.localhost\Ubuntu\home\user\lem2_runs\expanded_188_42seeds' --worktree $WT --log 'D:\Desk\LEM2_expanded_resume\reports\publish.log' --once 2>&1 | Out-Null
    Write-Log "publish --once exit=$LASTEXITCODE"
    $out = '/mnt/d/Desk/LEM2-worktrees/expanded-42seeds-results/docs/research/expanded_188_42seeds/report_final'
    $rep = & wsl.exe -d Ubuntu --exec bash -lc "cd /home/user/lem2_protocol && /home/user/lem2_venv/bin/python -I /mnt/d/Desk/LEM2_expanded_resume/tools/report_data.py --out $out" 2>&1
    Write-Log ("report_data: " + (($rep | Out-String).Trim() -replace "`r?`n", ' | '))
    if ($LASTEXITCODE -ne 0) { Write-Log 'report_data FAILED; will retry next cycle'; return $false }
    $dst = Join-Path $WT 'tools\expanded_resume_20261122'
    foreach ($f in 'report_data.py', 'autopilot_state.sh', '23_autopilot.ps1', '21_protocol_compare_pipeline.sh', 'orchestrate.py') {
        Copy-Item (Join-Path $Tools $f) (Join-Path $dst $f) -Force
    }
    Invoke-Git @('add', 'docs/research/expanded_188_42seeds/report_final', 'tools/expanded_resume_20261122') | Out-Null
    $msg = "docs(expanded): final report data (main 188x42, accelerated supplementary, 80/20 vs nested protocol comparison) [skip ci]`n`nGenerated automatically by tools/expanded_resume_20261122/23_autopilot.ps1 after all runs completed.`nMeans only (dataset-level, seeds averaged first); openml_1169 and openml_42732 excluded (infeasible).`n`nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    $msgFile = Join-Path $env:TEMP 'lem2_autopilot_commit.txt'
    [IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
    Invoke-Git @('commit', '-F', $msgFile) | Out-Null
    for ($i = 0; $i -lt 5; $i++) {
        if ((Invoke-Git @('push', 'origin', $Branch)) -eq 0) { Write-Log 'FINALIZE pushed'; return $true }
        Invoke-Git @('fetch', 'origin', $Branch) | Out-Null
        if ((Invoke-Git @('rebase', "origin/$Branch")) -ne 0) { Invoke-Git @('rebase', '--abort') | Out-Null; Write-Log 'rebase failed; manual attention needed'; return $false }
        Start-Sleep -Seconds 30
    }
    return $false
}

Write-Log "autopilot start (pid $PID)"
while (-not (Test-Path $Done)) {
    $s = Get-State
    if ($null -ne $s) {
        Write-Log ("state main {0}/{1} driver={2} | protocol {3}/{4} driver={5}" -f $s.main_decided, $MainExpected, $s.main_driver, $s.protocol_decided, $ProtExpected, $s.protocol_driver)
        if (-not $Once) {
            Ensure-Running $s 'main' $s.main_decided $MainExpected $s.main_driver $s.main_launcher '17_detached_pipeline_defer.sh'
            Ensure-Running $s 'protocol' $s.protocol_decided $ProtExpected $s.protocol_driver $s.protocol_launcher '21_protocol_compare_pipeline.sh'
            if ($s.main_decided -ge $MainExpected -and $s.protocol_decided -ge $ProtExpected -and $s.main_driver -eq 0 -and $s.protocol_driver -eq 0) {
                if (Finalize) { Set-Content -Path $Done -Value (Get-Date -Format s); Write-Log 'AUTOPILOT DONE'; break }
            }
        }
    }
    if ($Once) { break }
    Start-Sleep -Seconds 1800
}
Write-Log 'autopilot exit'
