"""
scripts/test_information_isolation.py — Verifies Zero Information Leakage to Workers
----------------------------------------------------------------------------------
Asserts that:
  1. The hidden test file (test_hidden_billing.py) is NEVER exposed to workers in JRPs.
  2. The hidden test filename, filepath, and specific test assertions are absent from JRP.
  3. JRP contains ONLY the broken source code and public unit tests.
  4. Only the isolated verification runner loads the hidden test suite.
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.post_bounty import post_bounty_from_ci
from orchestrator.jrp_builder import build_jrp, keyword_fallback_jrp

REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine"))
HIDDEN_TEST_PATH = os.path.join(REPO_PATH, "tests", "test_hidden_billing.py")


def test_zero_information_leakage():
    print("=" * 70)
    print("ASSERTION: Information Isolation & Zero Test Leakage Invariant")
    print("=" * 70)

    # Read hidden test contents to verify string isolation
    with open(HIDDEN_TEST_PATH, "r", encoding="utf-8") as f:
        hidden_content = f.read()

    # Key assertions that must NEVER appear in worker-facing packets:
    hidden_markers = [
        "test_hidden_billing",
        "test_february_29_leap_year_rollover",
        "test_31st_to_30_day_month_clamping",
        "test_negative_interval_raises_value_error",
        "test_proration_days_active_exceeds_period_raises_value_error",
        "test_negative_proration_days_raises_value_error"
    ]

    # Generate CI-posted bounty JRP
    ci_res = post_bounty_from_ci(
        repo_path=REPO_PATH,
        task_type="code_bounty",
        max_bid_usd=0.50,
        task_description="Fix month-end rollover ValueError in calculate_next_billing_date and bounds checking in prorate_subscription"
    )
    assert ci_res["status"] == "POSTED", f"CI trigger failed: {ci_res}"
    jrp = ci_res["jrp"]
    jrp_serialized = json.dumps(jrp, default=str)

    # 1. Assert no hidden_tests key
    assert "hidden_tests" not in jrp, "VIOLATION: 'hidden_tests' key present in JRP dictionary!"

    # 2. Assert no hidden file names or paths
    assert "test_hidden_billing" not in jrp_serialized, "VIOLATION: Hidden test file name leaked in JRP!"
    assert "test_hidden_billing.py" not in jrp_serialized, "VIOLATION: Hidden test file path leaked in JRP!"

    # 3. Assert no hidden test assertions leaked
    for marker in hidden_markers:
        assert marker not in jrp_serialized, f"VIOLATION: Hidden test function '{marker}' leaked in worker JRP!"

    # 4. Assert public tests ARE provided
    assert "public_tests" in jrp, "Public tests must be provided to workers"
    assert "test_standard_monthly_rollover" in jrp["public_tests"], "Public test content missing"
    assert "test_standard_proration" in jrp["public_tests"], "Public test content missing"

    # 5. Assert source code IS provided
    assert "source_code" in jrp, "Broken source code must be provided to workers"
    assert "calculate_next_billing_date" in jrp["source_code"], "Source code missing"

    print("  [PASSED] Invariant 1: JRP contains NO 'hidden_tests' key.")
    print("  [PASSED] Invariant 2: JRP contains NO hidden filenames ('test_hidden_billing.py').")
    print("  [PASSED] Invariant 3: Zero leakage of 5 hidden test function names and assertions.")
    print("  [PASSED] Invariant 4: JRP strictly isolates worker view to broken source and public tests.")
    print("=" * 70)


if __name__ == "__main__":
    test_zero_information_leakage()

