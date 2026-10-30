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


def score_bids(bids: list[dict]) -> list[dict]:
    """
    Score valid bids: lower price × higher reputation = higher score.
    Enforces cold-start allocation cap.
    """
    valid = []
    rejected = []

    for b in bids:
        if b.get("status") != "BID":
            rejected.append(b)
            continue

        worker_id = b.get("worker_id")
        rep = get_worker_reputation(worker_id)
        b["reputation_score"] = rep["reputation_score"]
        b["allocation_cap_usd"] = rep["allocation_cap_usd"]
        b["is_cold_start"] = rep["is_cold_start"]
        b["sample_size_n"] = rep.get("n_samples", 0)
        if "avg_latency_recent_10" in rep and rep["avg_latency_recent_10"] > 0:
            b["measured_latency"] = rep["avg_latency_recent_10"]

        # Enforce cold-start allocation cap
        if b.get("bid_usd", 0.0) > rep["allocation_cap_usd"]:
            b["status"] = "REJECTED_OVER_ALLOCATION_CAP"
            b["rejection_reason"] = f"Bid ${b['bid_usd']:.2f} exceeds cold-start cap ${rep['allocation_cap_usd']:.2f}"
            rejected.append(b)
        else:
            valid.append(b)

    if not valid:
        return rejected

    max_price = max(b["bid_usd"] for b in valid) or 1.0

    for b in valid:
        price_score = 1.0 - (b["bid_usd"] / max_price)        # lower price = higher score
        reputation = b["reputation_score"]
        b["composite_score"] = round(0.7 * price_score + 0.3 * reputation, 4)

    valid.sort(key=lambda b: b["composite_score"], reverse=True)
    return valid + rejected
