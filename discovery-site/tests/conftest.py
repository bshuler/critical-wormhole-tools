"""Shared pytest fixtures for discovery site integration tests."""

import os
import sys
import pytest
from pathlib import Path

# Add tests directory to path for imports
TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# Check for playwright availability
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    Page = None

try:
    from utils import WormholeServer, ConsoleTracker
except ImportError:
    WormholeServer = None
    ConsoleTracker = None


# Path to test fixtures (browser extension test site)
FIXTURES_PATH = Path(__file__).parent.parent.parent / "browser-extension" / "tests" / "e2e" / "fixtures"

# Discovery site URL (from Makefile)
DISCOVERY_URL = os.environ.get(
    "DISCOVERY_URL",
    "https://discovery.prod.criticalwormholebrowser.apps.criticalwormhole.tools"
)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require network and browser)"
    )


@pytest.fixture
def wormhole_server():
    """Start a wormhole server serving the test fixtures.

    This fixture is function-scoped - each test gets a fresh server with
    a new wormhole code to avoid "crowded" errors from the relay.

    Yields:
        WormholeServer: Server instance with .code attribute for the wormhole code
    """
    if not FIXTURES_PATH.exists():
        pytest.skip(f"Test fixtures not found at {FIXTURES_PATH}")

    server = WormholeServer(FIXTURES_PATH, timeout=60)
    try:
        server.start()
        yield server
    finally:
        server.stop()


@pytest.fixture
async def browser():
    """Provide a Playwright browser instance.

    Uses headed mode by default (for xvfb-run). Set HEADLESS=1 for headless.

    Yields:
        Browser: Playwright browser instance
    """
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed. Run: pip install playwright && playwright install")

    headless = os.environ.get("HEADLESS", "0") == "1"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-web-security",  # Allow cross-origin for testing
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Provide a browser page with reasonable defaults.

    Yields:
        Page: Playwright page instance
    """
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    page = await context.new_page()

    # Set longer default timeout for wormhole operations
    page.set_default_timeout(60000)

    yield page

    await context.close()


@pytest.fixture
async def page_with_tracking(browser: Browser):
    """Provide a browser page with console tracking attached.

    Yields:
        tuple[Page, ConsoleTracker]: Page and tracker instances
    """
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    page = await context.new_page()
    page.set_default_timeout(60000)

    tracker = ConsoleTracker(page)

    yield page, tracker

    await context.close()


@pytest.fixture
def discovery_url():
    """Get the discovery site URL.

    Returns:
        str: URL of the discovery site to test against
    """
    return DISCOVERY_URL


@pytest.fixture
def fixtures_path():
    """Get the path to test fixtures.

    Returns:
        Path: Path to the test fixtures directory
    """
    return FIXTURES_PATH
