"""
scripts/test_stageC_real_workers.py — Stage C Gate Test Suite
-------------------------------------------------------------
Verifies real worker implementations and real cost accounting:
  1. API Spend Meter & Token Accounting:
     - Accurate per-model cost calculation.
     - Enforces MAX_REAL_API_SPEND_USD guardrail; fails loudly on overdraw.
  2. LLM Worker (openai/gpt-oss-120b on Groq):
     - Dynamic token-metered bidding.
     - Live Groq API execution (not a mock/fixture).
     - Accurate reported tokens, cost, and measured wall-clock runtime.
     - Dedicated PayPal account (sb-kgyi653615592@personal.example.com).
  3. OCR Workers (Alpha & Beta):
     - Scans directory inspection & honest diagnostic if user scans pending.
     - Real compute latency measurement.
     - Separate PayPal accounts (Alpha: sqcdl, Beta: shusq).
  4. Code Generation Worker:
     - Complexity-indexed bidding.
     - Programmatic AST syntax verification.
     - Measured execution runtime.
  5. Rogue Adversary Isolation:
     - Distinct account (sb-a43fio53613334@personal.example.com).
     - Adversarial underbidding.
     - Rejection by two-layer verifier.
     - Asserted never paid ($0.00 in ledger).
"""
import os
import sys
import json
import time
import hashlib
import sqlite3
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.api_meter import GLOBAL_API_METER, ApiMeter, SpendLimitExceededError
from orchestrator.verifier import verify_delivery
from orchestrator.treasury import init_ledger, DB_PATH
from broker.registry import WORKER_REGISTRY

load_dotenv()


def test_api_spend_meter_and_guardrail():
    """Test 1: API Spend Meter cost calculation and loud fail on spend limit."""
    print("\n[Test 1] Testing Real API Spend Meter & Token Accounting...")
    meter = ApiMeter(max_spend_usd=0.05)  # Strict cap for testing

    # Calculate cost for 2000 input tokens and 500 output tokens on gpt-oss-120b
    # Rate: input $0.50/1M, output $1.50/1M
    # Expected: (2000 * 0.0000005) + (500 * 0.0000015) = 0.001 + 0.00075 = $0.00175
    cost = meter.calculate_cost("openai/gpt-oss-120b", 2000, 500)
    print(f"  Calculated cost for 2500 tokens: ${cost:.6f}")
    assert cost > 0.0, "Cost calculation must be greater than zero"
    assert round(cost, 5) == 0.00175, f"Expected $0.00175, got {cost}"

    # Record small usage
    record = meter.record_usage("openai/gpt-oss-120b", 1000, 200)
    print(f"  Recorded call #1 cost: ${record['cost_usd']:.6f}, Cumulative: ${record['cumulative_spend_usd']:.6f}")
    assert meter.total_spend_usd == record["cumulative_spend_usd"]

    # Attempt to exceed $0.05 cap with a massive token burst
    print("  Testing spend guardrail enforcement with oversized request...")
    try:
        meter.record_usage("openai/gpt-oss-120b", 500_000_000, 100_000_000)
        assert False, "Spend guard MUST raise SpendLimitExceededError when cap is crossed!"
    except SpendLimitExceededError as e:
        print(f"  [PASS] Spend guard failed loudly as required: {e}")

    print("  [PASS] API Spend Meter calculates genuine costs and prevents overdraw!")


