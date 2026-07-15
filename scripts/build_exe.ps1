param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = "py -3.11"

if (-not $SkipInstall) {
    Invoke-Expression "$Python -m pip install --upgrade pip"
    Invoke-Expression "$Python -m pip install -r requirements.txt"
}

Invoke-Expression "$Python -m PyInstaller --clean --noconfirm MailAutoScreenshot.spec"

Write-Host ""
Write-Host "Build complete:"
Write-Host "  dist\MailAutoScreenshot.exe"
Write-Host ""
Write-Host "Before running a task, make sure Chrome is installed."
