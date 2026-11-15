# install_ae_runner.ps1 - install the Claude hot-folder runner into the user Scripts folder of the newest AE version.
# Copies a Startup stub (runner starts on every AE launch) and the docked panel (Window > Claude Runner.jsx).
# Both point at claude_runner_core.jsx in the kit, so later edits to the core need only an AE restart, not a reinstall.
# usage: powershell -ExecutionPolicy Bypass -File install_ae_runner.ps1 [-Version 26.5]
param([string]$Version = "")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$core = (Join-Path $here "claude_runner_core.jsx") -replace "\\", "/"
$root = Join-Path $env:APPDATA "Adobe\After Effects"
if (-not $Version) {
    $Version = Get-ChildItem $root -Directory | Where-Object { $_.Name -match '^\d+\.\d+$' -and (Test-Path (Join-Path $_.FullName "Adobe After Effects $($_.Name) Prefs.txt")) } |
        Sort-Object { [version]$_.Name } | Select-Object -Last 1 -ExpandProperty Name
}
$scripts = Join-Path $root "$Version\Scripts"
foreach ($sub in "Startup", "ScriptUI Panels") { New-Item -ItemType Directory -Force (Join-Path $scripts $sub) | Out-Null }
$utf8 = New-Object System.Text.UTF8Encoding $true
$pairs = @(
    @{ src = "claude_runner_startup.jsx"; dst = "Startup\claude_runner_startup.jsx" },
    @{ src = "Claude Runner.jsx";         dst = "ScriptUI Panels\Claude Runner.jsx" }
)
foreach ($p in $pairs) {
    $text = [IO.File]::ReadAllText((Join-Path $here $p.src)) -replace "__CORE__", $core
    [IO.File]::WriteAllText((Join-Path $scripts $p.dst), $text, $utf8)
    "installed $($p.dst)"
}
New-Item -ItemType Directory -Force (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "claude-ae-queue\done") | Out-Null
"AE $Version -> $scripts  (restart AE; dock it once from Window > Claude Runner.jsx)"
