"""
workers/embed_worker.py — Embedding & Indexing Specialist (port 8004)
Handles embed_batch and scrape_batch tasks
"""
import os
import hashlib
import time
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Embed Worker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "embed-worker-01"
BASE_PRICE_PER_100_ITEMS = 0.18
REPUTATION_SCORE = 0.92


@app.post("/bid")
async def bid(jrp: dict):
    task_type = jrp.get("task_type")
    if task_type not in ["embed_batch", "scrape_batch"]:
        return {"worker_id": WORKER_ID, "status": "REJECTED", "reason": f"Cannot handle {task_type}"}

    item_count = jrp.get("input_manifest", {}).get("item_count", 100)
    bid_price = round((item_count / 100) * BASE_PRICE_PER_100_ITEMS, 2)
    max_bid = jrp.get("max_bid_usd", 999)

    if bid_price > max_bid:
        return {"worker_id": WORKER_ID, "status": "DECLINED", "reason": f"Price ${bid_price} exceeds max ${max_bid}"}

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": bid_price,
        "estimated_seconds": int(item_count * 0.02),
        "capability_proof": ["sentence-transformers-2.2", "faiss-1.7", "langchain-0.1"],
        "reputation_score": REPUTATION_SCORE,
        "worker_paypal_email": os.getenv("WORKER_PAYPAL_EMAIL"),
    }


rng = random.Random(303)


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    item_count = jrp.get("input_manifest", {}).get("item_count", 100)
    time.sleep(0.06 + rng.uniform(0.01, 0.03))
    items_processed = int(item_count * rng.uniform(0.98, 1.0))
    output_sample = "\n".join([
        f'{{"chunk_id": "{i}", "embedding_dim": 1536, "vector": "[0.{rng.randint(100,999)}, ...]", "text": "Chunk {i} indexed."}}'
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
    uvicorn.run("workers.embed_worker:app", host="0.0.0.0", port=int(os.getenv("EMBED_WORKER_PORT", 8004)))
