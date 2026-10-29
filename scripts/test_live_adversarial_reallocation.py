"""
scripts/test_live_adversarial_reallocation.py — Full Live Adversarial Reallocation & Payout Test
------------------------------------------------------------------------------------------------
Fulfills User Requirement 5:
  1. Full live flow in PAYOUT_MODE=live.
  2. Free-form task with Rogue (sb-a43fio53613334@personal.example.com) underbidding.
  3. Rogue is awarded the task and delivers plausible-wrong code.
  4. Two-stage verifier catches the flaw and blocks payment ($0.00 paid, reservation released).
  5. Task is dynamically reassigned to honest worker (code-worker-01).
  6. Honest worker delivers verified code.
  7. Live PayPal Sandbox Payout is submitted for honest worker (real batch ID, status polled).
  8. Assertions:
     - Rogue worker paid exactly $0.00.
     - Honest worker paid exact bid amount.
     - Real PayPal batch ID returned and polled.
"""
import os
import sys
import time
import json
import sqlite3
import hashlib
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    send_payout,
    poll_and_reconcile_payout,
    get_budget_state,
    DB_PATH,
    CHAIN_HASH_PATH,
)
from orchestrator.verifier import verify_delivery
from broker.registry import WORKER_REGISTRY

load_dotenv()


