"""
bottleneck_sensor.py — Detects when local capacity is exhausted and procurement is needed
"""
import asyncio
from typing import Callable

# Simulated local worker queue (in production this would hook into an actual task runner)
LOCAL_QUEUE_CAPACITY = 3
_current_queue_size = LOCAL_QUEUE_CAPACITY  # Start at full to trigger procurement immediately in demo


def is_bottlenecked(task_type: str) -> tuple[bool, str]:
    """
    Returns (is_bottlenecked: bool, reason: str).
    In a real system this checks:
      - Local worker queue occupancy
      - API rate limit headers
      - GPU memory / CPU thresholds
    For demo we simulate queue-full condition.
    """
    global _current_queue_size

    if _current_queue_size >= LOCAL_QUEUE_CAPACITY:
        return True, f"Local queue full ({_current_queue_size}/{LOCAL_QUEUE_CAPACITY} workers busy)"

    # Simulate rate-limit check for OCR
    if task_type == "ocr_batch":
        return True, "Local OCR worker rate limit reached (1000 pages/min cap exceeded)"

    return False, "Local capacity available"


def simulate_queue_full():
    """Force bottleneck condition (used in demo)."""
    global _current_queue_size
    _current_queue_size = LOCAL_QUEUE_CAPACITY


def simulate_queue_available():
    """Reset to available (used in tests)."""
    global _current_queue_size
    _current_queue_size = 0
