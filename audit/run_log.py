"""
audit/run_log.py — Unified Audit & Execution Log
------------------------------------------------
Maintains audit/run_log.jsonl as the single source of truth for:
  • Every benchmark, test, and live task execution
  • Exact timestamp, worker_id, model, pass/fail status, latency (s), token_cost ($), source_script
  • Bayesian reputation and rolling speed scores computed exclusively from this log
  • Sample size (N) tracked and displayed per worker
"""
import os
import json
import datetime
from typing import List, Dict, Any, Optional

RUN_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_log.jsonl"))

ALPHA_PRIOR = 2.0
BETA_PRIOR = 1.0


def append_run_log(
    worker_id: str,
    model: str,
    pass_fail: str,
    latency: float,
    token_cost: float,
    source_script: str,
    timestamp: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Appends an execution record to audit/run_log.jsonl."""
    os.makedirs(os.path.dirname(RUN_LOG_PATH), exist_ok=True)
    if not timestamp:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entry = {
        "timestamp": timestamp,
        "worker_id": worker_id,
        "model": model,
        "pass_fail": pass_fail.upper(),  # 'PASS' or 'FAIL'
        "latency_sec": round(float(latency), 4),
        "token_cost_usd": round(float(token_cost), 6),
        "source_script": source_script,
    }
    if notes:
        entry["notes"] = notes

    with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def get_all_run_logs(worker_id: Optional[str] = None, exclude_backfilled: bool = False) -> List[Dict[str, Any]]:
    """Reads all run logs, optionally filtering by worker_id and backfilled status."""
    if not os.path.exists(RUN_LOG_PATH):
        return []

    records = []
    with open(RUN_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if exclude_backfilled and "backfilled" in rec.get("notes", "").lower():
                    continue
                if worker_id is None or rec.get("worker_id") == worker_id:
                    records.append(rec)
            except Exception:
                continue
    return records


def get_run_counts_by_source() -> Dict[str, Dict[str, int]]:
    """Returns run counts by worker and source script, categorizing backfilled vs live."""
    records = get_all_run_logs(exclude_backfilled=False)
    summary: Dict[str, Dict[str, int]] = {}
    for r in records:
        wid = r.get("worker_id", "unknown")
        src = r.get("source_script", "unknown")
        notes = r.get("notes", "")
        key = f"{src} [backfilled]" if "backfilled" in notes.lower() else f"{src} [live]"
        if wid not in summary:
            summary[wid] = {}
        summary[wid][key] = summary[wid].get(key, 0) + 1
    return summary


def compute_worker_metrics_from_log(worker_id: str, exclude_backfilled: bool = True) -> Dict[str, Any]:
    """
    Computes reputation (Bayesian Beta), latency, and sample size N
    strictly from audit/run_log.jsonl.
    By default excludes backfilled rows so scores reflect fresh live benchmark runs.
    """
    records = get_all_run_logs(worker_id=worker_id, exclude_backfilled=exclude_backfilled)
    all_records = get_all_run_logs(worker_id=worker_id, exclude_backfilled=False)
    n = len(records)

    passes = sum(1 for r in records if r.get("pass_fail") == "PASS")
    failures = sum(1 for r in records if r.get("pass_fail") == "FAIL")

    alpha = ALPHA_PRIOR + passes
    beta = BETA_PRIOR + failures
    reputation_score = round(alpha / (alpha + beta), 4)

    latencies = [r.get("latency_sec", 0.0) for r in records if r.get("latency_sec") is not None]
    avg_latency = round(sum(latencies) / len(latencies), 4) if latencies else 0.0

    # Rolling average of last 10 runs
    recent_10 = latencies[-10:] if latencies else []
    recent_avg_latency = round(sum(recent_10) / len(recent_10), 4) if recent_10 else avg_latency

    costs = [r.get("token_cost_usd", 0.0) for r in records if r.get("token_cost_usd") is not None]
    avg_cost = round(sum(costs) / len(costs), 6) if costs else 0.0

    return {
        "worker_id": worker_id,
        "n_samples": n,
        "total_records_with_backfill": len(all_records),
        "backfilled_count": len(all_records) - n,
        "passes": passes,
        "failures": failures,
        "pass_rate": round(passes / n, 4) if n > 0 else 0.0,
        "alpha": alpha,
        "beta": beta,
        "reputation_score": reputation_score,
        "avg_latency_all": avg_latency,
        "avg_latency_recent_10": recent_avg_latency,
        "avg_token_cost": avg_cost,
        "is_cold_start": n < 3,
        "allocation_cap_usd": 1.00 if n < 3 else 15.00
    }

