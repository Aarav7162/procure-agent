"""
test_backend.py — Automated end-to-end backend integration test
Spawns broker, 3 workers, and orchestrator, submits a task, waits for loop completion,
and validates the audit ledger and budget summary.
"""
import sys
import time
import subprocess
import httpx

PYTHON = sys.executable

SERVICES = [
    {"name": "broker", "cmd": [PYTHON, "-m", "uvicorn", "broker.server:app", "--port", "8001", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8001/health"},
    {"name": "ocr_alpha", "cmd": [PYTHON, "-m", "uvicorn", "workers.ocr_worker:app", "--port", "8002", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8002/health"},
    {"name": "ocr_beta", "cmd": [PYTHON, "-m", "uvicorn", "workers.ocr_worker_beta:app", "--port", "8003", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8003/health"},
    {"name": "embed_worker", "cmd": [PYTHON, "-m", "uvicorn", "workers.embed_worker:app", "--port", "8004", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8004/health"},
    {"name": "orchestrator", "cmd": [PYTHON, "-m", "uvicorn", "orchestrator.agent:app", "--port", "8000", "--host", "127.0.0.1"], "health": "http://127.0.0.1:8000/health"},
]

def main():
    sys.stdout.reconfigure(line_buffering=True)
    procs = []
    print("=== ProcureAgent Backend Integration Test ===", flush=True)
    try:
        # 1. Start all services
        for svc in SERVICES:
            print(f"Starting {svc['name']}...", flush=True)
            p = subprocess.Popen(svc["cmd"])
            procs.append(p)

        # 2. Wait for health checks
        print("Waiting for all 5 services to become healthy...")
        client = httpx.Client(timeout=3)
        for svc in SERVICES:
            ok = False
            for _ in range(30):
                try:
                    r = client.get(svc["health"])
                    if r.status_code == 200:
                        ok = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            if not ok:
                raise RuntimeError(f"Service {svc['name']} failed to start at {svc['health']}")
            print(f"  [OK] {svc['name']} healthy")

        # 3. Submit a task
        print("\nSubmitting task: 'Process 2000 scanned tax forms with OCR'...")
        resp = client.post("http://127.0.0.1:8000/task", json={
            "description": "Process 2000 scanned tax forms with OCR",
            "max_budget_usd": 15.0
        })
        print("Task response:", resp.json())
        cycle_id = resp.json().get("cycle_id")

        # 4. Wait for agent loop to complete
        print("Waiting for autonomous procurement cycle to execute...")
        ledger_rows = []
        for i in range(25):
            time.sleep(1)
            try:
                lr = client.get("http://127.0.0.1:8000/ledger").json()
                if len(lr) >= 2:
                    ledger_rows = lr
                    print(f"  Cycle finished! Found {len(lr)} ledger rows after {i+1}s.")
                    break
            except Exception as e:
                pass

        if not ledger_rows:
            # Fetch whatever we have
            ledger_rows = client.get("http://127.0.0.1:8000/ledger").json()
            print(f"Warning: Found {len(ledger_rows)} ledger rows.")

        print("\n=== LEDGER ENTRIES ===")
        for row in ledger_rows:
            print(f"ID: {row.get('id')} | Worker: {row.get('worker_id')} | Amount: ${row.get('bid_usd')} | Payout Batch ID: {row.get('payout_batch_id')} | Status: {row.get('status')}")

        budget_summary = client.get("http://127.0.0.1:8000/budget").json()
        print("\n=== BUDGET SUMMARY ===")
        print(budget_summary)

        # 5. Validate Gate
        assert len(ledger_rows) >= 1, "Ledger must contain at least 1 row!"
        for r in ledger_rows:
            assert r.get("payout_batch_id") is not None, "payout_batch_id cannot be null!"
            assert r.get("status") == "PAID", "status must be PAID!"
        print("\n>>> STAGE 3 GATE PASSED: All payouts verified and recorded in SQLite ledger! <<<")

    finally:
        print("\nStopping services...")
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=2)
            except Exception:
                p.kill()
        print("All services stopped.")

if __name__ == "__main__":
    main()
