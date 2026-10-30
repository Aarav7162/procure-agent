"""
scripts/test_gate3_code_bounty_live.py — Gate 3 Live Code Bounty & PayPal Settlement Suite
------------------------------------------------------------------------------------------
Verifies Gate 3 requirements:
  1. Simulated CI trigger posts policy-approved bounty JRP for demo_repos/billing_engine.
  2. Cold-start allocation cap check shown in event stream ($1.00 cap does not block $0.45 bid).
  3. Rogue worker underbids ($0.30); fails hidden tests; blocked with $0.00 paid.
  4. Dynamic reallocation to honest worker (code-worker-01).
  5. Live Groq LLM inference (openai/gpt-oss-120b) synthesizes fix.
  6. Individual evaluation on all 5 hidden unit tests reported.
  7. Reports attempts taken and actual token compute cost.
  8. Real PayPal Sandbox payout submitted in PAYOUT_MODE=live and reconciled to PAYOUT_SUCCESS.
  9. Final audit in SQLite ledger: Rogue paid $0.00, honest worker paid $0.45.
"""
import os
import sys
import time
import json
import sqlite3
import hashlib
import asyncio
from typing import Dict, Any, List

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.policy import evaluate_bounty_policy
from orchestrator.reputation import get_worker_reputation, record_worker_outcome, init_reputation_schema
from orchestrator.verifier import verify_code_unit_tests, verify_delivery
from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    send_payout,
    poll_and_reconcile_payout,
    get_budget_state,
    DB_PATH,
)
from scripts.post_bounty import post_bounty_from_ci
from workers.rogue_worker import do_work as rogue_work, bid as rogue_bid
from workers.code_worker import do_work as honest_code_work, bid as honest_code_bid

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))
HIDDEN_TESTS_FILE = os.path.join(REPO_PATH, "tests", "test_hidden_billing.py")


def evaluate_5_hidden_tests(candidate_code: str) -> Dict[str, Any]:
    """Evaluates candidate code against each of the 5 hidden test functions individually."""
    with open(HIDDEN_TESTS_FILE, "r", encoding="utf-8") as f:
        hidden_source = f.read()

    test_cases = [
        ("test_month_end_january_to_february", "Jan 31 + 1 month clamps to Feb 28"),
        ("test_month_end_31_to_30", "March 31 + 1 month clamps to April 30"),
        ("test_leap_year_rollover", "Feb 29 on leap year + 12 months clamps to Feb 28"),
        ("test_invalid_interval_rejected", "interval <= 0 raises ValueError"),
        ("test_invalid_proration_days_rejected", "days_active > days_in_period raises ValueError"),
    ]

    results = {}
    for func_name, description in test_cases:
        test_script = (
            f"{hidden_source}\n\n"
            f"if __name__ == '__main__':\n"
            f"    {func_name}()\n"
        )
        ok, msg, det = verify_code_unit_tests(candidate_code, test_script)
        results[func_name] = {
            "description": description,
            "passed": ok,
            "message": msg,
            "details": det,
        }

    all_passed = all(r["passed"] for r in results.values())
    return {
        "all_passed": all_passed,
        "results": results,
    }


