$ErrorActionPreference = "Stop"

Write-Host "Building Canopy Tray (PyInstaller)..." -ForegroundColor Cyan

# Run from repo root
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-Not (Test-Path ".\\venv\\Scripts\\python.exe")) {
  Write-Host "Creating venv..." -ForegroundColor Cyan
  python -m venv venv
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& .\\venv\\Scripts\\pip.exe install -r .\\requirements.txt
& .\\venv\\Scripts\\pip.exe install -r .\\canopy_tray\\requirements.txt

Write-Host "Running PyInstaller..." -ForegroundColor Cyan
& .\\venv\\Scripts\\pyinstaller.exe .\\canopy_tray\\build.spec --clean

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Output: dist\\Canopy.exe" -ForegroundColor Green
