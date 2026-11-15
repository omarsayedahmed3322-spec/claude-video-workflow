# Copies every skill in Kit_01\skills to the Claude Code skills folder on this PC (~\.claude\skills).
# The Kit copy is the master: edit it there, then run:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "<Claude-Workflow>\Kit_01_General_Video_Rules\tools\sync_skills.ps1"
# -Dst: another skills folder (install.py passes <ClaudeDir>\skills, e.g. a temp folder for a dry test).
# Default: $env:CLAUDE_CONFIG_DIR\skills if Claude Code is pointed at another config dir, else ~\.claude\skills.
param([string]$Dst)
$src = Join-Path $PSScriptRoot '..\skills'
if (-not $Dst) {
    $cfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $env:USERPROFILE '.claude' }
    $Dst = Join-Path $cfg 'skills'
}
Get-ChildItem $src -Directory | Where-Object { $_.Name -notlike '_*' } | ForEach-Object {   # _TEMPLATE etc. are not skills
    $target = Join-Path $Dst $_.Name
    New-Item -ItemType Directory -Force $target | Out-Null
    Copy-Item (Join-Path $_.FullName '*') $target -Recurse -Force
    "synced: $($_.Name) -> $target"
}
