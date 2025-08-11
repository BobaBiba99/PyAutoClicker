# install.ps1 — PyAutoClicker (Windows) v1.1
# One-liner: irm https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$OwnerRepo = "GoblinRules/PyAutoClicker"
$branches  = @("main","master")
$candidates = @("pyautoclicker.py","src/pyautoclicker.py","app/pyautoclicker.py","PyAutoClicker.py","trusty_clicker.py")

function Test-Url([string]$u) { try { (Invoke-WebRequest -UseBasicParsing -Method Head -Uri $u -TimeoutSec 10).StatusCode -eq 200 } catch { $false } }

$ScriptUrl = $null
foreach ($b in $branches) {
  $RawBase = "https://raw.githubusercontent.com/$OwnerRepo/$b"
  foreach ($f in $candidates) {
    $u = "$RawBase/$f"; if (Test-Url $u) { $ScriptUrl = $u; break }
  }
  if ($ScriptUrl) { break }
}
if (-not $ScriptUrl) { Write-Error "Could not find app file."; exit 1 }

$IconPngUrl = ($ScriptUrl -replace '/[^/]+$','/assets/pyautoclicker.png')
$IconIcoUrl = ($ScriptUrl -replace '/[^/]+$','/assets/pyautoclicker.ico')

$InstallDir = Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$VenvDir    = Join-Path $InstallDir ".venv"
$Pyw        = Join-Path $VenvDir "Scripts\pythonw.exe"
$Py         = Join-Path $VenvDir "Scripts\python.exe"
$IconDir    = Join-Path $InstallDir "assets"
$IconPng    = Join-Path $IconDir "pyautoclicker.png"
$IconIco    = Join-Path $IconDir "pyautoclicker.ico"

New-Item -Force -ItemType Directory $InstallDir | Out-Null
New-Item -Force -ItemType Directory $IconDir | Out-Null

Write-Host "Downloading app from $ScriptUrl" -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl -OutFile (Join-Path $InstallDir "pyautoclicker.py")
try { Invoke-WebRequest -UseBasicParsing $IconPngUrl -OutFile $IconPng } catch {}
try { Invoke-WebRequest -UseBasicParsing $IconIcoUrl -OutFile $IconIco } catch {}

function Get-PythonCmd {
  foreach ($c in @("py -3","py","python","python3")) {
    try { $v = & $env:ComSpec /c "$c -c ""import sys;print(sys.version_info[:2])""" ; if ($LASTEXITCODE -eq 0 -and $v) { return $c } } catch {}
  }; $null
}
$pyCmd = Get-PythonCmd
if (-not $pyCmd) { Write-Warning "Python 3 is required."; exit 1 }

Write-Host "Creating virtual environment…" -ForegroundColor Cyan
& $env:ComSpec /c "$pyCmd -m venv `"$VenvDir`""

Write-Host "Installing dependencies…" -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
& $Py -m pip install pynput pystray Pillow

Write-Host "Creating shortcuts…" -ForegroundColor Cyan
$Target     = $Pyw
$Arguments  = "`"`"$InstallDir\pyautoclicker.py`"`""
$WorkingDir = $InstallDir
$StartMenu  = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PyAutoClicker"
New-Item -Force -ItemType Directory $StartMenu | Out-Null
$shell = New-Object -ComObject WScript.Shell
$smLnk = $shell.CreateShortcut((Join-Path $StartMenu "PyAutoClicker.lnk"))
$smLnk.TargetPath = $Target; $smLnk.Arguments = $Arguments; $smLnk.WorkingDirectory = $WorkingDir
if (Test-Path $IconIco) { $smLnk.IconLocation = $IconIco }; $smLnk.Save()
$desktop = [Environment]::GetFolderPath('Desktop')
$dsLnk = $shell.CreateShortcut((Join-Path $desktop "PyAutoClicker.lnk"))
$dsLnk.TargetPath = $Target; $dsLnk.Arguments = $Arguments; $dsLnk.WorkingDirectory = $WorkingDir
if (Test-Path $IconIco) { $dsLnk.IconLocation = $IconIco }; $dsLnk.Save()
Write-Host "Done! Installed to $InstallDir" -ForegroundColor Green
