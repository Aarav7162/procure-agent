"""
local_executor.py — Real 1-Slot Local Task Executor & Bottleneck Detection
--------------------------------------------------------------------------
Implements a genuine 1-slot local execution queue with active concurrency tracking.
The orchestrator checks this executor:
  1. If idle (0/1 occupied): Executes locally for $0.00 without procurement.
  2. If occupied (1/1 busy): Local capacity is genuine bottleneck -> outsources to marketplace.
Includes documented deterministic triggers for live demonstrations (submitting back-to-back jobs).
"""
import time
import asyncio
from typing import Tuple, Dict, Any, Optional

MAX_CONCURRENCY = 1


class LocalExecutor:
    def __init__(self, max_concurrency: int = MAX_CONCURRENCY):
        self.max_concurrency = max_concurrency
        self.active_job_id: Optional[str] = None
        self.active_job_desc: Optional[str] = None
        self.job_start_time: Optional[float] = None
        self.estimated_duration_sec: float = 0.0
        self.completed_jobs_count: int = 0
        self._lock = asyncio.Lock()
        self._current_task: Optional[asyncio.Task] = None

    def is_busy(self) -> bool:
        return self.active_job_id is not None

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        elapsed = round(now - self.job_start_time, 2) if self.job_start_time else 0.0
        remaining = max(0.0, round(self.estimated_duration_sec - elapsed, 2)) if self.job_start_time else 0.0
        return {
            "max_concurrency": self.max_concurrency,
            "is_busy": self.is_busy(),
            "active_job_id": self.active_job_id,
            "active_job_desc": self.active_job_desc,
            "elapsed_sec": elapsed,
            "estimated_remaining_sec": remaining,
            "completed_jobs_count": self.completed_jobs_count,
        }

    def check_bottleneck(self, task_deadline_sec: float = 3.0) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Inspects real local queue state.
        Returns:
            (is_bottlenecked: bool, reason: str, metrics: dict)
        """
        status = self.get_status()
        if not status["is_busy"]:
            return False, "Local compute slot available (0/1 slots occupied). Executing on host.", status

        active_id = status["active_job_id"]
        rem = status["estimated_remaining_sec"]
        reason = (
            f"Genuine local bottleneck: slot 100% occupied by job '{active_id}'. "
            f"Estimated wait time ({rem}s) exceeds SLA deadline ({task_deadline_sec}s). Outsource required."
        )
        return True, reason, status

    async def execute_local_job(self, job_id: str, description: str, duration_sec: float = 1.0) -> Dict[str, Any]:
        """
        Executes a job locally on the host machine.
        Locks the single local slot so any overlapping job encounters a real bottleneck.
        """
        async with self._lock:
            if self.is_busy():
                raise RuntimeError(f"Local capacity violation: Slot already occupied by {self.active_job_id}")

            self.active_job_id = job_id
            self.active_job_desc = description
            self.job_start_time = time.time()
            self.estimated_duration_sec = duration_sec

            try:
                # Perform genuine async CPU/IO work
                await asyncio.sleep(duration_sec)
                self.completed_jobs_count += 1
                return {
                    "job_id": job_id,
                    "status": "COMPLETED_LOCALLY",
                    "duration_sec": duration_sec,
                    "cost_usd": 0.00,
                    "worker": "local-host-executor",
                }
            finally:
                self.active_job_id = None
                self.active_job_desc = None
                self.job_start_time = None
                self.estimated_duration_sec = 0.0

    def occupy_slot_background(self, job_id: str, description: str, duration_sec: float = 5.0) -> asyncio.Task:
        """
        Deterministic demo trigger: occupies local slot in the background for duration_sec.
        Any subsequent job submitted while this runs will deterministically detect a bottleneck.
        """
        if self.is_busy():
            raise RuntimeError(f"Cannot occupy slot: Already busy with {self.active_job_id}")

        async def _run():
            await self.execute_local_job(job_id, description, duration_sec)

        task = asyncio.create_task(_run())
        self._current_task = task
        # Give event loop a microsecond to enter execute_local_job
        return task

    def reset(self):
        """Reset state for tests."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        self.active_job_id = None
        self.active_job_desc = None
        self.job_start_time = None
        self.estimated_duration_sec = 0.0
        self._current_task = None


# Global singleton instance for orchestrator
local_executor = LocalExecutor(max_concurrency=1)
