# Standalone Nix expression for critical-wormhole-tools
# Usage: nix-build default.nix
# Or: nix-env -if default.nix

{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python312;
in
python.pkgs.buildPythonApplication rec {
  pname = "critical-wormhole-tools";
  version = "0.4.0";
  format = "pyproject";

  src = pkgs.fetchFromGitHub {
    owner = "bshuler";
    repo = "critical-wormhole-tools";
    rev = "v${version}";
    sha256 = "PLACEHOLDER";
  };

  nativeBuildInputs = with python.pkgs; [
    setuptools
    wheel
  ];

  propagatedBuildInputs = with python.pkgs; [
    magic-wormhole
    asyncssh
    click
    twisted
    attrs
    httpx
    rich
    noiseprotocol
    pynacl
    aiohttp
    pyyaml
  ];

  # Skip tests in release build
  doCheck = false;

  meta = with pkgs.lib; {
    description = "Secure network utilities using Magic Wormhole code-based addressing";
    longDescription = ''
      Critical Wormhole Tools (wh/cwt) provides secure network utilities using
      Magic Wormhole code-based addressing. Instead of IP addresses and port
      forwarding, users share human-readable codes like "7-guitar-sunset" to
      connect securely from anywhere.

      Features:
      - wh nc: Netcat-style bidirectional pipe
      - wh ssh: SSH client over wormhole
      - wh scp: Secure file copy
      - wh sftp: Interactive SFTP client
      - wh curl/wget: HTTP requests through wormhole
      - wh tunnel: SSH-style port forwarding
    '';
    homepage = "https://github.com/bshuler/critical-wormhole-tools";
    license = licenses.mit;
    maintainers = [];
    mainProgram = "wh";
    platforms = platforms.unix;
  };
}
