"""
scripts/post_bounty.py — Simulated CI Trigger for Autonomous Bounty Posting
----------------------------------------------------------------------------
Simulates a CI/CD pipeline webhook (e.g. GitHub Actions failure trigger).
When a test fails, this script:
  1. Inspects the repository and verifies test failure.
  2. Evaluates the procurement policy (weekly spend cap, allowed task types, approval threshold).
  3. Formulates a Job Request Package (JRP) with public test assertions.
  4. Posts the bounty to the ProcureAgent market.
"""
import os
import sys
import json
import uuid
import time
import argparse
import subprocess
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator.policy import evaluate_bounty_policy


def run_repo_tests(repo_dir: str) -> Dict[str, Any]:
    """Runs repository tests in a subprocess to detect failures."""
    test_path = os.path.join(repo_dir, "tests")
    res = subprocess.run(
        [sys.executable, "-m", "pytest", test_path],
        capture_output=True,
        text=True,
        timeout=15.0
    )
    return {
        "exit_code": res.returncode,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "has_failures": (res.returncode != 0),
    }


def post_bounty_from_ci(
    repo_path: str,
    task_type: str = "code_bounty",
    max_bid_usd: float = 0.50,
    task_description: str = "Fix month-end rollover ValueError in calculate_next_billing_date",
) -> Dict[str, Any]:
    """Evaluates CI failure and formulates policy-governed bounty JRP."""
    print("=" * 70)
    print("PROCUREAGENT: Simulated CI Trigger (Autonomous Bounty Poster)")
    print("=" * 70)
    print(f"  Target Repository : {repo_path}")
    print(f"  Task Capability   : {task_type}")
    print(f"  Max Bounty Budget : ${max_bid_usd:.2f} USD")

    # 1. Verify failure
    test_res = run_repo_tests(repo_path)
    if not test_res["has_failures"]:
        print("  [CI RESULT] All tests passed! No bounty needed.")
        return {"status": "NO_BOUNTY_NEEDED", "message": "All repository tests passed."}

    print("  [CI RESULT] Test suite failed! Preparing autonomous capability procurement...")

    # 2. Evaluate Policy
    allowed, decision, details = evaluate_bounty_policy(task_type, max_bid_usd)
    print(f"  [POLICY CHECK] Decision: {decision}")
    print(f"                 Reason: {details.get('reason')}")

    if not allowed or decision == "POLICY_REJECTED":
        return {
            "status": "POLICY_REJECTED",
            "decision": decision,
            "details": details,
        }

    if decision == "REQUIRES_HUMAN_APPROVAL":
        return {
            "status": "REQUIRES_HUMAN_APPROVAL",
            "decision": decision,
            "details": details,
        }

    # 3. Read Public Test Code
    public_test_file = os.path.join(repo_path, "tests", "test_public_billing.py")
    public_tests_content = ""
    if os.path.exists(public_test_file):
        with open(public_test_file, "r", encoding="utf-8") as f:
            public_tests_content = f.read()

    # Read Source Code to repair
    source_file = os.path.join(repo_path, "billing.py")
    source_content = ""
    if os.path.exists(source_file):
        with open(source_file, "r", encoding="utf-8") as f:
            source_content = f.read()

    jrp_id = f"bounty_{uuid.uuid4().hex[:12]}"
    jrp = {
        "jrp_id": jrp_id,
        "task_type": task_type,
        "task_description": task_description,
        "repo_path": repo_path,
        "source_code": source_content,
        "public_tests": public_tests_content,
        "max_bid_usd": max_bid_usd,
        "required_capabilities": ["code_generation", "python_debugging"],
        "policy_approval": details,
        "status": "OPEN_FOR_BIDS",
        "created_at": time.time(),
    }

    print(f"  [JRP POSTED] JRP ID: {jrp_id}")
    print(f"               Max Bid: ${max_bid_usd:.2f}")
    print(f"               Status: OPEN_FOR_BIDS")
    print("=" * 70)
    return {
        "status": "POSTED",
        "jrp": jrp,
        "decision": decision,
        "details": details,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProcureAgent Simulated CI Trigger")
    parser.add_argument("--repo-path", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_repos", "billing_engine")))
    parser.add_argument("--task-type", default="code_bounty")
    parser.add_argument("--max-bid", type=float, default=0.50)
    parser.add_argument("--description", default="Fix month-end rollover ValueError in calculate_next_billing_date")

    args = parser.parse_args()
    res = post_bounty_from_ci(args.repo_path, args.task_type, args.max_bid, args.description)
    print(json.dumps(res, indent=2, default=str))

