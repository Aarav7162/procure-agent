"""
verifier.py — Two-Stage Delivery Verification Engine
  Stage 1: Integrity Check (SHA-256 Digest Match)
  Stage 2: Acceptance Check (Schema compliance, item count, ground-truth spot check)
"""
import os
import json
import hashlib
from typing import Tuple, Dict, Any

GROUND_TRUTH_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_ground_truth.json")
)


def load_ground_truth() -> dict:
    if os.path.exists(GROUND_TRUTH_PATH):
        with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def verify_integrity(output_data: str, claimed_hash: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Stage 1: Verifies whether the raw payload bytes match the worker's claimed digest.
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


def verify_acceptance(jrp: dict, delivery: dict) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Stage 2: Independent acceptance verification.
    Validates:
      1. Output format is valid JSONL with required fields.
      2. Item count satisfies acceptance criteria.
      3. Content spot check: text must not contain corrupted/adversarial tokens
         and must match ground-truth structure.
    """
    task_type = jrp.get("task_type", "ocr_batch")
    criteria = jrp.get("acceptance_criteria", {})
    min_items = criteria.get("min_items_processed", 1)

    items_processed = delivery.get("items_processed", 0)
    if items_processed < min_items:
        return False, f"Acceptance failed: processed {items_processed} items < required {min_items}", {
            "items_processed": items_processed,
            "min_items_required": min_items,
        }

    output_sample = delivery.get("output_sample", "")
    if not output_sample or not output_sample.strip():
        return False, "Acceptance failed: output payload is completely empty", {"records_inspected": 0}

    lines = [line.strip() for line in output_sample.splitlines() if line.strip()]
    if not lines:
        return False, "Acceptance failed: zero valid lines in output", {"records_inspected": 0}

    gt_data = load_ground_truth().get(task_type, {})
    required_fields = gt_data.get("required_fields", ["doc_id", "text"])
    forbidden_patterns = gt_data.get("forbidden_patterns", ["BOGUS", "CORRUPTED", "EMPTY_PAYLOAD"])

    parsed_records = []
    for idx, line in enumerate(lines):
        try:
            record = json.loads(line)
            parsed_records.append(record)
        except json.JSONDecodeError as e:
            return False, f"Acceptance failed: line #{idx+1} is not valid JSON ({e})", {"invalid_line": line[:60]}

        # Check required fields
        for field in required_fields:
            if field not in record:
                return False, f"Acceptance failed: line #{idx+1} missing required field '{field}'", {"record": record}

        # Spot-check text content for corruption/adversarial patterns
        text_val = str(record.get("text", ""))
        for pattern in forbidden_patterns:
            if pattern in text_val.upper():
                return False, f"Acceptance failed: ground-truth spot check detected adversarial/bogus token '{pattern}' in record #{idx+1}", {
                    "corrupted_record": record,
                    "forbidden_token": pattern,
                }

        # Check confidence threshold for OCR if available
        if "confidence" in record:
            conf = float(record["confidence"])
            if conf < 0.70:
                return False, f"Acceptance failed: confidence score {conf:.2f} below minimum threshold (0.70)", {"record": record}

    return True, f"Acceptance verified: {len(parsed_records)} sample records satisfy schema, threshold, and ground-truth spot checks", {
        "records_inspected": len(parsed_records),
        "task_type": task_type,
        "schema_valid": True,
        "ground_truth_passed": True,
    }


def verify_delivery(jrp: dict, delivery: dict) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Combined Two-Stage Verification Pipeline:
      Stage 1: verify_integrity (SHA-256)
      Stage 2: verify_acceptance (Schema + Ground Truth)
    Returns (passed: bool, stage_status: str, full_report: dict).
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
        }

    # Stage 2: Acceptance
    ok_acc, msg_acc, details_acc = verify_acceptance(jrp, delivery)
    if not ok_acc:
        return False, "ACCEPTANCE_FAILED", {
            "stage": "STAGE_2_ACCEPTANCE",
            "message": msg_acc,
            "integrity": details_int,
            "acceptance": details_acc,
        }

    return True, "VERIFIED", {
        "stage": "ALL_PASSED",
        "message": "Both Integrity (SHA-256) and Acceptance (Ground-Truth) passed successfully.",
        "integrity": details_int,
        "acceptance": details_acc,
    }
