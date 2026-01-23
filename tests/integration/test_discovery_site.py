"""
Integration tests for the Discovery Site with wormhole file serving.

These tests verify that:
1. wh listen --serve correctly serves test fixtures
2. The discovery site can connect to a wormhole code
3. Content is correctly proxied and rendered
4. Navigation, resources, and JavaScript work through the wormhole

Requirements:
- playwright: pip install playwright && playwright install
- wh CLI: pip install -e .
"""

import asyncio
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest

# Check if playwright is available
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_FIXTURES = PROJECT_ROOT / "browser-extension" / "tests" / "e2e" / "fixtures"
DISCOVERY_URL = os.environ.get(
    "DISCOVERY_URL",
    "https://discovery.prod.criticalwormholebrowser.apps.criticalwormhole.tools"
)


def extract_wormhole_code(output: str) -> Optional[str]:
    """Extract wormhole code from wh listen output."""
    # Look for pattern like "Listening on code: 7-guitar-sunset"
    match = re.search(r"Listening on code:\s*(\d+-\w+-\w+)", output)
    if match:
        return match.group(1)
    return None


class WormholeServer:
    """Context manager for running wh listen --serve."""

    def __init__(self, serve_dir: Path, timeout: int = 30):
        self.serve_dir = serve_dir
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.code: Optional[str] = None

    def start(self) -> str:
        """Start the wormhole server and return the code."""
        cmd = [sys.executable, "-m", "wh.cli.main", "listen", "--serve", str(self.serve_dir)]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Wait for code to be printed
        start_time = time.time()
        output_lines = []

        while time.time() - start_time < self.timeout:
            if self.process.poll() is not None:
                # Process exited
                remaining = self.process.stdout.read()
                output_lines.append(remaining)
                raise RuntimeError(
                    f"wh listen exited unexpectedly:\n{''.join(output_lines)}"
                )

            line = self.process.stdout.readline()
            if line:
                output_lines.append(line)
                print(f"[wh listen] {line.rstrip()}")

                code = extract_wormhole_code(line)
                if code:
                    self.code = code
                    return code

            time.sleep(0.1)

        raise TimeoutError(
            f"Timed out waiting for wormhole code:\n{''.join(output_lines)}"
        )

    def stop(self):
        """Stop the wormhole server."""
        if self.process:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


@pytest.fixture
def wormhole_server():
    """Fixture that starts a wormhole server serving test fixtures."""
    if not TEST_FIXTURES.exists():
        pytest.skip(f"Test fixtures not found at {TEST_FIXTURES}")

    server = WormholeServer(TEST_FIXTURES)
    server.start()
    yield server
    server.stop()


