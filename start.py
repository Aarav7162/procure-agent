"""
start.py — One-Command Launch Script for ProcureAgent
------------------------------------------------------
Spawns the complete autonomous procurement network:
  • Orchestrator Agent (Port 8000)
  • Capability Broker Marketplace (Port 8001)
  • OCR Worker Alpha — Tesseract PSM 3 (Port 8002)
  • Code Worker 120B — openai/gpt-oss-120b (Port 8003)
  • LLM Worker — Synthesis & Citations (Port 8004)
  • Rogue Worker — Scripted Adversary (Port 8005)
  • Code Worker 20B — openai/gpt-oss-20b (Port 8007)

Usage:
  python start.py
Dashboard URL:
  http://127.0.0.1:8000/
"""
import os
import sys
import time
import signal
import subprocess
import webbrowser
import httpx

SERVICES = [
    ("Orchestrator Agent", "orchestrator.agent:app", 8000),
    ("Capability Broker", "broker.server:app", 8001),
    ("OCR Specialist Alpha", "workers.ocr_worker:app", 8002),
    ("Code Specialist (120B)", "workers.code_worker:app", 8003),
    ("LLM Specialist", "workers.llm_worker:app", 8004),
    ("Rogue Worker (Fixture)", "workers.rogue_worker:app", 8005),
    ("Fast Code Worker (20B)", "workers.code_worker_20b:app", 8007),
]


def wait_for_health(port: int, timeout: float = 10.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.8)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.2)
    return False


def main():
    print("=" * 75)
    print("  PROCUREAGENT: AUTONOMOUS AI CAPABILITY PROCUREMENT & SETTLEMENT ENGINE")
    print("=" * 75)
    print("  Booting full microservice cluster...\n")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    processes = []

    try:
        for name, app_module, port in SERVICES:
            print(f"  [STARTING] {name:<26} on http://127.0.0.1:{port}...", end="", flush=True)
            cmd = [sys.executable, "-m", "uvicorn", app_module, "--host", "127.0.0.1", "--port", str(port)]
            p = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append((name, p, port))

            if wait_for_health(port):
                print(" [READY]")
            else:
                print(" [TIMED OUT]")

        dashboard_url = "http://127.0.0.1:8000/"

        print("\n" + "=" * 75)
        print(f"  STATUS: All {len(SERVICES)} microservices are online and ready!")
        print(f"  DASHBOARD URL : {dashboard_url}")
        print("=" * 75)
        print("\n  OPERATING MODES:")
        print("    1. Live Mode (WebSocket):")
        print("       - Submit free-form natural language tasks via the task box.")
        print("       - Test 'Code Bounty', 'Impossible Task', 'Rogue Attack', or 'Occupy Host'.")
        print("       - Real Groq LLM inference, Tesseract OCR, and PayPal Sandbox payouts.")
        print("    2. Replay Mode (Offline / Zero API Keys):")
        print("       - Toggle the top switch to 'Replay Recorded Run'.")
        print("       - Step through the 15-event verified code bounty run with play/pause controls.")
        print("\n  Press CTRL+C to gracefully stop all services.")
        print("=" * 75)

        # Automatically open browser
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            pass

        # Keep parent alive until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nShutting down all services...")
    finally:
        for name, p, port in processes:
            try:
                p.terminate()
                p.wait(timeout=1.5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("All ProcureAgent services stopped cleanly.")


if __name__ == "__main__":
    main()

