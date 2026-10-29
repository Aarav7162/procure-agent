"""
test_phase1_treasury.py — Rigorous verification suite for Phase 1:
  1. Concurrency Test: 5 concurrent threads try to reserve $4.00 against $10.00 cap.
     Asserts: Exactly 2 succeed ($8.00 reserved), exactly 3 fail, 0 overdrawn.
  2. Reservation Lifecycle: Release reservation and verify budget recovery.
  3. Tamper-Evident Hash Chain: Append rows, verify valid chain.
     Execute raw SQL UPDATE via a 2nd independent connection.
     Asserts: verify_ledger_chain() detects the exact tampered row!
"""
import os
import sys
import sqlite3
import shutil
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    get_budget_state,
    append_ledger,
    verify_ledger_chain,
    DB_PATH,
    CHAIN_HASH_PATH,
)

def run_phase1_tests():
    print("=" * 70)
    print("PHASE 1 GATE: Financial & Treasury Hardening Verification")
    print("=" * 70)

    # Clean test audit DB
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
    if os.path.exists(CHAIN_HASH_PATH):
        try:
            os.remove(CHAIN_HASH_PATH)
        except Exception:
            pass

    init_ledger()

    # ─────────────────────────────────────────────────────────────
    # Test 1: Concurrency Race Condition Test
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 1] Concurrency Test: 5 simultaneous threads reserving $4.00 against $10.00 cap...")
    cycle_id = "concurrent_cycle_01"
    max_budget = 10.00
    bid_amount = 4.00

    results = []

    def attempt_reservation(worker_num):
        ok, res_id, msg = reserve_budget(
            cycle_id=cycle_id,
            jrp_id=f"jrp_worker_{worker_num}",
            worker_id=f"worker_{worker_num}",
            amount_usd=bid_amount,
            max_budget_usd=max_budget,
            timeout_seconds=5.0,
        )
        return (ok, res_id, msg)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_reservation, i) for i in range(5)]
        for f in futures:
            results.append(f.result())

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]

    print(f"  Total Attempts: {len(results)}")
    print(f"  Successful Reservations: {len(successes)} (Expected: 2)")
    print(f"  Denied Overdraws:       {len(failures)} (Expected: 3)")

    for i, (ok, r_id, msg) in enumerate(results):
        status_tag = "[APPROVED]" if ok else "[DENIED]"
        print(f"    Thread #{i}: {status_tag} {msg}")

    state = get_budget_state(cycle_id, max_budget)
    print(f"  Budget State: Reserved=${state['reserved_usd']}, Available=${state['available_usd']}, Cap=${state['max_usd']}")

    assert len(successes) == 2, f"Expected exactly 2 successes, got {len(successes)}"
    assert len(failures) == 3, f"Expected exactly 3 failures, got {len(failures)}"
    assert state["reserved_usd"] == 8.00, f"Expected $8.00 reserved, got {state['reserved_usd']}"
    assert state["available_usd"] == 2.00, f"Expected $2.00 available, got {state['available_usd']}"
    print("  >>> [PASS] Test 1: Concurrency safety verified with zero overdraws! <<<")

    # ─────────────────────────────────────────────────────────────
    # Test 2: Safe Reservation Release & Recovery
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 2] Reservation Release & Safe Recovery...")
    res_to_release = successes[0][1]
    rel_ok, rel_msg = release_reservation(res_to_release, reason="Simulated task rejection")
    print(f"  Releasing Reservation {res_to_release} -> {rel_msg}")
    assert rel_ok, "Release must succeed"

    state_after = get_budget_state(cycle_id, max_budget)
    print(f"  Budget State After Release: Reserved=${state_after['reserved_usd']}, Available=${state_after['available_usd']}")
    assert state_after["reserved_usd"] == 4.00, "Reserved should drop to $4.00"
    assert state_after["available_usd"] == 6.00, "Available should recover to $6.00"
    print("  >>> [PASS] Test 2: Reservation released and budget recovered safely! <<<")

    # ─────────────────────────────────────────────────────────────
    # Test 3: Tamper-Evident Hash Chain & 2nd Connection UPDATE
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 3] Tamper-Evident Hash Chain & Row Modification Detection...")
    # Add 3 legitimate entries
    for i in range(1, 4):
        append_ledger({
            "cycle_id": "audit_cycle",
            "jrp_id": f"jrp_legit_{i}",
            "worker_id": f"worker_0{i}",
            "worker_email": f"worker{i}@paypal.com",
            "bid_usd": float(i * 2.50),
            "sha256_hash": f"digest_{i:04d}",
            "payout_batch_id": f"BATCH_{i:04d}",
            "status": "PAYOUT_SUCCESS",
            "notes": f"Legitimate transaction #{i}",
        })

    is_valid, desc, details = verify_ledger_chain()
    print(f"  Initial Ledger Verification: {desc}")
    assert is_valid, "Initial chain must be valid"

    # Now tamper with row #2 using a second raw SQLite connection
    print("\n  Simulating attacker: opening 2nd raw SQLite connection to alter ledger row #2...")
    conn2 = sqlite3.connect(DB_PATH)
    conn2.execute("UPDATE ledger SET bid_usd = 999.00 WHERE entry_index = 2")
    conn2.commit()
    conn2.close()
    print("  Attacker updated entry #2 bid_usd to $999.00 directly in SQLite.")

    # Re-verify ledger
    tamper_valid, tamper_desc, tamper_details = verify_ledger_chain()
    print(f"  Tamper-Evident Check: is_valid={tamper_valid}")
    print(f"  Tamper Notice: {tamper_desc}")
    print(f"  Details: {tamper_details}")

    assert not tamper_valid, "Tamper check MUST fail after raw SQL UPDATE"
    assert tamper_details.get("tampered_index") == 2, "Must identify tampered entry index #2"
    print("  >>> [PASS] Test 3: Tamper-evident ledger detected altered record at entry #2! <<<")

    print("\n" + "=" * 70)
    print("ALL PHASE 1 GATE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_phase1_tests()
    sys.exit(0 if success else 1)
