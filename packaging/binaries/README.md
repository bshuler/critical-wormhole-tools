# Standalone Binary Builds

Build standalone executables for Critical Wormhole Tools that run without Python installed.

## Supported Platforms

| Platform | Architecture | Status |
|----------|--------------|--------|
| Linux | x86_64 | Ready |
| Linux | arm64 | Ready |
| macOS | x86_64 | Ready |
| macOS | arm64 (Apple Silicon) | Ready |
| Windows | x86_64 | Ready |

## Building Locally

### Prerequisites
- Python 3.10+
- PyInstaller: `pip install pyinstaller`

### Build Command
```bash
cd packaging/binaries
python build.py
```

Output: `dist/wh-{version}-{os}-{arch}[.exe]`

## CI/CD

Binaries are automatically built on release via GitHub Actions.
See `/.github/workflows/binaries.yml`

## Included Commands

All 19 CLI tools are included:
- wh nc, listen, ssh, scp, sftp, curl, wget
- wh ping, rsync, proxy, tunnel, telnet, ftp
- wh nmap, traceroute, dns, mount, vnc, rdp
- wh daemon, relay, identity, namespace
