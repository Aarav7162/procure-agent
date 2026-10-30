"""
scripts/compute_deadline_scores_frozen.py
-----------------------------------------
Computes tight (6.0s) and loose (30.0s) deadline scores to four decimal places
across both:
  1. Rolling average latency basis (last 10 runs per model)
  2. All recorded runs latency basis (grand average)
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from audit.run_log import compute_worker_metrics_from_log
from broker.deadline_scorer import score_bids_with_deadline

def main():
    m120 = compute_worker_metrics_from_log("code-worker-01")
    m20  = compute_worker_metrics_from_log("code-worker-02")

    n120 = m120["n_samples"]
    n20  = m20["n_samples"]

    print("=" * 80)
    print("WORKER METRICS FROM AUDIT/RUN_LOG.JSONL")
    print("=" * 80)
    print(f"code-worker-01 (120B): N={n120}, Passes={m120['passes']}, Failures={m120['failures']}, PassRate={m120['pass_rate']:.4f}")
    print(f"  Reputation: {m120['reputation_score']:.4f} (Beta({m120['alpha']}, {m120['beta']}))")
    print(f"  All-runs Latency: {m120['avg_latency_all']:.4f}s | Recent-10 Latency: {m120['avg_latency_recent_10']:.4f}s")
    print(f"  Bid Price: $0.30 (Formula: raw_cost * 1.25 + $0.30 operating fee)")
    print()
    print(f"code-worker-02 (20B): N={n20}, Passes={m20['passes']}, Failures={m20['failures']}, PassRate={m20['pass_rate']:.4f}")
    print(f"  Reputation: {m20['reputation_score']:.4f} (Beta({m20['alpha']}, {m20['beta']}))")
    print(f"  All-runs Latency: {m20['avg_latency_all']:.4f}s | Recent-10 Latency: {m20['avg_latency_recent_10']:.4f}s")
    print(f"  Bid Price: $0.22 (Formula: raw_cost * 1.25 + $0.22 operating fee)")
    print()
    print(f"rogue-worker-01: Adversarial Fixture (Fresh worker)")
    print(f"  Reputation: 0.6667 (Beta(2, 1) prior)")
    print(f"  Latency: 1.0000s")
    print(f"  Bid Price: $0.18 (Formula: round(max(0.15, min(0.20, 0.50 * 0.36)), 2))")
    print("=" * 80)

    bases = [
        ("BASIS 1: Recent 10 Runs Rolling Latency", m120['avg_latency_recent_10'], m20['avg_latency_recent_10']),
        ("BASIS 2: All Recorded Runs Grand Average Latency", m120['avg_latency_all'], m20['avg_latency_all'])
    ]

    for label, lat120, lat20 in bases:
        print(f"\n{'='*80}\n{label}\n{'='*80}")
        bids = [
            {
                "worker_id": "code-worker-01",
                "name": "Python Code Gen (120B)",
                "status": "BID",
                "bid_usd": 0.30,
                "measured_latency": lat120,
                "reputation_score": m120["reputation_score"],
                "sample_size_n": n120
            },
            {
                "worker_id": "code-worker-02",
                "name": "Fast Code Gen (20B)",
                "status": "BID",
                "bid_usd": 0.22,
                "measured_latency": lat20,
                "reputation_score": m20["reputation_score"],
                "sample_size_n": n20
            },
            {
                "worker_id": "rogue-worker-01",
                "name": "Rogue Worker Fixture",
                "status": "BID",
                "bid_usd": 0.18,
                "measured_latency": 1.00,
                "reputation_score": 0.6667,
                "sample_size_n": 0
            }
        ]

        for d in [6.0, 30.0]:
            tag = "TIGHT DEADLINE (6.0s)" if d == 6.0 else "LOOSE DEADLINE (30.0s)"
            scored = score_bids_with_deadline(bids, deadline_sec=d)
            print(f"\n--- {tag} (lambda_t = {scored[0]['lambda_t']:.2f}) ---")
            w = scored[0]["weights"]
            print(f"Weights: W_speed={w['w_speed']:.2f}, W_price={w['w_price']:.2f}, W_rep={w['w_rep']:.2f}")
            for r, b in enumerate(scored, 1):
                c = b["component_scores"]
                win = " <-- WINNER" if r == 1 else ""
                print(f"  #{r} {b['worker_id']:<15} (N={b['sample_size_n']:<2}) | Bid: ${b['bid_usd']:.2f} | Lat: {b['measured_latency']:.4f}s | Rep: {b['reputation_score']:.4f} || S_p={c['price_score']:.4f}, S_spd={c['speed_score']:.4f}, S_rep={c['reputation_score']:.4f} => Composite: {b['composite_score']:.4f}{win}")

        print(f"\n--- HONEST WORKERS HEAD-TO-HEAD ({label}) ---")
        honest_bids = [b for b in bids if "rogue" not in b["worker_id"]]
        for d in [6.0, 30.0]:
            tag = "TIGHT (6.0s)" if d == 6.0 else "LOOSE (30.0s)"
            h_scored = score_bids_with_deadline(honest_bids, deadline_sec=d)
            w1 = h_scored[0]
            w2 = h_scored[1]
            print(f"  [{tag}] 1st: {w1['worker_id']} ({w1['composite_score']:.4f}) vs 2nd: {w2['worker_id']} ({w2['composite_score']:.4f}) | Diff = {w1['composite_score'] - w2['composite_score']:.4f}")


if __name__ == "__main__":
    main()
