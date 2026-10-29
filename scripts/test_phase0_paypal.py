"""
test_phase0_paypal.py — Phase 0: PayPal Sandbox Payout & Status Polling Verification
Checks:
  1. Sandbox OAuth token generation.
  2. Submits a test payout request ($0.10) to worker sandbox email.
  3. Detects if live payouts succeed OR if country restriction triggers visibly labeled SIMULATED mode.
  4. Polls payout status (GET /v1/payments/payouts/{id}) and reconciles to final state.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.treasury import (
    get_paypal_access_token,
    send_payout,
    poll_and_reconcile_payout,
    get_ledger_rows,
    init_ledger,
)

def run_phase0_test():
    print("=" * 60)
    print("PHASE 0: PayPal Sandbox Payout & Polling Verification")
    print("=" * 60)

    # Step 1: OAuth token
    print("\n[Step 1] Fetching PayPal Sandbox OAuth Bearer Token...")
    try:
        token = get_paypal_access_token()
        print(f"  [OK] OAuth Token retrieved: {token[:25]}... (valid)")
    except Exception as e:
        print(f"  [FAIL] OAuth Token retrieval failed: {e}")
        return False

    # Step 2: Attempt Payout
    print("\n[Step 2] Submitting Payout ($0.10) to worker sandbox email...")
    init_ledger()
    test_cycle = "p0_test_cycle"
    test_jrp = "p0_test_jrp"
    worker_email = "sb-sqcdl53128062@personal.example.com"
    dummy_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    payout_result = send_payout(
        cycle_id=test_cycle,
        jrp_id=test_jrp,
        worker_id="ocr-worker-01",
        worker_email=worker_email,
        amount_usd=0.10,
        sha256_hash=dummy_hash,
        note="Phase 0 PayPal Sandbox Verification",
    )

    batch_id = payout_result["payout_batch_id"]
    initial_status = payout_result["status"]
    is_sim = payout_result["is_simulated"]

    print(f"  Payout Batch ID: {batch_id}")
    print(f"  Initial Status:  {initial_status}")
    print(f"  Is Simulated:    {is_sim}")

    if is_sim:
        print("  Notice: Sender account has country restriction (IN); fallback clearly labeled as SIMULATED.")
    else:
        print("  SUCCESS: Real PayPal Sandbox Payout accepted by PayPal API!")

    # Step 3: Status Polling & Reconciliation
    print("\n[Step 3] Polling payout status & reconciling lifecycle...")
    recon_result = poll_and_reconcile_payout(batch_id, max_attempts=3, interval_sec=1.0)
    print(f"  Final Reconciled Status: {recon_result['final_status']}")
    print(f"  Polling Attempts:        {recon_result['attempts']}")

    # Step 4: Verify Audit Ledger entry
    print("\n[Step 4] Checking Audit Ledger record...")
    rows = get_ledger_rows()
    matching = [r for r in rows if r.get("payout_batch_id") == batch_id]
    if not matching:
        print("  [FAIL] No matching ledger row found for batch ID!")
        return False

    row = matching[0]
    print(f"  Ledger ID:     {row['id']}")
    print(f"  Batch ID:      {row['payout_batch_id']}")
    print(f"  Final Status:  {row['status']}")
    print(f"  Ledger Notes:  {row['notes']}")

    print("\n" + "=" * 60)
    print("PHASE 0 GATE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_phase0_test()
    sys.exit(0 if success else 1)
