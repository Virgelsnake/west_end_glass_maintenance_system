"""
Standalone WhatsApp text message smoke test.

AUTHENTICATION:
    The system uses phone number whitelisting for technician authentication.
    Employee phone numbers are validated against the database.
    Default technician: +15551234567 (John Smith)

Usage (from project root):
    cd test
    python test_whatsapp_text.py

    # Or with a custom recipient / message:
    python test_whatsapp_text.py --to +15551234567 --msg "Hello from West End Glass!"

Reads credentials from  ../backend_api/.env  (no running server required).
Requires:  pip install httpx python-dotenv
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from  backend_api/  regardless of where the script is invoked from
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit(
        "Missing dependency: run  pip install python-dotenv  then retry."
    )

try:
    import httpx
except ImportError:
    sys.exit("Missing dependency: run  pip install httpx  then retry.")

_ENV_PATH = Path(__file__).resolve().parent.parent / "backend_api" / ".env"
if not _ENV_PATH.exists():
    sys.exit(f"Could not find .env at {_ENV_PATH}")

load_dotenv(_ENV_PATH)

# ---------------------------------------------------------------------------
# Meta Cloud API constants
# ---------------------------------------------------------------------------
WHATSAPP_API_BASE = "https://graph.facebook.com/v19.0"

# ---------------------------------------------------------------------------
# Core send function (mirrors app/services/whatsapp.py)
# ---------------------------------------------------------------------------

async def send_text_message(to: str, text: str) -> dict:
    token = os.environ.get("META_WHATSAPP_TOKEN", "")
    phone_number_id = os.environ.get("META_PHONE_NUMBER_ID", "")

    if not token or token == "your_permanent_access_token_here":
        raise EnvironmentError(
            "META_WHATSAPP_TOKEN is not set in backend_api/.env — "
            "add your real access token and retry."
        )
    if not phone_number_id or phone_number_id == "your_phone_number_id_here":
        raise EnvironmentError(
            "META_PHONE_NUMBER_ID is not set in backend_api/.env — "
            "add your real phone number ID and retry."
        )

    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    print(f"  POST {url}")
    print(f"  To : {to}")
    print(f"  Msg: {text!r}")
    print()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers=headers)

    print(f"  HTTP {resp.status_code}")
    try:
        data = resp.json()
        print(f"  Response: {data}")
    except Exception:
        print(f"  Raw body: {resp.text}")
        data = {}

    resp.raise_for_status()
    return data


async def main(to: str, msg: str) -> None:
    print("=" * 60)
    print("  West End Glass — WhatsApp Text Send Test")
    print("=" * 60)
    print()

    try:
        result = await send_text_message(to, msg)
        message_id = (
            result.get("messages", [{}])[0].get("id", "—")
            if result.get("messages")
            else "—"
        )
        print()
        print(f"  SUCCESS  message_id={message_id}")
    except EnvironmentError as exc:
        print(f"\n  CONFIG ERROR: {exc}")
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(f"\n  API ERROR {exc.response.status_code}: {exc.response.text}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n  UNEXPECTED ERROR: {exc}")
        sys.exit(1)

    print()
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a WhatsApp test message.")
    parser.add_argument(
        "--to",
        default="+15551234567",
        help="Recipient phone number in E.164 format (default: +15551234567 — John Smith)",
    )
    parser.add_argument(
        "--msg",
        default="Hello from West End Glass! This is a connectivity test.",
        help="Message body to send",
    )
    args = parser.parse_args()

    asyncio.run(main(args.to, args.msg))
