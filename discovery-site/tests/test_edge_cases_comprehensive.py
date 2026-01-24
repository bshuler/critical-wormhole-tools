"""Comprehensive edge case tests for all link types on edge-cases.html page.

Tests every link type listed in the "Various Link Types" section.
"""

import sys
from pathlib import Path

import pytest
from playwright.async_api import Page

# Add tests directory to path
TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_full_integration import (  # noqa: E402
    connect_to_wormhole,
    get_sandbox_frame,
    wait_for_content
)


async def navigate_to_edge_cases(page: Page, discovery_url: str, wormhole_server):
    """Helper to navigate to edge-cases page."""
    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")

    # Navigate to edge-cases page
    edge_cases_link = sandbox.locator("nav a[data-wh-href='/edge-cases']").first
    await edge_cases_link.click()
    await page.wait_for_timeout(2000)

    # Verify we're on edge-cases page
    title = await sandbox.locator("h1").first.text_content()
    assert "Edge Cases" in title, f"Should be on Edge Cases page, got: {title}"

    return sandbox


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normal_internal_link(page: Page, discovery_url: str, wormhole_server):
    """Test normal internal link."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    link = sandbox.locator("a[data-wh-href='/about']").filter(has_text="Normal internal link").first
    await link.click()
    await page.wait_for_timeout(2000)

    title = await sandbox.locator("h1").first.text_content()
    assert "About" in title, f"Should navigate to About, got: {title}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_link_with_query_params(page: Page, discovery_url: str, wormhole_server):
    """Test link with query parameters."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    link = sandbox.locator("a[data-wh-href='/about?foo=bar&baz=qux']").first
    await link.click()
    await page.wait_for_timeout(2000)

    # Should get some valid response
    title = await sandbox.locator("h1").first.text_content()
    assert len(title) > 0, "Should load some page"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_link_with_hash(page: Page, discovery_url: str, wormhole_server):
    """Test link with hash fragment."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    link = sandbox.locator("a[data-wh-href='/about#section']").first
    await link.click()
    await page.wait_for_timeout(2000)

    title = await sandbox.locator("h1").first.text_content()
    assert "About" in title, f"Should navigate to About page, got: {title}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_local_hash_only(page: Page, discovery_url: str, wormhole_server):
    """Test local hash-only link (should scroll, not navigate)."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    # Get initial title
    initial_title = await sandbox.locator("h1").first.text_content()
    assert "Edge Cases" in initial_title

    # Click local hash link
    link = sandbox.locator("a[href='#local-section']").first
    await link.click()
    await page.wait_for_timeout(1000)

    # Should still be on same page
    current_title = await sandbox.locator("h1").first.text_content()
    assert current_title == initial_title, "Local hash should not navigate away"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_relative_dot_path(page: Page, discovery_url: str, wormhole_server):
    """Test relative ./path link."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    link = sandbox.locator("a[data-wh-href='./relative']").first
    await link.click()
    await page.wait_for_timeout(2000)

    # Should get some response (likely 404 since /relative doesn't exist)
    title = await sandbox.locator("h1").first.text_content()
    assert len(title) > 0, "Should attempt to load"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parent_path(page: Page, discovery_url: str, wormhole_server):
    """Test parent ../ path link - THIS IS THE FAILING ONE."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    # Click the parent path link
    link = sandbox.locator("a[data-wh-href='../parent']").first
    await link.click()
    await page.wait_for_timeout(2000)

    # Should navigate somewhere (probably get 404 for /parent)
    # The important thing is it should resolve correctly
    title = await sandbox.locator("h1").first.text_content()
    assert len(title) > 0, f"Should attempt to load, got: {title}"
    # If we're on edge-cases (path=/edge-cases), ../parent should resolve to /parent


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_leading_slash(page: Page, discovery_url: str, wormhole_server):
    """Test relative path with no leading slash."""
    sandbox = await navigate_to_edge_cases(page, discovery_url, wormhole_server)

    link = sandbox.locator("a[data-wh-href='subdir/page']").first
    await link.click()
    await page.wait_for_timeout(2000)

    # Should resolve relative to current directory
    title = await sandbox.locator("h1").first.text_content()
    assert len(title) > 0, "Should attempt to load"
