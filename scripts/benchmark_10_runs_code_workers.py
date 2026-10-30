"""
scripts/benchmark_10_runs_code_workers.py — 10-Run Empirical Benchmark
-----------------------------------------------------------------------
Executes 10 live model calls for openai/gpt-oss-120b and 10 live model calls for openai/gpt-oss-20b.
Evaluates every run against all 5 hidden unit tests in demo_repos/billing_engine.
Reports:
  • Pass rate out of 10 (all 5 hidden tests passing)
  • Average latency (seconds)
  • Average actual compute cost ($USD)
  • Plain listing of any failures
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

from scripts.post_bounty import post_bounty_from_ci
from scripts.test_gate3_code_bounty_live import evaluate_5_hidden_tests
from workers.code_worker import do_work as work_120b
from workers.code_worker_20b import do_work as work_20b

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))


async def benchmark_worker(worker_name: str, work_func, jrp: dict, num_runs: int = 10) -> Dict[str, Any]:
    print(f"\n{'='*70}")
    print(f"BENCHMARKING {worker_name} ({num_runs} LIVE MODEL CALLS)")
    print(f"{'='*70}")

    runs = []
    for i in range(1, num_runs + 1):
        print(f"  [Run {i:02d}/{num_runs:02d}] Calling live Groq API...", end="", flush=True)
        t0 = time.perf_counter()
        resp = await work_func({"jrp": jrp})
        wall_time = time.perf_counter() - t0
        code = resp.get("output_sample", "")
        cost = resp.get("api_cost_usd", 0.0)
        tokens = resp.get("tokens_consumed", 0)

        # Evaluate against 5 hidden tests
        eval_res = evaluate_5_hidden_tests(code)
        all_passed = eval_res["all_passed"]
        failed_tests = [k for k, v in eval_res["results"].items() if not v["passed"]]

        runs.append({
            "run_index": i,
            "all_passed": all_passed,
            "failed_tests": failed_tests,
            "wall_time": wall_time,
            "cost_usd": cost,
            "tokens": tokens,
        })

        status_str = "PASS (5/5)" if all_passed else f"FAIL ({len(failed_tests)} failed: {', '.join(failed_tests)})"
        print(f" -> {status_str} in {wall_time:.2f}s (${cost:.5f})")

    passed_count = sum(1 for r in runs if r["all_passed"])
    avg_latency = sum(r["wall_time"] for r in runs) / num_runs
    avg_cost = sum(r["cost_usd"] for r in runs) / num_runs
    total_cost = sum(r["cost_usd"] for r in runs)

    print(f"\n[{worker_name} Summary]")
    print(f"  Pass Rate       : {passed_count}/{num_runs} ({passed_count/num_runs:.1%})")
    print(f"  Average Latency : {avg_latency:.4f}s")
    print(f"  Average Cost    : ${avg_cost:.5f} USD")
    print(f"  Total Cost      : ${total_cost:.5f} USD")

    failures = [r for r in runs if not r["all_passed"]]
    if failures:
        print(f"  Failures Encountered ({len(failures)}):")
        for f in failures:
            print(f"    • Run {f['run_index']}: Failed tests {f['failed_tests']}")
    else:
        print("  Failures Encountered: NONE (100% reliability across all 5 hidden tests)")

    return {
        "worker_name": worker_name,
        "runs": runs,
        "passed_count": passed_count,
        "num_runs": num_runs,
        "pass_rate": passed_count / num_runs,
        "avg_latency": avg_latency,
        "avg_cost": avg_cost,
        "total_cost": total_cost,
        "failures": failures,
    }


async def main():
    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date and bounds checking in prorate_subscription"
    )
    jrp = ci_res["jrp"]

    # 1. Benchmark code-worker-01 (gpt-oss-120b)
    res_120b = await benchmark_worker("code-worker-01 (openai/gpt-oss-120b)", work_120b, jrp, num_runs=10)

    # 2. Benchmark code-worker-02 (gpt-oss-20b)
    res_20b = await benchmark_worker("code-worker-02 (openai/gpt-oss-20b)", work_20b, jrp, num_runs=10)

    print("\n" + "=" * 70)
    print("EMPIRICAL COMPARISON SUMMARY: gpt-oss-120b vs gpt-oss-20b")
    print("=" * 70)
    print(f"{'Metric':<25} | {'code-worker-01 (120B)':<22} | {'code-worker-02 (20B)':<22}")
    print("-" * 75)
    print(f"{'Pass Rate (5/5 tests)':<25} | {res_120b['passed_count']}/{res_120b['num_runs']} ({res_120b['pass_rate']:.1%}){' ':<10} | {res_20b['passed_count']}/{res_20b['num_runs']} ({res_20b['pass_rate']:.1%})")
    print(f"{'Average Latency':<25} | {res_120b['avg_latency']:.4f}s{' ':<13} | {res_20b['avg_latency']:.4f}s")
    print(f"{'Average Cost per Call':<25} | ${res_120b['avg_cost']:.5f} USD{' ':<8} | ${res_20b['avg_cost']:.5f} USD")
    print(f"{'Speed Advantage':<25} | Baseline{' ':<16} | {res_120b['avg_latency'] / max(0.001, res_20b['avg_latency']):.2f}x faster")
    print(f"{'Cost Advantage':<25} | Baseline{' ':<16} | {res_120b['avg_cost'] / max(0.00001, res_20b['avg_cost']):.2f}x cheaper")
    print("=" * 70)

    return res_120b, res_20b


if __name__ == "__main__":
    asyncio.run(main())

