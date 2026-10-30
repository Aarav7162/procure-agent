"""
scripts/test_5_runs_20b_reallocation.py — 5 Live Runs of 20B Failure & Dynamic Reallocation
---------------------------------------------------------------------------------------------
Executes 5 complete end-to-end cycles:
  1. Task posted: Month-end rollover bug in billing.py
  2. Bids: 20B ($0.22, cheaper) vs 120B ($0.30)
  3. 20B awarded first
  4. 20B executes live Groq inference (openai/gpt-oss-20b)
  5. 20B evaluated against all 5 hidden unit tests
  6. If 20B fails:
       - Reservation released, $0.00 paid
       - Reallocated to 120B (openai/gpt-oss-120b)
       - 120B executes live Groq inference and passes
       - Real live PayPal Sandbox payout submitted (PAYOUT_MODE=live)
       - Polled until PAYOUT_SUCCESS
  7. If 20B passes:
       - 20B verified and settled
Reports the exact frequency of failure & recovery across all 5 runs.
"""
import os
import sys
import time
import json
import asyncio
from typing import Dict, Any, List

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    send_payout,
    poll_and_reconcile_payout,
    get_budget_state,
)
from orchestrator.reputation import record_worker_outcome, init_reputation_schema
from scripts.post_bounty import post_bounty_from_ci
from scripts.test_gate3_code_bounty_live import evaluate_5_hidden_tests
from workers.code_worker import do_work as work_120b, bid as bid_120b
from workers.code_worker_20b import do_work as work_20b, bid as bid_20b

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))


async def run_single_iteration(idx: int) -> Dict[str, Any]:
    print(f"\n{'='*70}")
    print(f"RUN {idx}/5: 20B AWARD -> LIVE INFERENCE -> HIDDEN TESTS -> REALLOCATION -> PAYPAL")
    print(f"{'='*70}")

    cycle_id = f"realloc_5x_{int(time.time())}_{idx}"
    max_budget = 15.00
    init_ledger()
    init_reputation_schema()

    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date in billing.py"
    )
    jrp = ci_res["jrp"]

    b_120b = await bid_120b(jrp)
    b_20b = await bid_20b(jrp)

    print(f"  [Bids] code-worker-02 (20B): ${b_20b['bid_usd']:.2f} | code-worker-01 (120B): ${b_120b['bid_usd']:.2f}")

    # Award 20B
    ok_res, res_id_20, _ = reserve_budget(cycle_id, jrp["jrp_id"], "code-worker-02", b_20b["bid_usd"], max_budget)
    assert ok_res, "Budget reservation failed for 20B"
    print(f"  [Escrow] Reserved ${b_20b['bid_usd']:.2f} for code-worker-02 (Res ID: {res_id_20})")

    # 20B live inference
    print("  [Live Inference] Calling openai/gpt-oss-20b...")
    t0 = time.perf_counter()
    resp_20b = await work_20b({"jrp": jrp})
    lat_20b = time.perf_counter() - t0
    code_20b = resp_20b.get("output_sample", "")

    eval_20b = evaluate_5_hidden_tests(code_20b)
    passed_20b = eval_20b["all_passed"]
    failed_20b_names = [k for k, v in eval_20b["results"].items() if not v["passed"]]

    print(f"  [Verification 20B] in {lat_20b:.2f}s -> All 5 Passed: {passed_20b}")
    if not passed_20b:
        print(f"  [Failure Details] Failed: {failed_20b_names}")
        # Release reservation, pay $0
        release_reservation(res_id_20, reason=f"20B failed hidden tests: {failed_20b_names}")
        record_worker_outcome("code-worker-02", success=False, task_id=jrp["jrp_id"], notes="Calendar rollover failure")
        print("  [Zero Trust] Reservation released. code-worker-02 paid $0.00.")

        # Reallocate to 120B
        price_120b = b_120b["bid_usd"]
        print(f"\n  [Reallocation] Reassigning to code-worker-01 (120B) at ${price_120b:.2f}...")
        ok_res_120, res_id_120, _ = reserve_budget(cycle_id, jrp["jrp_id"], "code-worker-01", price_120b, max_budget)
        assert ok_res_120, "Reservation for 120B failed"

        print("  [Live Inference] Calling openai/gpt-oss-120b...")
        t1 = time.perf_counter()
        resp_120b = await work_120b({"jrp": jrp})
        lat_120b = time.perf_counter() - t1
        code_120b = resp_120b.get("output_sample", "")

        eval_120b = evaluate_5_hidden_tests(code_120b)
        assert eval_120b["all_passed"], f"120B failed hidden tests unexpectedly: {eval_120b}"
        print(f"  [Verification 120B] in {lat_120b:.2f}s -> All 5 Passed: TRUE")

        record_worker_outcome("code-worker-01", success=True, task_id=jrp["jrp_id"], notes="120B passed hidden tests")

        # PayPal Sandbox payout
        email_120b = os.getenv("CODE_WORKER_PAYPAL_EMAIL", "sb-bef9t53614820@personal.example.com")
        print(f"  [PayPal Payout] Sending ${price_120b:.2f} to {email_120b}...")
        payout = send_payout(
            cycle_id=cycle_id,
            jrp_id=jrp["jrp_id"],
            worker_id="code-worker-01",
            worker_email=email_120b,
            amount_usd=price_120b,
            sha256_hash=resp_120b.get("sha256_hash", ""),
            reservation_id=res_id_120,
            max_budget_usd=max_budget,
        )
        batch_id = payout["payout_batch_id"]
        print(f"  [PayPal Polling] Batch ID: {batch_id}")
        reconciled = poll_and_reconcile_payout(batch_id, max_attempts=12, interval_sec=2.0)
        final_status = reconciled.get("final_status", payout["status"])
        print(f"  [PayPal Final Status] {final_status}")
        assert final_status == "PAYOUT_SUCCESS", f"Payout status was {final_status}"

        return {
            "run": idx,
            "cycle_id": cycle_id,
            "20b_passed": False,
            "20b_latency": lat_20b,
            "20b_failures": failed_20b_names,
            "reallocated": True,
            "120b_passed": True,
            "120b_latency": lat_120b,
            "payout_batch_id": batch_id,
            "final_status": final_status,
            "amount_paid": price_120b,
        }
    else:
        # 20B passed
        record_worker_outcome("code-worker-02", success=True, task_id=jrp["jrp_id"], notes="20B passed hidden tests")
        email_20b = os.getenv("CODE_WORKER_20B_PAYPAL_EMAIL", "sb-kgyi653615592@personal.example.com")
        payout = send_payout(
            cycle_id=cycle_id,
            jrp_id=jrp["jrp_id"],
            worker_id="code-worker-02",
            worker_email=email_20b,
            amount_usd=b_20b["bid_usd"],
            sha256_hash=resp_20b.get("sha256_hash", ""),
            reservation_id=res_id_20,
            max_budget_usd=max_budget,
        )
        batch_id = payout["payout_batch_id"]
        reconciled = poll_and_reconcile_payout(batch_id, max_attempts=12, interval_sec=2.0)
        final_status = reconciled.get("final_status", payout["status"])
        return {
            "run": idx,
            "cycle_id": cycle_id,
            "20b_passed": True,
            "20b_latency": lat_20b,
            "20b_failures": [],
            "reallocated": False,
            "120b_passed": None,
            "120b_latency": None,
            "payout_batch_id": batch_id,
            "final_status": final_status,
            "amount_paid": b_20b["bid_usd"],
        }


