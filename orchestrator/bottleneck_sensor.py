"""
bottleneck_sensor.py — Real Local Capacity & Bottleneck Sensor
---------------------------------------------------------------
Replaces staged static checks with inspection of the real 1-slot LocalExecutor.
"""
from typing import Tuple, Dict, Any
from orchestrator.local_executor import local_executor


def is_bottlenecked(task_deadline_sec: float = 3.0) -> Tuple[bool, str]:
    """
    Returns (is_bottlenecked: bool, reason: str).
    Inspects real local executor state:
      - If local slot is free: returns (False, reason) -> agent executes locally for $0.
      - If local slot is occupied: returns (True, reason) -> agent outsources to broker.
    """
    bottlenecked, reason, _ = local_executor.check_bottleneck(task_deadline_sec=task_deadline_sec)
    return bottlenecked, reason


def get_local_executor_metrics() -> Dict[str, Any]:
    """Returns current real executor status and metrics."""
    return local_executor.get_status()
