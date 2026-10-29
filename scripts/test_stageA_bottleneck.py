"""
test_stageA_bottleneck.py — Stage A Gate Test: Real Local Executor & Bottleneck Gate
------------------------------------------------------------------------------------
Tests:
  1. Idle Local Slot:
     - Single task submitted to empty executor.
     - Runs on host machine for $0.00 cost.
     - Asserts NO procurement/external bids needed.
  2. Busy Local Slot (Genuine Bottleneck):
     - Slot occupied by an active job.
     - Incoming task checks capacity against SLA deadline.
     - Asserts genuine bottleneck detected with real queue metrics.
  3. Deterministic Demo Workflow (Back-to-Back Submission):
     - Job 1 submitted, starts occupying the 1-slot executor.
     - Job 2 submitted immediately while Job 1 is running.
     - Asserts Job 2 detects occupied slot and triggers external procurement.
     - Verifies slot releases cleanly when Job 1 completes.
"""
import os
import sys
import time
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.local_executor import local_executor, LocalExecutor
from orchestrator.bottleneck_sensor import is_bottlenecked, get_local_executor_metrics


async def run_stage_a_tests():
    print("=" * 70)
    print("STAGE A GATE: Real Local Executor & Bottleneck Detection Verification")
    print("=" * 70)

    # Clean initial state
    local_executor.reset()

    # ─────────────────────────────────────────────────────────────
    # Test 1: Idle Local Slot (Executes Locally for $0)
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 1] Testing Idle Local Slot (No Bottleneck)...")
    status_0 = get_local_executor_metrics()
    print(f"  Initial State: is_busy={status_0['is_busy']}, completed_count={status_0['completed_jobs_count']}")
    assert status_0["is_busy"] is False, "Initial executor must be idle"

    bottlenecked_1, reason_1 = is_bottlenecked(task_deadline_sec=3.0)
    print(f"  Bottleneck Check: {bottlenecked_1} | Reason: {reason_1}")
    assert bottlenecked_1 is False, "Idle executor must NOT report a bottleneck"

    print("  Executing Job 1 locally on host...")
    start_t = time.time()
    result_1 = await local_executor.execute_local_job(
        job_id="job_local_01",
        description="Local fast document processing",
        duration_sec=0.5,
    )
    elapsed_1 = time.time() - start_t
    print(f"  Job 1 Completed in {elapsed_1:.2f}s | Result: {result_1}")
    assert result_1["status"] == "COMPLETED_LOCALLY"
    assert result_1["cost_usd"] == 0.00
    assert result_1["worker"] == "local-host-executor"
    assert local_executor.completed_jobs_count == 1
    assert local_executor.is_busy() is False
    print("  >>> [PASS] Test 1: Task executed locally for $0.00 without procurement! <<<")

    # ─────────────────────────────────────────────────────────────
    # Test 2: Busy Local Slot (Genuine Capacity Exhaustion)
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 2] Testing Busy Slot Capacity Exhaustion (Genuine Bottleneck)...")
    # Occupy slot in background for 3 seconds
    bg_task = local_executor.occupy_slot_background(
        job_id="job_heavy_01",
        description="Heavy OCR batch running on host CPU",
        duration_sec=3.0,
    )
    await asyncio.sleep(0.1)  # Let background task enter execution

    status_busy = get_local_executor_metrics()
    print(f"  Executor Status: is_busy={status_busy['is_busy']}, active_job={status_busy['active_job_id']}")
    assert status_busy["is_busy"] is True, "Executor must report busy while running background job"
    assert status_busy["active_job_id"] == "job_heavy_01"

    # Check bottleneck for incoming Job 2 with tight deadline (1.0s)
    bottlenecked_2, reason_2 = is_bottlenecked(task_deadline_sec=1.0)
    print(f"  Bottleneck Check: {bottlenecked_2}")
    print(f"  Reason: {reason_2}")
    assert bottlenecked_2 is True, "Busy slot must trigger a genuine bottleneck!"
    assert "job_heavy_01" in reason_2, "Reason must identify the blocking active job"
    assert "exceeds SLA deadline" in reason_2, "Reason must explain deadline violation"
    print("  >>> [PASS] Test 2: Genuine bottleneck correctly detected with real queue metrics! <<<")

    # Await background job completion and verify slot cleanup
    print("  Waiting for background job to finish...")
    await bg_task
    status_freed = get_local_executor_metrics()
    print(f"  Freed State: is_busy={status_freed['is_busy']}, completed={status_freed['completed_jobs_count']}")
    assert status_freed["is_busy"] is False, "Slot must automatically free after completion"
    assert status_freed["completed_jobs_count"] == 2

    # ─────────────────────────────────────────────────────────────
    # Test 3: Back-to-Back Submission (Deterministic Demo Workflow)
    # ─────────────────────────────────────────────────────────────
    print("\n[Test 3] Testing Back-to-Back Deterministic Demo Flow...")
    # Simulate user submitting Job A (takes 2 seconds)
    print("  Submitting Job A to local executor...")
    job_a_task = local_executor.occupy_slot_background(
        job_id="demo_job_A",
        description="Batch OCR job A",
        duration_sec=2.0,
    )
    await asyncio.sleep(0.2)

    # Immediately submit Job B
    print("  Immediately submitting Job B back-to-back...")
    b_bottlenecked, b_reason = is_bottlenecked(task_deadline_sec=1.0)
    print(f"  Job B Bottleneck Check: {b_bottlenecked}")
    print(f"  Decision: {'OUTSOURCE TO BROKER' if b_bottlenecked else 'EXECUTE LOCALLY'}")
    assert b_bottlenecked is True, "Job B must detect slot occupied by Job A!"

    # Clean up
    await job_a_task
    assert local_executor.is_busy() is False
    print("  >>> [PASS] Test 3: Back-to-back submission deterministically triggers procurement! <<<")

    print("\n" + "=" * 70)
    print("ALL STAGE A GATE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_stage_a_tests())
    sys.exit(0 if success else 1)
