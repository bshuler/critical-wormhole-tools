"""
Quick test to verify headed browser mode works with xvfb-run.

Run with:
    xvfb-run -a python discovery-site/tests/test_headed_browser.py
"""

import asyncio
import sys


async def test_headed_browser():
    """Test that we can launch a headed browser with xvfb."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright not installed")
        print("Run: pip install playwright && playwright install")
        return False

    print("Testing headed browser mode...")

    async with async_playwright() as p:
        # Launch in headed mode (not headless)
        print("Launching Chromium in headed mode...")
        browser = await p.chromium.launch(headless=False)

        print("Creating new page...")
        page = await browser.new_page()

        # Navigate to a test URL
        print("Navigating to example.com...")
        await page.goto("https://example.com")

        # Get title
        title = await page.title()
        print(f"Page title: {title}")

        # Test WebSocket capability
        print("Testing WebSocket support...")
        ws_result = await page.evaluate("""
            () => {
                return {
                    hasWebSocket: typeof WebSocket !== 'undefined',
                    hasRTCPeerConnection: typeof RTCPeerConnection !== 'undefined'
                };
            }
        """)
        print(f"WebSocket available: {ws_result['hasWebSocket']}")
        print(f"RTCPeerConnection available: {ws_result['hasRTCPeerConnection']}")

        # Test actual WebSocket connection
        print("Testing WebSocket connection to public echo server...")
        ws_test_result = await page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    const ws = new WebSocket('wss://echo.websocket.org');
                    const timeout = setTimeout(() => {
                        ws.close();
                        resolve({success: false, error: 'timeout'});
                    }, 10000);

                    ws.onopen = () => {
                        ws.send('Hello from Playwright!');
                    };

                    ws.onmessage = (event) => {
                        clearTimeout(timeout);
                        ws.close();
                        resolve({success: true, data: event.data});
                    };

                    ws.onerror = (event) => {
                        clearTimeout(timeout);
                        ws.close();
                        resolve({success: false, error: 'connection error'});
                    };
                });
            }
        """)
        print(f"WebSocket test result: {ws_test_result}")

        await browser.close()
        print("\nHeaded browser test completed successfully!")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_headed_browser())
    sys.exit(0 if success else 1)