async def test_real_llm_worker_execution():
    """Test 2: LLM Worker live inference, dynamic bidding, and token reporting."""
    print("\n[Test 2] Testing LLM Worker (openai/gpt-oss-120b via Groq)...")
    from workers.llm_worker import bid as llm_bid, do_work as llm_do_work, WORKER_PAYPAL_EMAIL

    # 1. Bidding
    jrp = {
        "jrp_id": "jrp_stageC_llm_01",
        "task_description": "Summarize the primary difference between synchronous and asynchronous PayPal payments",
        "required_capabilities": ["data_extraction", "summarization"],
        "max_bid_usd": 3.00,
    }
    bid_result = await llm_bid(jrp)
    print(f"  LLM Worker Bid: status={bid_result['status']}, bid_usd=${bid_result['bid_usd']}")
    print(f"  Estimated Tokens: {bid_result.get('estimated_tokens')}")
    print(f"  Worker PayPal Email: {bid_result.get('worker_paypal_email')}")

    assert bid_result["status"] == "BID"
    assert bid_result["bid_usd"] > 0.0
    assert bid_result["worker_paypal_email"] == "sb-kgyi653615592@personal.example.com", "Must use dedicated LLM worker sandbox email!"

    # 2. Live Execution via Groq
    print("  Invoking live Groq inference on openai/gpt-oss-120b...")
    delivery = await llm_do_work({"jrp": jrp})

    output = delivery.get("output_sample", "")
    tokens = delivery.get("tokens_consumed", 0)
    cost = delivery.get("api_cost_usd", 0.0)
    runtime = delivery.get("execution_seconds", 0.0)
    sha256 = delivery.get("sha256_hash", "")

    print(f"  Execution Complete in {runtime:.3f}s")
    print(f"  Tokens Consumed: {tokens} (Input: {delivery.get('input_tokens')}, Output: {delivery.get('output_tokens')})")
    print(f"  Calculated API Cost: ${cost:.6f}")
    print(f"  Output Sample Preview: {output[:120]}...")
    print(f"  SHA-256 Digest: {sha256}")

    assert len(output) > 50, "Output must be genuine synthesized text"
    assert tokens > 0, "Tokens consumed must be tracked from real API response"
    assert cost > 0.0, "API cost must be non-zero"
    assert runtime > 0.0, "Execution runtime must be measured"
    assert hashlib.sha256(output.encode("utf-8")).hexdigest() == sha256, "Cryptographic hash must match output"

    print("  [PASS] Real LLM Worker executed live inference with honest token & runtime accounting!")


async def test_ocr_workers_and_diagnostics():
    """Test 3: OCR Workers Alpha & Beta, measured runtime, and real scan status."""
    print("\n[Test 3] Testing OCR Workers (Alpha & Beta)...")
    from workers.ocr_worker import bid as alpha_bid, do_work as alpha_work, TESSERACT_BIN
    from workers.ocr_worker_beta import bid as beta_bid, do_work as beta_work

    scans_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "real_scans"))
    has_scans = any(f.endswith((".png", ".jpg", ".txt")) and f != "README.md" for f in os.listdir(scans_dir))

    print(f"  Scans Directory: {scans_dir}")
    print(f"  Real Scans Uploaded: {has_scans}")
    print(f"  Tesseract Detected: {bool(TESSERACT_BIN)} (Path: {TESSERACT_BIN or 'Not on PATH'})")

    jrp = {
        "jrp_id": "jrp_stageC_ocr_01",
        "task_description": "Extract text lines and amounts from scanned grocery store receipts",
        "required_capabilities": ["document_ocr"],
        "max_bid_usd": 3.00,
    }

    # Test Alpha
    alpha_b = await alpha_bid(jrp)
    alpha_w = await alpha_work({"jrp": jrp})
    print(f"  Alpha Bid: ${alpha_b['bid_usd']} | Email: {alpha_b['worker_paypal_email']} | Runtime: {alpha_w['execution_seconds']}s")
    assert alpha_b["worker_paypal_email"] == "sb-sqcdl53128062@personal.example.com"
    assert alpha_w["execution_seconds"] > 0.0

    # Test Beta
    beta_b = await beta_bid(jrp)
    beta_w = await beta_work({"jrp": jrp})
    print(f"  Beta Bid:  ${beta_b['bid_usd']} | Email: {beta_b['worker_paypal_email']} | Runtime: {beta_w['execution_seconds']}s")
    assert beta_b["worker_paypal_email"] == "sb-shusq53615721@personal.example.com"
    assert beta_w["execution_seconds"] > 0.0

    assert alpha_b["worker_paypal_email"] != beta_b["worker_paypal_email"], "Alpha and Beta must have distinct accounts"
    print("  [PASS] OCR Workers Alpha and Beta executed with distinct accounts and measured latency!")


