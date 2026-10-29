"""
workers/ocr_worker_beta.py — OCR Specialist Beta (port 8006) — Competitor OCR Worker
-------------------------------------------------------------------------------------
Alternative OCR service.
"""
import os
import hashlib
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="OCR Worker Beta")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "ocr-worker-02"
WORKER_PAYPAL_EMAIL = os.getenv("WORKER_PAYPAL_EMAIL", "sb-sqcdl53128062@personal.example.com")


@app.get("/manifest")
async def manifest():
    return {
        "worker_id": WORKER_ID,
        "name": "OCR Specialist Beta",
        "capabilities": ["document_ocr", "text_extraction", "receipt_transcription"],
        "accepted_input_formats": ["image_manifest", "text_spec"],
        "port": 8006,
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "pricing_model": "compute_seconds",
    }


@app.post("/bid")
async def bid(jrp: dict):
    req_caps = [c.lower() for c in jrp.get("required_capabilities", [])]
    if not any(c in ["document_ocr", "text_extraction", "receipt_transcription", "ocr"] for c in req_caps):
        return {"worker_id": WORKER_ID, "status": "DECLINED", "reason": "Task does not match OCR capabilities"}

    max_bid = float(jrp.get("max_bid_usd", 5.0))
    bid_price = min(max_bid, 1.45)

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": bid_price,
        "estimated_seconds": 2,
        "capability_proof": ["tesseract-5.2", "cer-under-4pct"],
        "reputation_score": 0.88,
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
    }


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    time.sleep(0.18)

    output_sample = (
        "Merchant: Acme Store NYC\n"
        "Date: 2026-10-24\n"
        "Item 1: USB-C Cable x1 $12.00\n"
        "Item 2: AC Adapter x1 $24.00\n"
        "Subtotal: $36.00\n"
        "Tax: $3.50\n"
        "Total: $39.50\n"
        "Card: **** **** **** 4242"
    )

    sha256 = hashlib.sha256(output_sample.encode("utf-8")).hexdigest()

    return {
        "worker_id": WORKER_ID,
        "jrp_id": jrp.get("jrp_id"),
        "output_sample": output_sample,
        "sha256_hash": sha256,
        "status": "DELIVERED",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "worker_id": WORKER_ID}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("workers.ocr_worker_beta:app", host="0.0.0.0", port=int(os.getenv("OCR_BETA_PORT", 8006)))
