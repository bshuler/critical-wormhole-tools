"""Test that all version numbers across the project are consistent."""

import json
import re
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def test_version_consistency():
    """Verify all version numbers match across project files."""
    root = get_project_root()
    versions = {}

    # Read pyproject.toml version
    pyproject_path = root / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            versions["pyproject.toml"] = match.group(1)

    # Read browser-extension/manifest.json version
    manifest_path = root / "browser-extension" / "manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text())
        versions["browser-extension/manifest.json"] = data.get("version")

    # Read browser-extension/package.json version
    browser_pkg_path = root / "browser-extension" / "package.json"
    if browser_pkg_path.exists():
        data = json.loads(browser_pkg_path.read_text())
        versions["browser-extension/package.json"] = data.get("version")

    # Read discovery-site/package.json version
    discovery_pkg_path = root / "discovery-site" / "package.json"
    if discovery_pkg_path.exists():
        data = json.loads(discovery_pkg_path.read_text())
        versions["discovery-site/package.json"] = data.get("version")

    # Verify we found versions
    assert len(versions) > 0, "No version files found"

    # Get the canonical version (from pyproject.toml)
    canonical_version = versions.get("pyproject.toml")
    assert canonical_version is not None, "pyproject.toml version not found"

    # Check all versions match
    mismatches = []
    for file_path, version in versions.items():
        if version != canonical_version:
            mismatches.append(f"{file_path}: {version} (expected {canonical_version})")

    assert not mismatches, f"Version mismatch found:\n" + "\n".join(mismatches)


def test_version_format():
    """Verify version follows semver format."""
    root = get_project_root()
    pyproject_path = root / "pyproject.toml"

    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert match, "Version not found in pyproject.toml"

    version = match.group(1)
    # Semver pattern: MAJOR.MINOR.PATCH with optional pre-release
    semver_pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    assert re.match(semver_pattern, version), f"Version {version} does not follow semver format"
