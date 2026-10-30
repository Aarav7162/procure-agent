"""
scripts/test_gate2_rogue_and_reputation.py — Gate 2 Verification Suite
-----------------------------------------------------------------------
Verifies Gate 2 requirements:
  1. OCR Rogue Defect Rejection: Plausible-wrong OCR still fails under CER normalization rule.
  2. Zero Information Leakage: Hidden tests are NEVER exposed in the JRP or visible to workers.
  3. Rogue Code Delivery: Plausible fix passes public tests but fails hidden edge-case tests.
  4. Two-Layer Verification Block: Verifier detects failure and blocks payout ($0.00 paid).
  5. Reservation Release: Escrow is returned to the treasury pool without loss.
  6. Bayesian Beta(2,1) Reputation Drop: Rogue score drops from 0.6667 to 0.5000;
     honest worker score increases from 0.6667 to 0.7500.
"""
import os
import sys
import json
import time
import sqlite3
import hashlib
import tempfile
import subprocess
import pytest
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.verifier import compute_cer, verify_ocr_cer, verify_code_unit_tests, verify_delivery
from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    get_budget_state,
    DB_PATH,
)
from orchestrator.reputation import (
    init_reputation_schema,
    get_worker_reputation,
    record_worker_outcome,
    ALPHA_PRIOR,
    BETA_PRIOR,
)
from scripts.post_bounty import post_bounty_from_ci
from workers.rogue_worker import do_work as rogue_work, bid as rogue_bid

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))
SCANS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "real_scans"))


