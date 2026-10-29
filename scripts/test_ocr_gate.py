"""
scripts/test_ocr_gate.py — Real OCR Gate Test Suite (Alpha vs. Beta vs. Rogue)
-------------------------------------------------------------------------------
Evaluates real OCR execution on scans in data/real_scans/:
  1. Inspects data/real_scans/ for image files and companion .txt ground-truth transcripts.
  2. Runs ocr-worker-01 (Alpha, raw Tesseract PSM 3) on every scan.
  3. Runs ocr-worker-02 (Beta, preprocessed binarized Tesseract PSM 6) on every scan.
  4. Calculates exact Character Error Rate (CER = Levenshtein Distance / Ref Length).
  5. Compares speed, pricing ($0.70 vs $0.65), and accuracy per worker per document.
  6. Executes a full live adversarial flow:
     - Rogue worker underbids ($0.30) with plausible-wrong OCR (CER > 5%).
     - Verification fails; reservation is released; Rogue is paid $0.00.
     - Task is dynamically reallocated to the winning honest OCR worker.
     - Real PayPal Sandbox payout is sent in PAYOUT_MODE=live.
     - Reports real PayPal batch ID and final status.
"""
import os
import sys
import time
import json
import sqlite3
import hashlib
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestrator.verifier import compute_cer, verify_delivery
from orchestrator.treasury import (
    init_ledger,
    reserve_budget,
    release_reservation,
    send_payout,
    poll_and_reconcile_payout,
    get_budget_state,
    DB_PATH,
)
from workers.ocr_worker import do_work as alpha_work, bid as alpha_bid, TESSERACT_BIN as ALPHA_TESS
from workers.ocr_worker_beta import do_work as beta_work, bid as beta_bid, TESSERACT_BIN as BETA_TESS

load_dotenv()

SCANS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "real_scans"))


