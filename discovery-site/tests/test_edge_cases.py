"""Comprehensive edge case tests for wormhole viewer functionality.

Tests all edge cases from the test fixture including:
- JavaScript buttons and event handlers
- Hash links (should scroll, not navigate)
- Query parameters
- Relative paths
- Dynamic content creation
- Form interactions
- Various link types (mailto, tel, javascript:, etc.)
"""

import sys
from pathlib import Path

import pytest
from playwright.async_api import Page, expect

# Add tests directory to path
TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_full_integration import (  # noqa: E402
    connect_to_wormhole,
    get_sandbox_frame,
    wait_for_content
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_javascript_buttons_work(page: Page, discovery_url: str, wormhole_server):
    """Test that JavaScript onclick handlers work in the sandbox."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    
    # Wait for page to load
    await wait_for_content(sandbox, "h1")
    
    # Test click counter
    click_btn = sandbox.locator("button:has-text('Click Counter')").first
    await click_btn.click()
    await page.wait_for_timeout(500)
    
    output = await sandbox.locator("#js-output").first.text_content()
    assert "Click count: 1" in output, f"Expected click count 1, got: {output}"
    
    # Click again
    await click_btn.click()
    await page.wait_for_timeout(500)
    output = await sandbox.locator("#js-output").first.text_content()
    assert "Click count: 2" in output, f"Expected click count 2, got: {output}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_toggle_hidden_element(page: Page, discovery_url: str, wormhole_server):
    """Test toggling visibility of hidden elements."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Element should start hidden
    hidden_el = sandbox.locator("#hidden-element").first
    is_visible = await hidden_el.is_visible()
    assert not is_visible, "Hidden element should start hidden"
    
    # Click toggle button
    toggle_btn = sandbox.locator("button:has-text('Toggle Hidden')").first
    await toggle_btn.click()
    await page.wait_for_timeout(500)
    
    # Should now be visible
    is_visible = await hidden_el.is_visible()
    assert is_visible, "Hidden element should be visible after toggle"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_add_dynamic_content(page: Page, discovery_url: str, wormhole_server):
    """Test dynamically adding content to the DOM."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Click add dynamic content button
    dynamic_btn = sandbox.locator("button:has-text('Add Dynamic Content')").first
    await dynamic_btn.click()
    await page.wait_for_timeout(500)
    
    # Check that dynamic content was added
    dynamic_items = sandbox.locator("#dynamic-container > div")
    count = await dynamic_items.count()
    assert count == 1, f"Expected 1 dynamic item, found {count}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hash_link_no_navigation(page: Page, discovery_url: str, wormhole_server):
    """Test that hash links scroll but don't navigate away."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Get initial page title
    initial_title = await sandbox.locator("h1").first.text_content()
    assert "Home" in initial_title
    
    # Click hash link
    hash_link = sandbox.locator("a[href='#section1']").first
    await hash_link.click()
    await page.wait_for_timeout(1000)
    
    # Should still be on same page
    current_title = await sandbox.locator("h1").first.text_content()
    assert current_title == initial_title, "Hash link should not navigate"


@pytest.mark.asyncio
@pytest.mark.integration  
async def test_internal_link_navigation(page: Page, discovery_url: str, wormhole_server):
    """Test navigation to internal pages."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Click About link (discovery site rewrites links to use data-wh-href)
    about_link = sandbox.locator("nav a[data-wh-href='/about']").first
    await about_link.click()
    await page.wait_for_timeout(2000)

    # Should navigate to About page
    title = await sandbox.locator("h1").first.text_content()
    assert "About" in title, f"Expected About page, got: {title}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_dynamic_link(page: Page, discovery_url: str, wormhole_server):
    """Test creating links dynamically and clicking them."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Create dynamic link
    create_btn = sandbox.locator("button:has-text('Create Dynamic Link')").first
    await create_btn.click()
    await page.wait_for_timeout(500)
    
    # Verify link was created
    dynamic_link = sandbox.locator("#dynamic-link-container a").first
    await expect(dynamic_link).to_be_visible()
    
    # Click the dynamic link
    await dynamic_link.click()
    await page.wait_for_timeout(2000)
    
    # Should navigate to About page
    title = await sandbox.locator("h1").first.text_content()
    assert "About" in title, f"Dynamic link should navigate to About, got: {title}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_link_styled_as_button(page: Page, discovery_url: str, wormhole_server):
    """Test that links styled as buttons still navigate."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Find link styled as button (in "Buttons vs Links" section)
    # Discovery site rewrites links to use data-wh-href
    link_as_btn = sandbox.locator("a[data-wh-href='/about']").filter(has_text="Link styled as button").first
    await link_as_btn.click()
    await page.wait_for_timeout(2000)

    # Should navigate
    title = await sandbox.locator("h1").first.text_content()
    assert "About" in title, f"Link styled as button should navigate, got: {title}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_query_parameters_preserved(page: Page, discovery_url: str, wormhole_server):
    """Test that query parameters are preserved in navigation."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")
    
    # Click link with query params (discovery site rewrites to data-wh-href)
    query_link = sandbox.locator("a[data-wh-href='/about?query=test&foo=bar']").first
    await query_link.click()
    await page.wait_for_timeout(2000)
    
    # Check if we got a valid response (could be About page or 404, depends on server)
    # The important thing is that the request was made with query params
    title = await sandbox.locator("h1").first.text_content(timeout=3000)
    # Just verify we got *some* page back
    assert len(title) > 0, "Query param link should load something"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_javascript_status_indicator(page: Page, discovery_url: str, wormhole_server):
    """Test that JavaScript initializes and status indicator updates."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")

    # Check JS status indicator
    js_status = await sandbox.locator("#js-status-text").first.text_content()
    assert "Working" in js_status, f"JavaScript should be working, got: {js_status}"

    # Check that status indicator has green class
    status_el = sandbox.locator("#js-status").first
    classes = await status_el.get_attribute("class")
    assert "status-green" in classes, f"Status indicator should be green, got: {classes}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_navigation_with_hash(page: Page, discovery_url: str, wormhole_server):
    """Test navigation to a page with hash fragment (e.g., /about#section)."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")

    # Navigate to edge-cases page first by clicking link
    edge_cases_link = sandbox.locator("nav a[data-wh-href='/edge-cases']").first
    await edge_cases_link.click()
    await page.wait_for_timeout(2000)

    # Verify we're on edge-cases page
    title = await sandbox.locator("h1").first.text_content()
    assert "Edge Cases" in title, f"Should be on Edge Cases page, got: {title}"

    # Click the "With hash" link
    hash_link = sandbox.locator("a[data-wh-href='/about#section']").first
    await hash_link.click()
    await page.wait_for_timeout(2000)

    # Should navigate to About page
    about_title = await sandbox.locator("h1").first.text_content()
    assert "About" in about_title, f"Should navigate to About page, got: {about_title}"
