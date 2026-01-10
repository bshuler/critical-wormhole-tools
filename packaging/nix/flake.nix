{
  description = "Critical Wormhole Tools - Secure network utilities using Magic Wormhole";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;

        critical-wormhole-tools = python.pkgs.buildPythonApplication rec {
          pname = "critical-wormhole-tools";
          version = "0.4.0";
          format = "pyproject";

          src = ../..;

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

          nativeCheckInputs = with python.pkgs; [
            pytest
            pytest-asyncio
            pytest-mock
          ];

          checkPhase = ''
            runHook preCheck
            pytest tests/unit -v --ignore=tests/integration
            runHook postCheck
          '';

          meta = with pkgs.lib; {
            description = "Secure network utilities using Magic Wormhole code-based addressing";
            homepage = "https://github.com/bshuler/critical-wormhole-tools";
            license = licenses.mit;
            maintainers = [];
            mainProgram = "wh";
          };
        };
      in
      {
        packages = {
          default = critical-wormhole-tools;
          critical-wormhole-tools = critical-wormhole-tools;
        };

        apps.default = flake-utils.lib.mkApp {
          drv = critical-wormhole-tools;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            python.pkgs.pip
            python.pkgs.virtualenv
            python.pkgs.pytest
            python.pkgs.pytest-asyncio
            python.pkgs.ruff
            python.pkgs.mypy
            libsodium
            openssl
          ];

          shellHook = ''
            echo "Critical Wormhole Tools development shell"
            echo "Run 'pip install -e .[dev]' to install in development mode"
          '';
        };
      }
    );
}
