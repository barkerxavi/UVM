param(
    # Obtain the expected digest independently from a trusted distributor.
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedSha256
)

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
if ((Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash -ne $ExpectedSha256) {
    Remove-Item $ZipPath -Force
    throw "USD archive SHA-256 verification failed."
}
Expand-Archive `
    -Path $ZipPath `
    -DestinationPath $UsdDir

Remove-Item $ZipPath -Force

Write-Host ""
Write-Host "USD installed:"
Write-Host $UsdDir
