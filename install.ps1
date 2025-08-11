# install.ps1 — PyAutoClicker (Windows)
# Usage: irm https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$OwnerRepo = "<you>/PyAutoClicker"   # TODO: change to your GitHub user/repo
$RawBase   = "https://raw.githubusercontent.com/$OwnerRepo/main"
$ScriptUrl = "$RawBase/pyautoclicker.py"
$IconUrl   = "$RawBase/assets/clicker.png"  # optional

$InstallDir = Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$VenvDir    = Join-Path $InstallDir ".venv"
$Pyw        = Join-Path $VenvDir "Scripts\pythonw.exe"
$Py         = Join-Path $VenvDir "Scripts\python.exe"

New-Item -Force -ItemType Directory $InstallDir | Out-Null
New-Item -Force -ItemType Directory (Join-Path $InstallDir "assets") | Out-Null

Write-Host "Downloading app…" -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl -OutFile (Join-Path $InstallDir "pyautoclicker.py")
try { Invoke-WebRequest -UseBasicParsing $IconUrl -OutFile (Join-Path $InstallDir "assets\clicker.png") } catch {}

function Get-PythonCmd {
  $candidates = @("py -3", "py", "python", "python3")
  foreach ($c in $candidates) {
    try {
      $v = & $env:ComSpec /c "$c -c ""import sys;print(sys.version_info[:2])""" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v) { return $c }
    } catch {}
  }
  return $null
}
$pyCmd = Get-PythonCmd
if (-not $pyCmd) { Write-Warning "Python 3 required. Install it, then run this again."; exit 1 }

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
$smLnk.TargetPath = $Target; $smLnk.Arguments = $Arguments; $smLnk.WorkingDirectory = $WorkingDir; $smLnk.Save()
$desktop = [Environment]::GetFolderPath('Desktop')
$dsLnk = $shell.CreateShortcut((Join-Path $desktop "PyAutoClicker.lnk"))
$dsLnk.TargetPath = $Target; $dsLnk.Arguments = $Arguments; $dsLnk.WorkingDirectory = $WorkingDir; $dsLnk.Save()

Write-Host "Done! Installed to $InstallDir" -ForegroundColor Green
Write-Host "Launch via Start Menu or the desktop shortcut."
