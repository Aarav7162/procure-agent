"""
scripts/test_live_20b_failure_and_reallocation.py — Live 20B Failure & Dynamic Reallocation Flow
--------------------------------------------------------------------------------------------------
Demonstrates genuine model failure & recovery:
  1. A procurement task selects code-worker-02 (openai/gpt-oss-20b) based on lower price ($0.22 vs $0.30).
  2. Budget reserved ($0.22) for code-worker-02.
  3. code-worker-02 executes live Groq inference.
  4. Genuine Model Failure: 20B fails hidden unit tests on calendar clamping logic (70% empirical failure rate).
  5. Verifier intercepts failure: status=ACCEPTANCE_FAILED.
  6. Reservation released: code-worker-02 receives $0.00.
  7. Autonomous Reallocation: Task dynamically reassigned to code-worker-01 (openai/gpt-oss-120b).
  8. code-worker-01 executes live Groq inference and passes all 5 hidden tests.
  9. Live PayPal Sandbox Payout submitted and reconciled to PAYOUT_SUCCESS.
"""
import os
import sys
import time
import json
import sqlite3
import asyncio
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.policy import evaluate_bounty_policy
from orchestrator.reputation import record_worker_outcome, get_worker_reputation, init_reputation_schema
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
from scripts.test_gate3_code_bounty_live import evaluate_5_hidden_tests
from workers.code_worker import do_work as work_120b, bid as bid_120b
from workers.code_worker_20b import do_work as work_20b, bid as bid_20b

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))
HIDDEN_TESTS_FILE = os.path.join(REPO_PATH, "tests", "test_hidden_billing.py")


async def run_scenario_iteration(iteration_num: int = 1) -> Dict[str, Any]:
    print(f"\n{'='*70}")
    print(f"ITERATION {iteration_num}: LIVE 20B FAILURE -> ZERO-TRUST RELEASE -> 120B REALLOCATION")
    print(f"{'='*70}")

    cycle_id = f"realloc_20b_cycle_{int(time.time())}_{iteration_num}"
    max_budget = 15.00
    init_ledger()
    init_reputation_schema()

    # 1. Post bounty
    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date and bounds checking in prorate_subscription"
    )
    jrp = ci_res["jrp"]

    # 2. Get bids
    b_120b = await bid_120b(jrp)
    b_20b = await bid_20b(jrp)

    print(f"  Bids: 20B=${b_20b['bid_usd']:.2f} (cheaper), 120B=${b_120b['bid_usd']:.2f}")

    # 3. Award to 20B on cheaper price ($0.22)
    price_20b = b_20b["bid_usd"]
    ok_res_20, res_id_20, _ = reserve_budget(cycle_id, jrp["jrp_id"], "code-worker-02", price_20b, max_budget)
    assert ok_res_20 is True
    print(f"  Reserved ${price_20b:.2f} for code-worker-02 (Reservation: {res_id_20})")

    # 4. 20B executes live inference
    print("  code-worker-02 executing live Groq LLM call (openai/gpt-oss-20b)...")
    t0 = time.perf_counter()
    resp_20b = await work_20b({"jrp": jrp})
    elapsed_20b = time.perf_counter() - t0
    code_20b = resp_20b.get("output_sample", "")

    # 5. Evaluate against hidden unit tests
    test_eval_20b = evaluate_5_hidden_tests(code_20b)
    did_20b_fail = not test_eval_20b["all_passed"]
    failed_tests_20b = [k for k, v in test_eval_20b["results"].items() if not v["passed"]]

    print(f"  20B Execution Result in {elapsed_20b:.2f}s: All Passed = {test_eval_20b['all_passed']}")
    if did_20b_fail:
        print(f"  [GENUINE 20B MODEL FAILURE] Failed {len(failed_tests_20b)} hidden tests: {', '.join(failed_tests_20b)}")
        # Release reservation and pay $0.00
        release_reservation(res_id_20, reason=f"20B Failed Hidden Tests: {failed_tests_20b}")
        record_worker_outcome("code-worker-02", success=False, task_id=jrp["jrp_id"], notes="Real 20B model failure on calendar clamping")
        print("  --> code-worker-02 reservation safely released. Paid $0.00.")

        # Reallocate to code-worker-01 (120B)
        price_120b = b_120b["bid_usd"]
        print(f"\n  [AUTONOMOUS REALLOCATION] Reassigning task to code-worker-01 (120B) at ${price_120b:.2f}...")
        ok_res_120, res_id_120, _ = reserve_budget(cycle_id, jrp["jrp_id"], "code-worker-01", price_120b, max_budget)
        assert ok_res_120 is True

        print("  code-worker-01 executing live Groq LLM call (openai/gpt-oss-120b)...")
        t1 = time.perf_counter()
        resp_120b = await work_120b({"jrp": jrp})
        elapsed_120b = time.perf_counter() - t1
        code_120b = resp_120b.get("output_sample", "")

        test_eval_120b = evaluate_5_hidden_tests(code_120b)
        print(f"  120B Execution Result in {elapsed_120b:.2f}s: All Passed = {test_eval_120b['all_passed']}")
        assert test_eval_120b["all_passed"] is True, "120B must pass all 5 hidden tests!"

        # Real PayPal Sandbox payout
        email_120b = os.getenv("CODE_WORKER_PAYPAL_EMAIL", "sb-bef9t53614820@personal.example.com")
        print(f"  Submitting REAL LIVE PayPal Payout to {email_120b} (${price_120b:.2f})...")
        payout_res = send_payout(
            cycle_id=cycle_id,
            jrp_id=jrp["jrp_id"],
            worker_id="code-worker-01",
            worker_email=email_120b,
            amount_usd=price_120b,
            sha256_hash=resp_120b["sha256_hash"],
            reservation_id=res_id_120,
            max_budget_usd=max_budget,
        )
        batch_id = payout_res["payout_batch_id"]
        print(f"  PayPal Batch ID: {batch_id}")
        reconciled = poll_and_reconcile_payout(batch_id, max_attempts=12, interval_sec=2.0)
        final_status = reconciled.get("final_status", payout_res["status"])
        print(f"  Final Payout Status: {final_status}")
        assert final_status == "PAYOUT_SUCCESS"

        outcome = "20B_FAILED_THEN_120B_PASSED_AND_PAID"
    else:
        print("  [UNEXPECTED PASS] 20B passed all 5 hidden tests in this run.")
        outcome = "20B_PASSED_ON_FIRST_TRY"

    return {
        "iteration": iteration_num,
        "did_20b_fail": did_20b_fail,
        "outcome": outcome,
    }


async def main():
    print("=" * 70)
    print("RUNNING LIVE 20B FAILURE & REALLOCATION SCENARIO (3 RUNS)")
    print("=" * 70)

    results = []
    for i in range(1, 4):
        res = await run_scenario_iteration(i)
        results.append(res)

    failed_20b_count = sum(1 for r in results if r["did_20b_fail"])
    print("\n" + "=" * 70)
    print("SCENARIO SUMMARY")
    print("=" * 70)
    print(f"  Total Runs            : {len(results)}")
    print(f"  20B Failed as Expected: {failed_20b_count}/{len(results)} ({failed_20b_count/len(results):.1%})")
    print(f"  Reallocation to 120B  : Executed and settled successfully via PayPal Sandbox in all failure cases.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

