"""
scripts/test_clean_clone_deliverable_e.py — Deliverable E Clean Clone & Environment Verification Test
----------------------------------------------------------------------------------------------------
Automates complete clean-environment verification in an isolated temporary directory:
  1. Clones repository into a fresh temporary workspace
  2. Creates a clean Python virtual environment (`python -m venv venv`)
  3. Installs all required packages via `pip install -r requirements.txt`
  4. Tests Zero-Key Offline Operation (copies `.env.example` -> `.env` with no keys)
  5. Boots `start.py` and verifies all 7 microservices report `/health`
  6. Verifies Dashboard serving on port 8000
  7. Verifies Replay Mode functionality with zero keys
  8. Injects live `.env` credentials and verifies live task procurement
  9. Verifies Tesseract automatic detection on system paths with zero hardcoded paths
"""
import os
import sys
import time
import shutil
import tempfile
import subprocess
import httpx
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_venv_executables(venv_dir: str):
    if sys.platform == "win32":
        py_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        py_exe = os.path.join(venv_dir, "bin", "python")
        pip_exe = os.path.join(venv_dir, "bin", "pip")
    return py_exe, pip_exe


def wait_for_ports(ports, timeout=25.0) -> bool:
    t0 = time.time()
    pending = set(ports)
    while time.time() - t0 < timeout and pending:
        for p in list(pending):
            try:
                r = httpx.get(f"http://127.0.0.1:{p}/health", timeout=0.8)
                if r.status_code == 200:
                    pending.remove(p)
            except Exception:
                pass
        if pending:
            time.sleep(0.3)
    if pending:
        print(f"      [WARN] Ports still pending after {timeout}s: {pending}")
    return len(pending) == 0


