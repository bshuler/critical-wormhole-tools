"""Visual test to click through ALL edge case links and report results."""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import pytest
from playwright.async_api import Page

from test_full_integration import (
    connect_to_wormhole,
    get_sandbox_frame,
    wait_for_content,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_all_edge_case_links_visual(page: Page, discovery_url: str, wormhole_server):
    """Click every link in the Various Link Types section and report what happens."""

    await connect_to_wormhole(page, discovery_url, wormhole_server.code)
    sandbox = await get_sandbox_frame(page)
    await wait_for_content(sandbox, "h1")

    # Navigate to edge-cases page
    edge_cases_link = sandbox.locator("nav a[data-wh-href='/edge-cases']").first
    await edge_cases_link.click()
    await page.wait_for_timeout(2000)

    # Verify we're on edge-cases page
    title = await sandbox.locator("h1").first.text_content()
    print(f"\n✓ Navigated to edge-cases page: {title}")

    # Test each link type
    link_tests = [
        ("Normal internal link", "a[data-wh-href='/about']", "About"),
        ("With query params", "a[data-wh-href='/about?foo=bar&baz=qux']", None),
        ("With hash", "a[data-wh-href='/about#section']", "About"),
        ("Relative ./path", "a[data-wh-href='./relative']", None),
        ("Parent ../path", "a[data-wh-href='../parent']", "Parent"),
        ("No leading slash", "a[data-wh-href='subdir/page']", None),
    ]

    results = []

    for link_name, selector, expected_title in link_tests:
        # Navigate back to edge-cases before each test
        if link_name != "Normal internal link":
            edge_link = sandbox.locator("nav a[data-wh-href='/edge-cases']").first
            try:
                await edge_link.click()
                await page.wait_for_timeout(1500)
            except:
                pass

        # Find and click the link
        try:
            link = sandbox.locator(selector).filter(has_text=link_name).first
            await link.click()
            await page.wait_for_timeout(2000)

            # Check result
            result_title = await sandbox.locator("h1").first.text_content()

            if expected_title and expected_title in result_title:
                status = f"✓ SUCCESS: {link_name} → {result_title}"
            elif "404" in result_title:
                status = f"⚠ 404: {link_name} → {result_title} (expected, page doesn't exist)"
            elif "403" in result_title:
                status = f"✗ FAIL: {link_name} → {result_title} (forbidden)"
            else:
                status = f"? UNKNOWN: {link_name} → {result_title}"

            print(f"\n{status}")
            results.append((link_name, status))

        except Exception as e:
            status = f"✗ ERROR: {link_name} → {str(e)[:100]}"
            print(f"\n{status}")
            results.append((link_name, status))

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY OF ALL EDGE CASE LINK TESTS:")
    print("="*70)
    for link_name, status in results:
        print(f"  {status}")
    print("="*70)

    # Ensure at least some links worked
    success_count = sum(1 for _, s in results if "SUCCESS" in s or "404" in s)
    assert success_count >= 3, f"Too many failures. Only {success_count}/{len(results)} links worked"
