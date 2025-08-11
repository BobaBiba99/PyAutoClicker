# install.ps1 — PyAutoClicker (Windows, simple)
# One-liner:
# irm https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

# ---- Repo paths (hard-coded; case sensitive) ----
$ScriptUrl  = "https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/pyautoclicker.py"
$IconIcoUrl = "https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/assets/pyautoclicker.ico"
$IconPngUrl = "https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/assets/pyautoclicker.png"

# ---- Install locations ----
$InstallDir = Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$VenvDir    = Join-Path $InstallDir ".venv"
$Pyw        = Join-Path $VenvDir "Scripts\pythonw.exe"
$Py         = Join-Path $VenvDir "Scripts\python.exe"

New-Item -Force -ItemType Directory $InstallDir | Out-Null
New-Item -Force -ItemType Directory (Join-Path $InstallDir "assets") | Out-Null

Write-Host "Downloading app…" -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl  -OutFile (Join-Path $InstallDir "pyautoclicker.py")
try { Invoke-WebRequest -UseBasicParsing $IconIcoUrl -OutFile (Join-Path $InstallDir "assets\pyautoclicker.ico") } catch {}
try { Invoke-WebRequest -UseBasicParsing $IconPngUrl -OutFile (Join-Path $InstallDir "assets\pyautoclicker.png") } catch {}

# ---- Find Python 3 ----
function Get-PythonCmd {
  foreach ($c in @("py -3","py","python","python3")) {
    try {
      $v = & $env:ComSpec /c "$c -c ""import sys;print(sys.version_info[:2])"""
      if ($LASTEXITCODE -eq 0 -and $v) { return $c }
    } catch {}
  }
  return $null
}
$pyCmd = Get-PythonCmd
if (-not $pyCmd) { Write-Error "Python 3 is required. Install it and rerun."; exit 1 }

Write-Host "Creating virtual environment…" -ForegroundColor Cyan
& $env:ComSpec /c "$pyCmd -m venv `"$VenvDir`""

Write-Host "Installing dependencies…" -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
& $Py -m pip install pynput pystray Pillow

# ---- Shortcuts (with icon) ----
function New-Shortcut($Path, $Target, $ArgLine, $WorkingDir, $Icon) {
  $shell = New-Object -ComObject WScript.Shell
  $lnk = $shell.CreateShortcut($Path)
  $lnk.TargetPath = $Target
  $lnk.Arguments  = [string]$ArgLine
  $lnk.WorkingDirectory = $WorkingDir
  if (Test-Path $Icon) { $lnk.IconLocation = $Icon }
  $lnk.Save()
}

$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PyAutoClicker"
New-Item -Force -ItemType Directory $StartMenu | Out-Null

$IconPath     = Join-Path $InstallDir "assets\pyautoclicker.ico"
$ShortcutArgs = '"' + (Join-Path $InstallDir "pyautoclicker.py") + '"'

New-Shortcut (Join-Path $StartMenu "PyAutoClicker.lnk") $Pyw $ShortcutArgs $InstallDir $IconPath
$Desktop = [Environment]::GetFolderPath('Desktop')
New-Shortcut (Join-Path $Desktop "PyAutoClicker.lnk")   $Pyw $ShortcutArgs $InstallDir $IconPath

Write-Host "Done! Installed to $InstallDir" -ForegroundColor Green
Write-Host "Launch via Start Menu or the desktop shortcut."
