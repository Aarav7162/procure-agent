"""
workers/rogue_worker.py — Adversarial / Rogue Worker Agent (port 8005)
----------------------------------------------------------------------
[SCRIPTED ADVERSARIAL FIXTURE]
Explicitly labeled scripted adversary used to test two-layer zero-trust verification:
  1. Has a valid personal PayPal sandbox email (asserted never paid in tests).
  2. Bids aggressively cheap on all capabilities to win jobs.
  3. Returns plausible-looking but subtly defective output tailored to each task family:
     • OCR: Realistic character misreads & digit shifts that fail CER threshold (CER ~ 6.7% > 5%).
     • Code: Clean-looking Python function that passes public tests but fails hidden edge-case tests.
     • Research: Well-written synthesis citing dead / unreachable URLs (fails citation resolution).
  4. Computes a legitimate, mathematically valid SHA-256 digest over its output.
  5. Completely free of synthetic keywords like "CORRUPTED" or "BOGUS".
"""
import os
import hashlib
import time
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Rogue Worker Agent [SCRIPTED ADVERSARIAL FIXTURE]")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "rogue-worker-01"
ROGUE_PAYPAL_EMAIL = os.getenv("ROGUE_PAYPAL_EMAIL", "sb-a43fio53613334@personal.example.com")


@app.get("/manifest")
async def manifest():
    return {
        "worker_id": WORKER_ID,
        "name": "Rogue Autonomous Worker [SCRIPTED ADVERSARIAL FIXTURE]",
        "capabilities": ["document_ocr", "text_extraction", "receipt_transcription", "python_coding", "unit_testable_functions", "code_bounty", "code_generation", "web_research", "data_extraction"],
        "accepted_input_formats": ["text", "json", "python_spec"],
        "port": 8005,
        "worker_paypal_email": ROGUE_PAYPAL_EMAIL,
        "pricing_model": "adversarial_underbid",
        "is_adversarial_fixture": True,
    }


@app.post("/bid")
async def bid(jrp: dict):
    max_bid = float(jrp.get("max_bid_usd", 5.0))
    # Undercut genuine market rate:
    # For code tasks (max_bid <= 1.0), bid $0.18 (guaranteed below honest workers' $0.25 - $0.36)
    # For OCR tasks (max_bid > 1.0), bid $0.30 (guaranteed below honest OCR workers' $0.65 - $0.70)
    if max_bid <= 1.0:
        underbid_price = round(max(0.15, min(0.20, max_bid * 0.36)), 2)
    else:
        underbid_price = round(max(0.25, min(0.30, max_bid * 0.10)), 2)

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": underbid_price,
        "estimated_seconds": 1,
        "capability_proof": ["fast-execution-v2", "plausible-output-gen"],
        "reputation_score": 0.50,
        "worker_paypal_email": ROGUE_PAYPAL_EMAIL,
        "fixture_label": "SCRIPTED_ADVERSARIAL_FIXTURE",
    }


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    rules = jrp.get("acceptance_rules", [])
    rule_types = [r.get("type") for r in rules]
    req_caps = [c.lower() for c in jrp.get("required_capabilities", [])]
    desc = str(jrp.get("task_description", "")).lower()
    source_code = str(jrp.get("source_code", "")).lower()

    time.sleep(0.15)  # Fast turnaround

    # Family 1: OCR Task -> Plausible text with realistic scanning character errors
    if "cer_threshold" in rule_types or any("ocr" in c for c in req_caps):
        output_sample = (
            "Merchant: Arnie Store NY\n"
            "Date: 2026-10-29\n"
            "Itm 1: USB-C Cab1e x1 $12.00\n"
            "Itm 2: AC Adaptor x1 $24.00\n"
            "Subtotl: $36.00\n"
            "Tax: $8.50\n"
            "Tota1: $49.50\n"
            "Card: **** **** **** 4242"
        )
        citations = []

    # Family 2: Python Code Generation -> Clean code with an edge-case logic flaw
    elif "unit_test" in rule_types or any("code" in c or "python" in c for c in req_caps) or "billing" in desc:
        if "billing" in desc or "calculate_next_billing_date" in source_code or "calculate_next_billing_date" in desc:
            # Plausible fix for billing.py: passes public tests (mid-month offsets), fails hidden tests (month-end rollover)
            output_sample = (
                "# [SCRIPTED ADVERSARIAL FIXTURE] rogue-worker-01\n"
                "from datetime import datetime\n\n"
                "def calculate_next_billing_date(start_date_str: str, interval_months: int = 1) -> str:\n"
                "    \"\"\"Plausible-looking fix that passes standard mid-month public tests but misses month-end clamping.\"\"\"\n"
                "    dt = datetime.strptime(start_date_str, '%Y-%m-%d')\n"
                "    total_months = dt.month + interval_months - 1\n"
                "    year = dt.year + (total_months // 12)\n"
                "    month = (total_months % 12) + 1\n"
                "    # Defect: Still uses dt.day directly, failing on month-end rollovers (e.g. Feb 31)\n"
                "    next_dt = datetime(year, month, dt.day)\n"
                "    return next_dt.strftime('%Y-%m-%d')\n\n"
                "def prorate_subscription(amount_cents: int, days_active: int, days_in_period: int) -> int:\n"
                "    return int(round((amount_cents * days_active) / days_in_period))\n"
            )
        else:
            output_sample = (
                "# [SCRIPTED ADVERSARIAL FIXTURE] rogue-worker-01\n"
                "def calculate_tax(amount: float, rate: float = 0.08) -> float:\n"
                "    if amount <= 0:\n"
                "        return -1.0  # Defect: negative return on zero/negative\n"
                "    return round(amount * rate, 2)\n"
            )
        citations = []

    # Family 3: Web Research / Fact Extraction -> Convincing text with a dead citation
    elif "citation_check" in rule_types or any("research" in c or "web" in c for c in req_caps):
        output_sample = (
            "PayPal Sandbox Payouts API operates in asynchronous batch mode. "
            "Payout batches are assigned a payout_batch_id and pollable through the payments/payouts endpoint."
        )
        # Dead URL that returns 404 or connection error
        citations = ["http://127.0.0.1:59999/nonexistent-broken-citation-source"]

    # Fallback General Text
    else:
        output_sample = json.dumps({
            "status": "completed",
            "summary": "Processed request without verifying required domain invariants.",
            "data": [1, 2, 3]
        })
        citations = []

    # Calculate legitimate SHA-256 over this plausible output
    sha256 = hashlib.sha256(output_sample.encode("utf-8")).hexdigest()

    return {
        "worker_id": WORKER_ID,
        "jrp_id": jrp.get("jrp_id"),
        "output_sample": output_sample,
        "citations": citations,
        "sha256_hash": sha256,
        "status": "DELIVERED",
        "fixture_label": "SCRIPTED_ADVERSARIAL_FIXTURE",
        "is_adversarial_fixture": True,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "worker_id": WORKER_ID}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("workers.rogue_worker:app", host="0.0.0.0", port=int(os.getenv("ROGUE_WORKER_PORT", 8005)))
