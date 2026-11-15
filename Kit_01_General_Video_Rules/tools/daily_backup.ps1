# Daily backup of the Claude-Workflow folder to its private GitHub repo, and of the clients repo inside it
# (Kit_04_Clients = a separate private repo since 13 Nov 2026, ignored by the system repo).
# Commits anything changed by hand (the post-commit hook pushes it); if nothing changed,
# it still pushes, so a commit that failed to upload earlier (offline) goes up now.
# Run by the Windows task "Claude-Workflow Daily Backup"; log: %LOCALAPPDATA%\ClaudeWorkflowBackup\backup.log
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $git) { $git = 'C:\Program Files\Git\cmd\git.exe' }
$logDir = Join-Path $env:LOCALAPPDATA 'ClaudeWorkflowBackup'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir 'backup.log'
function Log($m) { Add-Content $log ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) -Encoding UTF8 }

function Backup($repo, $tag) {
    & $git -C $repo add -A
    & $git -C $repo diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $n = (& $git -C $repo diff --cached --name-only | Measure-Object).Count
        $msg = "Daily auto-backup {0} ({1} files changed by hand)" -f (Get-Date -Format 'yyyy-MM-dd'), $n
        $out = & $git -C $repo commit -q -m $msg 2>&1
        if ($LASTEXITCODE -ne 0) {
            # The pre-commit hook (check_text.py) refused it: log why, then save anyway so no day goes un-backed-up.
            $why = (($out | ForEach-Object { "$_" }) -join ' ') -replace '\s+', ' '
            Log ("$tag pre-commit refused the backup, committing with --no-verify. Reason: " + $why.Trim())
            & $git -C $repo commit -q --no-verify -m ($msg + " [control characters - run check_text.py]")
        }
        if ($LASTEXITCODE -eq 0) { Log "$tag committed $n file(s)" } else { Log "$tag commit FAILED - nothing saved today" }
    } else {
        Log "$tag no changes"
    }
    if (-not (& $git -C $repo remote)) { Log "$tag no remote - local commit only"; return }
    & $git -C $repo push -q origin HEAD 2>$null
    if ($LASTEXITCODE -eq 0) { Log "$tag pushed: $(& $git -C $repo rev-parse --short HEAD)" } else { Log "$tag push failed (offline?) - will retry next run" }
}

Backup $root '[system]'
$clients = Join-Path $root 'Kit_04_Clients'
if (Test-Path (Join-Path $clients '.git')) { Backup $clients '[clients]' }
