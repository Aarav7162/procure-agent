"""
tests/test_hidden_billing.py — Hidden Edge-Case Test Suite for Billing Engine
-----------------------------------------------------------------------------
These tests are NEVER provided to candidate workers in the JRP.
They evaluate adversarial/flawed submissions on month-end edge cases and invariants.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from billing import calculate_next_billing_date, prorate_subscription


def test_month_end_january_to_february():
    """Jan 31 + 1 month must clamp to Feb 28 in non-leap year (2026)."""
    assert calculate_next_billing_date("2026-01-31", 1) == "2026-02-28"


def test_month_end_31_to_30():
    """March 31 + 1 month must clamp to April 30."""
    assert calculate_next_billing_date("2026-03-31", 1) == "2026-04-30"


def test_leap_year_rollover():
    """Feb 29 on leap year + 12 months must clamp to Feb 28."""
    assert calculate_next_billing_date("2024-02-29", 12) == "2025-02-28"


def test_invalid_interval_rejected():
    """Interval <= 0 must raise ValueError."""
    try:
        calculate_next_billing_date("2026-03-15", 0)
        assert False, "Zero interval should raise ValueError"
    except ValueError:
        pass


def test_invalid_proration_days_rejected():
    """days_active > days_in_period must raise ValueError."""
    try:
        prorate_subscription(1000, 35, 30)
        assert False, "Over-period active days should raise ValueError"
    except ValueError:
        pass
