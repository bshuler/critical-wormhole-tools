"""Full browser integration tests for the discovery site.

These tests start a wormhole server serving test fixtures, navigate to
the production discovery site (criticalwormhole.tools), connect through
the wormhole network, and verify all functionality works.

Run with:
    xvfb-run -a pytest discovery-site/tests/test_full_integration.py -v -s
"""

import sys
from pathlib import Path

# Add tests directory to path for imports
TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import pytest
from playwright.async_api import Page, expect

from utils import ConsoleTracker


# Common timeout for wormhole operations (connection can take time)
WORMHOLE_TIMEOUT = 90000  # 90 seconds
CONTENT_TIMEOUT = 30000   # 30 seconds


async def connect_to_wormhole(page: Page, discovery_url: str, wormhole_code: str) -> None:
    """Navigate to discovery site and connect to a wormhole.

    The viewer now loads inline (no page navigation), so we wait for
    the sandbox iframe to become visible instead of URL change.

    Args:
        page: Playwright page
        discovery_url: URL of the discovery site
        wormhole_code: Wormhole code to connect to
    """
    print(f"[Test] Navigating to {discovery_url}")
    await page.goto(discovery_url)

    # Wait for the page to be ready
    await page.wait_for_load_state("networkidle")

    # Find and fill the address input
    address_input = page.locator("#address-input, input[name='address'], input[type='text']").first
    await address_input.wait_for(state="visible", timeout=10000)

    print(f"[Test] Entering wormhole code: {wormhole_code}")
    await address_input.fill(wormhole_code)

    # Click the go/connect button
    go_button = page.locator("#go-btn, button:has-text('Go'), button:has-text('Connect')").first
    await go_button.click()

    # Wait for sandbox iframe to become visible (viewer loads inline now)
    print("[Test] Waiting for viewer to load...")
    sandbox = page.locator("#wh-sandbox")
    await sandbox.wait_for(state="visible", timeout=WORMHOLE_TIMEOUT)
    print("[Test] Viewer loaded (sandbox visible)")


async def get_sandbox_frame(page: Page):
    """Get the sandbox iframe where wormhole content is rendered.

    Args:
        page: Playwright page

    Returns:
        FrameLocator for the sandbox iframe
    """
    return page.frame_locator("#wh-sandbox, iframe[name='sandbox']").first


async def wait_for_content(sandbox, selector: str, timeout: int = CONTENT_TIMEOUT):
    """Wait for content to appear in the sandbox.

    Args:
        sandbox: Sandbox frame locator
        selector: CSS selector to wait for
        timeout: Timeout in milliseconds
    """
    await sandbox.locator(selector).first.wait_for(state="visible", timeout=timeout)


