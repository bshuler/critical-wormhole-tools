# Packaging

This directory contains packaging configurations for various distribution channels.

## Available Packages

| Package Type | Directory | Status | Install Command |
|--------------|-----------|--------|-----------------|
| PyPI | (root) | Ready | `pip install critical-wormhole-tools` |
| Docker | (root) | Ready | `docker pull ghcr.io/bshuler/critical-wormhole-tools` |
| Standalone Binaries | `binaries/` | Ready | Download from GitHub releases |
| Homebrew | `homebrew/` | Ready | `brew install bshuler/tap/critical-wormhole-tools` |
| Debian/Ubuntu | `debian/` | Ready | `apt install critical-wormhole-tools` |
| RPM/Fedora | `rpm/` | Ready | `dnf install critical-wormhole-tools` |
| Snap | `snap/` | Ready | `snap install critical-wormhole-tools` |
| Scoop (Windows) | `scoop/` | Ready | `scoop install critical-wormhole-tools` |
| Chocolatey | `chocolatey/` | Ready | `choco install critical-wormhole-tools` |
| Nix | `nix/` | Ready | `nix profile install github:bshuler/critical-wormhole-tools` |
| Conda | `conda/` | Ready | `conda install -c conda-forge critical-wormhole-tools` |

## Building Packages Locally

### PyPI Package
```bash
pip install build
python -m build
# Output: dist/*.whl, dist/*.tar.gz
```

### Docker Image
```bash
docker build -t critical-wormhole-tools .
```

### Snap Package
```bash
cp packaging/snap/snapcraft.yaml .
snapcraft
# Output: *.snap
```

### Debian Package
```bash
sudo apt install devscripts debhelper dh-python
cp -r packaging/debian .
dpkg-buildpackage -us -uc -b
# Output: ../*.deb
```

### RPM Package
```bash
# On Fedora/RHEL
sudo dnf install rpm-build python3-devel
rpmbuild -ba packaging/rpm/critical-wormhole-tools.spec
# Output: ~/rpmbuild/RPMS/*/*.rpm
```

### Nix
```bash
cd packaging/nix
nix build
# Or for development:
nix develop
```

### Conda
```bash
conda build packaging/conda
```

### Standalone Binaries
```bash
cd packaging/binaries
pip install pyinstaller
python build.py
# Output: dist/wh-{version}-{os}-{arch}[.exe]
```

## Setting Up Distribution Channels

### Homebrew Tap

1. Create a tap repository: `github.com/bshuler/homebrew-tap`
2. Copy the formula: `cp packaging/homebrew/critical-wormhole-tools.rb Formula/`
3. Users install with: `brew tap bshuler/tap && brew install critical-wormhole-tools`

### Snap Store

1. Register name: `snapcraft register critical-wormhole-tools`
2. Login: `snapcraft login`
3. Upload: `snapcraft upload --release=stable *.snap`

### Chocolatey

1. Create account at https://chocolatey.org
2. Get API key from account settings
3. Push: `choco push critical-wormhole-tools.0.4.0.nupkg --api-key YOUR_KEY`

### Scoop Bucket

1. Create bucket repository: `github.com/bshuler/scoop-bucket`
2. Copy manifest: `cp packaging/scoop/critical-wormhole-tools.json bucket/`
3. Users install with: `scoop bucket add bshuler https://github.com/bshuler/scoop-bucket && scoop install critical-wormhole-tools`

### Conda-Forge

1. Fork https://github.com/conda-forge/staged-recipes
2. Copy `packaging/conda/meta.yaml` to `recipes/critical-wormhole-tools/`
3. Submit PR to staged-recipes
4. After merge, recipe moves to feedstock repo

## Automated Releases

The `.github/workflows/release.yml` workflow automatically builds and publishes packages when a GitHub release is created:

1. **PyPI**: Automatic upload
2. **Docker**: Multi-arch images pushed to Docker Hub and GHCR
3. **Snap**: Built and uploaded as artifact
4. **Debian**: Built and attached to release
5. **RPM**: Built and attached to release
6. **Homebrew**: Formula artifact generated

## Version Updates

When releasing a new version:

1. Update `version` in `pyproject.toml`
2. Update version in all packaging files:
   - `packaging/debian/changelog`
   - `packaging/rpm/critical-wormhole-tools.spec`
   - `packaging/snap/snapcraft.yaml`
   - `packaging/scoop/critical-wormhole-tools.json`
   - `packaging/chocolatey/critical-wormhole-tools.nuspec`
   - `packaging/conda/meta.yaml`
3. Create GitHub release with tag `v0.X.0`
4. Workflows handle the rest

## SHA256 Placeholders

Several files contain `PLACEHOLDER` or `PLACEHOLDER_SHA256` values. These are replaced during the release process with actual checksums computed from the built artifacts.
