"""
jrp_builder.py — Free-Form Job Request Packet (JRP) Builder
------------------------------------------------------------
Constructs technical JRPs from arbitrary natural-language tasks via Groq LLM.
No predefined task-type enums. Derives required capabilities and verifiable acceptance rules.
"""
import os
import uuid
import json
from datetime import datetime, timezone
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
WORKER_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """You are ProcureAgent's autonomous task specification generator.
Given any free-form natural language task description and an allocated budget, analyze the task and output a JSON Job Request Packet (JRP).
You must analyze the task to determine what technical capabilities are needed and formulate verifiable acceptance rules.
Output JSON with EXACTLY these fields:
{
  "task_description": string (clear technical summary of the goal),
  "required_capabilities": array of strings (e.g. ["document_ocr", "text_extraction"], ["python_coding", "unit_testable_functions"], ["web_research", "citation_verification"], ["data_extraction"]),
  "acceptance_criteria_text": string (plain-language summary of criteria for the judge),
  "acceptance_rules": [
    // Include applicable rules based on task type:
    // For structured output: {"type": "schema", "required_fields": ["..."]}
    // For OCR/transcription: {"type": "cer_threshold", "max_cer": 0.05}
    // For coding tasks: {"type": "unit_test", "test_suite_code": "def run_tests(): ..."}
    // For web research: {"type": "citation_check", "required_keywords": ["..."]}
    // Always include a judge rule for semantic validation: {"type": "llm_judge", "criteria": "..."}
  ],
  "max_bid_usd": float (must be <= provided max budget),
  "deadline_seconds": integer
}
Output ONLY valid JSON, no markdown fences, no explanation outside JSON."""


def build_jrp(task_description: str, max_budget_usd: float, cycle_id: str) -> dict:
    """Use live LLM API to parse free-form task into a structured JRP."""
    prompt = f"TASK DESCRIPTION:\n{task_description}\n\nMAX ALLOCATED BUDGET: ${max_budget_usd:.2f}"

    response = client.chat.completions.create(
        model=WORKER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1500,
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

    # Validate and clamp max_bid_usd
    if not parsed.get("max_bid_usd") or float(parsed["max_bid_usd"]) <= 0:
        parsed["max_bid_usd"] = round(max_budget_usd, 2)
    else:
        parsed["max_bid_usd"] = min(round(float(parsed["max_bid_usd"]), 2), round(max_budget_usd, 2))

    # Ensure required_capabilities is a non-empty list of normalized strings
    caps = parsed.get("required_capabilities", [])
    if isinstance(caps, str):
        caps = [caps]
    parsed["required_capabilities"] = [str(c).lower().strip() for c in caps if c]
    if not parsed["required_capabilities"]:
        parsed["required_capabilities"] = ["general_ai_execution"]

    # Ensure acceptance_rules is a list
    if not isinstance(parsed.get("acceptance_rules"), list):
        parsed["acceptance_rules"] = []

    # Inject infrastructure IDs
    parsed["jrp_id"] = str(uuid.uuid4())
    parsed["cycle_id"] = cycle_id
    parsed["status"] = "OPEN"
    parsed["created_at"] = datetime.now(timezone.utc).isoformat()

    return parsed


def build_jrp_direct(
    task_description: str,
    required_capabilities: list[str],
    acceptance_rules: list[dict],
    max_bid_usd: float,
    cycle_id: str,
    deadline_seconds: int = 60,
) -> dict:
    """Builds a structured JRP directly without LLM (used in unit tests and deterministic benchmark runs)."""
    return {
        "jrp_id": str(uuid.uuid4()),
        "cycle_id": cycle_id,
        "task_description": task_description,
        "required_capabilities": [c.lower().strip() for c in required_capabilities],
        "acceptance_criteria_text": "Satisfy all specified acceptance rules",
        "acceptance_rules": acceptance_rules,
        "max_bid_usd": round(max_bid_usd, 2),
        "deadline_seconds": deadline_seconds,
        "status": "OPEN",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
