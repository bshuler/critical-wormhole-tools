$ErrorActionPreference = 'Stop'

$packageName = 'critical-wormhole-tools'

Write-Host "Uninstalling $packageName via pip..."
python -m pip uninstall -y critical-wormhole-tools

if ($LASTEXITCODE -ne 0) {
    Write-Warning "pip uninstall returned non-zero exit code, package may already be uninstalled"
}

Write-Host "$packageName has been uninstalled."
