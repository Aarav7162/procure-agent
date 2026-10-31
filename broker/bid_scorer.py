"""
broker/bid_scorer.py — Scores and sorts bids by composite score (price + Bayesian reputation)
-----------------------------------------------------------------------------------------------
Integrates with orchestrator/reputation.py to score bids:
  • Queries dynamic Beta(2,1) reputation score.
  • Enforces cold-start allocation cap ($1.00 max for unproven workers with < 3 attempts).
  • Composite Score = 0.7 * (1 - price/max_price) + 0.3 * reputation_score.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator.reputation import get_worker_reputation


from broker.deadline_scorer import score_bids_with_deadline


def score_bids(bids: list[dict], deadline_sec: float = 30.0) -> list[dict]:
    """
    Score valid bids using unified continuous lambda deadline scorer.
    Enforces cold-start allocation cap and clamps speed score at 0.
    """
    return score_bids_with_deadline(bids, deadline_sec=deadline_sec)
