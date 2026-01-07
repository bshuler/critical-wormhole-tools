$ErrorActionPreference = 'Stop'

$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"

# Install via pip/pipx
$pipxInstalled = Get-Command pipx -ErrorAction SilentlyContinue

if ($pipxInstalled) {
    Write-Host "Installing critical-wormhole-tools via pipx..."
    pipx install critical-wormhole-tools
} else {
    Write-Host "Installing critical-wormhole-tools via pip..."
    pip install critical-wormhole-tools
}

Write-Host "Critical Wormhole Tools installed successfully!"
Write-Host "Run 'wh --help' or 'cwt --help' to get started."
