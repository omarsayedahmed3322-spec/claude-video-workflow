# ae_run.ps1 - run a JSX in After Effects through the Claude hot-folder runner and print its result.
# Replaces "AfterFX.exe -r" + the Bridge close/reopen cycle. Arabic text inside the script is fine (sent as UTF-8 with BOM),
# no \u conversion needed. The runner saves the project and copies it to _versions\ before the job (-NoVersion skips that).
# usage: powershell -ExecutionPolicy Bypass -File ae_run.ps1 -Jsx "<reel>\scripts\build_X.jsx" [-TimeoutSec 900] [-NoVersion]
# exit code: 0 OK, 1 script error, 2 runner not reachable / timeout.
param([Parameter(Mandatory = $true)][string]$Jsx, [int]$TimeoutSec = 900, [switch]$NoVersion)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$q = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "claude-ae-queue"
$hb = Join-Path $q "runner.heartbeat"
$afx = "C:\Program Files\Adobe\Adobe After Effects 2027\Support Files\AfterFX.exe"
function Get-HeartbeatAge {
    if (-not (Test-Path $hb)) { return 1e9 }
    return ((Get-Date) - (Get-Item $hb).LastWriteTime).TotalSeconds
}
$src = (Resolve-Path -LiteralPath $Jsx).Path
New-Item -ItemType Directory -Force $q | Out-Null

# 1. make sure the runner is alive (AE open, no modal dialog)
if ((Get-HeartbeatAge) -gt 5) {
    if (-not (Get-Process AfterFX -ErrorAction SilentlyContinue)) {
        "AE is not running -> starting it (the runner starts with it)"
        Start-Process $afx
        for ($i = 0; $i -lt 180 -and (Get-HeartbeatAge) -gt 5; $i++) { Start-Sleep 1 }
    } else {
        "runner heartbeat is stale -> AE is busy (render, modal dialog, Home screen?) - waiting up to 60s"
        for ($i = 0; $i -lt 60 -and (Get-HeartbeatAge) -gt 5; $i++) { Start-Sleep 1 }
    }
    if ((Get-HeartbeatAge) -gt 5) {
        "NO RUNNER: close any open dialog in AE, check Window > Claude Runner.jsx, or run install_ae_runner.ps1 and restart AE."
        exit 2
    }
}
if ((Get-Content $hb -TotalCount 4)[3] -eq "paused") { "runner is PAUSED (untick Pause in the Claude Runner panel)"; exit 2 }

# 2. queue the job: header + original script, UTF-8 with BOM
$name = ([IO.Path]::GetFileNameWithoutExtension($src) -replace '[^A-Za-z0-9_-]', '')
if (-not $name) { $name = "job" }
$id = (Get-Date -Format "yyyyMMdd_HHmmss_fff") + "_" + $name
$head = "// claude-src: $src`r`n"
if ($NoVersion) { $head += "// claude-no-version`r`n" }
$body = [IO.File]::ReadAllText($src)
# "// claude-include: <path>" lines are replaced by that file (path absolute or relative to the script) - #include doesn't work in jobs
# A path may start with <Claude-Workflow> = env CLAUDE_WORKFLOW (install.ps1), else the repo this script sits in.
$srcDir = Split-Path $src -Parent
$wf = if ($env:CLAUDE_WORKFLOW) { $env:CLAUDE_WORKFLOW } else { (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$body = [regex]::Replace($body, '(?m)^[ \t]*// claude-include:[ \t]*(.+?)[ \t]*\r?$', {
    param($m)
    $inc = $m.Groups[1].Value.Replace('<Claude-Workflow>', $wf)
    if (-not [IO.Path]::IsPathRooted($inc)) { $inc = Join-Path $srcDir $inc }
    if (-not (Test-Path -LiteralPath $inc)) { throw "claude-include not found: $inc" }
    "// --- included: $inc`r`n" + [IO.File]::ReadAllText($inc) + "`r`n// --- end include"
})
$tmp = Join-Path $q "$id.tmp"
[IO.File]::WriteAllText($tmp, $head + $body, (New-Object System.Text.UTF8Encoding $true))
Rename-Item $tmp "$id.jsx"   # atomic hand-off: the runner only picks up *.jsx

# 3. wait for the result
$res = Join-Path $q "$id.result.txt"
for ($i = 0; $i -lt $TimeoutSec -and -not (Test-Path $res); $i++) { Start-Sleep 1 }
if (-not (Test-Path $res)) { "TIMEOUT after ${TimeoutSec}s - job $id is still queued or running"; exit 2 }
Start-Sleep -Milliseconds 300
$out = Get-Content $res -Encoding UTF8
$out
if ($out[0] -ne "STATUS: OK") { exit 1 }
exit 0
