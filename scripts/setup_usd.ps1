$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot -Parent

$UsdVersion = "usd.py312.windows-x86_64.usdview.release-v25.08.71e038c1"
$UsdDir = Join-Path $ProjectRoot $UsdVersion

$ZipUrl = "https://developer.nvidia.com/downloads/usd/usd_binaries/25.08/$UsdVersion.zip"
$ZipPath = Join-Path $ProjectRoot "$UsdVersion.zip"

if (Test-Path $UsdDir) {
    Write-Host "USD already installed:"
    Write-Host $UsdDir
    exit 0
}

Write-Host "Downloading USD 25.08..."
Invoke-WebRequest `
    -Uri $ZipUrl `
    -OutFile $ZipPath

Write-Host "Extracting USD..."
Expand-Archive `
    -Path $ZipPath `
    -DestinationPath $ProjectRoot/$UsdVersion

Remove-Item $ZipPath -Force

Write-Host ""
Write-Host "USD installed:"
Write-Host $UsdDir