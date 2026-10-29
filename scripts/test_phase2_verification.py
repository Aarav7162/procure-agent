"""
test_phase2_verification.py — Phase 2 Gate: Two-Stage Verification & Rogue Worker Reallocation
Tests:
  1. Integrity vs Acceptance proof:
     Rogue worker generates valid SHA-256 for corrupted text.
     Asserts: Integrity = PASSED, Acceptance = FAILED.
  2. Full Money Flow & Reallocation Invariant:
     - Reserve $1.00 for Rogue -> R=$1.00, Available=$14.00.
     - Acceptance fails -> Reservation safely released -> R returns to $0.00, Available=$15.00.
     - Reallocate to Alpha -> Reserve $1.40 -> R=$1.40.
     - Alpha passes both stages -> Payout submitted and reconciled.
     - Final spend == $1.40 (Alpha only).
     - Zero payouts submitted for Rogue.
"""
import os
import sys
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.verifier import verify_integrity, verify_acceptance, verify_delivery
from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    send_payout,
    poll_and_reconcile_payout,
    get_budget_state,
    get_ledger_rows,
    verify_ledger_chain,
    DB_PATH,
    CHAIN_HASH_PATH,
)

def run_phase2_tests():
    print("=" * 70)
    print("PHASE 2 GATE: Two-Stage Verification & Rogue Reallocation")
    print("=" * 70)

    # Clean DB
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
    cycle_id = "phase2_realloc_cycle"
    max_budget = 15.00

    # ─────────────────────────────────────────────────────────────
    # Test 1: Integrity vs Acceptance Proof
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 1] Demonstrating Integrity vs Acceptance on Rogue Worker...")
    jrp = {
        "jrp_id": "jrp_p2_01",
        "cycle_id": cycle_id,
        "task_type": "ocr_batch",
        "acceptance_criteria": {
            "min_items_processed": 5,
            "output_format": "jsonl",
            "sha256_of_output_required": True,
        },
        "max_bid_usd": 6.00,
    }

    # Rogue worker output with valid SHA-256
    rogue_output = (
        '{"doc_id": "0", "text": "CORRUPTED_FABRICATED_PAYLOAD_PAGE_0", "confidence": 0.12}\n'
        '{"doc_id": "1", "text": "CORRUPTED_FABRICATED_PAYLOAD_PAGE_1", "confidence": 0.14}\n'
        '{"doc_id": "2", "text": "CORRUPTED_FABRICATED_PAYLOAD_PAGE_2", "confidence": 0.11}\n'
        '{"doc_id": "3", "text": "CORRUPTED_FABRICATED_PAYLOAD_PAGE_3", "confidence": 0.15}\n'
        '{"doc_id": "4", "text": "CORRUPTED_FABRICATED_PAYLOAD_PAGE_4", "confidence": 0.13}'
    )
    # Legitimate SHA-256 computed over the corrupted bytes
    rogue_sha256 = hashlib.sha256(rogue_output.encode("utf-8")).hexdigest()

    rogue_delivery = {
        "worker_id": "rogue-worker-01",
        "jrp_id": jrp["jrp_id"],
        "items_processed": 5,
        "output_sample": rogue_output,
        "sha256_hash": rogue_sha256,
        "status": "DELIVERED",
    }

    verified, stage, report = verify_delivery(jrp, rogue_delivery)
    print(f"  Stage 1 (Integrity):  {report['integrity']['match']} (Digest verified against payload bytes)")
    print(f"  Stage 2 (Acceptance): {verified} (Outcome: {stage})")
    print(f"  Rejection Reason:    {report['message']}")

    assert report["integrity"]["match"] is True, "Stage 1 Integrity check MUST pass (SHA-256 matches bytes)!"
    assert verified is False, "Overall verification MUST fail because acceptance check caught bogus data!"
    assert stage == "ACCEPTANCE_FAILED", f"Stage must be ACCEPTANCE_FAILED, got {stage}"
    print("  >>> [PASS] Test 1: Integrity passed while Acceptance failed and caught the rogue output! <<<")

    # ─────────────────────────────────────────────────────────────
    # Test 2: Full Money Flow & Reallocation Invariant
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 2] Full Money Flow & Atomic Reallocation...")
    initial_state = get_budget_state(cycle_id, max_budget)
    print(f"  Initial State: Spent=${initial_state['spent_usd']}, Reserved=${initial_state['reserved_usd']}, Available=${initial_state['available_usd']}")
    assert initial_state["spent_usd"] == 0.00
    assert initial_state["reserved_usd"] == 0.00
    assert initial_state["available_usd"] == 15.00

    # Step A: Reserve budget for Rogue worker ($1.00)
    print("\n  Step A: Rogue bids $1.00 -> Reserving budget...")
    ok_res1, res1_id, msg_res1 = reserve_budget(cycle_id, jrp["jrp_id"], "rogue-worker-01", 1.00, max_budget)
    assert ok_res1, "Reservation for rogue must succeed"
    state_a = get_budget_state(cycle_id, max_budget)
    print(f"    State after Rogue reservation: Reserved=${state_a['reserved_usd']}, Available=${state_a['available_usd']}")
    assert state_a["reserved_usd"] == 1.00
    assert state_a["available_usd"] == 14.00

    # Step B: Rogue fails verification -> Release reservation
    print("\n  Step B: Rogue fails acceptance -> Withholding payment & releasing reservation...")
    ok_rel, msg_rel = release_reservation(res1_id, reason="Acceptance failed: corrupted data")
    assert ok_rel, "Release must succeed"
    state_b = get_budget_state(cycle_id, max_budget)
    print(f"    State after release: Reserved=${state_b['reserved_usd']}, Available=${state_b['available_usd']}")
    assert state_b["reserved_usd"] == 0.00, "Reserved must return to $0.00"
    assert state_b["available_usd"] == 15.00, "Available must return to $15.00"

    # Step C: Reallocate to Alpha ($1.40)
    print("\n  Step C: Reallocating task to Alpha -> Reserving $1.40...")
    ok_res2, res2_id, msg_res2 = reserve_budget(cycle_id, jrp["jrp_id"], "ocr-worker-01", 1.40, max_budget)
    assert ok_res2, "Reservation for Alpha must succeed"
    state_c = get_budget_state(cycle_id, max_budget)
    print(f"    State after Alpha reservation: Reserved=${state_c['reserved_usd']}, Available=${state_c['available_usd']}")
    assert state_c["reserved_usd"] == 1.40
    assert state_c["available_usd"] == 13.60

    # Step D: Alpha delivers valid output
    alpha_output = (
        '{"doc_id": "0", "text": "Extracted text from page 0 of scanned document.", "confidence": 0.96}\n'
        '{"doc_id": "1", "text": "Extracted text from page 1 of scanned document.", "confidence": 0.95}\n'
        '{"doc_id": "2", "text": "Extracted text from page 2 of scanned document.", "confidence": 0.98}\n'
        '{"doc_id": "3", "text": "Extracted text from page 3 of scanned document.", "confidence": 0.97}\n'
        '{"doc_id": "4", "text": "Extracted text from page 4 of scanned document.", "confidence": 0.96}'
    )
    alpha_sha256 = hashlib.sha256(alpha_output.encode("utf-8")).hexdigest()
    alpha_delivery = {
        "worker_id": "ocr-worker-01",
        "jrp_id": jrp["jrp_id"],
        "items_processed": 5,
        "output_sample": alpha_output,
        "sha256_hash": alpha_sha256,
        "status": "DELIVERED",
    }
    alpha_verified, alpha_stage, alpha_report = verify_delivery(jrp, alpha_delivery)
    assert alpha_verified is True, "Alpha delivery must pass both verification stages"

    # Step E: Submit Payout for Alpha only
    print("\n  Step D & E: Alpha verified -> Submitting payout for $1.40...")
    payout = send_payout(
        cycle_id=cycle_id,
        jrp_id=jrp["jrp_id"],
        worker_id="ocr-worker-01",
        worker_email="sb-sqcdl53128062@personal.example.com",
        amount_usd=1.40,
        sha256_hash=alpha_sha256,
        reservation_id=res2_id,
        max_budget_usd=max_budget,
    )
    poll_and_reconcile_payout(payout["payout_batch_id"])

    # Step F: Final assertions on money flow & ledger
    final_state = get_budget_state(cycle_id, max_budget)
    print(f"\n  Final Budget State: Spent=${final_state['spent_usd']}, Reserved=${final_state['reserved_usd']}, Available=${final_state['available_usd']}")
    assert final_state["spent_usd"] == 1.40, f"Total spent must equal Alpha's bid only ($1.40), got {final_state['spent_usd']}"
    assert final_state["reserved_usd"] == 0.00, f"Reserved must equal $0.00, got {final_state['reserved_usd']}"
    assert final_state["available_usd"] == 13.60, f"Available must equal $13.60, got {final_state['available_usd']}"

    # Inspect Ledger rows
    ledger_rows = get_ledger_rows()
    print(f"  Total Ledger Rows: {len(ledger_rows)}")
    assert len(ledger_rows) == 1, "Exactly one payout must be logged in the ledger!"

    paid_row = ledger_rows[0]
    print(f"  Ledger Winner: {paid_row['worker_id']}, Amount: ${paid_row['bid_usd']}, Status: {paid_row['status']}")
    assert paid_row["worker_id"] == "ocr-worker-01", "Only Alpha must be paid!"
    assert paid_row["bid_usd"] == 1.40, "Paid amount must equal Alpha's bid ($1.40)!"

    # Assert no payout was ever submitted for rogue worker
    rogue_payouts = [r for r in ledger_rows if r["worker_id"] == "rogue-worker-01"]
    assert len(rogue_payouts) == 0, "No payout must ever be submitted for rogue worker!"
    print("  [Confirmed] Exactly 0 payouts submitted for rogue worker!")

    # Verify tamper-evident ledger integrity
    chain_ok, chain_desc, _ = verify_ledger_chain()
    assert chain_ok, f"Ledger chain must remain cryptographically valid: {chain_desc}"
    print(f"  Ledger Integrity: {chain_desc}")

    print("\n" + "=" * 70)
    print("ALL PHASE 2 GATE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_phase2_tests()
    sys.exit(0 if success else 1)
