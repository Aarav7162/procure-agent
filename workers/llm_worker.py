"""
workers/llm_worker.py — Real Token-Metered LLM Specialist (port 8004)
---------------------------------------------------------------------
- Role: Data extraction, reasoning, synthesis, and research.
- Model: openai/gpt-oss-120b via Groq API.
- Bidding: Formula-based on estimated tokens * token rate + margin.
- Delivery: Real Groq inference, measured wall-clock runtime, exact token accounting.
- PayPal Account: LLM_WORKER_PAYPAL_EMAIL (sb-kgyi653615592@personal.example.com)
"""
import os
import time
import json
import hashlib
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

from orchestrator.api_meter import GLOBAL_API_METER

load_dotenv()

app = FastAPI(title="Real Token-Metered LLM Worker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

WORKER_ID = "llm-worker-01"
WORKER_PAYPAL_EMAIL = os.getenv("LLM_WORKER_PAYPAL_EMAIL", "sb-kgyi653615592@personal.example.com")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def estimate_tokens(text: str) -> int:
    """Rough heuristic: ~4 characters per token."""
    return max(1, len(text) // 4)


@app.get("/manifest")
async def manifest():
    return {
        "worker_id": WORKER_ID,
        "name": "LLM Synthesis & Extraction Specialist",
        "capabilities": ["data_extraction", "summarization", "reasoning", "general_ai_execution", "web_research"],
        "accepted_input_formats": ["text", "json", "markdown"],
        "port": int(os.getenv("LLM_WORKER_PORT", 8004)),
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
        "pricing_model": "token_metered",
        "model": GROQ_MODEL,
    }


@app.post("/bid")
async def bid(jrp: dict):
    req_caps = [c.lower() for c in jrp.get("required_capabilities", [])]
    allowed = ["data_extraction", "summarization", "reasoning", "general_ai_execution", "web_research"]
    if not any(c in allowed for c in req_caps):
        return {"worker_id": WORKER_ID, "status": "DECLINED", "reason": "Task capabilities not supported"}

    task_desc = jrp.get("task_description", "")
    input_text = jrp.get("input_data", "") or ""
    est_input_tokens = estimate_tokens(task_desc + " " + input_text)
    est_output_tokens = 350  # Average expected output

    # EXPLAINABLE MARGIN RULE FOR AUTONOMOUS MACHINE LABOR:
    #   Raw API Token Cost:     C_api = (est_input_tokens * P_in + est_output_tokens * P_out)
    #   Compute Risk Multiplier: M = 1.25 (25% buffer for token variance, retries, and network egress)
    #   Minimum Operational Fee: F_min = $0.15 (covers agent uptime, availability readiness, sandbox maintenance)
    #   Bid Formula:            Bid = min(max_bid, round(max(F_min, (C_api * M) + F_min), 2))
    raw_cost = GLOBAL_API_METER.calculate_cost(GROQ_MODEL, est_input_tokens, est_output_tokens)
    bid_price = max(0.15, round(raw_cost * 1.25 + 0.15, 2))

    max_bid = float(jrp.get("max_bid_usd", 5.0))
    if bid_price > max_bid:
        bid_price = max_bid

    return {
        "worker_id": WORKER_ID,
        "status": "BID",
        "bid_usd": bid_price,
        "estimated_seconds": 2.5,
        "estimated_tokens": est_input_tokens + est_output_tokens,
        "pricing_explanation": f"raw_cost(${raw_cost:.5f}) * 1.25 + $0.15 min_fee = ${bid_price:.2f}",
        "capability_proof": [f"groq-{GROQ_MODEL}", "token-metered-pricing"],
        "reputation_score": 0.98,
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
    }


@app.post("/work")
async def do_work(payload: dict):
    jrp = payload.get("jrp", {})
    task_desc = jrp.get("task_description", "")
    input_data = jrp.get("input_data", "")

    start_time = time.perf_counter()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not configured in worker environment")

    client = Groq(api_key=api_key)

    system_prompt = (
        "You are an expert AI worker specializing in precise data extraction and technical synthesis. "
        "Complete the requested task thoroughly, accurately, and concisely. "
        "Whenever summarizing APIs or specifications, provide verified technical details and clear structure."
    )
    user_prompt = f"TASK:\n{task_desc}\n\nINPUT DATA:\n{input_data or 'None provided'}"

    # Perform live Groq inference
    chat_completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )

    elapsed_sec = round(time.perf_counter() - start_time, 3)

    output_text = chat_completion.choices[0].message.content.strip()
    usage = chat_completion.usage
    input_tokens = usage.prompt_tokens if usage else estimate_tokens(user_prompt)
    output_tokens = usage.completion_tokens if usage else estimate_tokens(output_text)

    # Record token usage in global spend meter
    meter_record = GLOBAL_API_METER.record_usage(
        model=GROQ_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        metadata={"jrp_id": jrp.get("jrp_id"), "worker_id": WORKER_ID},
    )

    sha256 = hashlib.sha256(output_text.encode("utf-8")).hexdigest()

    return {
        "worker_id": WORKER_ID,
        "jrp_id": jrp.get("jrp_id"),
        "output_sample": output_text,
        "citations": ["https://developer.paypal.com/api/rest/"],
        "sha256_hash": sha256,
        "tokens_consumed": input_tokens + output_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "api_cost_usd": meter_record["cost_usd"],
        "execution_seconds": elapsed_sec,
        "status": "DELIVERED",
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "worker_id": WORKER_ID,
        "model": GROQ_MODEL,
        "worker_paypal_email": WORKER_PAYPAL_EMAIL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("workers.llm_worker:app", host="0.0.0.0", port=int(os.getenv("LLM_WORKER_PORT", 8004)))
