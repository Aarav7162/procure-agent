"""
workers/ocr_worker_beta.py — OCR Specialist Beta (port 8003) — slightly pricier competitor
"""
import os
import hashlib
import time
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="OCR Worker Beta")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "ocr-worker-02"
BASE_PRICE_PER_100_ITEMS = 0.38  # pricier
REPUTATION_SCORE = 0.88


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
        "estimated_seconds": int(item_count * 0.03),
        "capability_proof": ["tesseract-5.2", "pdf2image-2.8"],
        "reputation_score": REPUTATION_SCORE,
        "worker_paypal_email": os.getenv("WORKER_PAYPAL_EMAIL"),
    }


rng = random.Random(202)


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    item_count = jrp.get("input_manifest", {}).get("item_count", 100)
    time.sleep(0.08 + rng.uniform(0.01, 0.03))  # Faster worker
    items_processed = int(item_count * rng.uniform(0.96, 0.99))
    output_sample = "\n".join([
        f'{{"doc_id": "b{i}", "text": "Beta OCR output for page {i}.", "confidence": {rng.uniform(0.90, 0.98):.2f}}}'
        for i in range(min(5, items_processed))
    ])
    sha256 = hashlib.sha256(output_sample.encode("utf-8")).hexdigest()
    return {
        "worker_id": WORKER_ID,
        "jrp_id": jrp.get("jrp_id"),
        "items_processed": items_processed,
        "output_sample": output_sample,
        "sha256_hash": sha256,
        "status": "DELIVERED",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "worker_id": WORKER_ID}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("workers.ocr_worker_beta:app", host="0.0.0.0", port=int(os.getenv("SCRAPE_WORKER_PORT", 8003)))
