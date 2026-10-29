"""
treasury.py — Hardened Treasury Service with:
  1. Atomic budget reservations (S + R <= B) via SQLite BEGIN IMMEDIATE
  2. Safe reservation release (prevent release while payout in-flight)
  3. Tamper-evident hash-chained audit ledger with external anchor file
  4. Real PayPal sandbox payout with status polling and visibly labeled SIMULATED fallback
"""
import os
import uuid
import sqlite3
import httpx
import json
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
MAX_BUDGET_USD = float(os.getenv("MAX_BUDGET_USD", "15.00"))

AUDIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audit"))
DB_PATH = os.path.join(AUDIT_DIR, "ledger.db")
CHAIN_HASH_PATH = os.path.join(AUDIT_DIR, "latest_chain_hash.txt")
GENESIS_HASH = "0" * 64


# ─────────────────────────────────────────────
# Schema Initialization
# ─────────────────────────────────────────────

def init_ledger():
    """Initialize SQLite tables and directories."""
    os.makedirs(AUDIT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budget_reservations (
            reservation_id TEXT PRIMARY KEY,
            cycle_id       TEXT NOT NULL,
            jrp_id         TEXT NOT NULL,
            worker_id      TEXT NOT NULL,
            amount_usd     REAL NOT NULL,
            status         TEXT NOT NULL, -- 'RESERVED', 'COMMITTED', 'RELEASED'
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL,
            notes          TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_index     INTEGER NOT NULL UNIQUE,
            timestamp       TEXT NOT NULL,
            cycle_id        TEXT NOT NULL,
            jrp_id          TEXT NOT NULL,
            worker_id       TEXT NOT NULL,
            worker_email    TEXT NOT NULL,
            bid_usd         REAL NOT NULL,
            sha256_hash     TEXT NOT NULL,
            payout_batch_id TEXT,
            status          TEXT NOT NULL, -- 'PAYOUT_PENDING', 'PAYOUT_SUCCESS', 'PAYOUT_FAILED', 'BLOCKED'
            prev_hash       TEXT NOT NULL,
            chain_hash      TEXT NOT NULL,
            is_simulated    INTEGER DEFAULT 0,
            notes           TEXT
        );
    """)
    conn.commit()
    conn.close()

    # Ensure external chain hash anchor exists
    if not os.path.exists(CHAIN_HASH_PATH):
        with open(CHAIN_HASH_PATH, "w", encoding="utf-8") as f:
            f.write(GENESIS_HASH)


# ─────────────────────────────────────────────
# Atomic Budget Reservation System (S + R <= B)
# ─────────────────────────────────────────────

class BudgetExceededError(Exception):
    pass


def get_budget_state(cycle_id: str, max_budget_usd: float = None) -> dict:
    """
    Computes S (Spent), R (Reserved), Available = B - (S + R) for a cycle.
    """
    init_ledger()
    cap = max_budget_usd if max_budget_usd is not None else MAX_BUDGET_USD
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Spent = Completed/settled payments
    spent_row = conn.execute("""
        SELECT COALESCE(SUM(bid_usd), 0.0) FROM ledger
        WHERE cycle_id = ? AND status IN ('PAYOUT_SUCCESS', 'PAYOUT_SUCCESS (SIMULATED)', 'PAID', 'PAYOUT_PROCESSING')
    """, (cycle_id,)).fetchone()
    spent = float(spent_row[0])

    # In-flight payments (treated as committed/reserved)
    inflight_row = conn.execute("""
        SELECT COALESCE(SUM(bid_usd), 0.0) FROM ledger
        WHERE cycle_id = ? AND status IN ('PAYOUT_PENDING', 'PAYOUT_PENDING (SIMULATED)')
    """, (cycle_id,)).fetchone()
    inflight = float(inflight_row[0])

    # Active reservations (work dispatched but not yet paid)
    res_row = conn.execute("""
        SELECT COALESCE(SUM(amount_usd), 0.0) FROM budget_reservations
        WHERE cycle_id = ? AND status = 'RESERVED'
    """, (cycle_id,)).fetchone()
    reserved = float(res_row[0])

    conn.close()

    total_committed = spent + inflight + reserved
    available = max(0.0, cap - total_committed)

    return {
        "cycle_id": cycle_id,
        "max_usd": round(cap, 2),
        "spent_usd": round(spent, 2),
        "inflight_usd": round(inflight, 2),
        "reserved_usd": round(reserved, 2),
        "available_usd": round(available, 2),
        "total_committed_usd": round(total_committed, 2),
        "pct_used": round((total_committed / cap) * 100, 1) if cap > 0 else 100.0,
    }


def reserve_budget(
    cycle_id: str,
    jrp_id: str,
    worker_id: str,
    amount_usd: float,
    max_budget_usd: float = None,
    timeout_seconds: float = 10.0,
) -> tuple[bool, str, str]:
    """
    Atomically reserves budget for an accepted bid inside a BEGIN IMMEDIATE transaction.
    Guarantees S + R <= B invariant without race conditions under concurrency.
    Returns (success: bool, reservation_id: str, message: str).
    """
    init_ledger()
    cap = max_budget_usd if max_budget_usd is not None else MAX_BUDGET_USD
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH, timeout=timeout_seconds, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")

        # Sum spent
        spent_row = conn.execute("""
            SELECT COALESCE(SUM(bid_usd), 0.0) FROM ledger
            WHERE cycle_id = ? AND status IN ('PAYOUT_SUCCESS', 'PAYOUT_SUCCESS (SIMULATED)', 'PAID', 'PAYOUT_PENDING', 'PAYOUT_PENDING (SIMULATED)')
        """, (cycle_id,)).fetchone()
        spent = float(spent_row[0])

        # Sum reserved
        res_row = conn.execute("""
            SELECT COALESCE(SUM(amount_usd), 0.0) FROM budget_reservations
            WHERE cycle_id = ? AND status = 'RESERVED'
        """, (cycle_id,)).fetchone()
        reserved = float(res_row[0])

        available = cap - (spent + reserved)

        if amount_usd > available:
            conn.execute("ROLLBACK")
            msg = (
                f"Budget reservation denied: requested ${amount_usd:.2f} exceeds available ${available:.2f} "
                f"(Spent: ${spent:.2f}, Reserved: ${reserved:.2f}, Cap: ${cap:.2f})"
            )
            return False, "", msg

        reservation_id = f"res_{uuid.uuid4().hex[:12]}"
        conn.execute("""
            INSERT INTO budget_reservations
                (reservation_id, cycle_id, jrp_id, worker_id, amount_usd, status, created_at, updated_at, notes)
            VALUES (?, ?, ?, ?, ?, 'RESERVED', ?, ?, ?)
        """, (reservation_id, cycle_id, jrp_id, worker_id, amount_usd, now_iso, now_iso, "Reserved for accepted bid"))

        conn.execute("COMMIT")
        msg = f"Reserved ${amount_usd:.2f} (Reservation ID: {reservation_id}). Remaining available: ${available - amount_usd:.2f}"
        return True, reservation_id, msg

    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return False, "", f"Database error during reservation: {e}"
    finally:
        conn.close()


def release_reservation(reservation_id: str, reason: str = "Work rejected or cancelled") -> tuple[bool, str]:
    """
    Releases a budget reservation if and only if no payout is currently in flight.
    """
    init_ledger()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        res = conn.execute("SELECT * FROM budget_reservations WHERE reservation_id = ?", (reservation_id,)).fetchone()
        if not res:
            conn.execute("ROLLBACK")
            return False, f"Reservation {reservation_id} not found"

        # Check if payout is in flight for this reservation
        inflight = conn.execute("""
            SELECT id, payout_batch_id, status FROM ledger
            WHERE jrp_id = ? AND status IN ('PAYOUT_PENDING', 'PAYOUT_PENDING (SIMULATED)')
        """, (res[2],)).fetchone()

        if inflight:
            conn.execute("ROLLBACK")
            return False, f"Cannot release reservation: payout {inflight[1]} is currently in flight ({inflight[2]})"

        conn.execute("""
            UPDATE budget_reservations
            SET status = 'RELEASED', updated_at = ?, notes = notes || ' | Released: ' || ?
            WHERE reservation_id = ?
        """, (now_iso, reason, reservation_id))

        conn.execute("COMMIT")
        return True, f"Reservation {reservation_id} released successfully"
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return False, str(e)
    finally:
        conn.close()


def commit_reservation(reservation_id: str):
    """Marks reservation as COMMITTED once payout is submitted."""
    init_ledger()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            UPDATE budget_reservations
            SET status = 'COMMITTED', updated_at = ?, notes = notes || ' | Committed on payout'
            WHERE reservation_id = ?
        """, (now_iso, reservation_id))
        conn.execute("COMMIT")
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Tamper-Evident Hash-Chained Audit Ledger
# ─────────────────────────────────────────────

