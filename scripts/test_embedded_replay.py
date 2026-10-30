"""
tests/test_embedded_replay.py
------------------------------
Asserts that dashboard/index.html's embedded RECORDED_RUN object
was generated from and equals demo/recorded_runs/recorded_rogue_run.json
without manual edits or drift.
"""
import os
import re
import json
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT_DIR, "dashboard", "index.html")
RECORDED_RUN_PATH = os.path.join(ROOT_DIR, "demo", "recorded_runs", "recorded_rogue_run.json")


def extract_embedded_recorded_run() -> dict:
    """Extracts the JSON payload from `let RECORDED_RUN = ... ;` in dashboard/index.html."""
    assert os.path.exists(INDEX_PATH), f"Dashboard file not found: {INDEX_PATH}"
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    match = re.search(r'let RECORDED_RUN\s*=\s*(\{.*?\n\s*\});\s*\n\s*let CURRENT_MODE', html, re.DOTALL)
    assert match, "Could not find `let RECORDED_RUN = { ... };` in dashboard/index.html"
    json_str = match.group(1)
    return json.loads(json_str)


def test_embedded_replay_equals_file():
    """Assert that the embedded RECORDED_RUN in dashboard/index.html is identical to demo/recorded_runs/recorded_rogue_run.json."""
    assert os.path.exists(RECORDED_RUN_PATH), f"Source recorded run file not found: {RECORDED_RUN_PATH}"
    with open(RECORDED_RUN_PATH, "r", encoding="utf-8") as f:
        file_data = json.load(f)

    embedded_data = extract_embedded_recorded_run()

    # Deep equality assertion
    assert embedded_data == file_data, "Mismatch between dashboard/index.html RECORDED_RUN and demo/recorded_runs/recorded_rogue_run.json!"

    # Field-level verification
    assert embedded_data["title"] == file_data["title"]
    assert embedded_data["metadata"]["payout_mode"] == "live"
    assert embedded_data["metadata"]["paypal_batch_id"] == file_data["metadata"]["paypal_batch_id"]
    assert embedded_data["metadata"]["amount_usd"] == file_data["metadata"]["amount_usd"]
    assert len(embedded_data["events"]) == len(file_data["events"])
    assert len(embedded_data["events"]) > 0


if __name__ == "__main__":
    test_embedded_replay_equals_file()
    print("[PASS] test_embedded_replay_equals_file passed! Embedded replay exactly matches demo/recorded_runs/recorded_rogue_run.json.")
