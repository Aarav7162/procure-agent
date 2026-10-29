"""
jrp_builder.py — Builds Job Request Packets from natural language via Groq LLM
"""
import os
import uuid
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

TASK_TYPE_MAP = {
    "ocr": "ocr_batch",
    "pdf": "ocr_batch",
    "scrape": "scrape_batch",
    "web": "scrape_batch",
    "embed": "embed_batch",
    "index": "embed_batch",
    "embedding": "embed_batch",
}

SYSTEM_PROMPT = """You are ProcureAgent's task parser. Given a natural language task description and a max budget, 
output a JSON Job Request Packet with EXACTLY these fields:
{
  "task_type": one of ["ocr_batch", "scrape_batch", "embed_batch"],
  "description": short technical description,
  "input_manifest": { "item_count": integer, "avg_size_kb": integer },
  "acceptance_criteria": { "min_items_processed": integer (95% of item_count), "output_format": "jsonl", "sha256_of_output_required": true },
  "max_bid_usd": float (set equal to or slightly below the provided max budget for this sub-task),
  "deadline_seconds": integer
}
Output ONLY valid JSON, no markdown, no explanation."""


def build_jrp(task_description: str, max_budget_usd: float, cycle_id: str) -> dict:
    """Use LLM to parse task and construct a JRP."""
    prompt = f"Task: {task_description}\nMax budget for this sub-task: ${max_budget_usd:.2f}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=512,
    )

    raw = response.choices[0].message.content.strip()
    # Strip any accidental markdown fences
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start_idx = raw.find("{")
    end_idx = raw.rfind("}")
    if start_idx != -1 and end_idx != -1:
        raw = raw[start_idx:end_idx + 1]

    parsed = json.loads(raw)

    # Ensure max_bid_usd is valid and capped at max_budget_usd
    if not parsed.get("max_bid_usd") or float(parsed["max_bid_usd"]) <= 0:
        parsed["max_bid_usd"] = round(max_budget_usd, 2)
    else:
        parsed["max_bid_usd"] = min(round(float(parsed["max_bid_usd"]), 2), round(max_budget_usd, 2))

    # Ensure min_items_processed in acceptance criteria is realistic (95% of item_count)
    item_count = parsed.get("input_manifest", {}).get("item_count", 100)
    if "acceptance_criteria" in parsed:
        parsed["acceptance_criteria"]["min_items_processed"] = int(item_count * 0.95)

    # Inject infrastructure fields
    parsed["jrp_id"] = str(uuid.uuid4())
    parsed["cycle_id"] = cycle_id
    parsed["status"] = "OPEN"

    return parsed



def build_jrp_manual(
    task_type: str,
    description: str,
    item_count: int,
    max_bid_usd: float,
    cycle_id: str,
    deadline_seconds: int = 120,
) -> dict:
    """Build a JRP directly without LLM (used in tests and simulation)."""
    return {
        "jrp_id": str(uuid.uuid4()),
        "cycle_id": cycle_id,
        "task_type": task_type,
        "description": description,
        "input_manifest": {"item_count": item_count, "avg_size_kb": 200},
        "acceptance_criteria": {
            "min_items_processed": int(item_count * 0.95),
            "output_format": "jsonl",
            "sha256_of_output_required": True,
        },
        "max_bid_usd": max_bid_usd,
        "deadline_seconds": deadline_seconds,
        "status": "OPEN",
    }