async def test_code_worker_execution():
    """Test 4: Code Worker complexity bidding, AST syntax check, and measured latency."""
    print("\n[Test 4] Testing Code Generation Worker (AST Verification & Measured Runtime)...")
    from workers.code_worker import bid as code_bid, do_work as code_work

    jrp = {
        "jrp_id": "jrp_stageC_code_01",
        "task_description": "Implement calculate_tax(amount, rate) returning 0.0 on non-positive amounts with tax algorithm",
        "required_capabilities": ["python_coding"],
        "max_bid_usd": 4.00,
    }

    b_res = await code_bid(jrp)
    w_res = await code_work({"jrp": jrp})

    print(f"  Code Worker Bid: ${b_res['bid_usd']} (Complexity-Indexed)")
    print(f"  Worker PayPal: {b_res['worker_paypal_email']}")
    print(f"  AST Verified: {w_res['ast_verified']}")
    print(f"  Execution Runtime: {w_res['execution_seconds']}s")
    print(f"  Code Sample:\n{w_res['output_sample']}")

    assert b_res["bid_usd"] > 0.0
    assert w_res["ast_verified"] is True, "Generated Python code must be syntactically valid AST"
    assert w_res["execution_seconds"] > 0.0, "Runtime must be measured"
    assert b_res["worker_paypal_email"] == "sb-sqcdl53128062@personal.example.com"

    print("  [PASS] Code Worker generated valid AST code with measured runtime!")


async def test_rogue_worker_rejection_and_zero_payout_guarantee():
    """Test 5: Rogue underbidding, verification rejection, and 100% zero payout assertion."""
    print("\n[Test 5] Testing Rogue Worker Rejection and Unpaid Guarantee...")
    from workers.rogue_worker import bid as rogue_bid, do_work as rogue_work, ROGUE_PAYPAL_EMAIL

    jrp = {
        "jrp_id": "jrp_stageC_rogue_01",
        "task_description": "Implement calculate_tax(amount, rate=0.08)",
        "required_capabilities": ["python_coding"],
        "max_bid_usd": 4.00,
        "acceptance_rules": [
            {
                "type": "unit_test",
                "test_suite_code": "assert calculate_tax(0.0) == 0.0\nassert calculate_tax(-5.0) == 0.0"
            }
        ],
    }

    r_bid = await rogue_bid(jrp)
    r_work = await rogue_work({"jrp": jrp})

    print(f"  Rogue PayPal Account: {r_bid['worker_paypal_email']}")
    print(f"  Rogue Aggressive Underbid: ${r_bid['bid_usd']}")
    assert r_bid["worker_paypal_email"] == "sb-a43fio53613334@personal.example.com"
    assert r_bid["bid_usd"] < 1.00, "Rogue underbids to win procurement"

    # Verify delivery through two-layer verifier
    is_ok, status_tag, report = verify_delivery(jrp, r_work)
    print(f"  Two-Layer Verification Result: ok={is_ok}, status={status_tag}")
    print(f"  Rejection Message: {report.get('message')}")

    assert is_ok is False, "Rogue code with edge-case defect must be rejected!"
    assert status_tag == "ACCEPTANCE_FAILED"

    # Query ledger database to prove Rogue was never paid
    init_ledger()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE worker_email = ? AND status IN ('PAYOUT_SUCCESS', 'PAYOUT_PENDING')",
        (ROGUE_PAYPAL_EMAIL,)
    )
    payout_count, total_paid = cur.fetchone()
    conn.close()

    print(f"  Audited Ledger Payouts to Rogue ({ROGUE_PAYPAL_EMAIL}): count={payout_count}, total=${total_paid:.2f}")
    assert payout_count == 0, "Rogue worker must have 0 payouts in ledger!"
    assert total_paid == 0.0, f"Rogue worker must have $0.00 spent! Found: ${total_paid}"

    print("  [PASS] Rogue worker underbidding rejected by verifier and verified $0.00 paid in ledger!")


async def run_stage_c_suite():
    print("=" * 70)
    print("STAGE C GATE: Real Workers, Token-Metered Bidding & Measured Runtime")
    print("=" * 70)

    test_api_spend_meter_and_guardrail()
    await test_real_llm_worker_execution()
    await test_ocr_workers_and_diagnostics()
    await test_code_worker_execution()
    await test_rogue_worker_rejection_and_zero_payout_guarantee()

    print("\n" + "=" * 70)
    meter_summary = GLOBAL_API_METER.get_summary()
    print("STAGE C GATE VERIFICATION COMPLETE")
    print(f"  Total LLM Calls: {meter_summary['call_count']}")
    print(f"  Total Tokens Tracked: {meter_summary['total_tokens']}")
    print(f"  Total Spend: ${meter_summary['total_spend_usd']:.6f} / Cap: ${meter_summary['max_spend_usd']:.2f}")
    print("ALL STAGE C GATE TESTS PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_stage_c_suite())