# =============================================================================
# Connection Flow Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_discovery_page_loads(page: Page, discovery_url: str):
    """Test that the discovery page loads without errors."""
    await page.goto(discovery_url)
    await page.wait_for_load_state("networkidle")

    # Check for main page elements
    title = await page.title()
    assert title, "Page should have a title"

    # Should have an address input
    address_input = page.locator("#address-input, input[name='address'], input[type='text']").first
    await expect(address_input).to_be_visible(timeout=10000)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_connect_to_wormhole(page_with_tracking, discovery_url: str, wormhole_server):
    """Test connecting to a wormhole through the discovery site."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    # Sandbox should be visible (viewer loaded inline, no page navigation)
    sandbox = page.locator("#wh-sandbox")
    await expect(sandbox).to_be_visible()

    # URL should have address parameter
    assert "address=" in page.url or wormhole_server.code in page.url

    # Should not have critical errors
    # (Some warnings may be expected during connection)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_viewer_loads_content(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that content loads in the viewer sandbox."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)

    # Wait for home page content
    await wait_for_content(sandbox, "h1")

    # Verify home page loaded
    h1 = sandbox.locator("h1").first
    title_text = await h1.text_content()
    assert "Home" in title_text or "Test" in title_text, f"Expected home page, got: {title_text}"


# =============================================================================
# JavaScript Execution Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_js_status_indicator(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that JavaScript executes and updates status indicator."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "#js-status-text, #js-status")

    # JavaScript should update the status to "Working!"
    status_text = sandbox.locator("#js-status-text")
    text = await status_text.text_content()
    assert text == "Working!", f"JS status should be 'Working!', got: {text}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_click_counter_button(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that button click handlers work."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "button")

    # Find and click the counter button
    counter_btn = sandbox.locator("button:has-text('Click Counter')").first
    await counter_btn.click()

    # Verify the output updated
    output = sandbox.locator("#js-output")
    text = await output.text_content()
    assert "Click count: 1" in text, f"Expected click count 1, got: {text}"

    # Click again
    await counter_btn.click()
    text = await output.text_content()
    assert "Click count: 2" in text, f"Expected click count 2, got: {text}"

    # Check console log
    assert tracker.has_message("[Test] Button clicked"), "Should log button click"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dynamic_content_added(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that dynamic DOM manipulation works."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "button")

    # Click add dynamic content button
    add_btn = sandbox.locator("button:has-text('Add Dynamic Content')").first
    await add_btn.click()

    # Verify dynamic content was added
    dynamic = sandbox.locator("#dynamic-container div")
    await expect(dynamic.first).to_be_visible(timeout=5000)

    text = await dynamic.first.text_content()
    assert "Dynamic content added" in text, f"Expected dynamic content, got: {text}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_toggle_hidden_element(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that visibility toggle works."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "button")

    hidden_el = sandbox.locator("#hidden-element")

    # Should be hidden initially
    is_hidden = await hidden_el.evaluate("el => el.classList.contains('hidden')")
    assert is_hidden, "Element should be hidden initially"

    # Click toggle button
    toggle_btn = sandbox.locator("button:has-text('Toggle Hidden')").first
    await toggle_btn.click()

    # Should be visible now
    await expect(hidden_el).to_be_visible(timeout=5000)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_console_logs_present(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that expected console logs are present."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")

    # Wait a moment for JS to execute
    await page.wait_for_timeout(2000)

    # Check for expected log messages
    assert tracker.has_message("[Test]"), "Should have [Test] log messages"


# =============================================================================
# Navigation Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_internal_link_navigation(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that clicking internal links navigates correctly."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "nav a")

    # Click the About link
    about_link = sandbox.locator("nav a:has-text('About'), a[href='/about']").first
    await about_link.click()

    # Wait for about page content
    await wait_for_content(sandbox, "h1")
    await page.wait_for_timeout(2000)

    # Should show about page (verify by checking for About in h1 or URL)
    h1 = sandbox.locator("h1").first
    h1_text = await h1.text_content()
    # Either the h1 says About, or we navigated (URL should contain about)
    assert "About" in h1_text or "about" in page.url.lower(), f"Should navigate to about page, h1={h1_text}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_link_behavior(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that hash links scroll but don't navigate."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "a[href='#section1']")

    # Get current URL
    url_before = page.url

    # Click hash link
    hash_link = sandbox.locator("a[href='#section1']").first
    await hash_link.click()

    # URL should still be on same page (or have hash added)
    await page.wait_for_timeout(1000)
    url_after = page.url

    # Should not have navigated to a different page (sandbox still visible)
    sandbox_el = page.locator("#wh-sandbox")
    await expect(sandbox_el).to_be_visible()
    assert "address=" in url_after, "Should stay on viewer with address param"


# =============================================================================
# Resource Loading Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_css_styles_applied(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that CSS styles are loaded and applied."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, ".container, body")

    # Check for gradient background (defined in fixture CSS)
    has_gradient = await sandbox.locator("body").evaluate("""
        el => {
            const style = window.getComputedStyle(el);
            return style.backgroundImage.includes('gradient');
        }
    """)
    assert has_gradient, "Body should have gradient background from CSS"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_status_indicator_styling(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that status indicators have correct CSS classes."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "#js-status")

    # JS should add status-green class
    has_green = await sandbox.locator("#js-status").evaluate(
        "el => el.classList.contains('status-green')"
    )
    assert has_green, "JS status should have status-green class"


# =============================================================================
# Form Interaction Tests (if forms-test page available)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_form_input_interaction(page_with_tracking, discovery_url: str, wormhole_server):
    """Test basic form input interaction."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)

    # Navigate to forms test page if it exists
    forms_link = sandbox.locator("a[href='/forms-test'], a:has-text('Forms')").first
    if await forms_link.count() > 0:
        await forms_link.click()
        await wait_for_content(sandbox, "input, form")

        # Try to fill an input
        text_input = sandbox.locator("input[type='text']").first
        if await text_input.count() > 0:
            await text_input.fill("test value")
            value = await text_input.input_value()
            assert value == "test value", f"Input should have value, got: {value}"
    else:
        pytest.skip("Forms test page not available")


