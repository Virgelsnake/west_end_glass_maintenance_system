"""
Standalone WhatsApp smoke test — supports both free-form text and templates.

AUTHENTICATION:
    The system uses phone number whitelisting for technician authentication.
    Employee phone numbers are validated against the database.
    Default technician: +17692188324 (Joe Ronie)

Usage (from project root):
    # Free-form text (only works within a 24-hr session window):
    python test/test_whatsapp_text.py

    # Template message (works anytime, required for new conversations):
    python test/test_whatsapp_text.py --template test_maintenance_chat --params "Tech Name" "Date" "Service" "Machine ID"

    # Custom message body:
    python test/test_whatsapp_text.py --msg "Hello from test!"

    # Send to different number:
    python test/test_whatsapp_text.py --to +447717207677

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
    sys.exit("Missing dependency: run  pip install python-dotenv  then retry.")

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
# Template info helpers
# ---------------------------------------------------------------------------

def get_waba_id(token: str, phone_number_id: str) -> str | None:
    """Return WABA ID from env, or None if not set."""
    waba_id = os.environ.get("META_WABA_ID", "")
    if waba_id and waba_id != "your_waba_id_here":
        return waba_id
    print("  [META_WABA_ID not set in backend_api/.env]")
    print("  Find it: Meta Business Manager → Business Settings → WhatsApp Accounts")
    return None


async def print_template_info(template_name: str, token: str, phone_number_id: str) -> None:
    """Fetch and print template status and body from Meta."""
    print("  Template Info")
    print("  " + "-" * 40)
    waba_id = get_waba_id(token, phone_number_id)
    if not waba_id:
        print("  [could not resolve WABA ID — skipping template lookup]\n")
        return

    url = f"{WHATSAPP_API_BASE}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"name": template_name, "fields": "name,status,language,category,components"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        print(f"  [template lookup failed: HTTP {resp.status_code}]\n")
        return

    data = resp.json().get("data", [])
    if not data:
        print(f"  [no template found with name '{template_name}']\n")
        return

    for t in data:
        print(f"  Name     : {t.get('name')}")
        print(f"  Status   : {t.get('status')}")
        print(f"  Category : {t.get('category')}")
        print(f"  Language : {t.get('language')}")
        for comp in t.get("components", []):
            ctype = comp.get("type", "").upper()
            text = comp.get("text", "")
            if text:
                print(f"  [{ctype}]  {text}")
    print()


async def list_all_templates(token: str, phone_number_id: str) -> None:
    """Fetch and print all templates on the account with full details."""
    print("  Account Templates")
    print("  " + "-" * 56)

    waba_id = get_waba_id(token, phone_number_id)
    if not waba_id:
        print("  [could not resolve WABA ID]")
        return
    print(f"  WABA ID  : {waba_id}")
    print()

    url = f"{WHATSAPP_API_BASE}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"fields": "name,status,language,category,components", "limit": 100}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        print(f"  [API error: HTTP {resp.status_code}]")
        print(f"  {resp.text}")
        return

    templates = resp.json().get("data", [])
    if not templates:
        print("  [no templates found on this account]")
        return

    print(f"  Found {len(templates)} template(s):\n")
    for t in templates:
        status = t.get('status', '?')
        status_icon = "✓" if status == "APPROVED" else "✗" if status == "REJECTED" else "~"
        print(f"  [{status_icon}] {t.get('name')}")
        print(f"      Status   : {status}")
        print(f"      Category : {t.get('category')}")
        print(f"      Language : {t.get('language')}")
        for comp in t.get("components", []):
            ctype = comp.get("type", "").upper()
            text = comp.get("text", "")
            if text:
                print(f"      [{ctype}]  {text}")
        print()


# ---------------------------------------------------------------------------
# Send functions
# ---------------------------------------------------------------------------

async def send_text_message(to: str, text: str, token: str, phone_number_id: str) -> dict:
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    print(f"  POST {url}")
    print(f"  To   : {to}")
    print(f"  Mode : free-form text")
    print(f"  Msg  : {text!r}")
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


async def send_template_message(to: str, template_name: str, lang: str, token: str, phone_number_id: str, params: list[str] | None = None) -> dict:
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    template_obj = {
        "name": template_name,
        "language": {"code": lang},
    }
    
    # Add parameters if provided
    if params:
        template_obj["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in params]
            }
        ]
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template_obj,
    }

    print(f"  POST {url}")
    print(f"  To       : {to}")
    print(f"  Mode     : template")
    print(f"  Template : {template_name}  [{lang}]")
    if params:
        print(f"  Params   : {params}")
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(to: str, msg: str, template: str | None, lang: str, params: list[str] | None, list_templates: bool) -> None:
    print("=" * 60)
    print("  West End Glass — WhatsApp Send Test")
    print("=" * 60)
    print()

    token = os.environ.get("META_WHATSAPP_TOKEN", "")
    phone_number_id = os.environ.get("META_PHONE_NUMBER_ID", "")

    if not token or token == "your_permanent_access_token_here":
        print("  CONFIG ERROR: META_WHATSAPP_TOKEN is not set in backend_api/.env")
        sys.exit(1)
    if not phone_number_id or phone_number_id == "your_phone_number_id_here":
        print("  CONFIG ERROR: META_PHONE_NUMBER_ID is not set in backend_api/.env")
        sys.exit(1)

    if list_templates:
        await list_all_templates(token, phone_number_id)
        print("=" * 60)
        return

    if template:
        await print_template_info(template, token, phone_number_id)

    try:
        if template:
            result = await send_template_message(to, template, lang, token, phone_number_id, params)
        else:
            result = await send_text_message(to, msg, token, phone_number_id)

        message_id = (
            result.get("messages", [{}])[0].get("id", "—")
            if result.get("messages")
            else "—"
        )
        print()
        print(f"  SUCCESS  message_id={message_id}")
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
    parser = argparse.ArgumentParser(description="Send a WhatsApp test message (text or template).")
    parser.add_argument(
        "--to",
        default="+17692188324",
        help="Recipient phone number in E.164 format (default: +17692188324 — Joe Ronie)",
    )
    parser.add_argument(
        "--msg",
        default="Hello from West End Glass! This is a connectivity test.",
        help="Message body for free-form text sends",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Template name to use instead of free-form text (e.g. test_maintenance_chat)",
    )
    parser.add_argument(
        "--params",
        nargs="*",
        default=None,
        help="Parameters for template (space-separated, e.g. --params 'John' 'March 27, 2026' 'Maintenance' 'WEG-123')",
    )
    parser.add_argument(
        "--lang",
        default="en_US",
        help="Language code for template sends (default: en_US)",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List all templates on the account with status and body text",
    )
    args = parser.parse_args()

    asyncio.run(main(args.to, args.msg, args.template, args.lang, args.params, args.list_templates))
