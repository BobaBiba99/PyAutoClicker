# install.ps1 — PyAutoClicker (Windows) v1.0
# One-liner: irm https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

# --- Repo ---
$OwnerRepo = "GoblinRules/PyAutoClicker"   # change only if you fork/rename

# Try both branches and common file locations
$branches  = @("main","master")
$candidates = @(
  "pyautoclicker.py",
  "src/pyautoclicker.py",
  "app/pyautoclicker.py",
  "PyAutoClicker.py",         # legacy casing
  "trusty_clicker.py"         # legacy name
)

function Test-Url($u) {
  try { (Invoke-WebRequest -UseBasicParsing -Method Head -Uri $u -TimeoutSec 10).StatusCode -eq 200 }
  catch { $false }
}

$ScriptUrl = $null
$RawBaseTried = @()
foreach ($b in $branches) {
  $RawBase = "https://raw.githubusercontent.com/$OwnerRepo/$b"
  foreach ($f in $candidates) {
    $u = "$RawBase/$f"
    if (Test-Url $u) { $ScriptUrl = $u; break }
  }
  $RawBaseTried += $RawBase
  if ($ScriptUrl) { break }
}
if (-not $ScriptUrl) {
  Write-Error "Could not find app file in $($RawBaseTried -join ', '). Tried: $($candidates -join ', ')"
  exit 1
}

# Optional icon (ignore if missing)
$IconUrl = ($ScriptUrl -replace '/[^/]+$','/assets/clicker.png')

# --- Install locations ---
$InstallDir = Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$VenvDir    = Join-Path $InstallDir ".venv"
$Pyw        = Join-Path $VenvDir "Scripts\pythonw.exe"
$Py         = Join-Path $VenvDir "Scripts\python.exe"

New-Item -Force -ItemType Directory $InstallDir | Out-Null
New-Item -Force -ItemType Directory (Join-Path $InstallDir "assets") | Out-Null

Write-Host "Downloading app from $ScriptUrl" -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl -OutFile (Join-Path $InstallDir "pyautoclicker.py")
try { Invoke-WebRequest -UseBasicParsing $IconUrl -OutFile (Join-Path $InstallDir "assets\clicker.png") } catch {}

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
if (-not $pyCmd) {
  Write-Warning "Python 3 is required. Install it (python.org or Microsoft Store) then re-run the installer."
  exit 1
}

Write-Host "Creating virtual environment…" -ForegroundColor Cyan
& $env:ComSpec /c "$pyCmd -m venv `"$VenvDir`""

Write-Host "Installing dependencies…" -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
& $Py -m pip install pynput pystray Pillow

# --- Shortcuts ---
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
Write-Host "Launch via Start Menu → PyAutoClicker, or the desktop shortcut."
Write-Host "You can also run: `"$Pyw`" `"$InstallDir\pyautoclicker.py`""
