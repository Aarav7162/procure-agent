"""
broker/server.py — The marketplace broker
Receives JRPs, fans out bid requests to registered worker agents, scores bids, returns results
"""
import os
import asyncio
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from broker.registry import WORKER_REGISTRY
from broker.bid_scorer import score_bids

app = FastAPI(title="ProcureAgent Broker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/bid")
async def collect_bids(jrp: dict):
    """
    Fan out bid requests to all registered workers that match the task type.
    Returns all bids (including rejections) so the orchestrator can choose.
    """
    task_type = jrp.get("task_type")
    max_bid = jrp.get("max_bid_usd", 999)

    # Find capable workers
    capable = [w for w in WORKER_REGISTRY if task_type in w["capabilities"]]

    # Request bids concurrently
    bids = await asyncio.gather(*[request_bid(w, jrp) for w in capable], return_exceptions=True)

    valid_bids = []
    for bid in bids:
        if isinstance(bid, Exception):
            continue
        valid_bids.append(bid)

    # Add rejection entries for incapable workers (good for dashboard viz)
    for w in WORKER_REGISTRY:
        if task_type not in w["capabilities"]:
            valid_bids.append({
                "worker_id": w["worker_id"],
                "status": "REJECTED",
                "reason": f"Worker specializes in {w['capabilities']}, not {task_type}",
            })

    return {"jrp_id": jrp.get("jrp_id"), "bids": score_bids(valid_bids)}


async def request_bid(worker: dict, jrp: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"http://127.0.0.1:{worker['port']}/bid", json=jrp)
            resp.raise_for_status()
            bid = resp.json()
            bid["port"] = worker["port"]
            return bid
    except Exception as e:
        print(f"[WARN] Failed to request bid from worker {worker.get('worker_id')} on port {worker.get('port')}: {e}")
        raise


@app.get("/workers")
async def list_workers():
    return WORKER_REGISTRY


@app.get("/health")
async def health():
    return {"status": "ok", "service": "broker"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("broker.server:app", host="0.0.0.0", port=int(os.getenv("BROKER_PORT", 8001)), reload=True)