def test_gate2():
    print("=" * 70)
    print("GATE 2 VERIFICATION: Rogue Rejection & Bayesian Reputation Drop")
    print("=" * 70)

    # -------------------------------------------------------------
    # Step 1: OCR Rogue Defect Rejection Under CER Normalization
    # -------------------------------------------------------------
    print("\n[Step 1] Verifying OCR Rogue Fails Under Normalization...")
    # Test on all 5 documents to prove normalization cannot let plausible defects pass
    substitutions = {"e": "c", "E": "C", "o": "0", "O": "0", "l": "1", "I": "1", "a": "e", "A": "4", "s": "5"}
    
    for doc_id in ["doc_01", "doc_02", "doc_03", "doc_04", "doc_05"]:
        txt_path = os.path.join(SCANS_DIR, f"{doc_id}.txt")
        if not os.path.exists(txt_path):
            continue
        with open(txt_path, "r", encoding="utf-8") as f:
            clean_ref = f.read().strip()
        
        # Inject plausible OCR noise (every 10th character substituted, giving ~5.5% - 8.5% CER)
        chars = list(clean_ref)
        for idx in range(0, len(chars), 10):
            c = chars[idx]
            if c in substitutions:
                chars[idx] = substitutions[c]
            elif c.isalpha():
                chars[idx] = "r" if c.islower() else "R"
        distorted_ocr = "".join(chars)

        cer = compute_cer(clean_ref, distorted_ocr)
        ok_cer, msg_cer, _ = verify_ocr_cer(clean_ref, distorted_ocr, max_cer=0.05)
        
        print(f"  {doc_id}: Plausible Defect CER = {cer:.2%} (Threshold <= 5.00%) -> Passed: {ok_cer}")
        assert ok_cer is False, f"Plausible defect in {doc_id} must FAIL CER check despite normalization!"
        assert cer > 0.05, f"Distorted text in {doc_id} must have CER > 5.00% (was {cer:.2%})"

    print("  --> Verified: Separator line normalization does NOT let corrupted OCR pass.")

    # -------------------------------------------------------------
    # Step 2: Information Isolation (Hidden Tests Never in JRP)
    # -------------------------------------------------------------
    print("\n[Step 2] Verifying Information Isolation (Zero Information Leakage)...")
    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date"
    )
    assert ci_res["status"] == "POSTED"
    jrp = ci_res["jrp"]

    # Stringent isolation assertions
    assert "hidden_tests" not in jrp, "CRITICAL LEAK: 'hidden_tests' key present in public JRP!"
    assert "test_hidden_billing" not in str(jrp), "CRITICAL LEAK: Hidden test filename or code leaked in JRP!"
    assert "test_standard_monthly_rollover" in jrp["public_tests"], "Public tests must be included."
    assert "calculate_next_billing_date" in jrp["source_code"], "Broken source code must be included."
    print("  --> Verified: JRP contains ONLY broken source code and public tests.")
    print("  --> Verified: Hidden tests (test_hidden_billing.py) are completely isolated from worker view.")

    # -------------------------------------------------------------
    # Step 3: Rogue Submits Plausible Code (Passes Public Tests)
    # -------------------------------------------------------------
    print("\n[Step 3] Rogue Worker Submits Plausible Fix...")
    rogue_payload = {"jrp": jrp}
    rogue_resp = None
    import asyncio
    rogue_resp = asyncio.run(rogue_work(rogue_payload))

    print(f"  Worker ID: {rogue_resp['worker_id']}")
    print(f"  Fixture Label: {rogue_resp.get('fixture_label')}")
    assert rogue_resp.get("is_adversarial_fixture") is True
    rogue_code = rogue_resp["output_sample"]

    # Test candidate code against PUBLIC tests in sandbox
    public_tests_code = jrp["public_tests"]
    ok_pub, msg_pub, det_pub = verify_code_unit_tests(rogue_code, public_tests_code)
    print(f"  Public Test Suite Execution: Passed={ok_pub} (Exit Code: {det_pub.get('exit_code')})")
    assert ok_pub is True, f"Rogue code must pass public tests to be plausible! Error: {msg_pub}"
    print("  --> Verified: Rogue fix looks convincing and passes all public tests.")

    # -------------------------------------------------------------
    # Step 4: Verifier Executes Hidden Tests in Sandbox -> FAILS
    # -------------------------------------------------------------
    print("\n[Step 4] Verifier Evaluates Rogue Code Against Hidden Tests...")
    hidden_test_file = os.path.join(REPO_PATH, "tests", "test_hidden_billing.py")
    with open(hidden_test_file, "r", encoding="utf-8") as f:
        hidden_tests_code = f.read()

    # Two-layer verifier delivery check
    verification_jrp = {
        **jrp,
        "acceptance_rules": [
            {"type": "unit_test", "test_suite_code": hidden_tests_code}
        ]
    }
    ok_v, status_v, rep_v = verify_delivery(verification_jrp, rogue_resp)
    print(f"  Verifier Outcome: Passed={ok_v}, Status={status_v}")
    print(f"  Failure Detail  : {rep_v.get('message')}")
    assert ok_v is False, "Rogue code must FAIL hidden edge-case tests!"
    assert status_v == "ACCEPTANCE_FAILED"
    assert "Hidden unit tests failed" in rep_v.get("message", "")
    print("  --> Verified: Verifier caught the defect on month-end edge cases.")

    # -------------------------------------------------------------
    # Step 5: Financial Protection: Reservation Released, $0.00 Paid
    # -------------------------------------------------------------
    print("\n[Step 5] Escrow Protection & Treasury Audit Verification...")
    cycle_id = f"gate2_cycle_{int(time.time())}"
    init_ledger()
    max_budget = 15.00

    rogue_bid_val = 0.30
    ok_res, res_id, _ = reserve_budget(cycle_id, jrp["jrp_id"], "rogue-worker-01", rogue_bid_val, max_budget)
    assert ok_res is True

    # Check budget reserved
    state_reserved = get_budget_state(cycle_id, max_budget)
    assert state_reserved["reserved_usd"] == rogue_bid_val

    # Rejection triggers safe reservation release
    release_reservation(res_id, reason=f"Rejected: {rep_v.get('message')}")
    state_released = get_budget_state(cycle_id, max_budget)
    assert state_released["reserved_usd"] == 0.00
    assert state_released["spent_usd"] == 0.00

    # Assert Rogue receives $0.00 in ledger
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_id = 'rogue-worker-01'", (cycle_id,))
    r_count, r_paid = cur.fetchone()
    conn.close()
    assert r_paid == 0.00, f"Rogue must receive $0.00! Got: ${r_paid}"
    print("  --> Verified: Reservation safely released back to treasury.")
    print("  --> Verified: Rogue received $0.00 in ledger audit.")

    # -------------------------------------------------------------
    # Step 6: Bayesian Beta(2,1) Reputation Updating
    # -------------------------------------------------------------
    print("\n[Step 6] Bayesian Beta(2,1) Reputation Engine Verification...")
    init_reputation_schema()
    
    # Clean test entry for fresh evaluation
    test_rogue_id = f"rogue-worker-test-{int(time.time())}"
    test_honest_id = f"code-worker-test-{int(time.time())}"

    # Cold-start priors
    prior_rogue = get_worker_reputation(test_rogue_id)
    print(f"  Cold-Start Prior (Rogue): Score = {prior_rogue['reputation_score']:.4f} [Beta({prior_rogue['alpha']:.0f}, {prior_rogue['beta']:.0f})]")
    assert prior_rogue["reputation_score"] == round(ALPHA_PRIOR / (ALPHA_PRIOR + BETA_PRIOR), 4) # 2/3 = 0.6667
    assert prior_rogue["is_cold_start"] is True
    assert prior_rogue["allocation_cap_usd"] == 1.00

    # Record Rogue Failure
    rogue_outcome = record_worker_outcome(test_rogue_id, success=False, task_id=jrp["jrp_id"], notes="Failed hidden edge-case unit tests")
    print(f"  Post-Failure (Rogue)    : Score = {rogue_outcome['new_score']:.4f} [Beta({rogue_outcome['alpha']:.0f}, {rogue_outcome['beta']:.0f})]")
    print(f"                            Delta = {rogue_outcome['score_delta']:+.4f}")
    assert rogue_outcome["new_score"] == 0.5000, f"Expected 0.5000 after failure (Beta(2,2)), got {rogue_outcome['new_score']}"
    assert rogue_outcome["score_delta"] == round(0.5000 - 0.6667, 4)

    # Record Honest Worker Success
    prior_honest = get_worker_reputation(test_honest_id)
    honest_outcome = record_worker_outcome(test_honest_id, success=True, task_id=jrp["jrp_id"], notes="Passed all unit tests")
    print(f"  Post-Success (Honest)   : Score = {honest_outcome['new_score']:.4f} [Beta({honest_outcome['alpha']:.0f}, {honest_outcome['beta']:.0f})]")
    print(f"                            Delta = {honest_outcome['score_delta']:+.4f}")
    assert honest_outcome["new_score"] == 0.7500, f"Expected 0.7500 after success (Beta(3,1)), got {honest_outcome['new_score']}"
    assert honest_outcome["score_delta"] == round(0.7500 - 0.6667, 4)

    print("\n" + "=" * 70)
    print("GATE 2 PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test_gate2()
