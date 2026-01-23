#!/usr/bin/env python3
"""Verify test counts in documentation match actual test counts.

This script runs pytest and npm test to get actual counts, then compares
them against documented values in PLAN.md and other docs.

Exit codes:
- 0: All counts match (within 5% tolerance)
- 1: Mismatch found
- 2: Error running tests
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_python_test_count() -> int:
    """Run pytest --collect-only and count tests."""
    root = get_project_root()
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Look for pattern like "791 tests collected"
        match = re.search(r"(\d+) tests? collected", result.stdout)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Error counting Python tests: {e}", file=sys.stderr)
    return 0


def get_browser_test_count() -> int:
    """Run npm test and count tests."""
    root = get_project_root()
    browser_dir = root / "browser-extension"
    if not browser_dir.exists():
        return 0

    try:
        result = subprocess.run(
            ["npm", "test", "--", "--reporter=json"],
            cwd=browser_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        # Parse JSON output for numTotalTests
        data = json.loads(result.stdout)
        return data.get("numTotalTests", 0)
    except Exception as e:
        print(f"Error counting browser tests: {e}", file=sys.stderr)
    return 0


def get_documented_counts(file_path: Path) -> dict:
    """Extract documented test counts from a markdown file."""
    counts = {}
    if not file_path.exists():
        return counts

    content = file_path.read_text()

    # Pattern: "Python Tests: XXX passing" or similar
    python_match = re.search(r"Python Tests[:\s]+(\d+)", content, re.IGNORECASE)
    if python_match:
        counts["python"] = int(python_match.group(1))

    # Pattern: "Browser Extension Tests: XXX passing" or similar
    browser_match = re.search(
        r"Browser (?:Extension )?Tests[:\s]+(\d+)", content, re.IGNORECASE
    )
    if browser_match:
        counts["browser"] = int(browser_match.group(1))

    return counts


def main():
    root = get_project_root()

    print("Counting actual tests...")
    actual_python = get_python_test_count()
    actual_browser = get_browser_test_count()

    print(f"  Python tests: {actual_python}")
    print(f"  Browser tests: {actual_browser}")
    print(f"  Total: {actual_python + actual_browser}")

    # Check documented counts in PLAN.md
    plan_path = root / "PLAN.md"
    documented = get_documented_counts(plan_path)

    if not documented:
        print(f"\nNo test counts found in {plan_path}")
        return 0

    print(f"\nDocumented in PLAN.md:")
    print(f"  Python tests: {documented.get('python', 'N/A')}")
    print(f"  Browser tests: {documented.get('browser', 'N/A')}")

    # Compare with 5% tolerance
    tolerance = 0.05
    errors = []

    if "python" in documented:
        diff = abs(actual_python - documented["python"]) / max(documented["python"], 1)
        if diff > tolerance:
            errors.append(
                f"Python test count mismatch: documented {documented['python']}, "
                f"actual {actual_python} (diff: {diff:.1%})"
            )

    if "browser" in documented:
        diff = abs(actual_browser - documented["browser"]) / max(
            documented["browser"], 1
        )
        if diff > tolerance:
            errors.append(
                f"Browser test count mismatch: documented {documented['browser']}, "
                f"actual {actual_browser} (diff: {diff:.1%})"
            )

    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("\nAll test counts match (within 5% tolerance)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