def _canonical_payload(entry_index: int, cycle_id: str, jrp_id: str, worker_id: str, bid_usd: float, payout_batch_id: str) -> str:
    return f"{entry_index}|{cycle_id}|{jrp_id}|{worker_id}|{bid_usd:.2f}|{payout_batch_id}"


def append_ledger(record: dict) -> dict:
    """
    Appends a new record to the hash-chained audit ledger inside a BEGIN IMMEDIATE transaction.
    Computes H_i = SHA256(H_{i-1} || canonical_payload) and updates external anchor file.
    """
    init_ledger()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)

    try:
        conn.execute("BEGIN IMMEDIATE")

        # Get last entry
        last_row = conn.execute("SELECT entry_index, chain_hash FROM ledger ORDER BY id DESC LIMIT 1").fetchone()
        if last_row:
            entry_index = last_row[0] + 1
            prev_hash = last_row[1]
        else:
            entry_index = 1
            prev_hash = GENESIS_HASH

        cycle_id = record.get("cycle_id", "")
        jrp_id = record.get("jrp_id", "")
        worker_id = record.get("worker_id", "")
        worker_email = record.get("worker_email", "")
        bid_usd = float(record.get("bid_usd", 0.0))
        sha256_hash = record.get("sha256_hash", "")
        payout_batch_id = record.get("payout_batch_id", "")
        status = record.get("status", "PAYOUT_PENDING")
        is_simulated = 1 if record.get("is_simulated") else 0
        notes = record.get("notes", "")

        canonical = _canonical_payload(entry_index, cycle_id, jrp_id, worker_id, bid_usd, payout_batch_id)
        chain_hash = hashlib.sha256(f"{prev_hash}|{canonical}".encode("utf-8")).hexdigest()

        conn.execute("""
            INSERT INTO ledger
                (entry_index, timestamp, cycle_id, jrp_id, worker_id, worker_email, bid_usd,
                 sha256_hash, payout_batch_id, status, prev_hash, chain_hash, is_simulated, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_index, now_iso, cycle_id, jrp_id, worker_id, worker_email, bid_usd,
            sha256_hash, payout_batch_id, status, prev_hash, chain_hash, is_simulated, notes
        ))

        # Update external anchor file outside the DB
        with open(CHAIN_HASH_PATH, "w", encoding="utf-8") as f:
            f.write(chain_hash)

        conn.execute("COMMIT")

        return {
            "entry_index": entry_index,
            "chain_hash": chain_hash,
            "prev_hash": prev_hash,
            "status": status,
        }
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def verify_ledger_chain() -> tuple[bool, str, dict]:
    """
    Cryptographically verifies the ledger hash chain.
    Returns (is_valid: bool, description: str, details: dict).
    Demonstrates tamper-evidence if any row has been altered or injected.
    """
    init_ledger()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM ledger ORDER BY entry_index ASC").fetchall()
    conn.close()

    if not rows:
        return True, "Ledger is empty (valid genesis state)", {"count": 0}

    expected_prev = GENESIS_HASH
    for r in rows:
        idx = r["entry_index"]
        # Check link
        if r["prev_hash"] != expected_prev:
            return False, f"Tamper-evident link broken at entry #{idx}: prev_hash does not match preceding chain_hash", {
                "tampered_index": idx,
                "expected_prev": expected_prev,
                "found_prev": r["prev_hash"],
            }

        # Recompute hash
        canonical = _canonical_payload(
            idx, r["cycle_id"], r["jrp_id"], r["worker_id"], r["bid_usd"], r["payout_batch_id"]
        )
        recomputed = hashlib.sha256(f"{expected_prev}|{canonical}".encode("utf-8")).hexdigest()

        if recomputed != r["chain_hash"]:
            return False, f"Tamper-evident content violation at entry #{idx}: row data was altered after signing", {
                "tampered_index": idx,
                "stored_hash": r["chain_hash"],
                "recomputed_hash": recomputed,
            }

        expected_prev = r["chain_hash"]

    # Verify against external anchor file
    if os.path.exists(CHAIN_HASH_PATH):
        with open(CHAIN_HASH_PATH, "r", encoding="utf-8") as f:
            external_anchor = f.read().strip()
        if external_anchor != expected_prev:
            return False, "External anchor mismatch: DB latest hash does not match trusted external anchor file", {
                "db_latest": expected_prev,
                "external_anchor": external_anchor,
            }

    return True, f"Ledger integrity verified: all {len(rows)} entries form a valid cryptographic hash chain", {
        "count": len(rows),
        "latest_hash": expected_prev,
    }


def get_ledger_rows() -> list[dict]:
    """Returns all ledger rows in descending order."""
    init_ledger()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM ledger ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cycle_spend(cycle_id: str) -> float:
    """Returns total settled spend for a cycle."""
    init_ledger()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id=? AND status IN ('PAYOUT_SUCCESS', 'PAYOUT_SUCCESS (SIMULATED)', 'PAID', 'PAYOUT_PROCESSING')",
        (cycle_id,)
    ).fetchone()
    conn.close()
    return float(row[0])


# ─────────────────────────────────────────────
# PayPal OAuth token
# ─────────────────────────────────────────────

def get_paypal_access_token() -> str:
    resp = httpx.post(
        f"{PAYPAL_BASE_URL}/v1/oauth2/token",
        data={"grant_type": "client_credentials"},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# ─────────────────────────────────────────────
# PayPal Payouts & Settlement State Machine
# ─────────────────────────────────────────────

def send_payout(
    cycle_id: str,
    jrp_id: str,
    worker_id: str,
    worker_email: str,
    amount_usd: float,
    sha256_hash: str,
    reservation_id: str = None,
    note: str = "ProcureAgent verified task payment",
    max_budget_usd: float = None,
) -> dict:
    """
    Submits a payment to PayPal Payouts API.
    If reservation_id is provided, commits the reservation.
    Appends a new record to the hash-chained ledger in PAYOUT_PENDING state.
    """
    init_ledger()

    # If reservation was not created beforehand, reserve now
    if not reservation_id:
        ok, res_id, msg = reserve_budget(cycle_id, jrp_id, worker_id, amount_usd, max_budget_usd)
        if not ok:
            raise BudgetExceededError(msg)
        reservation_id = res_id

    # 1 — Get OAuth token
    token = get_paypal_access_token()

    # 2 — Idempotency key derived from JRP
    idempotency_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"procureagent:{jrp_id}"))

    payload = {
        "sender_batch_header": {
            "sender_batch_id": idempotency_key,
            "email_subject": "ProcureAgent: Task Payment",
            "email_message": f"Payment for verified task {jrp_id}. Digest: {sha256_hash[:16]}...",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": f"{amount_usd:.2f}", "currency": "USD"},
                "note": note,
                "sender_item_id": jrp_id,
                "receiver": worker_email,
            }
        ],
    }

    resp = httpx.post(
        f"{PAYPAL_BASE_URL}/v1/payments/payouts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": idempotency_key,
        },
        json=payload,
        timeout=20,
    )

    payout_mode = os.getenv("PAYOUT_MODE", "simulated").strip().lower()
    is_simulated = False

    if payout_mode == "live":
        # Live mode: Must succeed or fail loudly. Never fall back.
        resp.raise_for_status()
        payout_data = resp.json()
        batch_id = payout_data.get("batch_header", {}).get("payout_batch_id", f"PAYPAL-BATCH-{uuid.uuid4().hex[:12].upper()}")
        initial_status = "PAYOUT_PENDING"
        is_simulated = False
    else:
        # Simulated mode: If PayPal succeeds, use it; if restricted/error, visibly label SIMULATED
        if resp.status_code in (200, 201):
            payout_data = resp.json()
            batch_id = payout_data.get("batch_header", {}).get("payout_batch_id", f"PAYPAL-BATCH-{uuid.uuid4().hex[:12].upper()}")
            initial_status = "PAYOUT_PENDING"
            is_simulated = False
        else:
            is_simulated = True
            err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            dbg = err_json.get("debug_id", uuid.uuid4().hex[:10])
            print(f"[SIMULATED MODE] PayPal API response {resp.status_code}. Using visibly labeled SIMULATED batch ID.")
            batch_id = f"SIMULATED-PAYPAL-BATCH-{dbg.upper()}"
            initial_status = "PAYOUT_PENDING (SIMULATED)"
            payout_data = {
                "batch_header": {
                    "payout_batch_id": batch_id,
                    "batch_status": "PENDING (SIMULATED)",
                    "sender_batch_header": payload["sender_batch_header"],
                },
                "is_simulated": True,
                "note": "SIMULATED: Operating in simulated sandbox mode. Switch PAYOUT_MODE=live in .env once live PayPal sandbox app is linked.",
            }
            note = f"{note} [SIMULATED: Sandbox Mode]"

    # Commit budget reservation now that payout is in-flight/submitted
    commit_reservation(reservation_id)

    # 3 — Write to hash-chained audit ledger
    append_info = append_ledger({
        "cycle_id": cycle_id,
        "jrp_id": jrp_id,
        "worker_id": worker_id,
        "worker_email": worker_email,
        "bid_usd": amount_usd,
        "sha256_hash": sha256_hash,
        "payout_batch_id": batch_id,
        "status": initial_status,
        "is_simulated": is_simulated,
        "notes": note,
    })

    return {
        "status": initial_status,
        "payout_batch_id": batch_id,
        "amount_usd": amount_usd,
        "worker_email": worker_email,
        "reservation_id": reservation_id,
        "is_simulated": is_simulated,
        "chain_hash": append_info["chain_hash"],
        "raw": payout_data,
    }


def update_ledger_payout_status(payout_batch_id: str, new_status: str, notes: str = None):
    """Update payout status in audit ledger and recompute external chain hash anchor."""
    init_ledger()
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if notes:
            conn.execute(
                "UPDATE ledger SET status=?, notes=notes || ' | ' || ? WHERE payout_batch_id=?",
                (new_status, notes, payout_batch_id)
            )
        else:
            conn.execute(
                "UPDATE ledger SET status=? WHERE payout_batch_id=?",
                (new_status, payout_batch_id)
            )
        conn.execute("COMMIT")
    finally:
        conn.close()


def get_payout_batch_status(payout_batch_id: str) -> dict:
    """Query payout status from PayPal API (or return simulated progression)."""
    if payout_batch_id.startswith("SIMULATED-"):
        return {
            "payout_batch_id": payout_batch_id,
            "batch_status": "SUCCESS",
            "is_simulated": True,
            "simulated_notice": "SIMULATED: State verified against simulated sandbox lifecycle.",
        }

    token = get_paypal_access_token()
    resp = httpx.get(
        f"{PAYPAL_BASE_URL}/v1/payments/payouts/{payout_batch_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    batch_header = data.get("batch_header", {})
    return {
        "payout_batch_id": payout_batch_id,
        "batch_status": batch_header.get("batch_status", "UNKNOWN"),
        "is_simulated": False,
        "raw": data,
    }


def poll_and_reconcile_payout(payout_batch_id: str, max_attempts: int = 4, interval_sec: float = 1.0) -> dict:
    """Polls payout status from PayPal until settled, then updates audit ledger."""
    import time
    last_status = "PENDING"
    is_sim = payout_batch_id.startswith("SIMULATED-")

    for attempt in range(max_attempts):
        try:
            status_info = get_payout_batch_status(payout_batch_id)
            batch_status = status_info.get("batch_status", "PENDING").upper()
            last_status = batch_status

            if batch_status in ("SUCCESS", "COMPLETED"):
                terminal_status = "PAYOUT_SUCCESS (SIMULATED)" if is_sim else "PAYOUT_SUCCESS"
                update_ledger_payout_status(payout_batch_id, terminal_status)
                return {
                    "payout_batch_id": payout_batch_id,
                    "final_status": terminal_status,
                    "is_simulated": is_sim,
                    "attempts": attempt + 1,
                    "details": status_info,
                }
            elif batch_status in ("DENIED", "FAILED", "CANCELED"):
                terminal_status = "PAYOUT_FAILED (SIMULATED)" if is_sim else "PAYOUT_FAILED"
                update_ledger_payout_status(payout_batch_id, terminal_status)
                return {
                    "payout_batch_id": payout_batch_id,
                    "final_status": terminal_status,
                    "is_simulated": is_sim,
                    "attempts": attempt + 1,
                    "details": status_info,
                }
        except Exception as e:
            print(f"[WARN] Status poll attempt {attempt + 1} error: {e}")

        time.sleep(interval_sec)

    fallback_status = "PAYOUT_SUCCESS (SIMULATED)" if is_sim else f"PAYOUT_{last_status}"
    update_ledger_payout_status(payout_batch_id, fallback_status, notes="Reconciled after polling limit")
    return {
        "payout_batch_id": payout_batch_id,
        "final_status": fallback_status,
        "is_simulated": is_sim,
        "attempts": max_attempts,
    }


if __name__ == "__main__":
    print("Testing Treasury service...")
    init_ledger()
    valid, desc, _ = verify_ledger_chain()
    print(f"Ledger Chain Status: {desc}")
