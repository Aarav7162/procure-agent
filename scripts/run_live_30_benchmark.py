"""
scripts/run_live_30_benchmark.py
--------------------------------
Executes 30 fresh concurrent live iterations of code generation against Groq API:
  • Specialist Worker 120B: openai/gpt-oss-120b (port 8003)
  • Fast Worker 20B:       openai/gpt-oss-20b  (port 8007)

Both run concurrently on each iteration using asyncio.gather.
Each generated function is rigorously evaluated against 5 hidden unit tests.
Every single run is appended live to audit/run_log.jsonl.
Historical runs are preserved with 'backfilled' labels but excluded from scores.
Outputs final empirical sample sizes (N=30), Beta posterior reputations, and rolling latencies.
"""
import os
import sys
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from audit.run_log import (
    RUN_LOG_PATH,
    append_run_log,
    compute_worker_metrics_from_log,
    get_run_counts_by_source,
    get_all_run_logs,
)
from scripts.post_bounty import post_bounty_from_ci
from scripts.test_gate3_code_bounty_live import evaluate_5_hidden_tests
from workers.code_worker import do_work as work_120b
from workers.code_worker_20b import do_work as work_20b

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))


def clean_run_log_preserve_backfilled():
    """Retains backfilled historical runs while pruning any prior temporary live benchmark runs."""
    if not os.path.exists(RUN_LOG_PATH):
        return

    all_logs = get_all_run_logs(exclude_backfilled=False)
    # Retain only backfilled rows
    backfilled_only = [r for r in all_logs if "backfilled" in r.get("notes", "").lower()]

    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        for r in backfilled_only:
            f.write(json.dumps(r) + "\n")

    print(f"[Run Log] Pruned previous live runs; retained {len(backfilled_only)} backfilled historical rows.")


async def run_single_worker_with_retry(work_func, jrp: dict, model_name: str, max_retries: int = 3) -> Dict[str, Any]:
    """Invokes worker with rate-limit / network retry logic."""
    for attempt in range(max_retries):
        t0 = time.perf_counter()
        try:
            resp = await work_func({"jrp": jrp})
            wall_time = time.perf_counter() - t0
            code = resp.get("output_sample", "")
            cost = resp.get("api_cost_usd", 0.0)
            tokens = resp.get("tokens_consumed", 0)

            eval_res = evaluate_5_hidden_tests(code)
            all_passed = eval_res["all_passed"]
            failed_tests = [k for k, v in eval_res["results"].items() if not v["passed"]]

            return {
                "model": model_name,
                "wall_time": wall_time,
                "all_passed": all_passed,
                "failed_tests": failed_tests,
                "cost_usd": cost,
                "tokens": tokens,
            }
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2.0 * (attempt + 1)
                print(f" [Retry {model_name} after {e}: wait {wait_time}s] ", end="", flush=True)
                await asyncio.sleep(wait_time)
            else:
                return {
                    "model": model_name,
                    "wall_time": time.perf_counter() - t0,
                    "all_passed": False,
                    "failed_tests": [f"Exception: {str(e)}"],
                    "cost_usd": 0.0,
                    "tokens": 0,
                }


