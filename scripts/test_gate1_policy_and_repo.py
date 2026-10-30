"""
scripts/test_gate1_policy_and_repo.py — Gate 1 Verification Suite
-----------------------------------------------------------------
Verifies Gate 1 requirements:
  1. Demo repo has genuine failing test suite with captured realistic failure output.
  2. Public tests pass; hidden tests fail on month-end edge cases.
  3. Policy engine enforces whitelist, weekly spend cap, and human approval threshold.
  4. Simulated CI trigger autonomously posts compliant bounty JRP.
"""
import os
import sys
import json
import pytest
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator.policy import evaluate_bounty_policy, load_policy
from scripts.post_bounty import run_repo_tests, post_bounty_from_ci

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))


def test_gate1():
    print("=" * 70)
    print("GATE 1 VERIFICATION: Policy Engine & Demo Repository")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Real Failing Test Suite Verification on Broken Repo
    # -------------------------------------------------------------
    print("\n[Step 1] Executing Test Suite on Demo Repo...")
    test_res = run_repo_tests(REPO_PATH)
    print(f"  Process Exit Code: {test_res['exit_code']}")
    print(f"  Failures Detected: {test_res['has_failures']}")
    
    # Assert real failures exist
    assert test_res["has_failures"] is True, "Demo repo test suite must fail on broken code!"
    assert "ValueError: day is out of range for month" in test_res["stdout"], "Expected real ValueError month-end failure!"
    assert "5 failed, 3 passed" in test_res["stdout"], "Expected 5 hidden failures and 3 public passes!"
    print("  --> Real failure verified: 'ValueError: day is out of range for month'")
    print("  --> Public tests PASS (3 passed), Hidden edge-case tests FAIL (5 failed).")

    # -------------------------------------------------------------
    # 2. Policy Engine Whitelist Check
    # -------------------------------------------------------------
    print("\n[Step 2] Testing Policy Whitelist Check...")
    ok_disallowed, dec_disallowed, det_disallowed = evaluate_bounty_policy("crypto_arbitrage", 0.50)
    print(f"  Disallowed Task ('crypto_arbitrage') -> Decision: {dec_disallowed}")
    assert ok_disallowed is False, "Disallowed task type must not be approved!"
    assert dec_disallowed == "POLICY_REJECTED"
    print("  --> Whitelist check enforced successfully.")

    # -------------------------------------------------------------
    # 3. Policy Engine Weekly Spend Cap Check
    # -------------------------------------------------------------
    print("\n[Step 3] Testing Policy Weekly Spend Cap ($25.00)...")
    ok_overcap, dec_overcap, det_overcap = evaluate_bounty_policy("code_bounty", 50.00)
    print(f"  Excessive Bounty ($50.00 > $25.00 Cap) -> Decision: {dec_overcap}")
    assert ok_overcap is False, "Bounty exceeding weekly cap must be rejected!"
    assert dec_overcap == "POLICY_REJECTED"
    assert "Weekly spend cap exceeded" in det_overcap.get("reason", "")
    print("  --> Weekly spend cap enforced successfully.")

    # -------------------------------------------------------------
    # 4. Policy Engine Human Approval Threshold Check
    # -------------------------------------------------------------
    print("\n[Step 4] Testing Policy Approval Threshold ($5.00)...")
    ok_thresh, dec_thresh, det_thresh = evaluate_bounty_policy("code_bounty", 8.00)
    print(f"  High Bounty ($8.00 > $5.00 Threshold) -> Decision: {dec_thresh}")
    assert ok_thresh is True
    assert dec_thresh == "REQUIRES_HUMAN_APPROVAL"
    assert "exceeds autonomous threshold" in det_thresh.get("reason", "")
    print("  --> Human approval escalation enforced successfully.")

    # -------------------------------------------------------------
    # 5. Compliant Autonomous Bounty Posting via Simulated CI Trigger
    # -------------------------------------------------------------
    print("\n[Step 5] Testing Autonomous Simulated CI Trigger Posting...")
    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date"
    )
    print(f"  CI Posting Status: {ci_res['status']}")
    assert ci_res["status"] == "POSTED"
    assert ci_res["decision"] == "AUTONOMOUS_APPROVED"
    assert "jrp" in ci_res
    jrp = ci_res["jrp"]
    assert "calculate_next_billing_date" in jrp["source_code"]
    assert "test_standard_monthly_rollover" in jrp["public_tests"]
    assert jrp["max_bid_usd"] == 0.50
    print(f"  JRP Created: ID={jrp['jrp_id']}, Status={jrp['status']}")
    print("  --> Compliant bounty autonomously approved and posted.")

    print("\n" + "=" * 70)
    print("GATE 1 PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test_gate1()
