"""
orchestrator/policy.py — Autonomous Policy Enforcement Engine
--------------------------------------------------------------
Enforces spend caps, allowed task types, and human approval thresholds
before any Job Request Package (JRP) is posted to the open market.
"""
import os
import yaml
import sqlite3
import datetime
from typing import Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()

POLICY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "bounty_policy.yaml"))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ledger.db"))


def load_policy() -> Dict[str, Any]:
    """Loads bounty governance policy from YAML config."""
    default_policy = {
        "weekly_spend_cap_usd": 25.00,
        "allowed_task_types": ["code_bounty", "document_ocr", "llm_synthesis"],
        "approval_threshold_usd": 5.00,
    }
    if not os.path.exists(POLICY_FILE):
        return default_policy

    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return {**default_policy, **data}


def get_weekly_settled_and_reserved_usd() -> float:
    """Calculates total spend committed in the past 7 days from SQLite ledger."""
    if not os.path.exists(DB_PATH):
        return 0.0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(bid_usd), 0.0)
        FROM ledger
        WHERE status IN ('SETTLED', 'RESERVED')
          AND datetime(timestamp) >= datetime('now', '-7 days')
    """)
    row = cur.fetchone()
    total_spent = float(row[0]) if row else 0.0
    conn.close()
    return total_spent


def evaluate_bounty_policy(task_type: str, max_bid_usd: float) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Evaluates proposed bounty against governance rules:
      1. Task Type Whitelist: Must be an allowed capability.
      2. Weekly Spend Cap: Settled + reserved + proposed <= weekly_spend_cap.
      3. Approval Threshold: Bounties <= threshold are AUTONOMOUS_APPROVED;
         bounties > threshold require human approval.
    """
    policy = load_policy()
    allowed_types = policy.get("allowed_task_types", [])
    spend_cap = float(policy.get("weekly_spend_cap_usd", 25.00))
    threshold = float(policy.get("approval_threshold_usd", 5.00))

    weekly_spent = get_weekly_settled_and_reserved_usd()
    remaining_cap = max(0.0, spend_cap - weekly_spent)

    # 1. Whitelist Check
    if task_type not in allowed_types:
        return False, "POLICY_REJECTED", {
            "reason": f"Task type '{task_type}' is not in allowed types: {allowed_types}",
            "task_type": task_type,
            "allowed_task_types": allowed_types,
        }

    # 2. Spend Cap Check
    if (weekly_spent + max_bid_usd) > spend_cap:
        return False, "POLICY_REJECTED", {
            "reason": f"Weekly spend cap exceeded. Spent: ${weekly_spent:.2f}, Proposed: ${max_bid_usd:.2f}, Cap: ${spend_cap:.2f}",
            "weekly_spent_usd": weekly_spent,
            "proposed_bid_usd": max_bid_usd,
            "weekly_spend_cap_usd": spend_cap,
            "remaining_cap_usd": remaining_cap,
        }

    # 3. Approval Threshold Check
    if max_bid_usd > threshold:
        return True, "REQUIRES_HUMAN_APPROVAL", {
            "reason": f"Bounty amount ${max_bid_usd:.2f} exceeds autonomous threshold of ${threshold:.2f}",
            "proposed_bid_usd": max_bid_usd,
            "approval_threshold_usd": threshold,
            "remaining_cap_usd": remaining_cap,
        }

    return True, "AUTONOMOUS_APPROVED", {
        "reason": f"Bounty compliant with policy. Within ${spend_cap:.2f} cap and under ${threshold:.2f} threshold.",
        "proposed_bid_usd": max_bid_usd,
        "weekly_spent_usd": weekly_spent,
        "remaining_cap_usd": remaining_cap,
        "weekly_spend_cap_usd": spend_cap,
    }

