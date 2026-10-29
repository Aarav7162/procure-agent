"""
broker/bid_scorer.py — Scores and sorts bids by composite score (price + reputation)
"""


def score_bids(bids: list[dict]) -> list[dict]:
    """
    Score valid bids: lower price × higher reputation = higher score.
    Rejections pass through unsorted.
    """
    valid = [b for b in bids if b.get("status") == "BID"]
    rejected = [b for b in bids if b.get("status") != "BID"]

    if not valid:
        return rejected

    max_price = max(b["bid_usd"] for b in valid) or 1

    for b in valid:
        price_score = 1 - (b["bid_usd"] / max_price)        # lower price = higher score
        reputation = b.get("reputation_score", 0.5)
        b["composite_score"] = round(0.7 * price_score + 0.3 * reputation, 4)

    valid.sort(key=lambda b: b["composite_score"], reverse=True)
    return valid + rejected
