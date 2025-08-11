# uninstall.ps1 — PyAutoClicker v1.1
param([switch]$KeepData)
$ErrorActionPreference = "Stop"
$InstallDir = Join-Path $env:LOCALAPPDATA "PyAutoClicker"
$StartMenu  = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\PyAutoClicker"
$DesktopLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) "PyAutoClicker.lnk"

if(-not (Test-Path $InstallDir)){Write-Host "PyAutoClicker is not installed." -ForegroundColor Yellow; exit 0}

Write-Host "Stopping running instances..." -ForegroundColor Cyan
try{ Get-CimInstance Win32_Process | ?{ $_.CommandLine -match "pyautoclicker.py" } | % { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }catch{}

if($KeepData){
  $Backup = Join-Path $env:LOCALAPPDATA ("PyAutoClicker_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
  New-Item -Force -ItemType Directory $Backup | Out-Null
  foreach($sub in @("config","sequences")){
    $src=Join-Path $InstallDir $sub; if(Test-Path $src){ Copy-Item -Recurse -Force $src $Backup }
  }
  Write-Host "Preserved config/sequences at: $Backup" -ForegroundColor Yellow
}

Write-Host "Removing shortcuts…" -ForegroundColor Cyan
try{ Remove-Item -Force -Recurse $StartMenu -ErrorAction SilentlyContinue }catch{}
try{ Remove-Item -Force $DesktopLnk -ErrorAction SilentlyContinue }catch{}

Write-Host "Deleting install folder…" -ForegroundColor Cyan
try{ Remove-Item -Force -Recurse $InstallDir }catch{}

Write-Host "Uninstall complete." -ForegroundColor Green
