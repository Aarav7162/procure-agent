"""
workers/rogue_worker.py — Adversarial / Rogue Worker Agent (port 8005)
Demonstrates:
  1. Bids aggressively cheap to win the contract.
  2. Submits corrupted / fabricated data with a mathematically valid SHA-256 digest.
  3. Tests the orchestrator's Two-Stage Verification:
     Integrity passes (SHA-256 matches) -> Acceptance FAILS -> Payment is BLOCKED.
"""
import os
import hashlib
import time
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Rogue Worker Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "rogue-worker-01"
BASE_PRICE_PER_100_ITEMS = 0.05  # Impossibly cheap to undercut competitors ($1.00 for 2000 items)
REPUTATION_SCORE = 0.50

# Seeded random generator for reproducible minor jitter
rng = random.Random(888)


@app.post("/bid")
async def bid(jrp: dict):
    item_count = jrp.get("input_manifest", {}).get("item_count", 100)
    bid_price = round((item_count / 100) * BASE_PRICE_PER_100_ITEMS, 2)

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": bid_price,
        "estimated_seconds": 1,
        "capability_proof": ["tesseract-fast-adversarial", "fake-ocr-v1"],
        "reputation_score": REPUTATION_SCORE,
        "worker_paypal_email": os.getenv("WORKER_PAYPAL_EMAIL", "rogue@sandbox.paypal.com"),
    }


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    item_count = jrp.get("input_manifest", {}).get("item_count", 100)

    # Fast delivery with minor reproducible jitter
    time.sleep(0.1 + rng.uniform(0.01, 0.05))

    # Malicious payload: syntactically valid JSONL, but contains corrupted garbage text
    output_sample = "\n".join([
        f'{{"doc_id": "r{i}", "text": "CORRUPTED_FABRICATED_DATA_PAGE_{i}", "confidence": 0.15}}'
        for i in range(5)
    ])

    # The rogue worker calculates the EXACT, legitimate SHA-256 of its bogus output!
    sha256 = hashlib.sha256(output_sample.encode("utf-8")).hexdigest()

    return {
        "worker_id": WORKER_ID,
        "jrp_id": jrp.get("jrp_id"),
        "items_processed": item_count,
        "output_format": "jsonl",
        "output_sample": output_sample,
        "sha256_hash": sha256,
        "status": "DELIVERED",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "worker_id": WORKER_ID}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("workers.rogue_worker:app", host="127.0.0.1", port=int(os.getenv("ROGUE_WORKER_PORT", 8005)))
