# install.ps1 — PyAutoClicker (Windows, simple + Python auto-install)
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

# ---- Get an existing Python, if present ----
function Get-PythonCmd {
  foreach ($c in @("py -3","py","python","python3")) {
    try {
      $v = & $env:ComSpec /c "$c -c ""import sys;print(sys.version_info[:2])""" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v) { return $c }
    } catch {}
  }
  return $null
}

# ---- Get an existing Python, if present ----
function Get-PythonCmd {
  foreach ($c in @("py -3","py","python","python3")) {
    try {
      $v = & $env:ComSpec /c "$c -c ""import sys;print(sys.executable)""" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v) { return $c }
    } catch {}
  }
  return $null
}

# ---- Try to locate python.exe on disk (even if PATH isn't refreshed) ----
function Find-LocalPython {
  $candidates = @()

  # Common per-user locations
  $candidates += Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
  $candidates += Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"

  # Common machine-wide locations
  $pf = ${env:ProgramFiles}
  $pf86 = ${env:ProgramFiles(x86)}
  if ($pf)   { $candidates += (Join-Path $pf   "Python312\python.exe"), (Join-Path $pf   "Python311\python.exe") }
  if ($pf86) { $candidates += (Join-Path $pf86 "Python312-32\python.exe"), (Join-Path $pf86 "Python311-32\python.exe") }

  foreach ($p in $candidates) { if (Test-Path $p) { return "`"$p`"" } }
  return $null
}

# ---- Ensure Python is installed (per-user), otherwise install it ----
function Ensure-Python {
  $cmd = Get-PythonCmd
  if ($cmd) { return $cmd }

  Write-Host "Python not found — installing Python 3 (per-user)..." -ForegroundColor Yellow

  $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "win32" }
  $versions = @("3.12.5","3.11.9")
  $installed = $false

  foreach ($ver in $versions) {
    $url = "https://www.python.org/ftp/python/$ver/python-$ver-$arch.exe"
    $tmp = Join-Path $env:TEMP ("python-$ver-$arch.exe")
    try {
      Invoke-WebRequest -UseBasicParsing $url -OutFile $tmp
      if (Test-Path $tmp) {
        $args = "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 SimpleInstall=1"
        Start-Process -FilePath $tmp -ArgumentList $args -Wait
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        $installed = $true
        break
      }
    } catch { }
  }

  if (-not $installed) {
    # Fallback to winget (try multiple IDs)
    $wingetOK = $false
    try { $null = winget --version; $wingetOK = $true } catch { $wingetOK = $false }
    if ($wingetOK) {
      $ids = @("Python.Python.3.12","Python.Python.3.11")
      foreach ($id in $ids) {
        try {
          winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements --source winget
          $installed = $true
          break
        } catch { }
      }
    }
  }

  # Re-detect, including scanning typical folders (PATH may not refresh yet)
  $cmd = Get-PythonCmd
  if (-not $cmd) { $cmd = Find-LocalPython }

  if (-not $cmd) {
    Write-Error "Python installation appears to have failed. Please install manually (python.org or Microsoft Store), then re-run."
    exit 1
  }
  return $cmd
}

  # Prefer python.org installer (pinned version); fall back to winget if needed.
  $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "win32" }
  $ver  = "3.12.5"   # update here when you want a newer default
  $url  = "https://www.python.org/ftp/python/$ver/python-$ver-$arch.exe"
  $tmp  = Join-Path $env:TEMP ("python-$ver-$arch.exe")

  $downloaded = $false
  try {
    Invoke-WebRequest -UseBasicParsing $url -OutFile $tmp
    $downloaded = (Test-Path $tmp)
  } catch {
    $downloaded = $false
  }

  if ($downloaded) {
    # Silent per-user install, add to PATH, include pip & launcher
    $args = "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 SimpleInstall=1"
    Start-Process -FilePath $tmp -ArgumentList $args -Wait
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  } else {
    Write-Host "Direct download failed; trying winget..." -ForegroundColor Yellow
    try {
      winget install -e --id Python.Python.3.12 --source winget --silent --accept-package-agreements --accept-source-agreements
    } catch {
      Write-Error "Couldn’t install Python automatically. Install it from https://www.python.org/downloads/ and re-run." ; exit 1
    }
  }

  # Re-detect
  $cmd = Get-PythonCmd
  if (-not $cmd) {
    Write-Error "Python installation appears to have failed. Please install manually, then re-run." ; exit 1
  }
  return $cmd
}

# ---- Download app + icons ----
Write-Host "Downloading app…" -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl  -OutFile (Join-Path $InstallDir "pyautoclicker.py")
try { Invoke-WebRequest -UseBasicParsing $IconIcoUrl -OutFile (Join-Path $InstallDir "assets\pyautoclicker.ico") } catch {}
try { Invoke-WebRequest -UseBasicParsing $IconPngUrl -OutFile (Join-Path $InstallDir "assets\pyautoclicker.png") } catch {}

# ---- Make sure Python exists (install if missing) ----
$pyCmd = Ensure-Python

# ---- Create venv + deps ----
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