async def main():
    print("=" * 70)
    print("EXECUTING 5 CONSECUTIVE LIVE END-TO-END SCENARIOS")
    print("=" * 70)

    results = []
    for i in range(1, 6):
        res = await run_single_iteration(i)
        results.append(res)
        await asyncio.sleep(1)

    print("\n" + "=" * 70)
    print("FINAL 5-RUN SCENARIO AUDIT REPORT")
    print("=" * 70)
    failed_20b_runs = [r for r in results if not r["20b_passed"]]
    passed_20b_runs = [r for r in results if r["20b_passed"]]

    print(f"Total Iterations: {len(results)}")
    print(f"20B Genuinely Failed Hidden Tests: {len(failed_20b_runs)}/5 ({len(failed_20b_runs)/5:.1%})")
    print(f"20B Passed on First Try:          {len(passed_20b_runs)}/5 ({len(passed_20b_runs)/5:.1%})")
    print("\nRun-by-Run Breakdown:")
    for r in results:
        status_str = "FAILED -> Reallocated to 120B -> PAID" if not r["20b_passed"] else "PASSED -> PAID Directly"
        print(f"  Run {r['run']}: 20B ({r['20b_latency']:.2f}s) -> {status_str} (Batch: {r['payout_batch_id']}, ${r['amount_paid']:.2f})")

    if failed_20b_runs:
        avg_lat_fail = sum(r["20b_latency"] for r in failed_20b_runs) / len(failed_20b_runs)
        print(f"\n20B Average Latency on Failing Runs: {avg_lat_fail:.2f}s")
    if passed_20b_runs:
        avg_lat_pass = sum(r["20b_latency"] for r in passed_20b_runs) / len(passed_20b_runs)
        print(f"20B Average Latency on Passing Runs: {avg_lat_pass:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
