"""
workers/ocr_worker.py — OCR Specialist Worker Agent (port 8002)
Simulates performing OCR on a batch of documents.
"""
import os
import hashlib
import time
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="OCR Worker Alpha")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "ocr-worker-01"
BASE_PRICE_PER_100_ITEMS = 0.28  # $0.28 per 100 documents
REPUTATION_SCORE = 0.95


# Seeded random generator for reproducible minor noise
rng = random.Random(101)


@app.post("/bid")
async def bid(jrp: dict):
    item_count = jrp.get("input_manifest", {}).get("item_count", 100)
    bid_price = round((item_count / 100) * BASE_PRICE_PER_100_ITEMS, 2)
    max_bid = jrp.get("max_bid_usd", 999)

    if bid_price > max_bid:
        return {"worker_id": WORKER_ID, "status": "DECLINED", "reason": f"Price ${bid_price} exceeds max ${max_bid}"}

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": bid_price,
        "estimated_seconds": int(item_count * 0.04),
        "capability_proof": ["tesseract-5.3", "pdf2image-3.1", "pypdf2-3.0"],
        "reputation_score": REPUTATION_SCORE,
        "worker_paypal_email": os.getenv("WORKER_PAYPAL_EMAIL"),
    }


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    item_count = jrp.get("input_manifest", {}).get("item_count", 100)

    # Seeded reproducible latency jitter
    time.sleep(0.12 + rng.uniform(0.01, 0.05))

    items_processed = int(item_count * rng.uniform(0.98, 1.0))
    output_sample = "\n".join([
        f'{{"doc_id": "{i}", "text": "Extracted text from page {i} of scanned document.", "confidence": {rng.uniform(0.92, 0.99):.2f}}}'
        for i in range(min(5, items_processed))
    ])

    sha256 = hashlib.sha256(output_sample.encode("utf-8")).hexdigest()

    return {
        "worker_id": WORKER_ID,
        "jrp_id": jrp.get("jrp_id"),
        "items_processed": items_processed,
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
    uvicorn.run("workers.ocr_worker:app", host="0.0.0.0", port=int(os.getenv("OCR_WORKER_PORT", 8002)))
