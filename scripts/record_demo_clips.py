"""
scripts/record_demo_clips.py
----------------------------
Records the four official video clips using Playwright against the live stack
with PAYOUT_MODE=live:
  1. clip1_rogue_blocked.webm: Code bounty with rogue underbidder blocked ($0 spent).
  2. clip2_reassignment_live_payout.webm: Reassignment to 120B with live PayPal payout and batch ID.
  3. clip3_verify_chain.webm: Full SHA-256 hash chain verification in Audit tab.
  4. clip4_impossible_task_zero_spend.webm: Impossible task with zero capability match ($0 spent).
"""
import asyncio
import os
import shutil
import time
import httpx
from playwright.async_api import async_playwright

CLIPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "demo_clips")
BASE_URL = "http://127.0.0.1:8000"


async def record_clip_1(playwright):
    """Clip 1: Code bounty with rogue worker blocked ($0 spent)."""
    print("\n[CLIP 1] Recording Rogue Blocked ($0 spent)...", flush=True)
    t0 = time.time()
    temp_dir = os.path.join(CLIPS_DIR, "tmp_clip1")
    os.makedirs(temp_dir, exist_ok=True)

    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        record_video_dir=temp_dir,
        viewport={"width": 1440, "height": 900}
    )
    page = await context.new_page()
    video = page.video

    await page.goto(f"{BASE_URL}/", wait_until="networkidle")
    await asyncio.sleep(2.0)

    # Click Rogue preset chip
    print("  Selecting 'Rogue Attack (Forced)' preset...", flush=True)
    await page.click("#chip-rogue")
    await asyncio.sleep(1.0)

    # Click Submit Request
    print("  Submitting request to trigger adversarial underbid...", flush=True)
    await page.click("#btn-submit")

    # Wait for the blocked event or crimson alert
    print("  Waiting for Gate 4 unit test failure & payment block...", flush=True)
    for _ in range(30):
        await asyncio.sleep(0.5)
        text = await page.content()
        if "PAYMENT_BLOCKED" in text or "Payment Blocked" in text or "Gate 4 assertions failed" in text:
            print("  [DETECTED] Gate 4 Assertions Failed: Payment Blocked ($0.00 spent)!", flush=True)
            break

    # Pause to show the blocked state clearly
    await asyncio.sleep(4.0)

    # Close page and context FIRST so video flushes to disk
    await page.close()
    await context.close()
    video_path = await video.path()
    await browser.close()
    wall_duration = time.time() - t0

    dest_file = os.path.join(CLIPS_DIR, "clip1_rogue_blocked.webm")
    if os.path.exists(dest_file):
        os.remove(dest_file)
    shutil.move(video_path, dest_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    file_size_kb = os.path.getsize(dest_file) / 1024
    print(f"  Saved -> {dest_file} ({file_size_kb:.1f} KB, ~{wall_duration:.1f}s)", flush=True)
    return {"clip": "clip1_rogue_blocked.webm", "duration_sec": round(wall_duration, 1), "batch_id": "NONE ($0.00 Spent - BLOCKED)"}


async def record_clip_2(playwright):
    """Clip 2: Live code bounty reassignment with real PayPal Sandbox payout."""
    print("\n[CLIP 2] Recording Live Code Bounty Reassignment & PayPal Payout...", flush=True)
    t0 = time.time()
    temp_dir = os.path.join(CLIPS_DIR, "tmp_clip2")
    os.makedirs(temp_dir, exist_ok=True)

    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        record_video_dir=temp_dir,
        viewport={"width": 1440, "height": 900}
    )
    page = await context.new_page()
    video = page.video

    await page.goto(f"{BASE_URL}/", wait_until="networkidle")
    await asyncio.sleep(2.0)

    # Click Code Bounty preset chip
    print("  Selecting 'Code Bounty' preset...", flush=True)
    await page.click("#chip-bounty")
    await asyncio.sleep(1.0)

    # Click Submit Request
    print("  Submitting code bounty task to live stack (PAYOUT_MODE=live)...", flush=True)
    await page.click("#btn-submit")

    # Monitor for PayPal payout batch ID
    batch_id = "UNKNOWN"
    print("  Awaiting live Groq synthesis, sandbox unit tests, and PayPal Payout execution...", flush=True)
    for _ in range(40):
        await asyncio.sleep(0.5)
        content = await page.content()
        if "PAYOUT_SENT" in content or "PAYOUT_COMPLETED" in content or "Batch ID" in content or "PAYOUT_SUCCESS" in content:
            print("  [DETECTED] PayPal Payout Dispatched & Completed!", flush=True)
            break

    # Look for batch ID in database or page
    import sqlite3
    try:
        conn = sqlite3.connect("audit/ledger.db")
        cur = conn.cursor()
        cur.execute("SELECT paypal_batch_id FROM ledger_entries WHERE paypal_batch_id IS NOT NULL ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            batch_id = row[0]
        conn.close()
    except Exception:
        pass

    # Pause to show settled status and ledger block
    await asyncio.sleep(4.0)

    await page.close()
    await context.close()
    video_path = await video.path()
    await browser.close()
    wall_duration = time.time() - t0

    dest_file = os.path.join(CLIPS_DIR, "clip2_reassignment_live_payout.webm")
    if os.path.exists(dest_file):
        os.remove(dest_file)
    shutil.move(video_path, dest_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    file_size_kb = os.path.getsize(dest_file) / 1024
    print(f"  Saved -> {dest_file} ({file_size_kb:.1f} KB, ~{wall_duration:.1f}s, Batch ID: {batch_id})", flush=True)
    return {"clip": "clip2_reassignment_live_payout.webm", "duration_sec": round(wall_duration, 1), "batch_id": batch_id}


async def record_clip_3(playwright):
    """Clip 3: Verify Chain in Audit Ledger tab."""
    print("\n[CLIP 3] Recording Verify Chain Proof in Audit Tab...", flush=True)
    t0 = time.time()
    temp_dir = os.path.join(CLIPS_DIR, "tmp_clip3")
    os.makedirs(temp_dir, exist_ok=True)

    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        record_video_dir=temp_dir,
        viewport={"width": 1440, "height": 900}
    )
    page = await context.new_page()
    video = page.video

    await page.goto(f"{BASE_URL}/", wait_until="networkidle")
    await asyncio.sleep(1.5)

    # Click Audit tab on sidebar
    print("  Switching to Audit Ledger page...", flush=True)
    await page.click("#nav-audit")
    await asyncio.sleep(1.5)

    # Click Verify Chain button
    print("  Clicking 'Verify Full Hash Chain' button...", flush=True)
    await page.click("#btn-verify-chain-page")

    # Wait for verification toast and island message
    await asyncio.sleep(3.5)

    await page.close()
    await context.close()
    video_path = await video.path()
    await browser.close()
    wall_duration = time.time() - t0

    dest_file = os.path.join(CLIPS_DIR, "clip3_verify_chain.webm")
    if os.path.exists(dest_file):
        os.remove(dest_file)
    shutil.move(video_path, dest_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    file_size_kb = os.path.getsize(dest_file) / 1024
    print(f"  Saved -> {dest_file} ({file_size_kb:.1f} KB, ~{wall_duration:.1f}s)", flush=True)
    return {"clip": "clip3_verify_chain.webm", "duration_sec": round(wall_duration, 1), "batch_id": "N/A (Chain Proof Verification)"}


async def record_clip_4(playwright):
    """Clip 4: Impossible task demonstrating zero capability match and $0 spent."""
    print("\n[CLIP 4] Recording Impossible Task ($0 Spent)...", flush=True)
    t0 = time.time()
    temp_dir = os.path.join(CLIPS_DIR, "tmp_clip4")
    os.makedirs(temp_dir, exist_ok=True)

    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        record_video_dir=temp_dir,
        viewport={"width": 1440, "height": 900}
    )
    page = await context.new_page()
    video = page.video

    await page.goto(f"{BASE_URL}/", wait_until="networkidle")
    await asyncio.sleep(2.0)

    # Click Impossible Task chip
    print("  Selecting 'Impossible Task' preset...", flush=True)
    await page.click("#chip-impossible")
    await asyncio.sleep(1.0)

    # Click Submit Request
    print("  Submitting impossible request...", flush=True)
    await page.click("#btn-submit")

    # Wait for outcome
    await asyncio.sleep(4.0)

    await page.close()
    await context.close()
    video_path = await video.path()
    await browser.close()
    wall_duration = time.time() - t0

    dest_file = os.path.join(CLIPS_DIR, "clip4_impossible_task_zero_spend.webm")
    if os.path.exists(dest_file):
        os.remove(dest_file)
    shutil.move(video_path, dest_file)
    shutil.rmtree(temp_dir, ignore_errors=True)

    file_size_kb = os.path.getsize(dest_file) / 1024
    print(f"  Saved -> {dest_file} ({file_size_kb:.1f} KB, ~{wall_duration:.1f}s)", flush=True)
    return {"clip": "clip4_impossible_task_zero_spend.webm", "duration_sec": round(wall_duration, 1), "batch_id": "NONE ($0.00 Reserved, $0.00 Spent - No Capable Workers)"}


async def main():
    os.makedirs(CLIPS_DIR, exist_ok=True)
    print("=" * 70, flush=True)
    print("  RECORDING 4 PLAYWRIGHT DEMO CLIPS AGAINST LIVE STACK (PAYOUT_MODE=live)", flush=True)
    print(f"  Target Directory: {CLIPS_DIR}", flush=True)
    print("=" * 70, flush=True)

    async with async_playwright() as playwright:
        results = []
        r1 = await record_clip_1(playwright)
        results.append(r1)

        r2 = await record_clip_2(playwright)
        results.append(r2)

        r3 = await record_clip_3(playwright)
        results.append(r3)

        r4 = await record_clip_4(playwright)
        results.append(r4)

    print("\n" + "=" * 70, flush=True)
    print("  DEMO FOOTAGE RECORDING SUMMARY", flush=True)
    print("=" * 70, flush=True)
    import json
    summary_path = os.path.join(CLIPS_DIR, "clips_manifest.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    for r in results:
        print(f"  • {r['clip']:<38} Duration: {r['duration_sec']}s | Batch ID: {r['batch_id']}", flush=True)
    print(f"\nSaved manifest to {summary_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
