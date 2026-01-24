"""Configuration for performance tests."""
import pytest


def pytest_configure(config):
    """Register custom markers for performance tests."""
    config.addinivalue_line("markers", "slow: performance tests (deselected by default)")
