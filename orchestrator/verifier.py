"""
verifier.py — Two-Stage Delivery Verification Engine
-----------------------------------------------------
Stage 1: Cryptographic Integrity (SHA-256 Digest Match)
Stage 2: Acceptance Verification (Two Layers):
  Layer 1 - Hard Checks (Deterministic):
    • OCR: Character Error Rate (CER) against human ground-truth transcripts (Levenshtein distance <= 5%).
    • Code: Hidden unit test execution in a sandboxed subprocess with timeout.
    • Research: HTTP citation resolution (200 OK) + fact presence verification.
    • General: Schema compliance & invariant math validation.
  Layer 2 - Independent LLM Judge:
    • Evaluates semantic completeness using Qwen 27B (different model from worker's GPT-OSS).
    • Instructed to look for errors, not confirm.
    • Programmatic quote verification: every piece of evidence quoted by the judge must
      appear verbatim in the source material or worker output. Unverifiable quotes fail immediately.
Basis Tracking:
  Records basis as 'HARD_CHECK', 'JUDGE_ONLY', or 'BOTH'.
  Judge-only approvals are explicitly labeled 'LOWER_CONFIDENCE (JUDGE_ONLY)'.
"""
import os
import sys
import json
import uuid
import httpx
import hashlib
import subprocess
import tempfile
from typing import Tuple, Dict, Any, List, Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Independent Judge Model (different model family from worker's openai/gpt-oss-120b)
JUDGE_MODEL = os.getenv("GROQ_JUDGE_MODEL", "qwen/qwen3.8-27b")


# ─────────────────────────────────────────────
# Stage 1: Cryptographic Integrity Verification
# ─────────────────────────────────────────────

def verify_integrity(output_data: str, claimed_hash: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Stage 1: Verifies whether raw payload bytes match the worker's claimed digest.
    Proves transmission integrity, NOT correctness.
    """
    if not output_data or not claimed_hash:
        return False, "Missing output data or SHA-256 digest", {"computed": "", "claimed": claimed_hash}

    computed_hash = hashlib.sha256(output_data.encode("utf-8")).hexdigest()
    match = (computed_hash == claimed_hash)

    details = {
        "computed_hash": computed_hash,
        "claimed_hash": claimed_hash,
        "match": match,
    }

    if not match:
        return False, f"Integrity violation: computed {computed_hash[:16]}... != claimed {claimed_hash[:16]}...", details

    return True, "Integrity verified: SHA-256 digest matches payload bytes", details


# ─────────────────────────────────────────────
# Stage 2 (Layer 1): Deterministic Hard Checks
# ─────────────────────────────────────────────

def levenshtein_distance(s1: str, s2: str) -> int:
    """Computes exact Levenshtein edit distance in pure Python."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalize_ocr_text(text: str) -> str:
    """
    Standard OCR text normalization rule:
    1. Removes decorative separator lines consisting solely of repeated symbols
       (e.g., '---', '===', '___') which OCR engines treat as graphical horizontal rules
       rather than semantic text characters.
    2. Collapses multi-line whitespace and column padding into single spaces.
    """
    import re
    lines = [line.strip() for line in text.splitlines()]
    filtered = [l for l in lines if not re.match(r'^[-=_*~]{3,}$', l) and l]
    return " ".join(" ".join(filtered).split())


def compute_cer(reference: str, hypothesis: str) -> float:
    """
    Computes Character Error Rate (CER = Levenshtein Edit Distance / Normalized Reference Length).
    Applies standard OCR normalization (stripping graphic separator rules and collapsing whitespace).
    """
    ref_norm = normalize_ocr_text(reference)
    hyp_norm = normalize_ocr_text(hypothesis)
    if not ref_norm:
        return 0.0 if not hyp_norm else 1.0
    dist = levenshtein_distance(ref_norm, hyp_norm)
    return dist / len(ref_norm)


def verify_ocr_cer(reference_text: str, candidate_text: str, max_cer: float = 0.05) -> Tuple[bool, str, Dict[str, Any]]:
    """Hard Check: Verifies OCR output against ground-truth transcript via CER."""
    cer = compute_cer(reference_text, candidate_text)
    details = {
        "cer": round(cer, 4),
        "max_cer_allowed": max_cer,
        "reference_len": len(reference_text),
        "candidate_len": len(candidate_text),
    }
    if cer > max_cer:
        return False, f"OCR Hard Check Failed: Character Error Rate ({cer:.2%}) exceeds threshold ({max_cer:.2%})", details
    return True, f"OCR Hard Check Passed: Character Error Rate ({cer:.2%}) within tolerance", details


def verify_code_unit_tests(code_str: str, test_suite_code: str, timeout_sec: float = 3.0) -> Tuple[bool, str, Dict[str, Any]]:
    """Hard Check: Executes candidate code against hidden unit test suite in an isolated subprocess."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code_str + "\n\n" + test_suite_code)
        temp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        passed = (proc.returncode == 0)
        details = {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:500],
            "stderr": proc.stderr[:500],
        }
        if not passed:
            err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Exited with code {proc.returncode}"
            return False, f"Code Hard Check Failed: Hidden unit tests failed: {err_msg}", details
        return True, "Code Hard Check Passed: All hidden unit tests passed successfully", details
    except subprocess.TimeoutExpired:
        return False, f"Code Hard Check Failed: Execution timed out after {timeout_sec}s", {"timeout": True}
    except Exception as e:
        return False, f"Code Hard Check Failed: Subprocess error: {e}", {"error": str(e)}
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def verify_citations(citations: List[str], required_keywords: Optional[List[str]] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """Hard Check: Verifies citations are live HTTP URLs and optionally contain required fact keywords."""
    if not citations:
        return False, "Citation Hard Check Failed: No citations provided", {"citations": []}

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ProcureAgent-Verifier/1.0"}
    checked_results = []
    with httpx.Client(timeout=8, follow_redirects=True, headers=headers) as client:
        for url in citations:
            try:
                resp = client.get(url)
                if resp.status_code >= 400:
                    return False, f"Citation Hard Check Failed: Citation '{url}' returned HTTP {resp.status_code} (dead link)", {
                        "failed_url": url,
                        "status_code": resp.status_code,
                    }
                content = resp.text
                if required_keywords:
                    missing = [kw for kw in required_keywords if kw.lower() not in content.lower()]
                    if missing:
                        return False, f"Citation Hard Check Failed: Citation '{url}' missing claimed facts: {missing}", {
                            "url": url,
                            "missing_keywords": missing,
                        }
                checked_results.append({"url": url, "status": resp.status_code, "valid": True})
            except Exception as e:
                return False, f"Citation Hard Check Failed: Citation '{url}' unreachable ({e})", {"failed_url": url, "error": str(e)}

    return True, f"Citation Hard Check Passed: All {len(citations)} citations are live and verified", {"citations": checked_results}


def verify_schema(output_text: str, required_fields: List[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """Hard Check: Verifies JSON format and mandatory fields."""
    try:
        data = json.loads(output_text)
    except Exception as e:
        return False, f"Schema Hard Check Failed: Output is not valid JSON ({e})", {"raw": output_text[:100]}

    if isinstance(data, dict):
        missing = [f for f in required_fields if f not in data]
        if missing:
            return False, f"Schema Hard Check Failed: Missing mandatory fields: {missing}", {"missing": missing}
    elif isinstance(data, list):
        if not data:
            return False, "Schema Hard Check Failed: Output array is empty", {}
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                missing = [f for f in required_fields if f not in item]
                if missing:
                    return False, f"Schema Hard Check Failed: Item #{idx} missing fields: {missing}", {"missing": missing}

    return True, "Schema Hard Check Passed: JSON structure and required fields valid", {"fields_checked": required_fields}


# ─────────────────────────────────────────────
# Stage 2 (Layer 2): Independent LLM Judge
# ─────────────────────────────────────────────

def verify_llm_judge(
    task_description: str,
    acceptance_criteria: str,
    worker_output: str,
    source_material: str = "",
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Independent LLM Judge using Qwen 27B on Groq.
    Enforces programmatic quote verification: all quoted evidence must appear verbatim
    in worker_output or source_material. Unverifiable quotes fail immediately.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return False, "Judge Evaluation Failed: Missing GROQ_API_KEY", {}

    client = Groq(api_key=api_key)

    system_prompt = (
        "You are an adversarial, critical acceptance verifier for an autonomous AI procurement engine.\n"
        "Your task is to inspect the worker's output against the task description and acceptance criteria.\n"
        "INSTRUCTIONS:\n"
        "1. Look for flaws, omissions, inaccuracies, contradictions, or non-compliance. Do NOT assume correctness.\n"
        "2. For every criterion, you MUST provide 'quoted_evidence' which is an EXACT, verbatim substring copied from either the worker output or source material.\n"
        "3. Output MUST be valid JSON with this exact structure:\n"
        "{\n"
        '  "passed": boolean,\n'
        '  "evaluations": [\n'
        '    {"criterion": string, "status": "PASS"|"FAIL", "quoted_evidence": string, "reasoning": string}\n'
        "  ],\n"
        '  "summary": string\n'
        "}\n"
        "Output ONLY JSON. No explanation outside JSON."
    )

    user_prompt = (
        f"TASK:\n{task_description}\n\n"
        f"ACCEPTANCE CRITERIA:\n{acceptance_criteria}\n\n"
        f"SOURCE MATERIAL:\n{source_material or 'None provided'}\n\n"
        f"WORKER OUTPUT TO EVALUATE:\n{worker_output}\n"
    )

    try:
        resp = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.05,
            max_tokens=600,
        )
        raw_content = resp.choices[0].message.content.strip()
        # Clean markdown
        if "```" in raw_content:
            parts = raw_content.split("```")
            raw_content = parts[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
        start_idx = raw_content.find("{")
        end_idx = raw_content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            raw_content = raw_content[start_idx:end_idx + 1]

        judge_data = json.loads(raw_content)
        passed = bool(judge_data.get("passed", False))
        evaluations = judge_data.get("evaluations", [])

        # Programmatic Quoted Evidence Verification
        combined_text = (worker_output + " " + source_material).lower()
        unverified_quotes = []

        for ev in evaluations:
            quote = ev.get("quoted_evidence", "").strip().lower()
            if quote and len(quote) > 3:
                # Check if quote exists verbatim in output or source
                if quote not in combined_text:
                    unverified_quotes.append(ev.get("quoted_evidence"))

        if unverified_quotes:
            return False, f"Judge Verification Failed: Judge fabricated unverifiable evidence quotes: {unverified_quotes[:2]}", {
                "judge_model": JUDGE_MODEL,
                "unverified_quotes": unverified_quotes,
                "raw_verdict": judge_data,
            }

        if not passed:
            return False, f"Judge Verification Rejected: {judge_data.get('summary', 'Failed criteria')}", {
                "judge_model": JUDGE_MODEL,
                "evaluations": evaluations,
                "raw_verdict": judge_data,
            }

        return True, f"Judge Verification Passed: {judge_data.get('summary', 'All criteria satisfied with verified quotes')}", {
            "judge_model": JUDGE_MODEL,
            "evaluations": evaluations,
            "quotes_verified": len(evaluations),
        }

    except Exception as e:
        return False, f"Judge Evaluation Exception: {e}", {"judge_model": JUDGE_MODEL, "error": str(e)}


# ─────────────────────────────────────────────
# Unified Two-Stage Verification Pipeline
# ─────────────────────────────────────────────

def verify_delivery(jrp: dict, delivery: dict) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Two-Stage Verification Pipeline:
      Stage 1: Cryptographic Integrity (SHA-256 Digest Match)
      Stage 2: Acceptance Verification (Hard Checks + Independent LLM Judge)
    Returns:
      (is_verified: bool, status_tag: str, full_report: dict)
    """
    claimed_hash = delivery.get("sha256_hash", "")
    output_sample = delivery.get("output_sample", "")

    # Stage 1: Integrity
    ok_int, msg_int, details_int = verify_integrity(output_sample, claimed_hash)
    if not ok_int:
        return False, "INTEGRITY_FAILED", {
            "stage": "STAGE_1_INTEGRITY",
            "message": msg_int,
            "integrity": details_int,
            "acceptance": None,
            "basis": "NONE",
            "confidence": "REJECTED",
        }

    # Stage 2: Acceptance Rules Dispatch
    acceptance_rules = jrp.get("acceptance_rules", [])
    hard_check_results = []
    hard_checks_ran = False
    hard_checks_passed = True
    judge_ran = False
    judge_passed = True
    judge_details = {}

    for rule in acceptance_rules:
        rule_type = rule.get("type")

        # 1. OCR Character Error Rate (CER) Hard Check
        if rule_type == "cer_threshold":
            hard_checks_ran = True
            ref_text = rule.get("reference_text", "")
            max_cer = float(rule.get("max_cer", 0.05))
            ok_cer, msg_cer, det_cer = verify_ocr_cer(ref_text, output_sample, max_cer)
            hard_check_results.append({"type": "ocr_cer", "passed": ok_cer, "message": msg_cer, "details": det_cer})
            if not ok_cer:
                hard_checks_passed = False
                break

        # 2. Code Hidden Unit Test Hard Check
        elif rule_type == "unit_test":
            hard_checks_ran = True
            test_suite = rule.get("test_suite_code", "")
            ok_test, msg_test, det_test = verify_code_unit_tests(output_sample, test_suite)
            hard_check_results.append({"type": "unit_test", "passed": ok_test, "message": msg_test, "details": det_test})
            if not ok_test:
                hard_checks_passed = False
                break

        # 3. Citation Health Hard Check
        elif rule_type == "citation_check":
            hard_checks_ran = True
            citations = delivery.get("citations", [])
            kws = rule.get("required_keywords", [])
            ok_cit, msg_cit, det_cit = verify_citations(citations, kws)
            hard_check_results.append({"type": "citations", "passed": ok_cit, "message": msg_cit, "details": det_cit})
            if not ok_cit:
                hard_checks_passed = False
                break

        # 4. Schema Hard Check
        elif rule_type == "schema":
            hard_checks_ran = True
            req_fields = rule.get("required_fields", [])
            ok_sch, msg_sch, det_sch = verify_schema(output_sample, req_fields)
            hard_check_results.append({"type": "schema", "passed": ok_sch, "message": msg_sch, "details": det_sch})
            if not ok_sch:
                hard_checks_passed = False
                break

        # 5. LLM Judge Layer
        elif rule_type == "llm_judge":
            judge_ran = True
            task_desc = jrp.get("task_description", "")
            crit = rule.get("criteria", "Accuracy and adherence to specification")
            source_mat = rule.get("source_material", "")
            ok_j, msg_j, det_j = verify_llm_judge(task_desc, crit, output_sample, source_mat)
            judge_passed = ok_j
            judge_details = {"passed": ok_j, "message": msg_j, "details": det_j}
            if not ok_j:
                break

    # If no hard checks ran and judge was not explicitly listed, run Judge by default
    if not hard_checks_ran and not judge_ran:
        judge_ran = True
        task_desc = jrp.get("task_description", "")
        crit = jrp.get("acceptance_criteria_text", "Must satisfy user task description accurately")
        ok_j, msg_j, det_j = verify_llm_judge(task_desc, crit, output_sample)
        judge_passed = ok_j
        judge_details = {"passed": ok_j, "message": msg_j, "details": det_j}

    # Determine Basis and Confidence Label
    if hard_checks_ran and judge_ran:
        basis = "BOTH"
        confidence = "HIGH (CRYPTOGRAPHIC + DETERMINISTIC + JUDGE)"
    elif hard_checks_ran:
        basis = "HARD_CHECK"
        confidence = "HIGH (CRYPTOGRAPHIC + DETERMINISTIC)"
    else:
        basis = "JUDGE_ONLY"
        confidence = "LOWER_CONFIDENCE (JUDGE_ONLY)"

    overall_passed = hard_checks_passed and judge_passed

    if not overall_passed:
        failure_reason = "Hard check failure" if not hard_checks_passed else "Judge rejected output"
        # Find exact failure message
        failed_checks = [c["message"] for c in hard_check_results if not c["passed"]]
        if failed_checks:
            failure_reason = failed_checks[0]
        elif not judge_passed:
            failure_reason = judge_details.get("message", "Judge rejection")

        return False, "ACCEPTANCE_FAILED", {
            "stage": "STAGE_2_ACCEPTANCE",
            "message": failure_reason,
            "basis": basis,
            "confidence": confidence,
            "integrity": details_int,
            "hard_checks": hard_check_results,
            "judge": judge_details if judge_ran else None,
        }

    return True, "VERIFIED", {
        "stage": "ALL_PASSED",
        "message": f"Verified successfully via {basis} ({confidence})",
        "basis": basis,
        "confidence": confidence,
        "integrity": details_int,
        "hard_checks": hard_check_results,
        "judge": judge_details if judge_ran else None,
    }
