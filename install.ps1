# install.ps1 — PyAutoClicker (Windows)
# One-liner:
# irm https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$OwnerRepo = "GoblinRules/PyAutoClicker"   # change if you fork/rename

# --- Resolve app URL (accept 200 OR 206; HEAD then GET fallback) ---
$OwnerRepo = "GoblinRules/PyAutoClicker"
$branches  = @("main","master")
$paths     = @("pyautoclicker.py","src/pyautoclicker.py","app/pyautoclicker.py","PyAutoClicker.py","trusty_clicker.py")

function Test-Exists($u) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Method Head -Uri $u -MaximumRedirection 5 -TimeoutSec 15
    return $r.StatusCode -in 200,206
  } catch {
    try {
      $r = Invoke-WebRequest -UseBasicParsing -Uri $u -Headers @{Range="bytes=0-0"} -MaximumRedirection 5 -TimeoutSec 15
      return $r.StatusCode -in 200,206
    } catch { return $false }
  }
}

$ScriptUrl = $null

# Try canonical first
$preferred = "https://raw.githubusercontent.com/$OwnerRepo/main/pyautoclicker.py"
if (Test-Exists $preferred) { $ScriptUrl = $preferred }
else {
  foreach ($b in $branches) {
    foreach ($p in $paths) {
      $u = "https://raw.githubusercontent.com/$OwnerRepo/$b/$p"
      if (Test-Exists $u) { $ScriptUrl = $u; break }
    }
    if ($ScriptUrl) { break }
  }
}

if (-not $ScriptUrl) {
  Write-Error "Could not find app file in $OwnerRepo. Checked: $($branches -join ', ') / $($paths -join ', ')"
  exit 1
}


# Icons (optional)
$IconIcoUrl = ($ScriptUrl -replace '/[^/]+$','/assets/pyautoclicker.ico')
$IconPngUrl = ($ScriptUrl -replace '/[^/]+$','/assets/pyautoclicker.png')

# --- Install locations ---
$InstallDir = Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$VenvDir    = Join-Path $InstallDir ".venv"
$Pyw        = Join-Path $VenvDir "Scripts\pythonw.exe"
$Py         = Join-Path $VenvDir "Scripts\python.exe"
New-Item -Force -ItemType Directory $InstallDir | Out-Null
New-Item -Force -ItemType Directory (Join-Path $InstallDir "assets") | Out-Null

Write-Host "Downloading app from $ScriptUrl" -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl -OutFile (Join-Path $InstallDir "pyautoclicker.py")
try { Invoke-WebRequest -UseBasicParsing $IconIcoUrl -OutFile (Join-Path $InstallDir "assets\pyautoclicker.ico") } catch {}
try { Invoke-WebRequest -UseBasicParsing $IconPngUrl -OutFile (Join-Path $InstallDir "assets\pyautoclicker.png") } catch {}

# --- Find Python 3 ---
function Get-PythonCmd {
  foreach ($c in @("py -3","py","python","python3")) {
    try {
      $v = & $env:ComSpec /c "$c -c ""import sys;print(sys.version_info[:2])"""
      if ($LASTEXITCODE -eq 0 -and $v) { return $c }
    } catch {}
  }
  $null
}
$pyCmd = Get-PythonCmd
if (-not $pyCmd) { Write-Warning "Python 3 required. Install it and rerun."; exit 1 }

Write-Host "Creating virtual environment…" -ForegroundColor Cyan
& $env:ComSpec /c "$pyCmd -m venv `"$VenvDir`""

Write-Host "Installing dependencies…" -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
& $Py -m pip install pynput pystray Pillow

# --- Shortcuts (with icon) ---
function New-Shortcut($Path,$Target,$Args,$WorkingDir,$Icon) {
  $shell = New-Object -ComObject WScript.Shell
  $lnk = $shell.CreateShortcut($Path)
  $lnk.TargetPath = $Target; $lnk.Arguments = $Args; $lnk.WorkingDirectory = $WorkingDir
  if (Test-Path $Icon) { $lnk.IconLocation = $Icon }
  $lnk.Save()
}
$StartMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PyAutoClicker"
New-Item -Force -ItemType Directory $StartMenu | Out-Null
$IconPath = Join-Path $InstallDir "assets\pyautoclicker.ico"
$Args     = "`"`"$InstallDir\pyautoclicker.py`"`""

New-Shortcut (Join-Path $StartMenu "PyAutoClicker.lnk") $Pyw $Args $InstallDir $IconPath
$Desktop = [Environment]::GetFolderPath('Desktop')
New-Shortcut (Join-Path $Desktop "PyAutoClicker.lnk")   $Pyw $Args $InstallDir $IconPath

Write-Host "Done! Installed to $InstallDir" -ForegroundColor Green
Write-Host "Launch via Start Menu or the desktop shortcut."
