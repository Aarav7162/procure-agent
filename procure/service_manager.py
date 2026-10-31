"""
procure/service_manager.py
--------------------------
Manages health-checking and autonomous background boot of the 7 microservices.
Ensures zero-friction CLI launch without requiring a separate terminal window.
"""
import os
import sys
import time
import subprocess
from typing import List, Dict, Any, Tuple
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

_SPAWNED_PROCESSES: List[Tuple[str, subprocess.Popen, int]] = []


def is_service_healthy(port: int, timeout: float = 0.6) -> bool:
    """Checks if a given microservice responds on /health."""
    try:
        r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def get_all_services_health() -> List[Dict[str, Any]]:
    """Returns status report for all 7 microservices."""
    res = []
    for name, module, port in SERVICES:
        healthy = is_service_healthy(port)
        res.append({
            "name": name,
            "module": module,
            "port": port,
            "healthy": healthy,
        })
    return res


def ensure_cluster_online(quiet: bool = False) -> bool:
    """
    Checks all services. If any are down, automatically launches them
    in background subprocesses and verifies health.
    """
    missing = [s for s in SERVICES if not is_service_healthy(s[2])]
    if not missing:
        return True

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PAYOUT_MODE"] = os.getenv("PAYOUT_MODE", "live")

    for name, module, port in missing:
        if not quiet:
            print(f"  [BOOTING] {name} on port {port}...", flush=True)
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _SPAWNED_PROCESSES.append((name, p, port))

    # Wait up to 10s for all to come online
    t0 = time.time()
    while time.time() - t0 < 10.0:
        all_up = all(is_service_healthy(s[2]) for s in missing)
        if all_up:
            return True
        time.sleep(0.3)

    return all(is_service_healthy(s[2]) for s in SERVICES)


def stop_spawned_services():
    """Cleanly terminates any processes spawned by this session."""
    global _SPAWNED_PROCESSES
    for name, p, port in _SPAWNED_PROCESSES:
        try:
            p.terminate()
            p.wait(timeout=1.0)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    _SPAWNED_PROCESSES = []

