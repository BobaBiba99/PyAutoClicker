# update.ps1 — PyAutoClicker v1.1
$ErrorActionPreference = "Stop"
$OwnerRepo = "GoblinRules/PyAutoClicker"
$branches  = @("main","master")
$candidates = @("pyautoclicker.py","src/pyautoclicker.py","app/pyautoclicker.py","PyAutoClicker.py","trusty_clicker.py")
function Test-Url([string]$u){try{(Invoke-WebRequest -UseBasicParsing -Method Head -Uri $u -TimeoutSec 10).StatusCode -eq 200}catch{$false}}

$ScriptUrl=$null; foreach($b in $branches){$RawBase="https://raw.githubusercontent.com/$OwnerRepo/$b"; foreach($f in $candidates){$u="$RawBase/$f"; if(Test-Url $u){$ScriptUrl=$u; break}} if($ScriptUrl){break}}
if(-not $ScriptUrl){Write-Error "Could not find app file in repo."; exit 1}

$InstallDir=Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$VenvDir=Join-Path $InstallDir ".venv"
$Py=Join-Path $VenvDir "Scripts\python.exe"
$Pyw=Join-Path $VenvDir "Scripts\pythonw.exe"
if(-not (Test-Path $InstallDir)){Write-Error "PyAutoClicker not installed."; exit 1}

Write-Host "Stopping running instances..." -ForegroundColor Cyan
try{ Get-CimInstance Win32_Process | ?{ $_.CommandLine -match "pyautoclicker.py" } | % { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }catch{}

Write-Host "Downloading latest app..." -ForegroundColor Cyan
Invoke-WebRequest -UseBasicParsing $ScriptUrl -OutFile (Join-Path $InstallDir "pyautoclicker.py")

$IconDir=Join-Path $InstallDir "assets"; New-Item -Force -ItemType Directory $IconDir | Out-Null
$IconPngUrl=($ScriptUrl -replace '/[^/]+$','/assets/pyautoclicker.png'); $IconIcoUrl=($ScriptUrl -replace '/[^/]+$','/assets/pyautoclicker.ico')
try{ Invoke-WebRequest -UseBasicParsing $IconPngUrl -OutFile (Join-Path $IconDir "pyautoclicker.png") }catch{}
try{ Invoke-WebRequest -UseBasicParsing $IconIcoUrl -OutFile (Join-Path $IconDir "pyautoclicker.ico") }catch{}

Write-Host "Upgrading dependencies..." -ForegroundColor Cyan
& $Py -m pip install --upgrade pip
& $Py -m pip install --upgrade pynput pystray Pillow

Write-Host "Refreshing shortcuts..." -ForegroundColor Cyan
$Target=$Pyw; $Arguments="`"`"$InstallDir\pyautoclicker.py`"`""; $WorkingDir=$InstallDir; $StartMenu=Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PyAutoClicker"; $IconIco=Join-Path $IconDir "pyautoclicker.ico"
New-Item -Force -ItemType Directory $StartMenu | Out-Null
$shell=New-Object -ComObject WScript.Shell
$sm=$shell.CreateShortcut((Join-Path $StartMenu "PyAutoClicker.lnk")); $sm.TargetPath=$Target; $sm.Arguments=$Arguments; $sm.WorkingDirectory=$WorkingDir; if(Test-Path $IconIco){$sm.IconLocation=$IconIco}; $sm.Save()
$desktop=[Environment]::GetFolderPath('Desktop')
$ds=$shell.CreateShortcut((Join-Path $desktop "PyAutoClicker.lnk")); $ds.TargetPath=$Target; $ds.Arguments=$Arguments; $ds.WorkingDirectory=$WorkingDir; if(Test-Path $IconIco){$ds.IconLocation=$IconIco}; $ds.Save()

Write-Host "Updated successfully." -ForegroundColor Green
