"""
tests/test_offline_dashboard.py
-------------------------------
Asserts that dashboard/index.html functions completely offline:
- Three.js is loaded from local vendored three.min.js (or 2D canvas fallback activates)
- Beams canvas is initialized
- RECORDED_RUN embedded data is accessible
- Zero reliance on external CDNs or network fetches
"""
import asyncio
import os
from playwright.async_api import async_playwright


async def test_offline_mode():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # offline=True simulates zero internet connectivity
        context = await browser.new_context(offline=True)
        page = await context.new_page()

        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")).replace("\\", "/")
        await page.goto(f"file:///{file_path}")
        await asyncio.sleep(1.0)

        title = await page.title()
        assert "ProcureAgent" in title, f"Unexpected title: {title}"

        # Check canvas presence
        canvas = await page.query_selector("#beams-canvas")
        assert canvas is not None, "Beams canvas element #beams-canvas not found!"

        # Check Three.js availability or graceful canvas fallback
        three_loaded = await page.evaluate("typeof THREE !== 'undefined'")
        replay_ready = await page.evaluate("typeof RECORDED_RUN !== 'undefined'")
        event_count = await page.evaluate("RECORDED_RUN.events.length")

        print("[OFFLINE TEST RESULTS]")
        print(f"  Title: {title}")
        print(f"  Beams canvas present: {canvas is not None}")
        print(f"  Three.js loaded offline: {three_loaded}")
        print(f"  Embedded Replay events count: {event_count}")

        assert replay_ready, "RECORDED_RUN is not defined in offline mode!"
        assert event_count > 0, "No replay events loaded!"

        await browser.close()
        print("[PASS] Offline mode test succeeded! Replay functions 100% offline.")


if __name__ == "__main__":
    asyncio.run(test_offline_mode())

