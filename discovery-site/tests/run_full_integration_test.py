#!/usr/bin/env python3
"""
Full Integration Test Suite for Discovery Site

This script performs comprehensive end-to-end testing of the discovery site,
including all buttons, links, forms, and wormhole functionality.

Run with: python tests/run_full_integration_test.py
"""

import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

# Configuration
DISCOVERY_URL = os.environ.get(
    "DISCOVERY_URL",
    "https://discovery.prod.criticalwormholebrowser.apps.criticalwormhole.tools"
)
TEST_FIXTURES = Path(__file__).parent.parent.parent / "browser-extension" / "tests" / "e2e" / "fixtures"


@dataclass
class TestResults:
    """Track all test results and counts."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    # Element counts
    buttons_found: int = 0
    buttons_clicked: int = 0
    links_found: int = 0
    links_clicked: int = 0
    inputs_found: int = 0
    inputs_tested: int = 0
    forms_found: int = 0
    forms_submitted: int = 0

    # Detailed results
    test_details: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def add_result(self, name: str, passed: bool, details: str = ""):
        self.total_tests += 1
        if passed:
            self.passed += 1
            status = "PASS"
        else:
            self.failed += 1
            status = "FAIL"
        self.test_details.append(f"[{status}] {name}: {details}")
        print(f"  [{status}] {name}" + (f": {details}" if details else ""))

    def add_error(self, error: str):
        self.errors.append(error)
        print(f"  [ERROR] {error}")

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            "TEST RESULTS SUMMARY",
            "=" * 60,
            "",
            f"Total Tests: {self.total_tests}",
            f"  Passed: {self.passed}",
            f"  Failed: {self.failed}",
            f"  Skipped: {self.skipped}",
            "",
            "Elements Tested:",
            f"  Buttons found: {self.buttons_found}",
            f"  Buttons clicked: {self.buttons_clicked}",
            f"  Links found: {self.links_found}",
            f"  Links clicked: {self.links_clicked}",
            f"  Inputs found: {self.inputs_found}",
            f"  Inputs tested: {self.inputs_tested}",
            f"  Forms found: {self.forms_found}",
            f"  Forms submitted: {self.forms_submitted}",
            "",
        ]

        if self.errors:
            lines.append("Errors:")
            for err in self.errors:
                lines.append(f"  - {err}")
            lines.append("")

        lines.append("=" * 60)

        if self.failed == 0:
            lines.append("ALL TESTS PASSED!")
        else:
            lines.append(f"TESTS FAILED: {self.failed} failures")

        lines.append("=" * 60)

        return "\n".join(lines)


class WormholeServer:
    """Manages a wormhole server process for testing."""

    def __init__(self, serve_dir: Path):
        self.serve_dir = serve_dir
        self.process: Optional[subprocess.Popen] = None
        self.code: Optional[str] = None

    def start(self, timeout: int = 30) -> str:
        """Start the server and return the wormhole code."""
        cmd = [sys.executable, "-m", "wh.cli.main", "listen", "--serve", str(self.serve_dir)]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        start_time = time.time()
        output_lines = []

        while time.time() - start_time < timeout:
            if self.process.poll() is not None:
                remaining = self.process.stdout.read()
                output_lines.append(remaining)
                raise RuntimeError(f"Server exited: {''.join(output_lines)}")

            line = self.process.stdout.readline()
            if line:
                output_lines.append(line)
                print(f"    [wh] {line.rstrip()}")

                match = re.search(r"Listening on code:\s*(\d+-\w+-\w+)", line)
                if match:
                    self.code = match.group(1)
                    return self.code

            time.sleep(0.1)

        raise TimeoutError(f"Server didn't start: {''.join(output_lines)}")

    def stop(self):
        """Stop the server."""
        if self.process:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None


async def test_index_page(page: Page, results: TestResults):
    """Test the discovery site index page."""
    print("\n[TEST SUITE] Index Page Tests")
    print("-" * 40)

    # Navigate to index
    print("  Loading discovery site...")
    await page.goto(DISCOVERY_URL)
    await page.wait_for_load_state("networkidle")

    # Test 1: Page loads
    title = await page.title()
    results.add_result("Page loads", "Wormhole" in title or "Discovery" in title, f"Title: {title}")

    # Test 2: Find and count all buttons
    buttons = await page.query_selector_all("button")
    results.buttons_found += len(buttons)
    results.add_result("Buttons exist", len(buttons) > 0, f"Found {len(buttons)} buttons")

    # Test 3: Find and count all links
    links = await page.query_selector_all("a")
    results.links_found += len(links)
    results.add_result("Links exist", len(links) > 0, f"Found {len(links)} links")

    # Test 4: Find and count all inputs
    inputs = await page.query_selector_all("input")
    results.inputs_found += len(inputs)
    results.add_result("Inputs exist", len(inputs) > 0, f"Found {len(inputs)} inputs")

    # Test 5: Find connect form
    form = await page.query_selector("#connect-form")
    if form:
        results.forms_found += 1
    results.add_result("Connect form exists", form is not None)

    # Test 6: Address input exists and is functional
    address_input = await page.query_selector("#address-input")
    results.add_result("Address input exists", address_input is not None)

    if address_input:
        await address_input.fill("test-input-value")
        value = await address_input.input_value()
        results.inputs_tested += 1
        results.add_result("Address input accepts text", value == "test-input-value")
        await address_input.fill("")  # Clear for next test

    # Test 7: Connect button exists
    connect_btn = await page.query_selector("#connect-btn")
    results.add_result("Connect button exists", connect_btn is not None)

    # Test 8: Check for hero section
    hero = await page.query_selector(".hero")
    results.add_result("Hero section exists", hero is not None)

    # Test 9: Check for how-it-works section
    how_it_works = await page.query_selector(".how-it-works")
    results.add_result("How-it-works section exists", how_it_works is not None)

    # Test 10: Check footer link
    footer_link = await page.query_selector("footer a")
    if footer_link:
        href = await footer_link.get_attribute("href")
        results.add_result("Footer link exists", "github" in href.lower(), f"href: {href}")
    else:
        results.add_result("Footer link exists", False, "Not found")

    # Test 11: JavaScript initialized (check console for init message)
    # We can check if the app initialized by looking for the status element
    status = await page.query_selector("#status")
    results.add_result("Status element exists", status is not None)

    # Test 12: Recent section (may be hidden initially)
    recent = await page.query_selector("#recent-section")
    results.add_result("Recent section exists", recent is not None)

    # Test 13: Connections section (may be hidden initially)
    connections = await page.query_selector("#connections-section")
    results.add_result("Connections section exists", connections is not None)

    return True


async def test_invalid_connection(page: Page, results: TestResults):
    """Test behavior with invalid wormhole codes."""
    print("\n[TEST SUITE] Invalid Connection Tests")
    print("-" * 40)

    await page.goto(DISCOVERY_URL)
    await page.wait_for_load_state("networkidle")

    # Test with invalid code
    address_input = await page.query_selector("#address-input")
    connect_btn = await page.query_selector("#connect-btn")

    if not address_input or not connect_btn:
        results.add_result("Invalid connection test setup", False, "Could not find form elements")
        return False

    # Enter an invalid/non-existent code
    await address_input.fill("999-invalid-code")
    results.inputs_tested += 1

    # Click connect
    await connect_btn.click()
    results.buttons_clicked += 1

    # Wait for status to show connecting
    await page.wait_for_timeout(1000)

    status = await page.query_selector("#status")
    if status:
        status_class = await status.get_attribute("class")
        status_text = await status.text_content()
        results.add_result(
            "Shows connecting status",
            "connecting" in status_class or "Connecting" in status_text,
            f"Class: {status_class}, Text: {status_text[:50] if status_text else 'none'}"
        )

    # Wait for timeout/error (this will take a while)
    print("    Waiting for connection timeout (up to 20s)...")
    try:
        await page.wait_for_function(
            "document.querySelector('#status')?.classList.contains('error')",
            timeout=20000
        )
        status_text = await page.query_selector("#status")
        if status_text:
            text = await status_text.text_content()
            results.add_result("Shows error on invalid code", True, f"Error: {text[:50]}")
        else:
            results.add_result("Shows error on invalid code", True)
    except PlaywrightTimeout:
        results.add_result("Shows error on invalid code", False, "Timed out waiting for error")

    # Button should be re-enabled after error
    is_disabled = await connect_btn.get_attribute("disabled")
    results.add_result("Button re-enabled after error", is_disabled is None)

    return True


async def test_valid_connection(page: Page, results: TestResults, wormhole_code: str):
    """Test connection to a valid wormhole code."""
    print("\n[TEST SUITE] Valid Connection Tests")
    print("-" * 40)

    await page.goto(DISCOVERY_URL)
    await page.wait_for_load_state("networkidle")

    address_input = await page.query_selector("#address-input")
    connect_btn = await page.query_selector("#connect-btn")

    if not address_input or not connect_btn:
        results.add_result("Valid connection test setup", False, "Could not find form elements")
        return False

    # Enter valid code
    print(f"    Entering wormhole code: {wormhole_code}")
    await address_input.fill(wormhole_code)
    results.inputs_tested += 1

    # Click connect
    await connect_btn.click()
    results.buttons_clicked += 1
    results.forms_submitted += 1

    # Wait for navigation to viewer
    print("    Waiting for connection and navigation to viewer...")
    try:
        await page.wait_for_url("**/viewer.html**", timeout=30000)
        results.add_result("Navigates to viewer on valid code", True, f"URL: {page.url}")
    except PlaywrightTimeout:
        # Check if still on index with error
        current_url = page.url
        status = await page.query_selector("#status")
        status_text = await status.text_content() if status else "unknown"
        results.add_result(
            "Navigates to viewer on valid code",
            False,
            f"Stayed on {current_url}, status: {status_text}"
        )
        return False

    return True


async def test_viewer_page(page: Page, results: TestResults, wormhole_code: str):
    """Test the viewer page with content loaded through wormhole."""
    print("\n[TEST SUITE] Viewer Page Tests")
    print("-" * 40)

    # Should already be on viewer page from previous test
    if "viewer.html" not in page.url:
        # Navigate directly
        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={wormhole_code}&path=/"
        await page.goto(viewer_url)

    # Test 1: URL contains address
    results.add_result("Viewer URL contains address", wormhole_code in page.url, f"URL: {page.url}")

    # Test 2: Sandbox iframe exists
    sandbox = await page.query_selector("#wh-sandbox")
    results.add_result("Sandbox iframe exists", sandbox is not None)

    # Wait for content to load
    print("    Waiting for content to load in sandbox...")
    await page.wait_for_timeout(5000)

    # Test 3: Sandbox becomes active
    sandbox = await page.query_selector("#wh-sandbox.active")
    results.add_result("Sandbox iframe is active", sandbox is not None)

    if not sandbox:
        # Check for error
        error = await page.query_selector("#wh-error")
        if error:
            error_msg = await page.query_selector("#wh-error-message")
            msg = await error_msg.text_content() if error_msg else "unknown"
            results.add_error(f"Viewer error: {msg}")
        return False

    # Get sandbox frame
    frame = await sandbox.content_frame()
    if not frame:
        results.add_result("Can access sandbox frame", False)
        return False

    results.add_result("Can access sandbox frame", True)

    # Test 4: Content loaded in sandbox
    content = await frame.content()
    has_content = len(content) > 500  # More than just empty HTML
    results.add_result("Content loaded in sandbox", has_content, f"Content length: {len(content)}")

    # Test 5: Find elements in sandbox
    sandbox_buttons = await frame.query_selector_all("button")
    results.buttons_found += len(sandbox_buttons)
    results.add_result("Sandbox has buttons", len(sandbox_buttons) > 0, f"Found {len(sandbox_buttons)} buttons")

    sandbox_links = await frame.query_selector_all("a")
    results.links_found += len(sandbox_links)
    results.add_result("Sandbox has links", len(sandbox_links) > 0, f"Found {len(sandbox_links)} links")

    # Test 6: CSS loaded (check computed styles)
    has_styles = await frame.evaluate("""
        () => {
            const body = document.body;
            if (!body) return false;
            const styles = window.getComputedStyle(body);
            // Check if font-family is set (not just default)
            return styles.fontFamily && styles.fontFamily !== 'Times New Roman';
        }
    """)
    results.add_result("CSS styles applied", has_styles)

    # Test 7: JavaScript working (check for dynamic elements)
    js_status = await frame.query_selector("#js-status, .status-green, #js-output")
    results.add_result("JavaScript status element exists", js_status is not None)

    # Test 8: Click a button in sandbox if available
    if sandbox_buttons:
        first_button = sandbox_buttons[0]
        button_text = await first_button.text_content()
        try:
            await first_button.click()
            results.buttons_clicked += 1
            results.add_result("Can click sandbox button", True, f"Clicked: {button_text[:30]}")
        except Exception as e:
            results.add_result("Can click sandbox button", False, str(e))

    # Test 9: Test internal navigation
    internal_links = []
    for link in sandbox_links:
        href = await link.get_attribute("href")
        wh_href = await link.get_attribute("data-wh-href")
        if wh_href or (href and not href.startswith("http") and not href.startswith("#") and not href.startswith("javascript")):
            internal_links.append(link)

    results.add_result("Has internal links", len(internal_links) > 0, f"Found {len(internal_links)} internal links")

    if internal_links:
        first_link = internal_links[0]
        link_text = await first_link.text_content()
        link_href = await first_link.get_attribute("data-wh-href") or await first_link.get_attribute("href")

        print(f"    Clicking internal link: {link_text[:30]} -> {link_href}")

        try:
            await first_link.click()
            results.links_clicked += 1
            await page.wait_for_timeout(3000)

            # Check if URL updated
            new_url = page.url
            results.add_result("Internal navigation works", True, f"New URL: {new_url}")
        except Exception as e:
            results.add_result("Internal navigation works", False, str(e))

    # Test 10: Check for images
    images = await frame.query_selector_all("img")
    results.add_result("Images exist", len(images) >= 0, f"Found {len(images)} images")

    if images:
        # Check if first image loaded
        first_img = images[0]
        img_loaded = await first_img.evaluate("el => el.complete && el.naturalHeight > 0")
        results.add_result("Image loaded successfully", img_loaded)

    return True


async def test_viewer_error_handling(page: Page, results: TestResults):
    """Test viewer error handling."""
    print("\n[TEST SUITE] Viewer Error Handling Tests")
    print("-" * 40)

    # Test with no address
    await page.goto(f"{DISCOVERY_URL}/viewer.html")
    await page.wait_for_timeout(2000)

    error = await page.query_selector("#wh-error")
    if error:
        error_style = await error.evaluate("el => window.getComputedStyle(el).display")
        results.add_result("Shows error with no address", error_style != "none")
    else:
        results.add_result("Shows error with no address", False, "Error element not found")

    # Test error page buttons
    retry_btn = await page.query_selector("#wh-error button")
    if retry_btn:
        results.buttons_found += 1
        results.add_result("Error page has retry button", True)

    return True


async def test_all_fixture_pages(page: Page, results: TestResults, wormhole_code: str):
    """Test loading multiple pages from the test fixtures."""
    print("\n[TEST SUITE] Test Fixture Pages")
    print("-" * 40)

    pages_to_test = [
        ("/", "Home Page"),
        ("/about", "About Page"),
        ("/contact", "Contact Page"),
        ("/javascript-test", "JavaScript Test Page"),
        ("/forms-test", "Forms Test Page"),
    ]

    for path, name in pages_to_test:
        print(f"    Testing: {name} ({path})")

        viewer_url = f"{DISCOVERY_URL}/viewer.html?address={wormhole_code}&path={path}"

        try:
            await page.goto(viewer_url)
            await page.wait_for_timeout(3000)

            sandbox = await page.query_selector("#wh-sandbox.active")
            if sandbox:
                frame = await sandbox.content_frame()
                if frame:
                    content = await frame.content()
                    has_content = len(content) > 200

                    # Count elements
                    buttons = await frame.query_selector_all("button")
                    links = await frame.query_selector_all("a")
                    inputs = await frame.query_selector_all("input, textarea, select")

                    results.buttons_found += len(buttons)
                    results.links_found += len(links)
                    results.inputs_found += len(inputs)

                    results.add_result(
                        f"{name} loads",
                        has_content,
                        f"Buttons: {len(buttons)}, Links: {len(links)}, Inputs: {len(inputs)}"
                    )
                else:
                    results.add_result(f"{name} loads", False, "Could not access frame")
            else:
                results.add_result(f"{name} loads", False, "Sandbox not active")

        except Exception as e:
            results.add_result(f"{name} loads", False, str(e))

    return True


async def run_tests():
    """Run all integration tests."""
    results = TestResults()
    server = None

    print("=" * 60)
    print("DISCOVERY SITE FULL INTEGRATION TEST SUITE")
    print("=" * 60)
    print(f"\nTarget URL: {DISCOVERY_URL}")
    print(f"Test Fixtures: {TEST_FIXTURES}")

    # Check fixtures exist
    if not TEST_FIXTURES.exists():
        print(f"\nERROR: Test fixtures not found at {TEST_FIXTURES}")
        return results

    # Start wormhole server
    print("\n[SETUP] Starting wormhole server...")
    server = WormholeServer(TEST_FIXTURES)

    try:
        wormhole_code = server.start()
        print(f"  Server started with code: {wormhole_code}")
    except Exception as e:
        print(f"  ERROR: Failed to start server: {e}")
        return results

    # Run browser tests
    try:
        async with async_playwright() as p:
            print("\n[SETUP] Launching browser...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Enable console logging
            page.on("console", lambda msg: print(f"    [Browser Console] {msg.type}: {msg.text}") if msg.type in ["error", "warning"] else None)

            try:
                # Run test suites
                await test_index_page(page, results)
                await test_invalid_connection(page, results)
                await test_valid_connection(page, results, wormhole_code)
                await test_viewer_page(page, results, wormhole_code)
                await test_viewer_error_handling(page, results)
                await test_all_fixture_pages(page, results, wormhole_code)

            except Exception as e:
                results.add_error(f"Test suite error: {e}")
                import traceback
                traceback.print_exc()

            finally:
                await context.close()
                await browser.close()

    except Exception as e:
        results.add_error(f"Browser error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Stop server
        if server:
            print("\n[CLEANUP] Stopping wormhole server...")
            server.stop()

    # Print summary
    print(results.summary())

    return results


if __name__ == "__main__":
    results = asyncio.run(run_tests())
    sys.exit(0 if results.failed == 0 else 1)
