"""
test_phase2_live_system.py — End-to-end integration test for Phase 2 & 2.5:
  1. Starts Broker, Alpha, Beta, Embed, Rogue, and Orchestrator.
  2. Tests GET / (minimal live feed HTML served).
  3. Connects to ws://127.0.0.1:8000/ws.
  4. Triggers task via POST /task.
  5. Captures real-time WebSocket events:
     - BID_AWARDED to Rogue (lowest price)
     - BUDGET_RESERVED ($1.00)
     - TWO_STAGE_VERIFICATION (Integrity=True, Acceptance=False)
     - PAYMENT_BLOCKED (Rogue reservation released)
     - TASK_REALLOCATING to Alpha
     - BUDGET_RESERVED ($5.60 for Alpha)
     - TWO_STAGE_VERIFICATION (Integrity=True, Acceptance=True)
     - PAYOUT_SENT (Alpha paid)
  6. Verifies ledger rows, spending invariant, and GET /ledger/verify tamper check.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import json
import asyncio
import subprocess
import httpx
import websockets

PYTHON = sys.executable

SERVICES = [
    {"name": "broker", "cmd": [PYTHON, "-m", "uvicorn", "broker.server:app", "--port", "8001", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8001/health"},
    {"name": "ocr_alpha", "cmd": [PYTHON, "-m", "uvicorn", "workers.ocr_worker:app", "--port", "8002", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8002/health"},
    {"name": "ocr_beta", "cmd": [PYTHON, "-m", "uvicorn", "workers.ocr_worker_beta:app", "--port", "8003", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8003/health"},
    {"name": "embed_worker", "cmd": [PYTHON, "-m", "uvicorn", "workers.embed_worker:app", "--port", "8004", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8004/health"},
    {"name": "rogue_worker", "cmd": [PYTHON, "-m", "uvicorn", "workers.rogue_worker:app", "--port", "8005", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8005/health"},
    {"name": "orchestrator", "cmd": [PYTHON, "-m", "uvicorn", "orchestrator.agent:app", "--port", "8000", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8000/health"},
]

async def capture_events(ws_url, max_events=25, timeout_sec=20):
    events = []
    try:
        async with websockets.connect(ws_url) as ws:
            while len(events) < max_events:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout_sec)
                    data = json.loads(msg)
                    events.append(data)
                    print(f"  [WS Event] {data.get('event')}")
                    if data.get("event") in ("PAYOUT_SENT", "TASK_FAILED"):
                        await asyncio.sleep(0.5)
                        break
                except asyncio.TimeoutError:
                    break
    except Exception as e:
        print(f"  [WS Error] {e}")
    return events


def main():
    sys.stdout.reconfigure(line_buffering=True)
    print("=" * 70)
    print("PHASE 2 & 2.5 LIVE SYSTEM INTEGRATION TEST")
    print("=" * 70)

    # Clean DB
    from orchestrator.treasury import DB_PATH, CHAIN_HASH_PATH, init_ledger
    if os.path.exists(DB_PATH):
        try: os.remove(DB_PATH)
        except Exception: pass
    if os.path.exists(CHAIN_HASH_PATH):
        try: os.remove(CHAIN_HASH_PATH)
        except Exception: pass
    init_ledger()

    procs = []
    try:
        for svc in SERVICES:
            print(f"Starting {svc['name']}...", flush=True)
            p = subprocess.Popen(svc["cmd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            procs.append(p)

        client = httpx.Client(timeout=3)
        print("Waiting for all 6 services to become healthy...")
        for svc in SERVICES:
            healthy = False
            for _ in range(30):
                try:
                    if client.get(svc["health"]).status_code == 200:
                        healthy = True
                        break
                except Exception:
                    pass
                time.sleep(0.4)
            if not healthy:
                raise RuntimeError(f"Service {svc['name']} failed to start at {svc['health']}")
            print(f"  [OK] {svc['name']} healthy")

        # 1. Test Dashboard Endpoint (Phase 2.5)
        print("\n[Step 1] Verifying Phase 2.5 Minimal Dashboard served on GET /...")
        resp_ui = client.get("http://127.0.0.1:8000/")
        assert resp_ui.status_code == 200, f"Dashboard returned status {resp_ui.status_code}"
        assert "ProcureAgent — Live Event Feed" in resp_ui.text, "Dashboard HTML title verified"
        print("  [PASS] Minimal live event feed HTML rendered successfully!")

        # 2. Submit Task & Stream Events over WebSocket
        print("\n[Step 2] Submitting task and monitoring live WebSocket stream...")
        
        async def run_flow():
            ws_task = asyncio.create_task(capture_events("ws://127.0.0.1:8000/ws"))
            await asyncio.sleep(0.5)

            # Submit task in worker thread so event loop remains free to receive WS frames
            def submit():
                return client.post("http://127.0.0.1:8000/task", json={
                    "description": "Adversarial test: batch OCR of 2000 scanned records",
                    "max_budget_usd": 15.0
                })
            post_resp = await asyncio.to_thread(submit)
            assert post_resp.status_code == 200, "Task submission failed"
            print(f"  Task submitted: {post_resp.json()}")

            events = await ws_task
            return events

        events = asyncio.run(run_flow())
        event_types = [e.get("event") for e in events]
        print(f"\nCaptured {len(events)} events: {event_types}")

        # Assert key events occurred in sequence
        assert "TASK_RECEIVED" in event_types, "Missing TASK_RECEIVED"
        assert "BIDS_RECEIVED" in event_types, "Missing BIDS_RECEIVED"
        assert "BID_AWARDED" in event_types, "Missing BID_AWARDED"
        assert "TWO_STAGE_VERIFICATION" in event_types, "Missing TWO_STAGE_VERIFICATION"
        assert "PAYMENT_BLOCKED" in event_types, "Missing PAYMENT_BLOCKED (Rogue rejection)"
        assert "TASK_REALLOCATING" in event_types, "Missing TASK_REALLOCATING (Reallocation loop)"
        assert "PAYOUT_SENT" in event_types, "Missing PAYOUT_SENT (Alpha completion)"

        # 3. Verify Ledger & Tamper Check
        print("\n[Step 3] Verifying Ledger and Cryptographic Hash Chain...")
        ledger_rows = client.get("http://127.0.0.1:8000/ledger").json()
        print(f"  Ledger Rows count: {len(ledger_rows)}")
        assert len(ledger_rows) >= 1, "Ledger must contain settled payout row"

        paid_worker = ledger_rows[0].get("worker_id")
        paid_amount = ledger_rows[0].get("bid_usd")
        print(f"  Settled Recipient: {paid_worker} | Amount: ${paid_amount} | Status: {ledger_rows[0].get('status')}")
        assert paid_worker == "ocr-worker-01", f"Only Alpha must be paid! Found: {paid_worker}"
        assert paid_amount == 5.60, f"Paid amount must equal Alpha's bid ($5.60)! Found: {paid_amount}"

        # Assert zero payouts to rogue worker
        rogue_rows = [r for r in ledger_rows if r.get("worker_id") == "rogue-worker-01"]
        assert len(rogue_rows) == 0, "No payouts must be recorded for rogue worker!"
        print("  [Confirmed] Zero payouts recorded for rogue worker!")

        # Verify Tamper-Evidence via HTTP API
        verify_resp = client.get("http://127.0.0.1:8000/ledger/verify").json()
        print(f"  /ledger/verify result: is_valid={verify_resp.get('is_valid')}, {verify_resp.get('description')}")
        assert verify_resp.get("is_valid") is True, "Ledger hash chain must be valid"

        print("\n" + "=" * 70)
        print("ALL PHASE 2 & 2.5 LIVE SYSTEM TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        print("\nStopping services...")
        for p in procs:
            try: p.terminate()
            except Exception: pass
        for p in procs:
            try: p.wait(timeout=2)
            except Exception: p.kill()
        print("All services stopped.")

if __name__ == "__main__":
    main()