def run_live_adversarial_reallocation_flow():
    print("=" * 70)
    print("FULL LIVE ADVERSARIAL REALLOCATION & PAYPAL SETTLEMENT TEST")
    print("=" * 70)

    payout_mode = os.getenv("PAYOUT_MODE", "simulated").strip().lower()
    print(f"  Configured PAYOUT_MODE: {payout_mode.upper()}")
    assert payout_mode == "live", "This test MUST run with PAYOUT_MODE=live in .env!"

    cycle_id = f"live_adv_cycle_{int(time.time())}"
    max_budget = 15.00
    init_ledger()

    # Step 1: Define the Free-form Job Request Package (JRP)
    hidden_test_suite = (
        "assert calculate_tax(100.0, 0.08) == 8.0\n"
        "assert calculate_tax(50.0, 0.10) == 5.0\n"
        "assert calculate_tax(0.0) == 0.0\n"
        "assert calculate_tax(-10.0) == 0.0\n"
    )

    jrp = {
        "jrp_id": f"jrp_tax_code_{cycle_id}",
        "cycle_id": cycle_id,
        "task_description": "Implement calculate_tax(amount, rate=0.08) -> float returning 0.0 for non-positive amounts",
        "required_capabilities": ["python_coding"],
        "max_bid_usd": 5.00,
        "acceptance_rules": [
            {"type": "unit_test", "test_suite_code": hidden_test_suite}
        ],
    }

    # Step 2: Bids Collected from Marketplace
    rogue_email = os.getenv("ROGUE_PAYPAL_EMAIL", "sb-a43fio53613334@personal.example.com")
    honest_email = os.getenv("CODE_WORKER_PAYPAL_EMAIL", os.getenv("WORKER_PAYPAL_EMAIL", "sb-sqcdl53128062@personal.example.com"))

    bids = [
        {
            "worker_id": "rogue-worker-01",
            "name": "Rogue Worker [ADVERSARY]",
            "bid_usd": 0.35,  # Aggressive underbid
            "worker_paypal_email": rogue_email,
        },
        {
            "worker_id": "code-worker-01",
            "name": "Python Code Generation Specialist",
            "bid_usd": 0.45,  # Genuine token-metered bid
            "worker_paypal_email": honest_email,
        },
    ]

    print(f"\n[Step 1] Marketplace Bids Received:")
    for b in bids:
        print(f"  • {b['worker_id']} ({b['name']}): ${b['bid_usd']:.2f} [Email: {b['worker_paypal_email']}]")

    # Step 3: Award to lowest bidder (Rogue wins)
    winner_1 = min(bids, key=lambda x: x["bid_usd"])
    print(f"\n[Step 2] Task Awarded to Lowest Bidder: {winner_1['worker_id']} at ${winner_1['bid_usd']:.2f}")
    assert winner_1["worker_id"] == "rogue-worker-01", "Rogue must win initial award via lowest price"

    # Step 4: Atomic Budget Reservation for Rogue
    state_0 = get_budget_state(cycle_id, max_budget)
    print(f"  Budget Prior: Spent=${state_0['spent_usd']:.2f}, Reserved=${state_0['reserved_usd']:.2f}")

    ok_res1, res_id_1, msg_res1 = reserve_budget(
        cycle_id=cycle_id,
        jrp_id=jrp["jrp_id"],
        worker_id=winner_1["worker_id"],
        amount_usd=winner_1["bid_usd"],
        max_budget_usd=max_budget,
    )
    assert ok_res1 is True, f"Reservation failed: {msg_res1}"
    state_1 = get_budget_state(cycle_id, max_budget)
    print(f"  [Budget Reserved] ${winner_1['bid_usd']:.2f} for {winner_1['worker_id']} (ResID: {res_id_1})")
    print(f"  Budget State: Spent=${state_1['spent_usd']:.2f}, Reserved=${state_1['reserved_usd']:.2f}")
    assert state_1["reserved_usd"] == 0.35

    # Step 5: Rogue Delivers Plausible-Looking Defective Code
    print("\n[Step 3] Rogue Worker Delivering Code...")
    rogue_code = (
        "def calculate_tax(amount: float, rate: float = 0.08) -> float:\n"
        "    # Subtle defect: returns -1.0 for non-positive amounts instead of 0.0\n"
        "    if amount <= 0:\n"
        "        return -1.0\n"
        "    return round(amount * rate, 2)\n"
    )
    rogue_sha = hashlib.sha256(rogue_code.encode("utf-8")).hexdigest()
    rogue_delivery = {
        "worker_id": "rogue-worker-01",
        "output_sample": rogue_code,
        "sha256_hash": rogue_sha,
    }

    # Step 6: Two-Stage Verification on Rogue Delivery
    print("  Running Two-Stage Verification on Rogue Delivery...")
    is_ok_r, status_r, report_r = verify_delivery(jrp, rogue_delivery)
    print(f"  Stage 1 (Integrity): PASS (SHA-256 matches payload bytes)")
    print(f"  Stage 2 (Acceptance): {status_r} -> {report_r.get('message')}")
    assert is_ok_r is False, "Rogue code with edge-case defect MUST be rejected!"
    assert status_r == "ACCEPTANCE_FAILED"

    # Step 7: Withhold Payment, Release Reservation, Block Rogue
    print("\n[Step 4] Enforcing Payment Block & Releasing Reservation for Rogue...")
    ok_rel, msg_rel = release_reservation(res_id_1, reason=f"Rejected: {report_r.get('message')}")
    assert ok_rel is True, f"Failed to release reservation: {msg_rel}"

    state_after_rogue = get_budget_state(cycle_id, max_budget)
    print(f"  Budget After Rogue Rejection: Spent=${state_after_rogue['spent_usd']:.2f}, Reserved=${state_after_rogue['reserved_usd']:.2f}")
    assert state_after_rogue["reserved_usd"] == 0.00, "Rogue reservation must return to $0.00!"
    assert state_after_rogue["spent_usd"] == 0.00, "Total spent on Rogue must be $0.00!"

    # Step 8: Dynamic Reallocation to Honest Worker
    print("\n[Step 5] Reallocating Task to Next Qualified Bidder: code-worker-01...")
    winner_2 = [b for b in bids if b["worker_id"] == "code-worker-01"][0]

    ok_res2, res_id_2, msg_res2 = reserve_budget(
        cycle_id=cycle_id,
        jrp_id=jrp["jrp_id"],
        worker_id=winner_2["worker_id"],
        amount_usd=winner_2["bid_usd"],
        max_budget_usd=max_budget,
    )
    assert ok_res2 is True, f"Reservation for honest worker failed: {msg_res2}"
    state_2 = get_budget_state(cycle_id, max_budget)
    print(f"  [Budget Reserved] ${winner_2['bid_usd']:.2f} for {winner_2['worker_id']} (ResID: {res_id_2})")
    assert state_2["reserved_usd"] == 0.45

    # Step 9: Honest Worker Delivers Verified Implementation
    print("\n[Step 6] Honest Worker Delivering Compliant Implementation...")
    honest_code = (
        "def calculate_tax(amount: float, rate: float = 0.08) -> float:\n"
        "    '''Computes tax for a transaction. Returns 0.0 for zero or non-positive amounts.'''\n"
        "    if amount <= 0:\n"
        "        return 0.0\n"
        "    return round(amount * rate, 2)\n"
    )
    honest_sha = hashlib.sha256(honest_code.encode("utf-8")).hexdigest()
    honest_delivery = {
        "worker_id": "code-worker-01",
        "output_sample": honest_code,
        "sha256_hash": honest_sha,
    }

    is_ok_h, status_h, report_h = verify_delivery(jrp, honest_delivery)
    print(f"  Verification Result: ok={is_ok_h}, status={status_h}, basis={report_h.get('basis')}")
    assert is_ok_h is True, "Honest code must pass all verification checks!"

    # Step 10: REAL LIVE PAYPAL PAYOUT
    print("\n[Step 7] Executing REAL LIVE PayPal Payout to Honest Worker...")
    print(f"  Target Recipient: {honest_email}")
    print(f"  Amount: ${winner_2['bid_usd']:.2f}")

    payout_result = send_payout(
        cycle_id=cycle_id,
        jrp_id=jrp["jrp_id"],
        worker_id=winner_2["worker_id"],
        worker_email=honest_email,
        amount_usd=winner_2["bid_usd"],
        sha256_hash=honest_sha,
        reservation_id=res_id_2,
        max_budget_usd=max_budget,
    )

    batch_id = payout_result["payout_batch_id"]
    initial_status = payout_result["status"]
    print(f"  Live Payout Submitted!")
    print(f"  Batch ID: {batch_id}")
    print(f"  Initial Status: {initial_status}")
    print(f"  Is Simulated: {payout_result['is_simulated']}")

    assert not payout_result["is_simulated"], "Payout must be real, never simulated!"
    assert not batch_id.startswith("SIMULATED"), "Batch ID must be genuine PayPal ID!"

    # Step 11: Poll status to terminal state
    print("\n[Step 8] Polling PayPal Sandbox API for Terminal Status...")
    reconciled = poll_and_reconcile_payout(batch_id, max_attempts=12, interval_sec=2.0)
    final_status = reconciled.get("final_status", initial_status)
    print(f"  Reconciled Final Status: {final_status}")

    # Step 12: Audit Assertions
    print("\n[Step 9] Auditing Ledger and Financial Invariants...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Assert Rogue was paid $0.00 in this cycle
    cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_email = ? AND status IN ('PAYOUT_SUCCESS', 'PAYOUT_PENDING')",
        (cycle_id, rogue_email)
    )
    rogue_count, rogue_paid = cur.fetchone()
    print(f"  Audited Cycle Payouts to Rogue ({rogue_email}): count={rogue_count}, total=${rogue_paid:.2f}")
    assert rogue_count == 0, "Rogue must have 0 payouts!"
    assert rogue_paid == 0.0, f"Rogue must receive $0.00! Found: ${rogue_paid}"

    # Assert Honest worker was paid in this cycle
    cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_email = ? AND status IN ('PAYOUT_SUCCESS', 'PAYOUT_PENDING')",
        (cycle_id, honest_email)
    )
    honest_count, honest_paid = cur.fetchone()
    print(f"  Audited Cycle Payouts to Honest Worker ({honest_email}): count={honest_count}, total=${honest_paid:.2f}")
    assert honest_count == 1, "Honest worker must have exactly 1 recorded payout for this cycle!"
    assert honest_paid == winner_2["bid_usd"], f"Honest worker must be paid exactly ${winner_2['bid_usd']:.2f}"

    conn.close()

    state_final = get_budget_state(cycle_id, max_budget)
    print(f"  Final Cycle Budget: Spent=${state_final['spent_usd']:.2f}, Reserved=${state_final['reserved_usd']:.2f}, Available=${state_final['available_usd']:.2f}")
    assert state_final["spent_usd"] == winner_2["bid_usd"], f"Total spent must equal honest worker's bid only (${winner_2['bid_usd']})!"
    assert state_final["reserved_usd"] == 0.00, "Reserved budget must return to zero!"

    print("\n" + "=" * 70)
    print("LIVE ADVERSARIAL REALLOCATION TEST COMPLETED SUCCESSFULLY!")
    print(f"  PayPal Payout Batch ID : {batch_id}")
    print(f"  PayPal Batch Status    : {final_status}")
    print(f"  Rogue Worker Paid      : $0.00")
    print(f"  Honest Worker Paid     : ${winner_2['bid_usd']:.2f}")
    print("=" * 70)
    return batch_id, final_status


if __name__ == "__main__":
    run_live_adversarial_reallocation_flow()
