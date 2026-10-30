"""
billing.py — Subscription Billing Cycle & Proration Engine
----------------------------------------------------------
Handles subscription cycle date offsets and proration accounting.
"""
from datetime import datetime


def calculate_next_billing_date(start_date_str: str, interval_months: int = 1) -> str:
    """
    Calculates the next billing date given an ISO date string (YYYY-MM-DD)
    and interval in months.
    
    Known Defect: Naively creates datetime with dt.day, failing on month-end rollovers
    (e.g. Jan 31 -> Feb 31 raises ValueError).
    """
    dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    year = dt.year + (dt.month + interval_months - 1) // 12
    month = (dt.month + interval_months - 1) % 12 + 1
    # Defect: day is unconstrained against target month length
    next_dt = datetime(year, month, dt.day)
    return next_dt.strftime("%Y-%m-%d")


def prorate_subscription(amount_cents: int, days_active: int, days_in_period: int) -> int:
    """
    Calculates prorated billing amount in integer cents.
    """
    # Defect: lacks bounds checking for days_active > days_in_period
    return int(round((amount_cents * days_active) / days_in_period))

