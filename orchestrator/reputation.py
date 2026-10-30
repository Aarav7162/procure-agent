"""
orchestrator/reputation.py — Bayesian Beta(2,1) Reputation Engine
------------------------------------------------------------------
Computes worker reputation using Bayesian conjugate updating under a Beta(2,1) prior:
  • Prior: Alpha = 2.0, Beta = 1.0
  • Cold-Start Baseline Score: 2 / (2 + 1) = 0.6667 (66.7%)
  • On Verified Success: Alpha <- Alpha + 1
  • On Rejection / Defect: Beta <- Beta + 1
  • Updated Score: Alpha / (Alpha + Beta)
  • Cold-Start Allocation Cap: Unproven workers (< 3 completed tasks) are capped at $1.00.
"""
import os
import sqlite3
import datetime
from typing import Dict, Any

AUDIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audit"))
DB_PATH = os.path.join(AUDIT_DIR, "ledger.db")

ALPHA_PRIOR = 2.0
BETA_PRIOR = 1.0
COLD_START_ATTEMPTS_THRESHOLD = 3
COLD_START_MAX_ALLOCATION_USD = 1.00


def init_reputation_schema():
    """Initializes SQLite tables for Bayesian reputation tracking."""
    os.makedirs(AUDIT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS worker_reputation (
            worker_id       TEXT PRIMARY KEY,
            successes       INTEGER NOT NULL DEFAULT 0,
            failures        INTEGER NOT NULL DEFAULT 0,
            current_score   REAL NOT NULL,
            last_updated    TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reputation_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            worker_id       TEXT NOT NULL,
            task_id         TEXT NOT NULL,
            success         INTEGER NOT NULL,
            prior_score     REAL NOT NULL,
            new_score       REAL NOT NULL,
            notes           TEXT
        );
    """)
    conn.commit()
    conn.close()


def get_worker_reputation(worker_id: str) -> Dict[str, Any]:
    """
    Retrieves the Bayesian reputation score and allocation status for a worker.
    Defaults to Beta(2,1) prior if no history exists.
    """
    init_reputation_schema()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT successes, failures, current_score
        FROM worker_reputation
        WHERE worker_id = ?
    """, (worker_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        successes, failures, score = row
    else:
        successes, failures = 0, 0
        score = ALPHA_PRIOR / (ALPHA_PRIOR + BETA_PRIOR)

    total_attempts = successes + failures
    is_cold_start = (total_attempts < COLD_START_ATTEMPTS_THRESHOLD)
    allocation_cap = COLD_START_MAX_ALLOCATION_USD if is_cold_start else 15.00

    return {
        "worker_id": worker_id,
        "alpha": ALPHA_PRIOR + successes,
        "beta": BETA_PRIOR + failures,
        "successes": successes,
        "failures": failures,
        "total_attempts": total_attempts,
        "reputation_score": round(score, 4),
        "is_cold_start": is_cold_start,
        "allocation_cap_usd": allocation_cap,
    }


def record_worker_outcome(worker_id: str, success: bool, task_id: str, notes: str = "") -> Dict[str, Any]:
    """
    Applies Bayesian update:
      success=True  -> Alpha + 1
      success=False -> Beta + 1
    Saves state to SQLite and returns the transition metrics.
    """
    init_reputation_schema()
    current_rep = get_worker_reputation(worker_id)
    prior_score = current_rep["reputation_score"]

    new_successes = current_rep["successes"] + (1 if success else 0)
    new_failures = current_rep["failures"] + (0 if success else 1)

    new_alpha = ALPHA_PRIOR + new_successes
    new_beta = BETA_PRIOR + new_failures
    new_score = new_alpha / (new_alpha + new_beta)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO worker_reputation (worker_id, successes, failures, current_score, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(worker_id) DO UPDATE SET
            successes = excluded.successes,
            failures = excluded.failures,
            current_score = excluded.current_score,
            last_updated = excluded.last_updated
    """, (worker_id, new_successes, new_failures, round(new_score, 4), now_iso))

    cur.execute("""
        INSERT INTO reputation_history (timestamp, worker_id, task_id, success, prior_score, new_score, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (now_iso, worker_id, task_id, 1 if success else 0, prior_score, round(new_score, 4), notes))

    conn.commit()
    conn.close()

    total_attempts = new_successes + new_failures
    is_cold_start = (total_attempts < COLD_START_ATTEMPTS_THRESHOLD)
    allocation_cap = COLD_START_MAX_ALLOCATION_USD if is_cold_start else 15.00

    return {
        "worker_id": worker_id,
        "success": success,
        "prior_score": prior_score,
        "new_score": round(new_score, 4),
        "score_delta": round(new_score - prior_score, 4),
        "alpha": new_alpha,
        "beta": new_beta,
        "total_attempts": total_attempts,
        "is_cold_start": is_cold_start,
        "allocation_cap_usd": allocation_cap,
        "notes": notes,
    }

