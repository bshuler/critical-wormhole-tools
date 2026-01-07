$ErrorActionPreference = 'Stop'

$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"

# Install via pip/pipx
$pipxInstalled = Get-Command pipx -ErrorAction SilentlyContinue

if ($pipxInstalled) {
    Write-Host "Installing critical-wormhole via pipx..."
    pipx install critical-wormhole
} else {
    Write-Host "Installing critical-wormhole via pip..."
    pip install critical-wormhole
}

Write-Host "Critical Wormhole Tools installed successfully!"
Write-Host "Run 'wh --help' or 'cwt --help' to get started."