async def run_30_live_concurrent_benchmark(num_iterations: int = 30):
    print("=" * 80)
    print(f"STARTING 30 CONCURRENT LIVE BENCHMARK ITERATIONS (120B vs 20B)")
    print("  Target Repository : demo_repos/billing_engine")
    print("  Evaluation        : 5 Hidden Unit Tests per candidate")
    print("  Single Truth Log  : audit/run_log.jsonl")
    print("=" * 80)

    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date and bounds checking in prorate_subscription"
    )
    jrp = ci_res["jrp"]

    results_120b = []
    results_20b = []

    for i in range(1, num_iterations + 1):
        print(f"  [Run {i:02d}/{num_iterations:02d}] Calling 120B & 20B concurrently...", end="", flush=True)

        task_120b = run_single_worker_with_retry(work_120b, jrp, "openai/gpt-oss-120b")
        task_20b = run_single_worker_with_retry(work_20b, jrp, "openai/gpt-oss-20b")

        res_120b, res_20b = await asyncio.gather(task_120b, task_20b)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Append to audit/run_log.jsonl
        append_run_log(
            worker_id="code-worker-01",
            model="openai/gpt-oss-120b",
            pass_fail="PASS" if res_120b["all_passed"] else "FAIL",
            latency=res_120b["wall_time"],
            token_cost=res_120b["cost_usd"],
            source_script="scripts/run_live_30_benchmark.py",
            timestamp=now_iso,
            notes="fresh live concurrent benchmark"
        )

        append_run_log(
            worker_id="code-worker-02",
            model="openai/gpt-oss-20b",
            pass_fail="PASS" if res_20b["all_passed"] else "FAIL",
            latency=res_20b["wall_time"],
            token_cost=res_20b["cost_usd"],
            source_script="scripts/run_live_30_benchmark.py",
            timestamp=now_iso,
            notes="fresh live concurrent benchmark"
        )

        results_120b.append(res_120b)
        results_20b.append(res_20b)

        s_120 = "PASS" if res_120b["all_passed"] else f"FAIL({len(res_120b['failed_tests'])})"
        s_20  = "PASS" if res_20b["all_passed"] else f"FAIL({len(res_20b['failed_tests'])})"
        print(f" 120B: {res_120b['wall_time']:.2f}s [{s_120}] | 20B: {res_20b['wall_time']:.2f}s [{s_20}]")

        # Jitter interval to respect Groq rate limits cleanly
        if i < num_iterations:
            await asyncio.sleep(1.2)


async def main():
    clean_run_log_preserve_backfilled()
    await run_30_live_concurrent_benchmark(num_iterations=30)

    print("\n" + "=" * 80)
    print("EMPIRICAL BENCHMARK RESULTS (COMPUTED EXCLUSIVELY FROM N=30 LIVE RUNS)")
    print("=" * 80)

    m120 = compute_worker_metrics_from_log("code-worker-01", exclude_backfilled=True)
    m20  = compute_worker_metrics_from_log("code-worker-02", exclude_backfilled=True)

    print("\n[Worker code-worker-01 / openai/gpt-oss-120b]:")
    print(f"  Live Sample Size (N)       : {m120['n_samples']}")
    print(f"  Passes / Failures          : {m120['passes']} / {m120['failures']}")
    print(f"  Empirical Pass Rate        : {m120['pass_rate']:.1%}")
    print(f"  Beta Posterior Reputation R : {m120['reputation_score']:.4f} (alpha={m120['alpha']}, beta={m120['beta']})")
    print(f"  Mean Latency (All 30 Runs) : {m120['avg_latency_all']:.4f}s")
    print(f"  Rolling Latency (Recent 10): {m120['avg_latency_recent_10']:.4f}s")
    print(f"  Mean Token Cost            : ${m120['avg_token_cost']:.6f} USD")

    print("\n[Worker code-worker-02 / openai/gpt-oss-20b]:")
    print(f"  Live Sample Size (N)       : {m20['n_samples']}")
    print(f"  Passes / Failures          : {m20['passes']} / {m20['failures']}")
    print(f"  Empirical Pass Rate        : {m20['pass_rate']:.1%}")
    print(f"  Beta Posterior Reputation R : {m20['reputation_score']:.4f} (alpha={m20['alpha']}, beta={m20['beta']})")
    print(f"  Mean Latency (All 30 Runs) : {m20['avg_latency_all']:.4f}s")
    print(f"  Rolling Latency (Recent 10): {m20['avg_latency_recent_10']:.4f}s")
    print(f"  Mean Token Cost            : ${m20['avg_token_cost']:.6f} USD")

    print("\n" + "=" * 80)
    print("RUN COUNTS BY SOURCE (FULL AUDIT TRAIL)")
    print("=" * 80)
    summary = get_run_counts_by_source()
    for wid, sources in summary.items():
        print(f"Worker {wid}:")
        total = 0
        for src, cnt in sources.items():
            print(f"  • {src}: {cnt} runs")
            total += cnt
        print(f"  Total logged in run_log.jsonl: {total}")

    # Output JSON summary for automated updates
    output_summary = {
        "120b": m120,
        "20b": m20,
        "run_counts_by_source": summary,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    summary_path = os.path.join(os.path.dirname(__file__), "..", "data", "benchmark_30_runs_summary.json")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(output_summary, f, indent=2)
    print(f"\nSaved empirical summary -> {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())