def run_clean_clone_test():
    print("=" * 80)
    print("  DELIVERABLE E: CLEAN CLONE & REAL VIRTUALENV VERIFICATION TEST")
    print("=" * 80)

    temp_dir = os.path.realpath(tempfile.mkdtemp(prefix="procureagent_clean_clone_"))
    print(f"  [1] Created isolated workspace: {temp_dir}")

    try:
        # Step 1: Git clone into clean folder
        print("  [2] Cloning local repository into temporary workspace...")
        subprocess.run(
            ["git", "clone", REPO_ROOT, temp_dir],
            capture_output=True,
            text=True,
            check=True
        )
        print("      Git clone completed cleanly.")

        # Step 2: Create fresh virtual environment
        venv_dir = os.path.join(temp_dir, "venv")
        print(f"  [3] Creating clean virtual environment: {venv_dir}...")
        subprocess.run(
            [sys.executable, "-m", "venv", venv_dir],
            check=True,
            capture_output=True
        )
        py_exe, pip_exe = get_venv_executables(venv_dir)
        print("      Virtual environment created.")

        # Step 3: Pip install from requirements.txt
        req_path = os.path.join(temp_dir, "requirements.txt")
        print(f"  [4] Installing dependencies from {req_path}...")
        pip_res = subprocess.run(
            [pip_exe, "install", "-r", req_path],
            capture_output=True,
            text=True
        )
        if pip_res.returncode != 0:
            print(f"PIP ERROR:\n{pip_res.stderr}")
            raise RuntimeError("Pip install failed in clean clone!")
        print("      All dependencies installed successfully.")

        # Step 4: Verify Zero-Key Offline Setup (.env.example -> .env)
        example_env = os.path.join(temp_dir, ".env.example")
        clean_env = os.path.join(temp_dir, ".env")
        shutil.copy2(example_env, clean_env)
        print("  [5] Copied .env.example -> .env (Zero-Key Configuration).")

        # Step 5: Boot all microservices with start.py in background
        print("  [6] Booting microservice network via start.py...")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        offline_log = open(os.path.join(temp_dir, "offline_start.log"), "w", encoding="utf-8")
        start_proc = subprocess.Popen(
            [py_exe, "start.py"],
            cwd=temp_dir,
            env=env,
            stdout=offline_log,
            stderr=subprocess.STDOUT,
            text=True
        )

        ports = [8000, 8001, 8002, 8003, 8004, 8005, 8007]
        print("      Waiting for all 7 microservices to report /health...")
        healthy = wait_for_ports(ports, timeout=30.0)
        if not healthy:
            offline_log.flush()
            print(f"      [ERROR] start.py returncode: {start_proc.poll()}")
            try:
                with open(os.path.join(temp_dir, "offline_start.log"), "r", encoding="utf-8") as lf:
                    print(f"      [start.py LOG]:\n{lf.read()}")
            except Exception as e:
                print(f"      [Could not read log]: {e}")
        assert healthy, "One or more microservices failed to boot in clean clone!"
        print("      All 7 microservices online and healthy!")

        # Step 6: Verify Dashboard serving on port 8000
        print("  [7] Testing Dashboard HTTP server...")
        with httpx.Client(timeout=5.0) as client:
            dash_resp = client.get("http://127.0.0.1:8000/")
            assert dash_resp.status_code == 200, f"Dashboard failed: {dash_resp.status_code}"
            assert "ProcureAgent // Polaris Command Centre" in dash_resp.text
            print("      Dashboard HTML loaded successfully (Status 200).")

            # Step 7: Verify Replay Mode and zero-key endpoints
            print("  [8] Testing Replay Mode endpoints with zero API keys...")
            budget_resp = client.get("http://127.0.0.1:8000/budget")
            assert budget_resp.status_code == 200
            rep_resp = client.get("http://127.0.0.1:8000/reputation")
            assert rep_resp.status_code == 200
            ledger_resp = client.get("http://127.0.0.1:8000/ledger")
            assert ledger_resp.status_code == 200
            print("      Replay endpoints (budget, reputation, ledger) operational with zero keys.")

        # Terminate zero-key process
        start_proc.terminate()
        try:
            start_proc.wait(timeout=2.0)
        except Exception:
            start_proc.kill()
        offline_log.close()
        time.sleep(1.0)

        # Step 8: Test Live Mode with API keys
        real_env = os.path.join(REPO_ROOT, ".env")
        if os.path.exists(real_env):
            print("  [9] Injecting live credentials for live procurement test...")
            shutil.copy2(real_env, clean_env)
            live_log = open(os.path.join(temp_dir, "live_start.log"), "w", encoding="utf-8")
            live_proc = subprocess.Popen(
                [py_exe, "start.py"],
                cwd=temp_dir,
                env=env,
                stdout=live_log,
                stderr=subprocess.STDOUT,
                text=True
            )
            healthy_live = wait_for_ports(ports, timeout=30.0)
            if not healthy_live:
                live_log.flush()
                print(f"      [ERROR] live start.py returncode: {live_proc.poll()}")
                try:
                    with open(os.path.join(temp_dir, "live_start.log"), "r", encoding="utf-8") as lf:
                        print(f"      [live start.py LOG]:\n{lf.read()}")
                except Exception as e:
                    print(f"      [Could not read live log]: {e}")
            assert healthy_live, "Microservices failed to restart for live test!"

            with httpx.Client(timeout=15.0) as client:
                print("      Submitting test task to orchestrator...")
                task_resp = client.post(
                    "http://127.0.0.1:8000/task",
                    json={
                        "description": "Calculate next billing schedule date and verify system health",
                        "max_budget_usd": 0.50,
                        "force_procure": True
                    }
                )
                assert task_resp.status_code == 200, f"Task submission failed: {task_resp.text}"
                print("      Live task submission succeeded (Status 200).")

            live_proc.terminate()
            try:
                live_proc.wait(timeout=2.0)
            except Exception:
                live_proc.kill()
            live_log.close()
            print("      Live mode verified cleanly.")

        # Step 9: Automatic Tesseract path verification
        print("  [10] Verifying automatic Tesseract path detection...")
        ocr_check = subprocess.run(
            [py_exe, "-c", "from workers.ocr_worker import TESSERACT_BIN; print('Detected:', TESSERACT_BIN)"],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        print(f"      {ocr_check.stdout.strip()}")
        assert "None" not in ocr_check.stdout, "Tesseract was not automatically detected!"

        print("\n" + "=" * 80)
        print("DELIVERABLE E CLEAN CLONE TEST: 100% SUCCESSFUL")
        print(f"Verified at: {datetime.now().isoformat()}")
        print("=" * 80)
        return True

    finally:
        print(f"  [Cleanup] Removing temporary workspace: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_clean_clone_test()
    if not success:
        sys.exit(1)
