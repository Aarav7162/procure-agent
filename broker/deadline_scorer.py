"""
broker/deadline_scorer.py — Continuous Clamped Lambda Scorer for Deadline Utility
---------------------------------------------------------------------------------
Evaluates candidate bids under deadline pressure using normalized weights:
  • lambda_t = clamp((T_max - deadline_sec) / (T_max - T_min), 0.0, 1.0)
  • T_min = 6.0s (achievable tight deadline), T_max = 30.0s (achievable loose deadline)
  • W_rep   = 0.20
  • W_speed = 0.80 * lambda_t
  • W_price = 0.80 * (1.0 - lambda_t)
  • Weight Normalization Invariant: W_speed + W_price + W_rep = 1.000 (identically 1.0 for all lambda_t)
Scores candidate bids using measured historical latency and token-derived prices.
"""
from typing import List, Dict, Any

T_MIN = 6.0   # Achievable tight turnaround time (seconds)
T_MAX = 30.0  # Achievable relaxed turnaround time (seconds)


def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, val))


def compute_lambda(deadline_sec: float) -> float:
    """Computes urgency weight lambda_t in [0.0, 1.0] over [T_MIN, T_MAX]."""
    raw_lambda = (T_MAX - deadline_sec) / (T_MAX - T_MIN)
    return round(clamp(raw_lambda, 0.0, 1.0), 4)


def score_bids_with_deadline(bids: List[Dict[str, Any]], deadline_sec: float) -> List[Dict[str, Any]]:
    """
    Evaluates bids under deadline pressure using strictly normalized weights summing to 1.000.
    Speed scores use measured latency.
    """
    valid = [b for b in bids if b.get("status") == "BID"]
    rejected = [b for b in bids if b.get("status") != "BID"]

    if not valid:
        return rejected

    lambda_t = compute_lambda(deadline_sec)

    # Normalized weights invariant: W_speed + W_price + W_rep == 1.000
    w_rep = 0.20
    w_speed = round(0.80 * lambda_t, 4)
    w_price = round(0.80 * (1.0 - lambda_t), 4)

    # Verify weight normalization invariant
    total_weights = round(w_speed + w_price + w_rep, 4)
    assert abs(total_weights - 1.0) < 1e-6, f"Weights must sum to 1.000! Got {total_weights}"

    max_price = max(b.get("bid_usd", 1.0) for b in valid) or 1.0
    # Use measured latency if present; otherwise fallback to estimated
    max_seconds = max(b.get("measured_latency", b.get("estimated_seconds", 5.0)) for b in valid) or 1.0

    scored = []
    for b in valid:
        worker_id = b.get("worker_id")
        rep_score = b.get("reputation_score")
        if worker_id and rep_score is None:
            try:
                from orchestrator.reputation import get_worker_reputation
                rep = get_worker_reputation(worker_id)
                rep_score = rep["reputation_score"]
                b["reputation_score"] = rep_score
                b["sample_size_n"] = rep.get("n_samples", 0)
                if "measured_latency" not in b and rep.get("avg_latency_recent_10", 0) > 0:
                    b["measured_latency"] = rep["avg_latency_recent_10"]
            except Exception:
                rep_score = 0.5
        elif rep_score is None:
            rep_score = 0.5

        bid_usd = b.get("bid_usd", max_price)
        latency = b.get("measured_latency", b.get("estimated_seconds", max_seconds))

        price_score = round(1.0 - (bid_usd / (max_price * 1.25)), 4)
        speed_score = round(1.0 - (latency / (max_seconds * 1.25)), 4)

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
                "sum_weights": total_weights,
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

