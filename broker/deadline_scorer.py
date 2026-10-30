"""
broker/deadline_scorer.py — Continuous Clamped Lambda Scorer for Deadline Utility
---------------------------------------------------------------------------------
Replaces hardcoded thresholds with a mathematically rigorous utility function:
  • lambda_t = clamp((T_max - deadline_sec) / (T_max - T_min), 0.0, 1.0)
  • W_speed = 0.40 * lambda_t
  • W_price = 0.40 * (1.0 - lambda_t)
  • W_rep   = 0.20 + 0.20 * (1.0 - lambda_t)
Scores candidate bids and outputs computed breakdown per bidder in the event stream.
"""
from typing import List, Dict, Any

T_MIN = 1.0   # Fastest turnaround time (seconds)
T_MAX = 10.0  # Relaxed turnaround time (seconds)


def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


def compute_lambda(deadline_sec: float) -> float:
    """Computes urgency weight lambda_t in [0.0, 1.0]."""
    raw_lambda = (T_MAX - deadline_sec) / (T_MAX - T_MIN)
    return round(clamp(raw_lambda, 0.0, 1.0), 4)


def score_bids_with_deadline(bids: List[Dict[str, Any]], deadline_sec: float) -> List[Dict[str, Any]]:
    """
    Evaluates bids under deadline pressure using continuous clamped lambda weights.
    Returns ranked bids with detailed score breakdown for event stream display.
    """
    valid = [b for b in bids if b.get("status") == "BID"]
    rejected = [b for b in bids if b.get("status") != "BID"]

    if not valid:
        return rejected

    lambda_t = compute_lambda(deadline_sec)

    # Dynamic weights
    w_speed = round(0.45 * lambda_t, 4)
    w_price = round(0.35 * (1.0 - lambda_t), 4)
    w_rep = round(0.20 + 0.15 * (1.0 - lambda_t), 4)

    max_price = max(b.get("bid_usd", 1.0) for b in valid) or 1.0
    max_seconds = max(b.get("estimated_seconds", 3.0) for b in valid) or 1.0

    scored = []
    for b in valid:
        bid_usd = b.get("bid_usd", max_price)
        est_sec = b.get("estimated_seconds", max_seconds)
        rep_score = b.get("reputation_score", 0.5)

        price_score = round(1.0 - (bid_usd / (max_price * 1.25)), 4)
        speed_score = round(1.0 - (est_sec / (max_seconds * 1.5)), 4)

        composite = round(
            w_price * price_score +
            w_speed * speed_score +
            w_rep * rep_score,
            4
        )

        scored_bid = {
            **b,
            "deadline_sec": deadline_sec,
            "lambda_t": lambda_t,
            "weights": {
                "w_price": w_price,
                "w_speed": w_speed,
                "w_rep": w_rep,
            },
            "component_scores": {
                "price_score": price_score,
                "speed_score": speed_score,
                "reputation_score": rep_score,
            },
            "composite_score": composite,
        }
        scored.append(scored_bid)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    return scored + rejected