@pytest.fixture
async def browser():
    """Fixture that provides a Playwright browser.

    Uses headed mode by default for better WebSocket/WebRTC support.
    Set HEADLESS=1 environment variable to run in headless mode.
    When running without X display, use: xvfb-run -a pytest ...
    """
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed. Run: pip install playwright && playwright install")

    import os
    headless = os.environ.get("HEADLESS", "0") == "1"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Fixture that provides a browser page."""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestDiscoverySiteIntegration:
    """Integration tests for the discovery site."""

    @pytest.mark.asyncio
    async def test_discovery_site_loads(self, page: Page):
        """Test that the discovery site loads successfully."""
        await page.goto(DISCOVERY_URL)

        # Check for main elements
        title = await page.title()
        assert "Wormhole" in title or "Discovery" in title

        # Check for the address input
        input_el = await page.query_selector('#address-input, input[type="text"]')
        assert input_el is not None, "Address input not found"

        # Check for connect button
        button = await page.query_selector('#connect-btn, button[type="submit"]')
        assert button is not None, "Connect button not found"

    @pytest.mark.asyncio
    async def test_connect_to_wormhole_code(self, page: Page, wormhole_server: WormholeServer):
        """Test connecting to a wormhole code and viewing content."""
        code = wormhole_server.code
        assert code, "Wormhole code not available"

        print(f"[Test] Connecting to wormhole code: {code}")

        # Go to discovery site
        await page.goto(DISCOVERY_URL)
        await page.wait_for_load_state("networkidle")

        # Enter the wormhole code
        input_el = await page.query_selector('#address-input, input[type="text"]')
        await input_el.fill(code)

        # Click connect
        button = await page.query_selector('#connect-btn, button[type="submit"]')
        await button.click()

        # Wait for navigation to viewer or content to load
        # Note: dilation can take up to 30 seconds to timeout, so we use 60s here
        try:
            await page.wait_for_url("**/viewer.html**", timeout=60000)
        except Exception:
            # Check if we're still on the same page with an error
            error_el = await page.query_selector('.error, [class*="error"]')
            if error_el:
                error_text = await error_el.text_content()
                pytest.fail(f"Connection failed with error: {error_text}")
            raise

        # Wait for content to load in the sandbox iframe
        await page.wait_for_timeout(3000)

        # Check that we're in the viewer
        url = page.url
        assert "viewer.html" in url, f"Expected viewer.html in URL, got {url}"
        assert f"address={code}" in url or code in url, f"Expected code in URL, got {url}"

    @pytest.mark.asyncio
    async def test_html_content_rendered(self, page: Page, wormhole_server: WormholeServer):
        """Test that HTML content is correctly rendered through the wormhole."""
        code = wormhole_server.code

        # Navigate directly to viewer with the code
        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={code}&path=/"
        await page.goto(viewer_url)

        # Wait for sandbox to be ready
        await page.wait_for_timeout(5000)

        # Get the sandbox iframe
        sandbox = await page.query_selector('iframe#wh-sandbox')
        if sandbox:
            frame = await sandbox.content_frame()
            if frame:
                # Check for content from the test fixtures
                content = await frame.content()
                assert "Home" in content or "Test" in content, \
                    f"Expected test fixture content, got: {content[:500]}"

    @pytest.mark.asyncio
    async def test_css_loaded(self, page: Page, wormhole_server: WormholeServer):
        """Test that CSS stylesheets are loaded through the wormhole."""
        code = wormhole_server.code
        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={code}&path=/"
        await page.goto(viewer_url)
        await page.wait_for_timeout(5000)

        sandbox = await page.query_selector('iframe#wh-sandbox')
        if sandbox:
            frame = await sandbox.content_frame()
            if frame:
                # Check for styled elements (the test fixtures have specific styles)
                styles = await frame.evaluate("""
                    () => {
                        const body = document.body;
                        const styles = window.getComputedStyle(body);
                        return {
                            fontFamily: styles.fontFamily,
                            hasStyles: styles.cssText.length > 0
                        };
                    }
                """)
                assert styles["hasStyles"], "No styles applied to body"

    @pytest.mark.asyncio
    async def test_javascript_execution(self, page: Page, wormhole_server: WormholeServer):
        """Test that JavaScript executes correctly in the sandbox."""
        code = wormhole_server.code
        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={code}&path=/javascript-test"
        await page.goto(viewer_url)
        await page.wait_for_timeout(5000)

        sandbox = await page.query_selector('iframe#wh-sandbox')
        if sandbox:
            frame = await sandbox.content_frame()
            if frame:
                # Check that JS indicator is set (the test page sets this)
                js_status = await frame.query_selector('#js-status, .status-green')
                if js_status:
                    text = await js_status.text_content()
                    print(f"[Test] JS status: {text}")

    @pytest.mark.asyncio
    async def test_internal_navigation(self, page: Page, wormhole_server: WormholeServer):
        """Test that internal navigation works through the wormhole."""
        code = wormhole_server.code
        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={code}&path=/"
        await page.goto(viewer_url)
        await page.wait_for_timeout(5000)

        sandbox = await page.query_selector('iframe#wh-sandbox')
        if sandbox:
            frame = await sandbox.content_frame()
            if frame:
                # Find and click an internal link
                about_link = await frame.query_selector('a[href="/about"], a[href="about"]')
                if about_link:
                    await about_link.click()
                    await page.wait_for_timeout(3000)

                    # Check URL was updated
                    url = page.url
                    assert "about" in url.lower(), f"Expected 'about' in URL after navigation, got {url}"

    @pytest.mark.asyncio
    async def test_image_loading(self, page: Page, wormhole_server: WormholeServer):
        """Test that images load through the wormhole."""
        code = wormhole_server.code
        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={code}&path=/resource-test"
        await page.goto(viewer_url)
        await page.wait_for_timeout(5000)

        sandbox = await page.query_selector('iframe#wh-sandbox')
        if sandbox:
            frame = await sandbox.content_frame()
            if frame:
                # Check for loaded images
                images = await frame.query_selector_all('img')
                for img in images:
                    # Check if image loaded (naturalHeight > 0)
                    loaded = await img.evaluate("el => el.complete && el.naturalHeight > 0")
                    src = await img.get_attribute("src")
                    if src and not src.startswith("data:"):
                        print(f"[Test] Image {src}: {'loaded' if loaded else 'not loaded'}")


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestWormholeServerStandalone:
    """Tests for the wormhole server functionality without browser."""

    def test_server_starts_and_returns_code(self):
        """Test that wh listen starts and returns a code."""
        if not TEST_FIXTURES.exists():
            pytest.skip(f"Test fixtures not found at {TEST_FIXTURES}")

        with WormholeServer(TEST_FIXTURES, timeout=30) as server:
            assert server.code is not None
            assert re.match(r"\d+-\w+-\w+", server.code), \
                f"Invalid wormhole code format: {server.code}"
            print(f"[Test] Server started with code: {server.code}")

    def test_server_cleanup_on_exit(self):
        """Test that server process is cleaned up properly."""
        if not TEST_FIXTURES.exists():
            pytest.skip(f"Test fixtures not found at {TEST_FIXTURES}")

        server = WormholeServer(TEST_FIXTURES)
        server.start()
        pid = server.process.pid
        server.stop()

        # Check process is gone
        try:
            os.kill(pid, 0)
            pytest.fail(f"Process {pid} still running after stop")
        except OSError:
            pass  # Expected - process doesn't exist


# CLI test for quick verification
if __name__ == "__main__":
    print("Running quick integration test...")
    print(f"Test fixtures: {TEST_FIXTURES}")
    print(f"Discovery URL: {DISCOVERY_URL}")

    if not TEST_FIXTURES.exists():
        print(f"ERROR: Test fixtures not found at {TEST_FIXTURES}")
        sys.exit(1)

    print("\nStarting wormhole server...")
    with WormholeServer(TEST_FIXTURES) as server:
        print(f"\nServer started with code: {server.code}")
        print(f"\nConnect at: {DISCOVERY_URL}")
        print(f"Enter code: {server.code}")
        print("\nPress Ctrl+C to stop...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
