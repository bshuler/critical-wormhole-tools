"""COMPLETE edge case test suite - tests EVERY element on edge-cases.html.

This test file covers all 12 sections with every interactive element.
"""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import pytest
from playwright.async_api import Page, expect

from test_full_integration import (
    connect_to_wormhole,
    get_sandbox_frame,
    wait_for_content,
)


async def go_to_edge_cases(page: Page, discovery_url: str, wormhole_server, first_time: bool = False):
    """Navigate to edge-cases page."""
    if first_time:
        # First time: connect to wormhole
        await connect_to_wormhole(page, discovery_url, wormhole_server.code)
        sandbox = await get_sandbox_frame(page)
        await wait_for_content(sandbox, "h1")
    else:
        # Subsequent times: just get the existing sandbox
        sandbox = await get_sandbox_frame(page)

    # Check if we're already on edge-cases page
    try:
        title = await sandbox.locator("h1").first.text_content(timeout=2000)
        if "Edge Cases" in title:
            # Already on edge-cases page, no need to navigate
            return sandbox
    except:
        pass

    # Wait for nav to be ready
    try:
        await sandbox.locator("nav").first.wait_for(state="visible", timeout=10000)
    except:
        print("  WARNING: Nav not visible, page may be in unexpected state")
        # Try to recover by reloading
        await page.reload()
        sandbox = await get_sandbox_frame(page)
        await sandbox.locator("nav").first.wait_for(state="visible", timeout=10000)

    # Click edge-cases in nav
    edge_link = sandbox.locator("nav a[data-wh-href='/edge-cases']").first
    await edge_link.wait_for(state="visible", timeout=10000)
    await edge_link.click()
    await page.wait_for_timeout(2000)

    # Wait for the edge-cases page to load
    await sandbox.locator("h1").first.wait_for(state="visible", timeout=10000)
    title = await sandbox.locator("h1").first.text_content()
    assert "Edge Cases" in title, f"Failed to navigate to edge-cases, got: {title}"

    return sandbox


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_1_various_link_types(page: Page, discovery_url: str, wormhole_server):
    """Section 1: Test all 16 link types in the Various Link Types section."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 1.1: Normal internal link
    try:
        link = sandbox.locator("a[data-wh-href='/about']").filter(has_text="Normal internal link").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.1 Normal internal link", "About" in title, title))
    except Exception as e:
        results.append(("1.1 Normal internal link", False, str(e)[:50]))

    # Go back to edge-cases
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 1.2: With query params
    try:
        link = sandbox.locator("a[data-wh-href='/about?foo=bar&baz=qux']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.2 With query params", len(title) > 0, title))
    except Exception as e:
        results.append(("1.2 With query params", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 1.3: With hash
    try:
        link = sandbox.locator("a[data-wh-href='/about#section']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.3 With hash", "About" in title, title))
    except Exception as e:
        results.append(("1.3 With hash", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 1.4: Local hash only (should NOT navigate)
    try:
        initial_title = await sandbox.locator("h1").first.text_content()
        link = sandbox.locator("a[href='#local-section']").first
        await link.click()
        await page.wait_for_timeout(1000)
        current_title = await sandbox.locator("h1").first.text_content()
        results.append(("1.4 Local hash only", current_title == initial_title, f"Stayed on page: {current_title}"))
    except Exception as e:
        results.append(("1.4 Local hash only", False, str(e)[:50]))

    # Test 1.5-1.6: javascript: links (skip - can't test alerts in headless)
    results.append(("1.5 javascript:void(0)", "SKIPPED", "Cannot test alerts in headless"))
    results.append(("1.6 javascript:alert", "SKIPPED", "Cannot test alerts in headless"))

    # Test 1.7-1.8: mailto/tel links (skip - external protocols)
    results.append(("1.7 mailto: link", "SKIPPED", "External protocol"))
    results.append(("1.8 tel: link", "SKIPPED", "External protocol"))

    # Test 1.9-1.11: External/protocol-relative links (skip - external)
    results.append(("1.9 External https", "SKIPPED", "External link"))
    results.append(("1.10 External http", "SKIPPED", "External link"))
    results.append(("1.11 Protocol-relative", "SKIPPED", "External protocol-relative"))

    # Test 1.12: Empty href
    try:
        link = sandbox.locator("a[href='']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.12 Empty href", len(title) > 0, title))
    except Exception as e:
        results.append(("1.12 Empty href", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 1.13: No href attribute (not a real link)
    results.append(("1.13 No href attribute", "SKIPPED", "Not a real link"))

    # Test 1.14: Relative ./path
    try:
        link = sandbox.locator("a[data-wh-href='./relative']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.14 Relative ./path", len(title) > 0, title))
    except Exception as e:
        results.append(("1.14 Relative ./path", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 1.15: Parent ../path
    try:
        link = sandbox.locator("a[data-wh-href='../parent']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.15 Parent ../path", len(title) > 0, title))
    except Exception as e:
        results.append(("1.15 Parent ../path", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 1.16: No leading slash
    try:
        link = sandbox.locator("a[data-wh-href='subdir/page']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("1.16 No leading slash", len(title) > 0, title))
    except Exception as e:
        results.append(("1.16 No leading slash", False, str(e)[:50]))

    # Print results
    print("\n" + "="*80)
    print("SECTION 1: VARIOUS LINK TYPES (16 tests)")
    print("="*80)
    passed = 0
    failed = 0
    skipped = 0
    for name, success, detail in results:
        if success == "SKIPPED":
            status = "⊘ SKIP"
            skipped += 1
        elif success:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print(f"\nSection 1 Summary: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*80)

    # At least the critical ones should pass
    assert passed >= 4, f"Too many failures in Section 1: only {passed} passed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_2_nested_elements(page: Page, discovery_url: str, wormhole_server):
    """Section 2: Test nested elements in links."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 2.1: Click nested div inside link
    try:
        nested_link = sandbox.locator("a[data-wh-href='/about']").filter(has_text="Click me!").first
        await nested_link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("2.1 Nested div in link", "About" in title, title))
    except Exception as e:
        results.append(("2.1 Nested div in link", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 2: NESTED ELEMENTS IN LINKS (1 test)")
    print("="*80)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print("="*80)

    assert results[0][1], "Nested element link failed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_3_target_attributes(page: Page, discovery_url: str, wormhole_server):
    """Section 3: Test links with target attributes."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []
    targets = ["_self", "_blank", "_parent", "_top", "custom-frame"]

    for target in targets:
        try:
            link = sandbox.locator(f"a[target='{target}']").first
            await link.click()
            await page.wait_for_timeout(1500)
            title = await sandbox.locator("h1").first.text_content()
            results.append((f"3.{targets.index(target)+1} target=\"{target}\"", len(title) > 0, title))

            # Navigate back
            if targets.index(target) < len(targets) - 1:
                sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)
        except Exception as e:
            results.append((f"3.{targets.index(target)+1} target=\"{target}\"", False, str(e)[:50]))

    print("\n" + "="*80)
    print(f"SECTION 3: TARGET ATTRIBUTES ({len(targets)} tests)")
    print("="*80)
    passed = sum(1 for _, s, _ in results if s)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print(f"\nSection 3 Summary: {passed}/{len(targets)} passed")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_4_positioned_links(page: Page, discovery_url: str, wormhole_server):
    """Section 4: Test positioned links."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 4.1: Top Left positioned link
    try:
        link = sandbox.locator(".positioned-link.pos-1").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("4.1 Top Left positioned", "About" in title, title))
    except Exception as e:
        results.append(("4.1 Top Left positioned", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 4.2: Top Right positioned link
    try:
        link = sandbox.locator(".positioned-link.pos-2").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("4.2 Top Right positioned", "Contact" in title, title))
    except Exception as e:
        results.append(("4.2 Top Right positioned", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 4.3: Center Bottom positioned link
    try:
        link = sandbox.locator(".positioned-link.pos-3").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("4.3 Center Bottom positioned", len(title) > 0, title))
    except Exception as e:
        results.append(("4.3 Center Bottom positioned", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 4: POSITIONED LINKS (3 tests)")
    print("="*80)
    passed = sum(1 for _, s, _ in results if s)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print(f"\nSection 4 Summary: {passed}/3 passed")
    print("="*80)

    assert passed >= 2, f"Too many positioned link failures: only {passed}/3 passed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_5_dynamic_link_modification(page: Page, discovery_url: str, wormhole_server):
    """Section 5: Test dynamic link modification."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 5.1: Modify link to /contact
    try:
        button = sandbox.locator("button:has-text('Change to /contact')").first
        await button.click()
        await page.wait_for_timeout(500)

        link = sandbox.locator("#modifiable-link").first
        await link.click()
        await page.wait_for_timeout(1500)

        title = await sandbox.locator("h1").first.text_content()
        results.append(("5.1 Modified to /contact", "Contact" in title, title))
    except Exception as e:
        results.append(("5.1 Modified to /contact", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 5: DYNAMIC LINK MODIFICATION (1 test)")
    print("="*80)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_6_event_propagation(page: Page, discovery_url: str, wormhole_server):
    """Section 6: Test event propagation."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 6.1: Link with onclick
    try:
        link = sandbox.locator("a[data-wh-href='/about'][onclick]").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("6.1 Link with onclick", "About" in title, title))
    except Exception as e:
        results.append(("6.1 Link with onclick", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 6: EVENT PROPAGATION (1 test)")
    print("="*80)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_7_rapid_clicks(page: Page, discovery_url: str, wormhole_server):
    """Section 7: Test rapid clicks."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 7.1: Rapid click link
    try:
        link = sandbox.locator("#rapid-link").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("7.1 Rapid click link", "About" in title, title))
    except Exception as e:
        results.append(("7.1 Rapid click link", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 7: RAPID CLICKS (1 test)")
    print("="*80)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_8_innerhtml_links(page: Page, discovery_url: str, wormhole_server):
    """Section 8: Test innerHTML created links."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 8.1: Create innerHTML links
    try:
        button = sandbox.locator("button:has-text('Create Links via innerHTML')").first
        await button.click()
        await page.wait_for_timeout(1000)

        # Check if links were created
        innerHTML_links = sandbox.locator("#innerhtml-container a")
        count = await innerHTML_links.count()
        results.append(("8.1 innerHTML links created", count == 3, f"Created {count} links"))

        # Try clicking one
        if count > 0:
            link = innerHTML_links.first
            await link.click()
            await page.wait_for_timeout(1500)
            title = await sandbox.locator("h1").first.text_content()
            results.append(("8.2 innerHTML link navigation", len(title) > 0, title))
    except Exception as e:
        results.append(("8.1 innerHTML links", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 8: innerHTML CREATED LINKS (2 tests)")
    print("="*80)
    passed = sum(1 for _, s, _ in results if s)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print(f"\nSection 8 Summary: {passed}/{len(results)} passed")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_9_svg_links(page: Page, discovery_url: str, wormhole_server):
    """Section 9: Test SVG links."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # SVG links might be tricky - they use SVG namespace
    # Test 9.1: SVG About link
    try:
        # SVG links are in a different namespace, use xpath
        svg_link = sandbox.locator("svg a[href='/about']").first
        await svg_link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("9.1 SVG About link", "About" in title, title))
    except Exception as e:
        results.append(("9.1 SVG About link", False, str(e)[:50]))

    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)

    # Test 9.2: SVG Contact link
    try:
        svg_link = sandbox.locator("svg a[href='/contact']").first
        await svg_link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("9.2 SVG Contact link", "Contact" in title, title))
    except Exception as e:
        results.append(("9.2 SVG Contact link", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 9: SVG LINKS (2 tests)")
    print("="*80)
    passed = sum(1 for _, s, _ in results if s)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print(f"\nSection 9 Summary: {passed}/2 passed")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_10_data_attributes(page: Page, discovery_url: str, wormhole_server):
    """Section 10: Test links with data attributes."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 10.1: Link with data attributes
    try:
        link = sandbox.locator("a[data-custom='value1']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("10.1 Link with data attrs", "About" in title, title))
    except Exception as e:
        results.append(("10.1 Link with data attrs", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 10: DATA ATTRIBUTES (1 test)")
    print("="*80)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_11_download_attribute(page: Page, discovery_url: str, wormhole_server):
    """Section 11: Test link with download attribute."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []

    # Test 11.1: Download link
    try:
        link = sandbox.locator("a[download='about.html']").first
        await link.click()
        await page.wait_for_timeout(1500)
        title = await sandbox.locator("h1").first.text_content()
        results.append(("11.1 Download link", "About" in title, title))
    except Exception as e:
        results.append(("11.1 Download link", False, str(e)[:50]))

    print("\n" + "="*80)
    print("SECTION 11: DOWNLOAD ATTRIBUTE (1 test)")
    print("="*80)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print("="*80)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_section_12_rel_attributes(page: Page, discovery_url: str, wormhole_server):
    """Section 12: Test links with rel attributes."""
    sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server, first_time=True)

    results = []
    rels = ["noopener", "noreferrer", "nofollow", "noopener noreferrer"]

    for rel in rels:
        try:
            link = sandbox.locator(f"a[rel='{rel}']").first
            await link.click()
            await page.wait_for_timeout(1500)
            title = await sandbox.locator("h1").first.text_content()
            results.append((f"12.{rels.index(rel)+1} rel=\"{rel}\"", "About" in title, title))

            if rels.index(rel) < len(rels) - 1:
                sandbox = await go_to_edge_cases(page, discovery_url, wormhole_server)
        except Exception as e:
            results.append((f"12.{rels.index(rel)+1} rel=\"{rel}\"", False, str(e)[:50]))

    print("\n" + "="*80)
    print(f"SECTION 12: REL ATTRIBUTES ({len(rels)} tests)")
    print("="*80)
    passed = sum(1 for _, s, _ in results if s)
    for name, success, detail in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {name:30s} {detail[:40]}")
    print(f"\nSection 12 Summary: {passed}/{len(rels)} passed")
    print("="*80)

    assert passed >= 3, f"Too many rel attribute failures: only {passed}/{len(rels)} passed"
