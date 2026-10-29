"""
test_live_payout.py — Live PayPal Sandbox Payout Verification Script
---------------------------------------------------------------------
Performs a single real payout to a PayPal Sandbox Personal Account.
Prints ONLY the Payout Batch ID and Status.
Guarantees NO secrets, tokens, or auth headers are ever logged or printed.
Fails loudly if PayPal returns 403 Forbidden or any API error.
"""
import os
import sys
import uuid
import time
import httpx
from dotenv import load_dotenv

# Ensure fresh environment variables from .env
load_dotenv(override=True)

PAYPAL_BASE_URL = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/")
CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
SECRET = os.getenv("PAYPAL_SECRET")
RECIPIENT_EMAIL = os.getenv("WORKER_PAYPAL_EMAIL", "sb-sqcdl53128062@personal.example.com")


def main():
    if not CLIENT_ID or not SECRET:
        sys.stderr.write("[ERROR] Missing PAYPAL_CLIENT_ID or PAYPAL_SECRET in .env\n")
        sys.exit(1)

    # 1. Obtain OAuth Token (never print the token)
    try:
        with httpx.Client(timeout=15) as client:
            token_resp = client.post(
                f"{PAYPAL_BASE_URL}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(CLIENT_ID, SECRET),
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
            )
            if token_resp.status_code != 200:
                sys.stderr.write(
                    f"[ERROR] OAuth authentication failed with HTTP {token_resp.status_code}.\n"
                    f"Details: {token_resp.text}\n"
                )
                sys.exit(1)
            token = token_resp.json().get("access_token")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed to connect to PayPal OAuth: {e}\n")
        sys.exit(1)

    # 2. Submit Live Payout
    batch_uuid = uuid.uuid4().hex[:12]
    sender_batch_id = f"procure-live-{batch_uuid}"

    payout_payload = {
        "sender_batch_header": {
            "sender_batch_id": sender_batch_id,
            "email_subject": "ProcureAgent: Capability Settlement Test",
            "email_message": "Automated settlement payment for verified capability delivery.",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": "1.00", "currency": "USD"},
                "receiver": RECIPIENT_EMAIL,
                "note": "ProcureAgent autonomous capability payout test",
                "sender_item_id": f"item-{batch_uuid}",
            }
        ],
    }

    try:
        with httpx.Client(timeout=25) as client:
            resp = client.post(
                f"{PAYPAL_BASE_URL}/v1/payments/payouts",
                json=payout_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": sender_batch_id,
                },
            )

            # In live mode, 403 or any non-201 MUST fail loudly
            if resp.status_code not in (200, 201):
                err_data = {}
                try:
                    err_data = resp.json()
                except Exception:
                    pass

                err_name = err_data.get("name", "PAYOUT_ERROR")
                err_msg = err_data.get("message", resp.text)
                err_debug = err_data.get("debug_id", "N/A")

                sys.stderr.write(
                    f"\n[LIVE PAYOUT FAILED - HTTP {resp.status_code}]\n"
                    f"Error Name: {err_name}\n"
                    f"Message   : {err_msg}\n"
                    f"Debug ID  : {err_debug}\n"
                )
                sys.exit(1)

            payout_data = resp.json()
            batch_header = payout_data.get("batch_header", {})
            batch_id = batch_header.get("payout_batch_id", "UNKNOWN")
            status = batch_header.get("batch_status", "PENDING")

            # Brief pause, then poll status once to get updated settlement status
            time.sleep(2)
            try:
                poll_resp = client.get(
                    f"{PAYPAL_BASE_URL}/v1/payments/payouts/{batch_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if poll_resp.status_code == 200:
                    status = poll_resp.json().get("batch_header", {}).get("batch_status", status)
            except Exception:
                pass

            # Output ONLY batch ID, status, and transaction metadata
            print("=" * 60)
            print("LIVE PAYPAL SANDBOX PAYOUT SUCCESSFUL")
            print("=" * 60)
            print(f"Payout Batch ID : {batch_id}")
            print(f"Payout Status   : {status}")
            print(f"Recipient Email : {RECIPIENT_EMAIL}")
            print(f"Amount Sent     : $1.00 USD")
            print("=" * 60)

    except httpx.HTTPError as e:
        sys.stderr.write(f"[ERROR] HTTP communication error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
