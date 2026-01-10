$ErrorActionPreference = 'Stop'

$packageName = 'critical-wormhole-tools'
$version = '0.4.0'

# Install via pip
Write-Host "Installing $packageName $version via pip..."
python -m pip install --upgrade critical-wormhole-tools==$version

if ($LASTEXITCODE -ne 0) {
    throw "Failed to install $packageName via pip"
}

Write-Host "$packageName $version has been installed successfully!"
Write-Host "Use 'wh --help' to see available commands."
