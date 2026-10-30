"""
tests/test_public_billing.py — Public Test Suite for Billing Engine
-------------------------------------------------------------------
These tests are public and provided to candidate worker agents in the JRP.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from billing import calculate_next_billing_date, prorate_subscription


def test_standard_monthly_rollover():
    """Standard mid-month rollover within same year."""
    assert calculate_next_billing_date("2026-03-15", 1) == "2026-04-15"
    assert calculate_next_billing_date("2026-05-10", 2) == "2026-07-10"


def test_standard_year_boundary():
    """Standard rollover crossing year boundary."""
    assert calculate_next_billing_date("2026-11-20", 3) == "2027-02-20"


def test_standard_proration():
    """Standard proration calculation."""
    assert prorate_subscription(1000, 15, 30) == 500
    assert prorate_subscription(3000, 10, 30) == 1000
    assert prorate_subscription(5000, 0, 30) == 0