async def run_gate3():
    print("=" * 70)
    print("GATE 3: Live Code Bounty Procurement, Verification & PayPal Settlement")
    print("=" * 70)

    payout_mode = os.getenv("PAYOUT_MODE", "simulated").strip().lower()
    print(f"  PAYOUT_MODE: {payout_mode.upper()}")
    assert payout_mode == "live", "Gate 3 requires PAYOUT_MODE=live for real PayPal settlement!"

    cycle_id = f"bounty_live_cycle_{int(time.time())}"
    max_budget = 15.00
    init_ledger()
    init_reputation_schema()

    # -------------------------------------------------------------
    # Step 1: Simulated CI Trigger Formulates & Posts JRP
    # -------------------------------------------------------------
    print("\n[Step 1] Simulated CI Trigger Ingesting Broken Repo Failure...")
    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date and bounds checking in prorate_subscription"
    )
    assert ci_res["status"] == "POSTED"
    jrp = ci_res["jrp"]
    print(f"  Bounty Posted: JRP ID={jrp['jrp_id']}, Max Budget=${jrp['max_bid_usd']:.2f}")

    # -------------------------------------------------------------
    # Step 2: Cold-Start Allocation Cap & Bidding
    # -------------------------------------------------------------
    print("\n[Step 2] Cold-Start Cap Checks & Competitive Market Bidding...")
    r_bid_raw = await rogue_bid(jrp)
    h_bid_raw = await honest_code_bid(jrp)

    # Check Cold-Start Allocation Cap ($1.00)
    r_rep = get_worker_reputation(r_bid_raw["worker_id"])
    h_rep = get_worker_reputation(h_bid_raw["worker_id"])

    print(f"  [CAP CHECK] {r_bid_raw['worker_id']}: Bid ${r_bid_raw['bid_usd']:.2f} <= Cap ${r_rep['allocation_cap_usd']:.2f} -> APPROVED")
    print(f"  [CAP CHECK] {h_bid_raw['worker_id']}: Bid ${h_bid_raw['bid_usd']:.2f} <= Cap ${h_rep['allocation_cap_usd']:.2f} -> APPROVED")
    assert r_bid_raw["bid_usd"] <= r_rep["allocation_cap_usd"], "Rogue bid must be within allocation cap!"
    assert h_bid_raw["bid_usd"] <= h_rep["allocation_cap_usd"], "Honest bid must be within allocation cap!"

    rogue_email = os.getenv("ROGUE_PAYPAL_EMAIL", "sb-a43fio53613334@personal.example.com")
    honest_email = os.getenv("CODE_WORKER_PAYPAL_EMAIL", "sb-bef9t53614820@personal.example.com")

    rogue_price = r_bid_raw["bid_usd"]      # $0.30
    honest_price = h_bid_raw["bid_usd"]    # $0.45 (or $0.20 base)

    print(f"  Rogue Worker underbids: ${rogue_price:.2f} [Email: {rogue_email}]")
    print(f"  Honest Worker bids    : ${honest_price:.2f} [Email: {honest_email}]")

    # -------------------------------------------------------------
    # Step 3: Round 1 — Rogue Awarded -> Defect Caught -> Blocked
    # -------------------------------------------------------------
    print("\n[Step 3] Round 1: Rogue Awarded via Aggressive Underbid...")
    ok_res_r, res_id_r, _ = reserve_budget(cycle_id, jrp["jrp_id"], "rogue-worker-01", rogue_price, max_budget)
    assert ok_res_r is True
    print(f"  Escrow Reserved for Rogue: ${rogue_price:.2f} (Reservation: {res_id_r})")

    # Rogue executes work
    rogue_work_resp = await rogue_work({"jrp": jrp})
    print(f"  Rogue Submits Delivery: Label={rogue_work_resp.get('fixture_label')}")

    # Verifier tests Rogue against hidden tests
    with open(HIDDEN_TESTS_FILE, "r", encoding="utf-8") as f:
        hidden_source = f.read()

    rogue_verif_jrp = {
        **jrp,
        "acceptance_rules": [{"type": "unit_test", "test_suite_code": hidden_source}]
    }
    ok_v_r, status_v_r, rep_v_r = verify_delivery(rogue_verif_jrp, rogue_work_resp)
    print(f"  Rogue Delivery Verification: Passed={ok_v_r}, Status={status_v_r}")
    print(f"  Failure Detail: {rep_v_r.get('message')}")
    assert ok_v_r is False, "Rogue code must FAIL hidden edge-case tests!"
    assert status_v_r == "ACCEPTANCE_FAILED"

    # Block payment and release reservation
    release_reservation(res_id_r, reason=f"Rejected: {rep_v_r.get('message')}")
    record_worker_outcome("rogue-worker-01", success=False, task_id=jrp["jrp_id"], notes="Failed hidden edge-case unit tests")
    print("  --> Rogue reservation released. Rogue receives $0.00.")

    # -------------------------------------------------------------
    # Step 4: Autonomous Reallocation to Honest Worker
    # -------------------------------------------------------------
    print("\n[Step 4] Autonomous Reallocation to code-worker-01...")
    ok_res_h, res_id_h, _ = reserve_budget(cycle_id, jrp["jrp_id"], "code-worker-01", honest_price, max_budget)
    assert ok_res_h is True
    print(f"  Escrow Reserved for Honest Worker: ${honest_price:.2f} (Reservation: {res_id_h})")

    # -------------------------------------------------------------
    # Step 5: Live Groq LLM Inference & 5 Hidden Tests Evaluation
    # -------------------------------------------------------------
    print("\n[Step 5] Honest Worker Executing Live Groq LLM Inference (openai/gpt-oss-120b)...")
    attempts = 0
    max_attempts = 2
    final_honest_resp = None
    test_eval_results = None

    while attempts < max_attempts:
        attempts += 1
        print(f"\n  [Attempt {attempts}/{max_attempts}] Querying Groq API...")
        honest_resp = await honest_code_work({"jrp": jrp})
        candidate_code = honest_resp["output_sample"]
        
        # Evaluate all 5 hidden tests individually
        test_eval = evaluate_5_hidden_tests(candidate_code)
        print(f"  Evaluation Results on 5 Hidden Test Cases (Attempt {attempts}):")
        for test_name, t_info in test_eval["results"].items():
            status_str = "PASS" if t_info["passed"] else "FAIL"
            print(f"    • {test_name:<38} : [{status_str}] - {t_info['description']}")

        if test_eval["all_passed"]:
            print(f"\n  --> ALL 5 HIDDEN TESTS PASSED on Attempt {attempts}!")
            final_honest_resp = honest_resp
            test_eval_results = test_eval
            break
        else:
            print(f"\n  [ATTEMPT {attempts} FAILED] Hidden test failures detected:")
            for t_name, t_info in test_eval["results"].items():
                if not t_info["passed"]:
                    print(f"    FAILED: {t_name} -> {t_info.get('message')}")
            
            if attempts < max_attempts:
                print("  [RETRYING WITHIN BUDGET] Injecting test failure feedback for second attempt...")
                # Add failure context into task description for the retry
                failed_details = "\n".join([f"- {k}: {v['message']}" for k, v in test_eval["results"].items() if not v["passed"]])
                jrp["task_description"] += f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{failed_details}\nPlease fix these issues."
            else:
                print("  [ATTEMPTS EXHAUSTED] Reallocation or human escalation required.")

    assert final_honest_resp is not None and test_eval_results["all_passed"], "Honest worker must pass all 5 hidden tests!"

    # Token and compute metrics
    in_tokens = final_honest_resp.get("input_tokens", 0)
    out_tokens = final_honest_resp.get("output_tokens", 0)
    total_tokens = final_honest_resp.get("tokens_consumed", in_tokens + out_tokens)
    cost_usd = final_honest_resp.get("api_cost_usd", 0.0)

    print("\n  [Execution & Token Metrics]")
    print(f"    Attempts Taken     : {attempts}")
    print(f"    Input Tokens       : {in_tokens}")
    print(f"    Output Tokens      : {out_tokens}")
    print(f"    Total Tokens       : {total_tokens}")
    print(f"    Actual Token Cost  : ${cost_usd:.5f} USD")
    print(f"    Execution Seconds  : {final_honest_resp.get('execution_seconds')}s")

    # Full verifier check
    ok_v_h, status_v_h, rep_v_h = verify_delivery(rogue_verif_jrp, final_honest_resp)
    assert ok_v_h is True, "Honest worker delivery must pass verifier!"
    assert status_v_h == "VERIFIED"

    # Record honest success in reputation
    record_worker_outcome("code-worker-01", success=True, task_id=jrp["jrp_id"], notes="Passed all 5 hidden unit tests")

    # -------------------------------------------------------------
    # Step 6: Real PayPal Sandbox Settlement (PAYOUT_MODE=live)
    # -------------------------------------------------------------
    print(f"\n[Step 6] Submitting REAL PayPal Sandbox Payout to {honest_email} (${honest_price:.2f})...")
    payout_res = send_payout(
        cycle_id=cycle_id,
        jrp_id=jrp["jrp_id"],
        worker_id="code-worker-01",
        worker_email=honest_email,
        amount_usd=honest_price,
        sha256_hash=final_honest_resp["sha256_hash"],
        reservation_id=res_id_h,
        max_budget_usd=max_budget,
    )

    batch_id = payout_res["payout_batch_id"]
    print(f"  PayPal Batch ID: {batch_id}")
    print("  Polling for final status...")
    reconciled = poll_and_reconcile_payout(batch_id, max_attempts=12, interval_sec=2.0)
    final_status = reconciled.get("final_status", payout_res["status"])
    print(f"  Final Payout Status: {final_status}")
    assert final_status == "PAYOUT_SUCCESS", f"Expected PAYOUT_SUCCESS, got {final_status}"

    # -------------------------------------------------------------
    # Step 7: Final Ledger Audit Assertions
    # -------------------------------------------------------------
    print("\n[Step 7] Verifying Final SQLite Ledger Audit Integrity...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_email = ?", (cycle_id, rogue_email))
    r_count, r_paid = cur.fetchone()
    assert r_paid == 0.00, f"Rogue must receive $0.00! Got: ${r_paid}"

    cur.execute("SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_email = ?", (cycle_id, honest_email))
    h_count, h_paid = cur.fetchone()
    assert h_paid == honest_price, f"Honest worker must receive ${honest_price}! Got: ${h_paid}"
    conn.close()

    print(f"  --> Ledger confirmed: Rogue ({rogue_email}) received $0.00.")
    print(f"  --> Ledger confirmed: Honest Worker ({honest_email}) received ${honest_price:.2f}.")

    print("\n" + "=" * 70)
    print("GATE 3 PASSED SUCCESSFULLY!")
    print(f"  PayPal Batch ID : {batch_id}")
    print(f"  Final Status    : {final_status}")
    print(f"  Recipient       : {honest_email}")
    print(f"  Amount Settled  : ${honest_price:.2f} USD")
    print("=" * 70)
    return True


if __name__ == "__main__":
    asyncio.run(run_gate3())

