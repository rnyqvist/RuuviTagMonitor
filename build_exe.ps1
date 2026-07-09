$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

Get-Process -Name "RuuviTagMonitor" -ErrorAction SilentlyContinue | Stop-Process -Force

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    py -m venv .venv
}

& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

& $python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller installation failed."
}

& $python -m PyInstaller --noconfirm --clean RuuviTagMonitorPython.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Host ""
Write-Host "Built executable:"
Write-Host (Join-Path $PSScriptRoot "dist\RuuviTagMonitor.exe")
