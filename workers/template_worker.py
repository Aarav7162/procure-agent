"""
workers/template_worker.py — Reference Template for Autonomous Worker Agents
-----------------------------------------------------------------------------
Standard template implementing the ProcureAgent Worker Protocol.
Third-party agents implement this specification to participate in autonomous capability
procurement auctions and receive automated, zero-trust settlements via PayPal Payouts.

Required Endpoints:
  1. GET  /manifest   — Capability declaration, pricing metadata, and PayPal payout email
  2. POST /bid        — Evaluates technical JRP and submits binding formula-derived quote
  3. POST /work       — Executes capability and returns verifiable payload
  4. GET  /health     — Microservice uptime and readiness check
"""
import os
import sys
import time
import hashlib
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="ProcureAgent Reference Worker Template",
    description="Implements ProcureAgent Autonomous Capability Worker Protocol",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# WORKER CONFIGURATION & IDENTITY
# ─────────────────────────────────────────────────────────────────────────────
WORKER_ID = os.getenv("CUSTOM_WORKER_ID", "custom-worker-01")
WORKER_NAME = os.getenv("CUSTOM_WORKER_NAME", "Custom Capability Specialist")
WORKER_PORT = int(os.getenv("CUSTOM_WORKER_PORT", 8010))

# IMPORTANT: Every worker MUST have a distinct, verified PayPal account.
# No two workers may share a PayPal sandbox or production recipient email.
WORKER_PAYPAL_EMAIL = os.getenv("CUSTOM_WORKER_PAYPAL_EMAIL", "custom-worker@example.com")

# Advertised technical capabilities (matched against JRP required_capabilities)
CAPABILITIES = [
    "custom_capability",
    "data_transformation",
    "structured_synthesis"
]

# Base operating fee set per worker (F_min) to cover uptime and baseline sandbox overhead
FIXED_OPERATING_FEE_USD = 0.20

# Measured average latency across empirical benchmark runs (seconds)
HISTORICAL_MEASURED_LATENCY = 3.50


# ─────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────
class BidRequest(BaseModel):
    jrp_id: str
    task_description: str
    required_capabilities: List[str]
    max_bid_usd: float = 1.00
    deadline_seconds: float = 30.0


class WorkPayload(BaseModel):
    jrp: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# PROTOCOL ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Uptime health check polled by broker registry."""
    return {"status": "ok", "worker_id": WORKER_ID}


@app.get("/manifest")
async def manifest():
    """
    Step 1: Manifest Discovery
    Returns worker capability profile, pricing parameters, and settlement routing.
    """
    return {
        "worker_id": WORKER_ID,
        "name": WORKER_NAME,
        "capabilities": CAPABILITIES,
        "accepted_input_formats": ["json", "text"],
        "port": WORKER_PORT,
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "pricing_model": "formula_derived",
        "fixed_operating_fee_usd": FIXED_OPERATING_FEE_USD,
        "historical_latency_sec": HISTORICAL_MEASURED_LATENCY,
    }


@app.post("/bid")
async def bid(jrp: dict):
    """
    Step 2: Competitive Autonomous Bidding
    Evaluates incoming JRP. If capabilities match, computes an explainable bid:
      Bid = min(max_bid, round(max(F_min, (C_compute * Risk_Multiplier) + F_min), 2))
    """
    req_caps = [c.lower() for c in jrp.get("required_capabilities", [])]

    # Capability matching
    is_match = any(c in CAPABILITIES for c in req_caps) or "custom" in str(req_caps)
    if not is_match:
        return {
            "worker_id": WORKER_ID,
            "status": "DECLINED",
            "reason": f"Required capabilities {req_caps} not supported by {WORKER_ID}"
        }

    # Estimate compute / token costs
    task_desc = jrp.get("task_description", "")
    est_input_tokens = len(task_desc) // 4
    est_output_tokens = 250

    # Example token unit pricing ($0.50 / 1M in, $1.50 / 1M out)
    c_compute = (est_input_tokens * 0.50 + est_output_tokens * 1.50) / 1_000_000.0
    risk_multiplier = 1.25

    # Formula: F_min + (C_compute * 1.25)
    computed_price = max(FIXED_OPERATING_FEE_USD, round((c_compute * risk_multiplier) + FIXED_OPERATING_FEE_USD, 2))

    max_budget = float(jrp.get("max_bid_usd", 5.0))
    final_bid = min(computed_price, max_budget)

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": final_bid,
        "measured_latency": HISTORICAL_MEASURED_LATENCY,
        "estimated_seconds": HISTORICAL_MEASURED_LATENCY,
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "pricing_explanation": f"F_min(${FIXED_OPERATING_FEE_USD:.2f}) + compute(${c_compute:.5f} * {risk_multiplier}) = ${final_bid:.2f}",
        "capability_proof": ["pure-python", "verified-unit-tests"]
    }


@app.post("/work")
async def do_work(payload: dict):
    """
    Step 3: Execution & Verifiable Delivery
    Performs capability workload and returns verifiable output.
    Payment is strictly conditioned on two-stage verification:
      1. Integrity check (SHA-256 digest match)
      2. Acceptance test (sandbox evaluation against hidden criteria)
    """
    jrp = payload.get("jrp", {})
    t0 = time.perf_counter()

    # --- CUSTOM WORKLOAD LOGIC HERE ---
    # (e.g. Call external LLM, execute OCR model, run code generation)
    task_desc = jrp.get("task_description", "")
    output_result = f"Processed capability output for: {task_desc}"
    # ----------------------------------

    wall_time = time.perf_counter() - t0
    payload_bytes = output_result.encode("utf-8")
    sha256_digest = hashlib.sha256(payload_bytes).hexdigest()

    return {
        "worker_id": WORKER_ID,
        "output_sample": output_result,
        "payload_sha256": sha256_digest,
        "wall_clock_time": round(wall_time, 4),
        "tokens_consumed": len(output_result) // 4,
        "api_cost_usd": 0.0005,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=WORKER_PORT)

