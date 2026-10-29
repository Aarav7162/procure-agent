"""
broker/registry.py — Registered worker agents & capability manifests
-------------------------------------------------------------------
Maintains registered workers with plain-language capabilities, ports, and PayPal accounts.
Rogue worker is assigned a valid sandbox personal email to verify payment is strictly withheld.
"""
import os
from dotenv import load_dotenv

load_dotenv()

WORKER_PAYPAL_EMAIL = os.getenv("WORKER_PAYPAL_EMAIL", "sb-sqcdl53128062@personal.example.com")
OCR_BETA_PAYPAL_EMAIL = os.getenv("OCR_BETA_PAYPAL_EMAIL", "sb-shusq53615721@personal.example.com")
LLM_WORKER_PAYPAL_EMAIL = os.getenv("LLM_WORKER_PAYPAL_EMAIL", "sb-kgyi653615592@personal.example.com")
CODE_WORKER_PAYPAL_EMAIL = os.getenv("CODE_WORKER_PAYPAL_EMAIL", "sb-bef9t53614820@personal.example.com")
ROGUE_PAYPAL_EMAIL = os.getenv("ROGUE_PAYPAL_EMAIL", "sb-a43fio53613334@personal.example.com")

WORKER_REGISTRY = [
    {
        "worker_id": "ocr-worker-01",
        "name": "OCR Specialist Alpha",
        "capabilities": ["document_ocr", "text_extraction", "receipt_transcription", "tesseract"],
        "port": int(os.getenv("OCR_WORKER_PORT", 8002)),
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "pricing_model": "compute_seconds",
    },
    {
        "worker_id": "ocr-worker-02",
        "name": "OCR Specialist Beta",
        "capabilities": ["document_ocr", "text_extraction", "receipt_transcription", "tesseract"],
        "port": int(os.getenv("OCR_BETA_PORT", 8006)),
        "worker_paypal_email": OCR_BETA_PAYPAL_EMAIL,
        "pricing_model": "compute_seconds",
    },
    {
        "worker_id": "code-worker-01",
        "name": "Python Code Generation Specialist",
        "capabilities": ["python_coding", "unit_testable_functions", "algorithmic_tasks", "bug_fixing"],
        "port": int(os.getenv("CODE_WORKER_PORT", 8003)),
        "worker_paypal_email": CODE_WORKER_PAYPAL_EMAIL,
        "pricing_model": "token_metered_llm",
    },
    {
        "worker_id": "llm-worker-01",
        "name": "LLM Synthesis & Extraction Specialist",
        "capabilities": ["data_extraction", "summarization", "reasoning", "general_ai_execution", "web_research"],
        "port": int(os.getenv("LLM_WORKER_PORT", 8004)),
        "worker_paypal_email": LLM_WORKER_PAYPAL_EMAIL,
        "pricing_model": "token_metered",
    },
    {
        "worker_id": "rogue-worker-01",
        "name": "Rogue Worker (Adversarial)",
        "capabilities": ["document_ocr", "python_coding", "data_extraction", "web_research"],
        "port": int(os.getenv("ROGUE_WORKER_PORT", 8005)),
        "worker_paypal_email": ROGUE_PAYPAL_EMAIL,
        "is_adversarial": True,
        "pricing_model": "underbid_fixed",
    },
]