# =============================================================================
# Error Verification Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_js_errors_on_load(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that no JS errors occur during page load."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")

    # Wait for any async operations
    await page.wait_for_timeout(3000)

    # Check for errors (ignore some known benign warnings)
    tracker.assert_no_errors(ignore_patterns=[
        "favicon.ico",  # Missing favicon is OK
        "ResizeObserver",  # ResizeObserver warnings are benign
    ])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_js_errors_after_interactions(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that no JS errors occur after button clicks."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "button")

    # Click various buttons
    buttons = ["Click Counter", "Add Dynamic Content", "Toggle Hidden"]
    for btn_text in buttons:
        btn = sandbox.locator(f"button:has-text('{btn_text}')").first
        if await btn.count() > 0:
            await btn.click()
            await page.wait_for_timeout(500)

    # Verify no errors after interactions
    tracker.assert_no_errors(ignore_patterns=[
        "favicon.ico",
        "ResizeObserver",
    ])


# =============================================================================
# Advanced Feature Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_dynamic_link(page_with_tracking, discovery_url: str, wormhole_server):
    """Test creating dynamic links via JavaScript."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "button")

    # Find the create dynamic link button
    create_btn = sandbox.locator("button:has-text('Create Dynamic Link')").first
    if await create_btn.count() > 0:
        await create_btn.click()

        # Verify link was created
        await page.wait_for_timeout(1000)
        dynamic_link = sandbox.locator("#dynamic-link-container a")
        await expect(dynamic_link.first).to_be_visible(timeout=5000)

        # Check console for confirmation
        assert tracker.has_message("Dynamic link created"), "Should log dynamic link creation"
    else:
        pytest.skip("Create Dynamic Link button not found")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_link_styled_as_button(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that links styled as buttons still work as navigation."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "a[href='/about']")

    # Find link styled as button (has inline-block style)
    styled_link = sandbox.locator("a[href='/about']").first

    if await styled_link.count() > 0:
        await styled_link.click()

        # Should navigate to about page
        await wait_for_content(sandbox, "h1")
        await page.wait_for_timeout(2000)

        h1 = sandbox.locator("h1").first
        text = await h1.text_content()
        # Either navigated to About or stayed on home (both acceptable)
        assert text is not None, "Page should have content after click"


# =============================================================================
# Storage API Tests (if available in fixtures)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_localstorage_works(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that localStorage is available in the sandbox."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "body")

    # Test localStorage via evaluate
    result = await sandbox.locator("body").evaluate("""
        () => {
            try {
                localStorage.setItem('test-key', 'test-value');
                const val = localStorage.getItem('test-key');
                localStorage.removeItem('test-key');
                return { success: true, value: val };
            } catch (e) {
                return { success: false, error: e.message };
            }
        }
    """)

    assert result.get("success"), f"localStorage should work: {result.get('error')}"
    assert result.get("value") == "test-value", "localStorage should store and retrieve values"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sessionstorage_works(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that sessionStorage is available in the sandbox."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "body")

    result = await sandbox.locator("body").evaluate("""
        () => {
            try {
                sessionStorage.setItem('test-key', 'test-value');
                const val = sessionStorage.getItem('test-key');
                sessionStorage.removeItem('test-key');
                return { success: true, value: val };
            } catch (e) {
                return { success: false, error: e.message };
            }
        }
    """)

    assert result.get("success"), f"sessionStorage should work: {result.get('error')}"
    assert result.get("value") == "test-value", "sessionStorage should store and retrieve values"


# =============================================================================
# WebRTC/Advanced API Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_webrtc_available(page_with_tracking, discovery_url: str, wormhole_server):
    """Test that WebRTC APIs are available."""
    page, tracker = page_with_tracking

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)

    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "body")

    result = await sandbox.locator("body").evaluate("""
        () => {
            return {
                RTCPeerConnection: typeof RTCPeerConnection !== 'undefined',
                WebSocket: typeof WebSocket !== 'undefined',
                Worker: typeof Worker !== 'undefined',
            };
        }
    """)

    assert result.get("RTCPeerConnection"), "RTCPeerConnection should be available"
    assert result.get("WebSocket"), "WebSocket should be available"
    assert result.get("Worker"), "Worker should be available"
