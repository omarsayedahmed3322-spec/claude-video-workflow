param([string]$Jsx, [string]$Prefix, [string]$Sheet, [string]$Result, [string]$Dir = "D:\AI\Claude\<project>\_build\")
# usage: .\run_and_sheet.ps1 -Dir "<reel>\scripts\" -Jsx NN_build.jsx -Result NN_result.txt -Prefix scNN_f -Sheet scNN_sheet.png
# Runs the JSX through the Claude Runner (ae_run.ps1), then tiles the PNGs it saved into a contact sheet.
$d = $Dir
$f = $d + $Result
Remove-Item $f -ErrorAction SilentlyContinue
Remove-Item ($d + $Prefix + "*.png") -ErrorAction SilentlyContinue
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "ae_run.ps1") -Jsx ($d + $Jsx)
if ($Result -and (Test-Path $f)) { Get-Content $f -Encoding UTF8 }
Start-Sleep 1
Add-Type -AssemblyName System.Drawing
$files = Get-ChildItem ($d + $Prefix + "*.png") | Sort-Object Name
$w = 225; $h = 400; $cols = 6
$rows = [math]::Ceiling($files.Count / $cols)
$bmp = New-Object System.Drawing.Bitmap ($w * $cols), (($h + 20) * $rows)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::Gray)
$font = New-Object System.Drawing.Font "Arial", 12
$i = 0
foreach ($p in $files) {
    $img = [System.Drawing.Image]::FromFile($p.FullName)
    $x = ($i % $cols) * $w; $y = [math]::Floor($i / $cols) * ($h + 20)
    $g.DrawImage($img, $x, $y + 20, $w, $h)
    $g.DrawString($p.BaseName, $font, [System.Drawing.Brushes]::Yellow, $x + 4, $y + 2)
    $img.Dispose(); $i++
}
$bmp.Save($d + $Sheet); $g.Dispose(); $bmp.Dispose()
"$i frames -> $Sheet"
