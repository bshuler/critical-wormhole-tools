"""
Debug script to investigate wormhole connection in browser.
"""

import asyncio
import signal
import subprocess
import sys
import time
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_FIXTURES = PROJECT_ROOT / "browser-extension" / "tests" / "e2e" / "fixtures"
DISCOVERY_URL = "https://discovery.prod.criticalwormholebrowser.apps.criticalwormhole.tools"


def extract_wormhole_code(output: str):
    """Extract wormhole code from wh listen output."""
    match = re.search(r"Listening on code:\s*(\d+-\w+-\w+)", output)
    if match:
        return match.group(1)
    return None


async def debug_connection():
    from playwright.async_api import async_playwright

    # Start wormhole server
    print(f"Starting wormhole server serving: {TEST_FIXTURES}")
    cmd = [sys.executable, "-m", "wh.cli.main", "listen", "--serve", str(TEST_FIXTURES)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Wait for code
    code = None
    start_time = time.time()
    while time.time() - start_time < 30:
        line = process.stdout.readline()
        if line:
            print(f"[wh] {line.rstrip()}")
            code = extract_wormhole_code(line)
            if code:
                break
        time.sleep(0.1)

    if not code:
        print("ERROR: Failed to get wormhole code")
        process.kill()
        return

    print(f"\nGot wormhole code: {code}")
    print(f"Connecting via: {DISCOVERY_URL}\n")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            # Enable console logging
            page.on("console", lambda msg: print(f"[console.{msg.type}] {msg.text}"))
            page.on("pageerror", lambda err: print(f"[page error] {err}"))

            print("Loading discovery site...")
            await page.goto(DISCOVERY_URL)
            await page.wait_for_load_state("networkidle")
            print("Page loaded")

            # Enter the code
            print(f"Entering code: {code}")
            input_el = await page.query_selector('#address-input')
            await input_el.fill(code)

            # Click connect
            print("Clicking connect...")
            button = await page.query_selector('#connect-btn')
            await button.click()

            # Wait and observe
            print("Waiting for connection (60 seconds)...")
            print("Watching for navigation or errors...\n")

            for i in range(60):
                url = page.url
                print(f"[{i}s] URL: {url}")

                # Check for error messages
                status_el = await page.query_selector('#status')
                if status_el:
                    status_text = await status_el.text_content()
                    if status_text:
                        print(f"[{i}s] Status: {status_text}")

                if "viewer.html" in url:
                    print("\n SUCCESS: Navigated to viewer!")
                    break

                await asyncio.sleep(1)

            # Get final state
            print("\n--- Final State ---")
            print(f"URL: {page.url}")
            content = await page.content()
            print(f"Page content length: {len(content)}")

            # Screenshot for debugging
            await page.screenshot(path="/tmp/discovery_debug.png")
            print("Screenshot saved to /tmp/discovery_debug.png")

            await browser.close()

    finally:
        print("\nStopping wormhole server...")
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    asyncio.run(debug_connection())
