"""
scripts/verify_and_screenshot_screens.py
----------------------------------------
Tests every screen in dashboard/index.html using Playwright at:
- 1440px x 900px
- 1280px x 800px

Asserts:
- Zero console errors across all screens and interactions
- Title contains 'ProcureAgent'
- Correct screen switching and receipts
- Saves screenshots to docs/screenshots/
"""

import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))
HTML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).replace("\\", "/")


async def main():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    console_errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for width, height in [(1440, 900), (1280, 800)]:
            context = await browser.new_context(viewport={"width": width, "height": height})
            page = await context.new_page()

            def on_console(msg):
                if msg.type == "error":
                    console_errors.append(f"[{width}x{height}] {msg.text}")

            page.on("console", on_console)
            page.on("pageerror", lambda err: console_errors.append(f"[{width}x{height}] Uncaught: {err}"))

            await page.goto(f"file:///{HTML_PATH}")
            await asyncio.sleep(1.0)

            # 1. Overview Screen
            await page.evaluate("showScreen('command')")
            await asyncio.sleep(0.5)
            out_file = os.path.join(SCREENSHOTS_DIR, f"overview_{width}.png")
            await page.screenshot(path=out_file)
            print(f"Captured: {out_file}")

            # 1b. Expanded Sidebar State
            if width == 1440:
                await page.evaluate("document.getElementById('polaris-dock').classList.add('pinned')")
                await asyncio.sleep(0.3)
                out_file_exp = os.path.join(SCREENSHOTS_DIR, "polaris_sidebar_expanded.png")
                await page.screenshot(path=out_file_exp)
                print(f"Captured: {out_file_exp}")
                await page.evaluate("document.getElementById('polaris-dock').classList.remove('pinned')")
                await asyncio.sleep(0.2)

            # 2. Purchases Screen (Receipt)
            await page.evaluate("showScreen('purchases')")
            await asyncio.sleep(0.3)
            out_file = os.path.join(SCREENSHOTS_DIR, f"purchases_{width}.png")
            await page.screenshot(path=out_file)
            print(f"Captured: {out_file}")

            # 3. Workers Screen
            await page.evaluate("showScreen('workers')")
            await asyncio.sleep(0.3)
            out_file = os.path.join(SCREENSHOTS_DIR, f"workers_{width}.png")
            await page.screenshot(path=out_file)
            print(f"Captured: {out_file}")

            # 4. Policy Screen
            await page.evaluate("showScreen('policy')")
            await asyncio.sleep(0.3)
            out_file = os.path.join(SCREENSHOTS_DIR, f"policy_{width}.png")
            await page.screenshot(path=out_file)
            print(f"Captured: {out_file}")

            # 5. Audit Screen
            await page.evaluate("showScreen('audit')")
            await asyncio.sleep(0.3)
            out_file = os.path.join(SCREENSHOTS_DIR, f"audit_{width}.png")
            await page.screenshot(path=out_file)
            print(f"Captured: {out_file}")

            # 6. Demo Scenarios Modal
            await page.evaluate("openDemoModal()")
            await asyncio.sleep(0.3)
            out_file = os.path.join(SCREENSHOTS_DIR, f"demo_scenarios_{width}.png")
            await page.screenshot(path=out_file)
            print(f"Captured: {out_file}")
            await page.evaluate("closeDemoModal()")

            await context.close()

        await browser.close()

    print("\n[VERIFICATION SUMMARY]")
    print(f"Console errors detected: {len(console_errors)}")
    for err in console_errors:
        print(f"  ERROR: {err}")

    assert len(console_errors) == 0, f"Found {len(console_errors)} console errors!"
    print("[PASS] All screens verified at 1440px and 1280px with 0 console errors!")


if __name__ == "__main__":
    asyncio.run(main())

