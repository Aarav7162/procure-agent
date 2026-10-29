"""
budget_manager.py — In-memory budget tracker per cycle, backed by atomic SQLite reservations
"""
from orchestrator.treasury import (
    get_budget_state,
    reserve_budget,
    release_reservation,
    MAX_BUDGET_USD,
)

class BudgetManager:
    def __init__(self, cycle_id: str, max_usd: float = MAX_BUDGET_USD):
        self.cycle_id = cycle_id
        self.max_usd = max_usd

    def state(self) -> dict:
        """Returns the source-of-truth state: spent, reserved, available, max."""
        return get_budget_state(self.cycle_id, self.max_usd)

    @property
    def spent(self) -> float:
        return self.state()["spent_usd"]

    @property
    def reserved(self) -> float:
        return self.state()["reserved_usd"]

    @property
    def remaining(self) -> float:
        return self.state()["available_usd"]

    def can_afford(self, amount: float) -> bool:
        return amount <= self.remaining

    def reserve(self, jrp_id: str, worker_id: str, amount: float) -> tuple[bool, str, str]:
        """Atomically reserve budget for an accepted bid."""
        return reserve_budget(self.cycle_id, jrp_id, worker_id, amount, self.max_usd)

    def release(self, reservation_id: str, reason: str = "Rejected") -> tuple[bool, str]:
        """Release a reservation if work fails or is rejected."""
        return release_reservation(reservation_id, reason)

    def summary(self) -> dict:
        return self.state()
