# ae_render.ps1 - background render with aerender (no GUI, AE stays usable), safe for Arabic folder names.
# Arabic paths break aerender from PowerShell 5.1, so the project folder and output folder are reached through
# ASCII junctions under C:\ae_jx\ (made once, reused). Renders the SAVED project: run any ae_run.ps1 job first
# (the runner saves before every job) or save in AE.
# -Preview : "Claude Preview Half" (draft, half res) for quick timing reviews; default is "Claude Final".
# Both need setup_render_templates.jsx run once (ae_run.ps1 -Jsx ...\ae_runner\setup_render_templates.jsx -NoVersion).
# usage: powershell -ExecutionPolicy Bypass -File ae_render.ps1 -Project "<reel>\X.aep" -Comp "00_Master_Reel" -Out "<reel>\exports - X\previews\SC01.mp4" [-StartFrame 0 -EndFrame 120] [-Preview] [-Type talking|montage|mg|ai-film|ugc]
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [Parameter(Mandatory = $true)][string]$Comp,
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$StartFrame = -1, [int]$EndFrame = -1,
    [switch]$Preview,
    [ValidateSet("", "talking", "montage", "mg", "ai-film", "ugc")][string]$Type = ""
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$aer = "C:\Program Files\Adobe\Adobe After Effects 2027\Support Files\aerender.exe"

function Get-AsciiDir([string]$dir) {
    if ($dir -notmatch '[^\x00-\x7F]') { return $dir }
    $md5 = [Security.Cryptography.MD5]::Create()
    $h = -join ($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($dir.ToLower())) | Select-Object -First 4 | ForEach-Object { $_.ToString("x2") })
    $j = "C:\ae_jx\$h"
    if (-not (Test-Path $j)) {
        New-Item -ItemType Directory -Force "C:\ae_jx" | Out-Null
        New-Item -ItemType Junction -Path $j -Target $dir | Out-Null
        Set-Content "C:\ae_jx\$h.txt" $dir -Encoding UTF8   # which folder this junction points to
    }
    return $j
}
function Get-AsciiPath([string]$path) {
    $leaf = Split-Path $path -Leaf
    if ($leaf -match '[^\x00-\x7F]') { throw "file name must be ASCII (folder names may be Arabic): $leaf" }
    return Join-Path (Get-AsciiDir (Split-Path $path -Parent)) $leaf
}

$projFull = (Resolve-Path -LiteralPath $Project).Path
$outDir = Split-Path $Out -Parent
New-Item -ItemType Directory -Force $outDir | Out-Null
$outFull = Join-Path (Resolve-Path -LiteralPath $outDir).Path (Split-Path $Out -Leaf)
if (Test-Path -LiteralPath $outFull) { Remove-Item -LiteralPath $outFull }
$p = Get-AsciiPath $projFull
$o = Get-AsciiPath $outFull
$rs = if ($Preview) { "Claude Preview Half" } else { "Claude Final" }
$aargs = @("-project", $p, "-comp", $Comp, "-output", $o, "-RStemplate", $rs, "-OMtemplate", "Claude H264 Audio", "-sound", "OFF")
if ($StartFrame -ge 0) { $aargs += @("-s", $StartFrame) }
if ($EndFrame -ge 0) { $aargs += @("-e", $EndFrame) }
"aerender $($aargs -join ' ')"
$t0 = Get-Date
& $aer @aargs 2>&1 | Where-Object { $_ -match 'PROGRESS:\s+Total|ERROR|WARNING|aerender' } | Select-Object -Last 15
$secs = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
if (-not (Test-Path -LiteralPath $outFull)) { "RENDER FAILED after ${secs}s - no output file"; exit 1 }
"rendered in ${secs}s -> $outFull"
# automatic QC (qc_reel.py): table pass/warn/FAIL + .qc.json + .qc_sheet.png next to the render.
# -Type talking|montage|mg|ai-film|ugc picks the loudness row of 05 s6 (loudness table); without it loudness is printed with no verdict.
# A FAIL (no audio, silent, clipping, not 9:16...) = this version is not sent to Omar.
$qc = Join-Path $PSScriptRoot "qc_reel.py"
$qargs = @("-I", "-X", "utf8", $qc, $outFull)
if ($Type) { $qargs += @("--type", $Type) }
& python @qargs
if ($LASTEXITCODE -ne 0) { "QC FAIL - don't send this version (see the table above)" }
exit 0
