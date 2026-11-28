# Host memory watchdog: throttles NEW job admission in the WSL run when Windows
# commit charge or available memory gets tight. Never kills any process.
$ErrorActionPreference = 'Continue'
$control = '\\wsl.localhost\Ubuntu\home\user\lem2_runs\expanded_188_42seeds\ORCHESTRATOR_CONTROL.json'
$doneFlag = '\\wsl.localhost\Ubuntu\home\user\lem2_runs\expanded_188_42seeds\ORCHESTRATOR_DONE'
$log = 'D:\Desk\LEM2_expanded_resume\reports\host_watchdog.log'
$normal = '{"max_jobs": 12, "max_heavy": 9, "mem_budget_gb": 14, "mem_reserve_gb": 2.0}'  # 2026-11-25: raised after VM/overlay closed
$emergency = '{"max_jobs": 4, "max_heavy": 2, "mem_budget_gb": 5, "mem_reserve_gb": 3.0}'
$mode = 'unknown'   # decided on the first check
$calmMinutes = 0
# The pagefile is system-managed (grows on demand), so physical availability is
# the primary signal; commit ratio only guards against a near-total commit.

function Write-Log([string]$msg) {
    Add-Content -Path $log -Value ("{0} {1}" -f (Get-Date -Format s), $msg) -Encoding utf8
}

function Set-Control([string]$json) {
    try {
        $tmp = "$control.wdtmp"
        [IO.File]::WriteAllText($tmp, $json)
        Move-Item -Path $tmp -Destination $control -Force
        return $true
    } catch {
        Write-Log "control write failed: $($_.Exception.Message)"
        return $false
    }
}

Write-Log 'watchdog start'
while (-not (Test-Path $doneFlag)) {
    try {
        $c = (Get-Counter '\Memory\Committed Bytes', '\Memory\Commit Limit', '\Memory\Available MBytes').CounterSamples
        $ratio = $c[0].CookedValue / $c[1].CookedValue
        $avail = $c[2].CookedValue
        $tight = ($ratio -gt 0.98) -or ($avail -lt 2000)
        $calm = ($ratio -lt 0.95) -and ($avail -gt 2500)  # 2026-11-25: WSL is capped at 10 GB, so 2.5 GB host headroom is enough
        if ($tight -and $mode -ne 'emergency') {
            if (Set-Control $emergency) { $mode = 'emergency'; $calmMinutes = 0 }
            Write-Log ("EMERGENCY throttle: commit={0:P1} availMB={1:N0}" -f $ratio, $avail)
        } elseif ($mode -eq 'unknown') {
            if (Set-Control $normal) { $mode = 'normal' }
            Write-Log ("start in normal limits: commit={0:P1} availMB={1:N0}" -f $ratio, $avail)
        } elseif ($mode -eq 'emergency') {
            if ($calm) { $calmMinutes++ } else { $calmMinutes = 0 }
            if ($calmMinutes -ge 10 -and (Set-Control $normal)) {
                $mode = 'normal'
                Write-Log ("restored normal limits: commit={0:P1} availMB={1:N0}" -f $ratio, $avail)
            }
        }
        if ((Get-Date).Minute % 30 -eq 0) {
            Write-Log ("heartbeat mode={0} commit={1:P1} availMB={2:N0}" -f $mode, $ratio, $avail)
        }
    } catch {
        Write-Log "check failed: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 60
}
Write-Log 'run finished; watchdog exit'
