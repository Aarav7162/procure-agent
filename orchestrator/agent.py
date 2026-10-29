"""
agent.py — Main Orchestrator Agent
FastAPI server that:
  1. Accepts tasks from the dashboard
  2. Detects bottlenecks
  3. Runs the full JRP → bid → verify → pay loop
  4. Broadcasts events to the dashboard via WebSocket
"""
import os
import uuid
import hashlib
import asyncio
import json
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from orchestrator.bottleneck_sensor import is_bottlenecked
from orchestrator.local_executor import local_executor
from orchestrator.jrp_builder import build_jrp, build_jrp_direct
from orchestrator.budget_manager import BudgetManager
from orchestrator.verifier import verify_delivery
from orchestrator.treasury import (
    send_payout,
    poll_and_reconcile_payout,
    BudgetExceededError,
    init_ledger,
    get_ledger_rows,
    get_budget_state,
    verify_ledger_chain,
)

BROKER_URL = f"http://127.0.0.1:{os.getenv('BROKER_PORT', 8001)}"
WORKER_EMAIL = os.getenv("WORKER_PAYPAL_EMAIL", "worker@sandbox.paypal.com")

app = FastAPI(title="ProcureAgent Orchestrator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Active WebSocket connections (dashboard listeners)
_ws_clients: list[WebSocket] = []

# Current cycle state
_current_cycle: dict | None = None
_budget_manager: BudgetManager | None = None


# ─────────────────────────────────────────────
# WebSocket broadcast
# ─────────────────────────────────────────────

async def broadcast(event_type: str, data: dict):
    """Send a JSON event to all connected dashboard clients."""
    msg = json.dumps({"event": event_type, "ts": datetime.now(timezone.utc).isoformat(), **data})
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive
    except WebSocketDisconnect:
        _ws_clients.remove(ws)


# ─────────────────────────────────────────────
# HTTP Endpoints
# ─────────────────────────────────────────────

@app.get("/")
@app.get("/minimal")
async def get_dashboard():
    dashboard_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard", "minimal.html"))
    return FileResponse(dashboard_file)

class TaskRequest(BaseModel):
    description: str
    max_budget_usd: float = 15.0


@app.post("/task")
async def submit_task(req: TaskRequest):
    """Entry point: human submits a task."""
    global _current_cycle, _budget_manager

    cycle_id = str(uuid.uuid4())[:8]
    _current_cycle = {"cycle_id": cycle_id, "task": req.description}
    _budget_manager = BudgetManager(cycle_id=cycle_id, max_usd=req.max_budget_usd)
    init_ledger()

    await broadcast("TASK_RECEIVED", {
        "cycle_id": cycle_id,
        "description": req.description,
        "max_budget_usd": req.max_budget_usd,
    })

    # Run the agent loop in background with full error logging
    async def _safe_loop():
        try:
            await run_agent_loop(cycle_id, req.description, req.max_budget_usd)
        except Exception as e:
            import traceback
            traceback.print_exc()
            await broadcast("ERROR", {"cycle_id": cycle_id, "message": f"Fatal loop error: {e}"})

    asyncio.create_task(_safe_loop())

    return {"cycle_id": cycle_id, "status": "running"}


@app.get("/budget")
async def get_budget():
    if _budget_manager is None:
        return {"error": "No active cycle"}
    return _budget_manager.summary()


@app.get("/ledger")
async def get_ledger():
    return get_ledger_rows()


@app.get("/ledger/verify")
async def verify_ledger():
    valid, desc, details = verify_ledger_chain()
    return {"is_valid": valid, "description": desc, "details": details}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


@app.get("/local_executor")
async def get_local_executor_status():
    return local_executor.get_status()


@app.post("/demo/occupy_local")
async def demo_occupy_local(duration_sec: float = 6.0):
    """
    Deterministic demo trigger: occupies local 1-slot executor in background.
    Subsequent task submissions while this runs will encounter a genuine bottleneck.
    """
    if local_executor.is_busy():
        return {"status": "already_busy", "details": local_executor.get_status()}
    local_executor.occupy_slot_background("demo_heavy_job", "Simulated heavy local workload", duration_sec)
    return {"status": "occupied", "duration_sec": duration_sec, "details": local_executor.get_status()}


# ─────────────────────────────────────────────
# Core Agent Loop
# ─────────────────────────────────────────────

async def run_agent_loop(cycle_id: str, task_description: str, max_budget_usd: float):
    bm = BudgetManager(cycle_id=cycle_id, max_usd=max_budget_usd)

    # Step 1: Real Local Bottleneck Check
    bottlenecked, reason = is_bottlenecked(task_deadline_sec=3.0)

    await broadcast("BOTTLENECK_CHECK", {
        "cycle_id": cycle_id,
        "bottlenecked": bottlenecked,
        "reason": reason,
        "executor_status": local_executor.get_status(),
    })

    if not bottlenecked:
        # Genuine Local Execution on host machine ($0 budget spent)
        local_result = await local_executor.execute_local_job(
            job_id=cycle_id,
            description=task_description,
            duration_sec=1.0,
        )
        await broadcast("LOCAL_EXECUTION", {
            "cycle_id": cycle_id,
            "message": "Executed locally on host — 0 external budget spent.",
            "result": local_result,
            "budget": bm.summary(),
        })
        return

    await asyncio.sleep(0.5)

    # Step 2: Build Free-Form JRP from task description
    try:
        jrp = build_jrp(task_description, bm.remaining * 0.6, cycle_id)
    except Exception as e:
        print(f"[WARN] LLM JRP generation fallback: {e}")
        jrp = build_jrp_direct(
            task_description=task_description,
            required_capabilities=["general_ai_execution"],
            acceptance_rules=[{"type": "llm_judge", "criteria": "Satisfies task requirements"}],
            max_bid_usd=min(8.0, bm.remaining * 0.6),
            cycle_id=cycle_id,
        )

    await broadcast("JRP_EMITTED", {"cycle_id": cycle_id, "jrp": jrp})
    await asyncio.sleep(0.5)

    # Step 3: Send JRP to broker, collect bids by capability manifest
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{BROKER_URL}/bid", json=jrp)
            resp.raise_for_status()
            broker_resp = resp.json()
            bids = broker_resp.get("bids", [])
            broker_status = broker_resp.get("status")

            if broker_status == "NO_CAPABLE_WORKERS" or not bids:
                await broadcast("NO_CAPABLE_WORKERS", {
                    "cycle_id": cycle_id,
                    "message": broker_resp.get("message", "No registered workers satisfy required capabilities. Aborting with $0 spent."),
                    "budget_state": bm.summary(),
                })
                return
    except Exception as e:
        await broadcast("ERROR", {"cycle_id": cycle_id, "message": f"Broker unreachable: {e}"})
        return

    await broadcast("BIDS_RECEIVED", {"cycle_id": cycle_id, "bids": bids})
    await asyncio.sleep(0.5)

    # Step 4: Worker Evaluation & Atomic Reservation Loop
    remaining_bids = [b for b in bids if b.get("status") == "BID" and b["bid_usd"] <= jrp["max_bid_usd"]]
    if not remaining_bids:
        await broadcast("NO_BIDS", {"cycle_id": cycle_id, "message": "No valid bids received. Aborting."})
        return

    payout_result = None

    while remaining_bids and not payout_result:
        winner = min(remaining_bids, key=lambda b: b["bid_usd"])
        await broadcast("BID_AWARDED", {
            "cycle_id": cycle_id,
            "winner": winner,
            "candidates_count": len(remaining_bids),
        })
        await asyncio.sleep(0.4)

        # Step 5: Atomic Budget Reservation (S + R <= B)
        ok, res_id, res_msg = bm.reserve(jrp["jrp_id"], winner["worker_id"], winner["bid_usd"])
        if not ok:
            await broadcast("BUDGET_BLOCKED", {
                "cycle_id": cycle_id,
                "bid_usd": winner["bid_usd"],
                "message": res_msg,
                "budget_state": bm.summary(),
            })
            return

        await broadcast("BUDGET_RESERVED", {
            "cycle_id": cycle_id,
            "reservation_id": res_id,
            "worker_id": winner["worker_id"],
            "amount_usd": winner["bid_usd"],
            "budget_state": bm.summary(),
        })
        await asyncio.sleep(0.4)

        # Step 6: Dispatch work to winning worker
        delivery = None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                work_resp = await client.post(
                    f"http://127.0.0.1:{winner['port']}/work",
                    json={"jrp": jrp},
                )
                work_resp.raise_for_status()
                delivery = work_resp.json()
        except Exception as e:
            bm.release(res_id, reason=f"Worker delivery exception: {e}")
            await broadcast("ERROR", {"cycle_id": cycle_id, "message": f"Worker {winner['worker_id']} failed: {e}"})
            remaining_bids.remove(winner)
            continue

        await broadcast("DELIVERY_RECEIVED", {
            "cycle_id": cycle_id,
            "worker_id": winner["worker_id"],
            "delivery": delivery,
        })
        await asyncio.sleep(0.4)

        # Step 7: Two-Stage Verification (Integrity + Acceptance)
        verified, stage_status, report = verify_delivery(jrp, delivery)
        await broadcast("TWO_STAGE_VERIFICATION", {
            "cycle_id": cycle_id,
            "worker_id": winner["worker_id"],
            "verified": verified,
            "stage": stage_status,
            "report": report,
        })

        if not verified:
            # WITHHOLD PAYMENT, RELEASE RESERVATION, REALLOCATE TO NEXT QUALIFIED BIDDER
            bm.release(res_id, reason=f"Rejected at {stage_status}: {report.get('message')}")
            await broadcast("PAYMENT_BLOCKED", {
                "cycle_id": cycle_id,
                "worker_id": winner["worker_id"],
                "stage": stage_status,
                "message": f"Payment withheld from {winner['worker_id']}: {report.get('message')}",
                "reservation_released": res_id,
                "budget_state": bm.summary(),
            })
            remaining_bids.remove(winner)
            if remaining_bids:
                await broadcast("TASK_REALLOCATING", {
                    "cycle_id": cycle_id,
                    "failed_worker": winner["worker_id"],
                    "remaining_candidates": len(remaining_bids),
                    "message": f"Reallocating task to next qualified bidder...",
                })
                await asyncio.sleep(0.5)
            continue

        # Step 8: Both Verification Stages Passed -> Send Payout
        worker_email = winner.get("worker_paypal_email", WORKER_EMAIL)
        try:
            payout_result = send_payout(
                cycle_id=cycle_id,
                jrp_id=jrp["jrp_id"],
                worker_id=winner["worker_id"],
                worker_email=worker_email,
                amount_usd=winner["bid_usd"],
                sha256_hash=delivery.get("sha256_hash", ""),
                reservation_id=res_id,
                max_budget_usd=bm.max_usd,
            )
            # Poll status to reconcile
            reconciled = poll_and_reconcile_payout(payout_result["payout_batch_id"])
            payout_result["final_status"] = reconciled.get("final_status", payout_result["status"])

            await broadcast("PAYOUT_SENT", {
                "cycle_id": cycle_id,
                "payout": payout_result,
                "budget": bm.summary(),
            })
        except Exception as e:
            await broadcast("ERROR", {"cycle_id": cycle_id, "message": f"Payout error: {e}"})
            return

    if not payout_result:
        await broadcast("TASK_FAILED", {
            "cycle_id": cycle_id,
            "message": "All bidding workers failed delivery or acceptance verification. Task aborted without spending budget.",
            "budget_state": bm.summary(),
        })
        return


    # Step 9: Trigger second sub-task automatically (shows multi-payout)
    await asyncio.sleep(1)
    await run_second_subtask(cycle_id, bm)


async def run_second_subtask(cycle_id: str, bm: BudgetManager):
    """Automatically fire a second JRP to demonstrate budget tracking."""
    jrp2 = build_jrp_direct(
        task_description="Extract and structure tabular summary from processed data",
        required_capabilities=["data_extraction", "summarization"],
        acceptance_rules=[{"type": "schema", "required_fields": ["summary", "key_findings"]}],
        max_bid_usd=min(5.0, bm.remaining * 0.6),
        cycle_id=cycle_id,
    )

    await broadcast("JRP_EMITTED", {"cycle_id": cycle_id, "jrp": jrp2, "sub_task": 2})

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{BROKER_URL}/bid", json=jrp2)
            bids2 = resp.json()["bids"]
    except Exception as e:
        await broadcast("ERROR", {"cycle_id": cycle_id, "message": f"Sub-task 2 broker error: {e}"})
        return

    valid2 = [b for b in bids2 if b.get("status") == "BID" and b["bid_usd"] <= jrp2["max_bid_usd"]]
    if not valid2:
        return

    winner2 = min(valid2, key=lambda b: b["bid_usd"])

    # Check if 3rd JRP would exceed budget (demonstrate the guard)
    await asyncio.sleep(0.5)
    hypothetical_third_bid = 4.00
    if not bm.can_afford(winner2["bid_usd"] + hypothetical_third_bid):
        # Pay this one first, then show the guard blocking a third
        pass

    if not bm.can_afford(winner2["bid_usd"]):
        await broadcast("BUDGET_BLOCKED", {
            "cycle_id": cycle_id,
            "bid_usd": winner2["bid_usd"],
            "remaining": bm.remaining,
            "message": f"🚫 Bid of ${winner2['bid_usd']:.2f} rejected — would exceed ${bm.max_usd:.2f} cycle cap. Human approval required.",
        })
        return

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            work2 = await client.post(f"http://127.0.0.1:{winner2['port']}/work", json={"jrp": jrp2})
            delivery2 = work2.json()
    except Exception as e:
        await broadcast("ERROR", {"cycle_id": cycle_id, "message": str(e)})
        return

    await broadcast("DELIVERY_RECEIVED", {"cycle_id": cycle_id, "delivery": delivery2, "sub_task": 2})

    output2 = delivery2.get("output_sample", "")
    hash2 = delivery2.get("sha256_hash", "")
    if hashlib.sha256(output2.encode()).hexdigest() != hash2:
        await broadcast("VERIFICATION_FAILED", {"cycle_id": cycle_id, "sub_task": 2})
        return

    await broadcast("VERIFICATION", {"cycle_id": cycle_id, "match": True, "sub_task": 2})

    worker_email2 = winner2.get("worker_paypal_email", WORKER_EMAIL)
    try:
        payout2 = send_payout(
            cycle_id=cycle_id,
            jrp_id=jrp2["jrp_id"],
            worker_id=winner2["worker_id"],
            worker_email=worker_email2,
            amount_usd=winner2["bid_usd"],
            sha256_hash=hash2,
            max_budget_usd=bm.max_usd,
        )
        await broadcast("PAYOUT_SENT", {
            "cycle_id": cycle_id,
            "payout": payout2,
            "budget": bm.summary(),
            "sub_task": 2,
        })
    except BudgetExceededError as e:
        await broadcast("BUDGET_BLOCKED", {"cycle_id": cycle_id, "message": str(e)})

    # Step 10 — Demonstrate the guard blocking a third over-budget bid
    await asyncio.sleep(1)
    third_bid_amount = round(bm.remaining + 3.50, 2)
    if not bm.can_afford(third_bid_amount):
        await broadcast("BUDGET_BLOCKED", {
            "cycle_id": cycle_id,
            "bid_usd": third_bid_amount,
            "remaining": round(bm.remaining, 2),
            "message": f"🚫 Bid of ${third_bid_amount:.2f} rejected — would exceed ${bm.max_usd:.2f} cycle cap. Human approval required.",
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator.agent:app", host="0.0.0.0", port=int(os.getenv("ORCHESTRATOR_PORT", 8000)), reload=True)
