#!/usr/bin/env python3
"""Build standalone binaries for Critical Wormhole Tools."""

import platform
import subprocess
import sys
from pathlib import Path

def get_version():
    """Extract version from pyproject.toml."""
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    for line in pyproject.read_text().splitlines():
        if line.startswith("version"):
            return line.split("=")[1].strip().strip('"')
    return "0.0.0"

def get_platform_info():
    """Get current platform and architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize architecture names
    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    arch = arch_map.get(machine, machine)

    # Normalize OS names
    os_map = {
        "darwin": "darwin",
        "linux": "linux",
        "windows": "windows",
    }
    os_name = os_map.get(system, system)

    return os_name, arch

def build():
    """Build the standalone binary."""
    version = get_version()
    os_name, arch = get_platform_info()

    # Output name
    ext = ".exe" if os_name == "windows" else ""
    output_name = f"wh-{version}-{os_name}-{arch}{ext}"

    # Build directory
    build_dir = Path(__file__).parent
    dist_dir = build_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", output_name.replace(ext, ""),
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir / "build"),
        "--specpath", str(build_dir / "specs"),
        # Hidden imports for all wh modules
        "--hidden-import", "wh.cli",
        "--hidden-import", "wh.cli.nc",
        "--hidden-import", "wh.cli.listen",
        "--hidden-import", "wh.cli.ssh",
        "--hidden-import", "wh.cli.scp",
        "--hidden-import", "wh.cli.sftp",
        "--hidden-import", "wh.cli.curl",
        "--hidden-import", "wh.cli.wget",
        "--hidden-import", "wh.cli.ping",
        "--hidden-import", "wh.cli.rsync",
        "--hidden-import", "wh.cli.proxy",
        "--hidden-import", "wh.cli.tunnel",
        "--hidden-import", "wh.cli.telnet",
        "--hidden-import", "wh.cli.ftp",
        "--hidden-import", "wh.cli.nmap",
        "--hidden-import", "wh.cli.traceroute",
        "--hidden-import", "wh.cli.dns",
        "--hidden-import", "wh.cli.mount",
        "--hidden-import", "wh.cli.vnc",
        "--hidden-import", "wh.cli.rdp",
        "--hidden-import", "wh.cli.daemon",
        "--hidden-import", "wh.cli.relay",
        "--hidden-import", "wh.core",
        "--hidden-import", "wh.ssh",
        "--hidden-import", "wh.http",
        "--hidden-import", "wh.transfer",
        "--hidden-import", "wh.wns",
        "--hidden-import", "wh.enterprise",
        # Entry point
        str(Path(__file__).parent.parent.parent / "src" / "wh" / "cli" / "main.py"),
    ]

    print(f"Building {output_name}...")
    result = subprocess.run(cmd, cwd=str(build_dir.parent.parent))

    if result.returncode == 0:
        output_path = dist_dir / (output_name.replace(ext, "") + ext)
        print(f"Success! Binary created: {output_path}")
        print(f"Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print(f"Build failed with exit code {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build()
