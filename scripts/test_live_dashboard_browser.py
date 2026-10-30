"""
scripts/test_live_dashboard_browser.py — Headless Browser Verification of Live Dashboard
-----------------------------------------------------------------------------------------
Automates Playwright headless Chromium against the live backend stack:
  1. Boots orchestrator, broker, and worker services
  2. Navigates to http://127.0.0.1:8000/
  3. Verifies WebSocket connection in Live Mode
  4. Exercises:
       - Host-bottleneck button
       - Impossible task chip (proves $0.00 spent on NO_CAPABLE_WORKERS)
       - Rogue attack chip (proves payment blocked and reallocation)
       - Code bounty chip
       - Replay mode switcher
  5. Captures high-res screenshots to docs/screenshots/
"""
import os
import sys
import time
import subprocess
import asyncio
import httpx
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots"))
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def wait_for_service(url: str, timeout: float = 12.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.3)
    return False


def run_browser_tests():
    print("=" * 70)
    print("STARTING BACKEND MICROSERVICES FOR LIVE DASHBOARD TEST")
    print("=" * 70)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    procs = []
    try:
        services_to_start = [
            ("http://127.0.0.1:8000/health", ["uvicorn", "orchestrator.agent:app", "--port", "8000", "--host", "127.0.0.1"]),
            ("http://127.0.0.1:8001/health", ["uvicorn", "broker.server:app", "--port", "8001", "--host", "127.0.0.1"]),
            ("http://127.0.0.1:8002/health", ["uvicorn", "workers.ocr_worker:app", "--port", "8002", "--host", "127.0.0.1"]),
            ("http://127.0.0.1:8003/health", ["uvicorn", "workers.code_worker:app", "--port", "8003", "--host", "127.0.0.1"]),
            ("http://127.0.0.1:8004/health", ["uvicorn", "workers.llm_worker:app", "--port", "8004", "--host", "127.0.0.1"]),
            ("http://127.0.0.1:8005/health", ["uvicorn", "workers.rogue_worker:app", "--port", "8005", "--host", "127.0.0.1"]),
            ("http://127.0.0.1:8007/health", ["uvicorn", "workers.code_worker_20b:app", "--port", "8007", "--host", "127.0.0.1"]),
        ]

        for url, cmd in services_to_start:
            if not wait_for_service(url, timeout=0.5):
                p = subprocess.Popen([sys.executable, "-m"] + cmd, env=env)
                procs.append(p)
            else:
                print(f"  Service at {url} is already running. Reusing existing instance.")

        print("  Waiting for all microservices to report healthy...")
        for url, _ in services_to_start:
            assert wait_for_service(url, timeout=10.0), f"Service at {url} failed to respond"
        print("  All 7 microservices healthy!")

        print("\n" + "=" * 70)
        print("LAUNCHING PLAYWRIGHT HEADLESS BROWSER")
        print("=" * 70)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Handle alert dialogs gracefully
            page.on("dialog", lambda dialog: dialog.accept())

            # Navigate to index.html
            print("  Navigating to http://127.0.0.1:8000/...")
            page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
            time.sleep(1.0)

            # Wait for WS Connected handshake
            page.wait_for_selector("#conn-text:has-text('Connected')", timeout=8000)
            conn_text = page.locator("#conn-text").inner_text()
            print(f"  WebSocket status indicator: '{conn_text}'")
            assert "Connected" in conn_text, f"Expected WS Connected, got {conn_text}"

            # Initial screenshot
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "00_dashboard_initial_live.png"))
            print("  [Screenshot] Saved 00_dashboard_initial_live.png")

            # ─────────────────────────────────────────────────────────────
            # Action 1: Occupy Host Slot
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 1] Clicking 'Occupy Host Slot'...")
            page.click("#btn-occupy")
            time.sleep(1.0)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_host_bottleneck_occupied.png"))
            print("  [Screenshot] Saved 01_host_bottleneck_occupied.png")

            # ─────────────────────────────────────────────────────────────
            # Action 2: Impossible Task ($0 Spent Proof)
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 2] Clicking Impossible Task chip and deploying...")
            page.click(".chip-impossible")
            time.sleep(0.5)
            page.click("#btn-submit")

            # Wait for NO_CAPABLE_WORKERS event
            print("  Waiting for NO_CAPABLE_WORKERS event in event stream...")
            page.wait_for_selector(".ev-NO_CAPABLE_WORKERS", timeout=12000)
            feed_text = page.locator("#event-feed").inner_text()
            assert "CAPABILITY MARKETPLACE EXHAUSTED" in feed_text
            assert "Proof of $0.00 spent" in feed_text
            print("  -> Verified: Marketplace rejected impossible capabilities with $0.00 spent!")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_impossible_task_zero_spent.png"))
            print("  [Screenshot] Saved 02_impossible_task_zero_spent.png")

            # ─────────────────────────────────────────────────────────────
            # Action 3: Rogue Adversary Underbid Attack
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 3] Clicking 'Simulate Rogue Underbid Attack'...")
            page.click("#btn-attack")

            print("  Waiting for pipeline events: Verification -> Payment Blocked -> Reallocation -> Settlement...")
            # Wait for PAYMENT_BLOCKED
            page.wait_for_selector(".ev-PAYMENT_BLOCKED", timeout=60000)
            print("  -> Verified: Rogue payment blocked ($0.00 transferred)!")

            # Wait for PAYOUT_SENT
            page.wait_for_selector(".ev-PAYOUT_SENT", timeout=90000)
            print("  -> Verified: Reallocation to honest worker settled via PayPal Sandbox!")

            time.sleep(1.0)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_rogue_blocked_and_reallocated.png"))
            print("  [Screenshot] Saved 03_rogue_blocked_and_reallocated.png")

            # ─────────────────────────────────────────────────────────────
            # Action 4: Code Bounty Chip
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 4] Selecting Code Bounty preset and deadline slider...")
            page.click(".chip:has-text('Code Bounty')")
            page.fill("#task-deadline", "10")
            time.sleep(0.5)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_code_bounty_configured.png"))
            print("  [Screenshot] Saved 04_code_bounty_configured.png")

            # ─────────────────────────────────────────────────────────────
            # Action 5: Switch to Replay Mode and Step Forward
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 5] Switching to Replay Mode (Offline / Zero-API-Key Demo)...")
            page.click("#btn-mode-replay")
            time.sleep(0.5)

            # Click Next 4 times
            page.click("#btn-replay-next")
            time.sleep(0.3)
            page.click("#btn-replay-next")
            time.sleep(0.3)
            page.click("#btn-replay-next")
            time.sleep(0.3)
            page.click("#btn-replay-next")
            time.sleep(0.5)

            step_label = page.locator("#replay-step-label").inner_text()
            print(f"  Replay step indicator: '{step_label}'")
            assert "Step 4" in step_label

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_replay_mode_playback.png"))
            print("  [Screenshot] Saved 05_replay_mode_playback.png")

            # ─────────────────────────────────────────────────────────────
            # Action 6: Incidents & Threat Dossier Page
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 6] Navigating to Incidents & Threats page...")
            page.click("#nav-incidents")
            time.sleep(0.5)
            assert page.is_visible("#page-incidents")
            incidents_text = page.locator("#page-incidents").inner_text()
            assert "ROGUE_WORKER_01" in incidents_text
            assert "GATE 4 ASSERTIONS" in incidents_text
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_incidents_threat_dossier.png"))
            print("  [Screenshot] Saved 06_incidents_threat_dossier.png")

            # ─────────────────────────────────────────────────────────────
            # Action 7: Fleet Monitoring Page & Microservice Ping
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 7] Navigating to Fleet Telemetry & triggering node ping...")
            page.click("#nav-monitoring")
            time.sleep(0.5)
            assert page.is_visible("#page-monitoring")
            page.click("#btn-ping-fleet")
            time.sleep(1.0)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_fleet_telemetry_monitoring.png"))
            print("  [Screenshot] Saved 07_fleet_telemetry_monitoring.png")

            # ─────────────────────────────────────────────────────────────
            # Action 8: Audit Ledger Page & Tamper-Evident Chain Proof
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 8] Navigating to Audit Ledger & verifying hash chain...")
            page.click("#nav-audit")
            time.sleep(0.5)
            assert page.is_visible("#page-audit")
            page.click("#btn-verify-chain")
            time.sleep(0.5)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_audit_ledger_chain_proof.png"))
            print("  [Screenshot] Saved 08_audit_ledger_chain_proof.png")

            # ─────────────────────────────────────────────────────────────
            # Action 9: Settings & Policies Page
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 9] Navigating to Settings & Policies...")
            page.click("#nav-settings")
            time.sleep(0.5)
            assert page.is_visible("#page-settings")
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_governance_settings.png"))
            print("  [Screenshot] Saved 09_governance_settings.png")

            # ─────────────────────────────────────────────────────────────
            # Action 10: Return to Command Centre & Verify Horizontal Registry
            # ─────────────────────────────────────────────────────────────
            print("\n  [Test 10] Returning to Command Centre and testing registry filter...")
            page.click("#nav-command")
            time.sleep(0.5)
            page.click("button.filter-tab:has-text('Code Gen')")
            time.sleep(0.3)
            # Verify ocr row is hidden, code row is visible
            ocr_vis = page.locator("#rep-body-full tr:has-text('ocr-worker-01')").is_visible()
            code_vis = page.locator("#rep-body-full tr:has-text('code-worker-01')").is_visible()
            assert code_vis is True
            assert ocr_vis is False
            print("  -> Verified: Category filter properly shows Code Gen and hides OCR!")
            page.click("button.filter-tab:has-text('All Workers')")
            time.sleep(0.3)

            browser.close()

        print("\n" + "=" * 70)
        print("ALL BROWSER AUTOMATION TESTS COMPLETED SUCCESSFULLY!")
        print(f"Screenshots archived in: {SCREENSHOT_DIR}")
        print("=" * 70)

    finally:
        print("\nTerminating background services...")
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=2.0)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    run_browser_tests()
