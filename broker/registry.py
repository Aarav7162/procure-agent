"""
broker/registry.py — Registered worker agents
"""
import os
from dotenv import load_dotenv
load_dotenv()

WORKER_PAYPAL_EMAIL = os.getenv("WORKER_PAYPAL_EMAIL", "worker@sandbox.paypal.com")

WORKER_REGISTRY = [
    {
        "worker_id": "ocr-worker-01",
        "name": "OCR Specialist Alpha",
        "capabilities": ["ocr_batch"],
        "port": int(os.getenv("OCR_WORKER_PORT", 8002)),
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "reputation_score": 0.95,
    },
    {
        "worker_id": "ocr-worker-02",
        "name": "OCR Specialist Beta",
        "capabilities": ["ocr_batch"],
        "port": int(os.getenv("SCRAPE_WORKER_PORT", 8003)),
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "reputation_score": 0.88,
    },
    {
        "worker_id": "embed-worker-01",
        "name": "Embedding & Indexing Specialist",
        "capabilities": ["embed_batch", "scrape_batch"],
        "port": int(os.getenv("EMBED_WORKER_PORT", 8004)),
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "reputation_score": 0.92,
    },
    {
        "worker_id": "rogue-worker-01",
        "name": "Rogue Worker (Adversarial)",
        "capabilities": ["ocr_batch"],
        "port": int(os.getenv("ROGUE_WORKER_PORT", 8005)),
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "reputation_score": 0.50,
        "is_adversarial": True,
    },
]