def find_available_scans() -> List[Dict[str, str]]:
    """Discovers paired images and companion transcripts in data/real_scans/."""
    valid_exts = (".png", ".jpg", ".jpeg", ".tif", ".tiff")
    pairs = []
    if not os.path.exists(SCANS_DIR):
        return pairs

    for fname in os.listdir(SCANS_DIR):
        base, ext = os.path.splitext(fname)
        if ext.lower() in valid_exts:
            img_path = os.path.join(SCANS_DIR, fname)
            txt_path = os.path.join(SCANS_DIR, f"{base}.txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    ground_truth = f.read().strip()
                pairs.append({
                    "name": fname,
                    "image_path": img_path,
                    "txt_path": txt_path,
                    "ground_truth": ground_truth,
                })
    return pairs


async def run_ocr_benchmark_and_gate():
    print("=" * 70)
    print("REAL OCR GATE: Alpha vs Beta Benchmark & Live Adversarial Settlement")
    print("=" * 70)

    payout_mode = os.getenv("PAYOUT_MODE", "simulated").strip().lower()
    print(f"  PAYOUT_MODE: {payout_mode.upper()}")
    print(f"  Tesseract Detected: Alpha={bool(ALPHA_TESS)}, Beta={bool(BETA_TESS)}")
    assert ALPHA_TESS and BETA_TESS, "Tesseract binary must be installed and detected!"

    scans = find_available_scans()
    print(f"  Scans Directory: {SCANS_DIR}")
    print(f"  Discovered Paired Scans with Ground-Truth Transcripts: {len(scans)}")

    if not scans:
        print("\n[PAUSED] No image-transcript pairs found in data/real_scans/.")
        print("  Expected files: doc_01.png + doc_01.txt (human-typed ground truth).")
        print("  The OCR gate cannot pass until real scans are placed in data/real_scans/.")
        return False, "AWAITING_USER_SCANS", {}

    results = []
    print("\n" + "-" * 70)
    print(f"{'Document':<16} | {'Worker':<14} | {'Bid ($)':<8} | {'Time (s)':<9} | {'CER (%)':<9} | {'Status'}")
    print("-" * 70)

    for item in scans:
        doc_name = item["name"]
        ref_text = item["ground_truth"]
        jrp_dummy = {
            "jrp_id": f"jrp_ocr_{doc_name}",
            "image_path": item["image_path"],
            "required_capabilities": ["document_ocr"],
            "max_bid_usd": 5.0,
        }

        # 1. Run Worker Alpha (Raw PSM 3)
        b_alpha = await alpha_bid(jrp_dummy)
        w_alpha = await alpha_work({"jrp": jrp_dummy})
        cer_alpha = compute_cer(ref_text, w_alpha["output_sample"])
        results.append({
            "doc": doc_name,
            "worker_id": "ocr-worker-01",
            "name": "Alpha (Raw PSM3)",
            "bid_usd": b_alpha["bid_usd"],
            "seconds": w_alpha["execution_seconds"],
            "cer": cer_alpha,
            "output": w_alpha["output_sample"],
        })
        print(f"{doc_name:<16} | {'ocr-worker-01':<14} | ${b_alpha['bid_usd']:<7.2f} | {w_alpha['execution_seconds']:<9.4f} | {cer_alpha:<9.2%} | {'PASS' if cer_alpha <= 0.05 else 'FAIL'}")

        # 2. Run Worker Beta (Preprocessed Binarized PSM 6)
        b_beta = await beta_bid(jrp_dummy)
        w_beta = await beta_work({"jrp": jrp_dummy})
        cer_beta = compute_cer(ref_text, w_beta["output_sample"])
        results.append({
            "doc": doc_name,
            "worker_id": "ocr-worker-02",
            "name": "Beta (Preproc PSM6)",
            "bid_usd": b_beta["bid_usd"],
            "seconds": w_beta["execution_seconds"],
            "cer": cer_beta,
            "output": w_beta["output_sample"],
        })
        print(f"{doc_name:<16} | {'ocr-worker-02':<14} | ${b_beta['bid_usd']:<7.2f} | {w_beta['execution_seconds']:<9.4f} | {cer_beta:<9.2%} | {'PASS' if cer_beta <= 0.05 else 'FAIL'}")

    print("-" * 70)

    # Calculate overall metrics
    alpha_avg_cer = sum(r["cer"] for r in results if r["worker_id"] == "ocr-worker-01") / len(scans)
    beta_avg_cer = sum(r["cer"] for r in results if r["worker_id"] == "ocr-worker-02") / len(scans)
    alpha_avg_sec = sum(r["seconds"] for r in results if r["worker_id"] == "ocr-worker-01") / len(scans)
    beta_avg_sec = sum(r["seconds"] for r in results if r["worker_id"] == "ocr-worker-02") / len(scans)
    alpha_bid_price = [r["bid_usd"] for r in results if r["worker_id"] == "ocr-worker-01"][0]
    beta_bid_price = [r["bid_usd"] for r in results if r["worker_id"] == "ocr-worker-02"][0]

    cheaper_worker = "ocr-worker-02 (Beta)" if beta_bid_price < alpha_bid_price else "ocr-worker-01 (Alpha)"
    more_accurate_worker = "ocr-worker-02 (Beta)" if beta_avg_cer < alpha_avg_cer else "ocr-worker-01 (Alpha)"

    print("\n[Measured Comparison Summary]")
    print(f"  Cheaper Worker       : {cheaper_worker} (${min(alpha_bid_price, beta_bid_price):.2f} vs ${max(alpha_bid_price, beta_bid_price):.2f})")
    print(f"  More Accurate Worker : {more_accurate_worker} (Avg CER: {min(alpha_avg_cer, beta_avg_cer):.2%} vs {max(alpha_avg_cer, beta_avg_cer):.2%})")
    print(f"  Speed Difference     : Alpha={alpha_avg_sec:.4f}s avg vs Beta={beta_avg_sec:.4f}s avg")

    # Step 2: Live Adversarial Run with Rogue OCR Worker
    print("\n" + "=" * 70)
    print("LIVE ADVERSARIAL OCR FLOW (Rogue Underbid -> Block -> Live Reallocation)")
    print("=" * 70)

    cycle_id = f"ocr_live_cycle_{int(time.time())}"
    max_budget = 15.00
    init_ledger()

    # Target doc_04 (clean paragraph scan where honest Tesseract achieves 0% CER)
    target_doc = next((s for s in scans if "doc_04" in s["name"]), scans[0])
    jrp_live = {
        "jrp_id": f"jrp_ocr_live_{cycle_id}",
        "cycle_id": cycle_id,
        "task_description": f"Transcribe scanned document {target_doc['name']} with high fidelity",
        "required_capabilities": ["document_ocr"],
        "max_bid_usd": 5.00,
        "acceptance_rules": [
            {"type": "cer_threshold", "max_cer": 0.05, "reference_text": target_doc["ground_truth"]}
        ],
    }

    rogue_email = os.getenv("ROGUE_PAYPAL_EMAIL", "sb-a43fio53613334@personal.example.com")
    # Honest winner selected based on benchmark accuracy
    honest_worker_id = "ocr-worker-02" if beta_avg_cer < alpha_avg_cer else "ocr-worker-01"
    honest_email = os.getenv("OCR_BETA_PAYPAL_EMAIL") if honest_worker_id == "ocr-worker-02" else os.getenv("WORKER_PAYPAL_EMAIL")
    honest_bid = beta_bid_price if honest_worker_id == "ocr-worker-02" else alpha_bid_price

    # 1. Rogue underbids
    rogue_bid_usd = 0.30
    print(f"  Target Document: {target_doc['name']}")
    print(f"  Rogue Worker underbids: ${rogue_bid_usd:.2f} [Email: {rogue_email}]")
    print(f"  Honest Worker ({honest_worker_id}) bids: ${honest_bid:.2f} [Email: {honest_email}]")

    # 2. Awarded to Rogue
    ok_res_r, res_id_r, _ = reserve_budget(cycle_id, jrp_live["jrp_id"], "rogue-worker-01", rogue_bid_usd, max_budget)
    assert ok_res_r is True

    # 3. Rogue delivers plausible-wrong OCR (realistic scanning noise: CER ~ 7.8% > 5%)
    clean_ref = target_doc["ground_truth"]
    substitutions = {"e": "c", "E": "C", "o": "0", "O": "0", "l": "1", "I": "1", "a": "e", "A": "4", "s": "5"}
    chars = list(clean_ref)
    for idx in range(0, len(chars), 13):
        c = chars[idx]
        if c in substitutions:
            chars[idx] = substitutions[c]
        elif c.isalpha():
            chars[idx] = "r" if c.islower() else "R"
    rogue_ocr_text = "".join(chars)
    rogue_cer = compute_cer(clean_ref, rogue_ocr_text)
    print(f"  Rogue Defect Generation: CER={rogue_cer:.2%} (Threshold <= 5.00%)")
    rogue_sha = hashlib.sha256(rogue_ocr_text.encode("utf-8")).hexdigest()

    rogue_delivery = {
        "worker_id": "rogue-worker-01",
        "output_sample": rogue_ocr_text,
        "sha256_hash": rogue_sha,
    }

    ok_v_r, status_v_r, rep_v_r = verify_delivery(jrp_live, rogue_delivery)
    print(f"  Rogue Verification: ok={ok_v_r}, status={status_v_r} -> {rep_v_r.get('message')}")
    assert ok_v_r is False, "Rogue OCR with distorted characters must fail CER threshold!"

    # 4. Release Rogue Reservation
    release_reservation(res_id_r, reason=f"Rejected: {rep_v_r.get('message')}")
    print("  Rogue reservation released ($0.00 paid).")

    # 5. Reallocate to Honest Winner
    print(f"  Reallocating task to {honest_worker_id}...")
    ok_res_h, res_id_h, _ = reserve_budget(cycle_id, jrp_live["jrp_id"], honest_worker_id, honest_bid, max_budget)
    assert ok_res_h is True

    # 6. Honest worker processes document
    if honest_worker_id == "ocr-worker-02":
        honest_work_resp = await beta_work({"jrp": {"image_path": target_doc["image_path"], "jrp_id": jrp_live["jrp_id"]}})
    else:
        honest_work_resp = await alpha_work({"jrp": {"image_path": target_doc["image_path"], "jrp_id": jrp_live["jrp_id"]}})

    ok_v_h, status_v_h, rep_v_h = verify_delivery(jrp_live, honest_work_resp)
    print(f"  Honest Worker Verification: ok={ok_v_h}, status={status_v_h}")
    assert ok_v_h is True, "Honest worker OCR output must pass CER check!"

    # 7. Real PayPal Live Payout
    print(f"\n  Submitting REAL LIVE PayPal Payout to {honest_worker_id} ({honest_email})...")
    payout_res = send_payout(
        cycle_id=cycle_id,
        jrp_id=jrp_live["jrp_id"],
        worker_id=honest_worker_id,
        worker_email=honest_email,
        amount_usd=honest_bid,
        sha256_hash=honest_work_resp["sha256_hash"],
        reservation_id=res_id_h,
        max_budget_usd=max_budget,
    )

    batch_id = payout_res["payout_batch_id"]
    print(f"  PayPal Batch ID: {batch_id}")
    print(f"  Polling for final status...")
    reconciled = poll_and_reconcile_payout(batch_id, max_attempts=12, interval_sec=2.0)
    final_status = reconciled.get("final_status", payout_res["status"])
    print(f"  Final Payout Status: {final_status}")

    # 8. Assertions
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_email = ?", (cycle_id, rogue_email))
    r_count, r_paid = cur.fetchone()
    assert r_paid == 0.0, "Rogue must receive $0.00!"

    cur.execute("SELECT COUNT(*), COALESCE(SUM(bid_usd), 0.0) FROM ledger WHERE cycle_id = ? AND worker_email = ?", (cycle_id, honest_email))
    h_count, h_paid = cur.fetchone()
    assert h_paid == honest_bid, f"Honest worker must receive ${honest_bid}!"
    conn.close()

    print("\n" + "=" * 70)
    print("REAL OCR GATE PASSED SUCCESSFULLY!")
    print(f"  Batch ID               : {batch_id}")
    print(f"  Batch Status           : {final_status}")
    print(f"  Cheaper Worker         : {cheaper_worker}")
    print(f"  More Accurate Worker   : {more_accurate_worker}")
    print("=" * 70)
    return True, batch_id, {
        "cheaper": cheaper_worker,
        "more_accurate": more_accurate_worker,
        "batch_id": batch_id,
        "status": final_status,
        "results": results,
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_ocr_benchmark_and_gate())
