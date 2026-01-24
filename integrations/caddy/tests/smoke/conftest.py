"""
Smoke test configuration for pytest.
"""


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "smoke: quick validation tests for CI/CD (should complete in <30 seconds total)"
    )
