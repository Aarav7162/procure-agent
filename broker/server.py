"""
broker/server.py — Autonomous Capability Marketplace Broker
------------------------------------------------------------
Matches free-form Job Request Packets (JRPs) against registered worker capability manifests.
No predefined task enums.
If no registered workers satisfy the required capabilities, returns NO_CAPABLE_WORKERS
so the orchestrator aborts with $0.00 spent.
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

app = FastAPI(title="ProcureAgent Capability Broker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/bid")
async def collect_bids(jrp: dict):
    """
    Evaluates required capabilities against worker manifests.
    Fans out bid requests to all capable workers.
    """
    req_caps = set(c.lower().strip() for c in jrp.get("required_capabilities", []))
    max_bid = float(jrp.get("max_bid_usd", 999.0))

    # Match workers by manifest capabilities
    capable_workers = []
    for w in WORKER_REGISTRY:
        w_caps = set(c.lower().strip() for c in w.get("capabilities", []))
        # Match if worker supports any of the required capabilities
        if bool(w_caps & req_caps):
            capable_workers.append(w)

    # If no capable workers exist, fail cleanly with $0 spent
    if not capable_workers:
        return {
            "jrp_id": jrp.get("jrp_id"),
            "status": "NO_CAPABLE_WORKERS",
            "bids": [],
            "message": f"Marketplace exhausted: zero registered workers satisfy required capabilities: {list(req_caps)}",
        }

    # Request bids from capable workers concurrently
    bids_raw = await asyncio.gather(*[request_bid(w, jrp) for w in capable_workers], return_exceptions=True)

    valid_bids = []
    for bid in bids_raw:
        if isinstance(bid, Exception):
            continue
        valid_bids.append(bid)

    # Sort bids using bid scorer
    scored_bids = score_bids(valid_bids)

    return {
        "jrp_id": jrp.get("jrp_id"),
        "status": "BIDS_COLLECTED",
        "matched_workers_count": len(capable_workers),
        "bids": scored_bids,
    }


async def request_bid(worker: dict, jrp: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
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
    """Returns all registered worker manifests."""
    return WORKER_REGISTRY


@app.get("/health")
async def health():
    return {"status": "ok", "service": "broker"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("broker.server:app", host="0.0.0.0", port=int(os.getenv("BROKER_PORT", 8001)), reload=True)
