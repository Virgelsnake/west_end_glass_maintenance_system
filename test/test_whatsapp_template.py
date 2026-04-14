"""
WhatsApp template message smoke test.

Uses a pre-approved Meta message template instead of free-form text.
The built-in 'hello_world' template works on all accounts without setup.

Usage (from project root):
    python test/test_whatsapp_template.py --to +447717207677

    # Or with a custom template:
    python test/test_whatsapp_template.py --to +447717207677 --template westend_glass__machine_servicing_system2 --lang en_US

Reads credentials from  ../backend_api/.env  (no running server required).
Requires:  pip install httpx python-dotenv
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

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

WHATSAPP_API_BASE = "https://graph.facebook.com/v19.0"


async def fetch_template_info(template_name: str, token: str, waba_id: str) -> None:
    """Fetch and print template details from Meta Business API."""
    url = f"{WHATSAPP_API_BASE}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"name": template_name, "fields": "name,status,language,category,components"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        print(f"  [template lookup failed: HTTP {resp.status_code}]")
        return

    data = resp.json().get("data", [])
    if not data:
        print(f"  [no template found with name '{template_name}']")
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


async def send_template_message(to: str, template_name: str, lang: str) -> dict:
    token = os.environ.get("META_WHATSAPP_TOKEN", "")
    phone_number_id = os.environ.get("META_PHONE_NUMBER_ID", "")

    if not token or token == "your_permanent_access_token_here":
        raise EnvironmentError("META_WHATSAPP_TOKEN is not set in backend_api/.env")
    if not phone_number_id or phone_number_id == "your_phone_number_id_here":
        raise EnvironmentError("META_PHONE_NUMBER_ID is not set in backend_api/.env")

    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang},
        },
    }

    print(f"  POST {url}")
    print(f"  To       : {to}")
    print(f"  Template : {template_name}  [{lang}]")
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


async def fetch_waba_id(token: str, phone_number_id: str) -> str | None:
    """Resolve the WhatsApp Business Account ID from the phone number ID."""
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"fields": "whatsapp_business_account"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers, params=params)
    if resp.status_code == 200:
        return resp.json().get("whatsapp_business_account", {}).get("id")
    return None


async def main(to: str, template_name: str, lang: str) -> None:
    print("=" * 60)
    print("  West End Glass — WhatsApp Template Send Test")
    print("=" * 60)
    print()

    token = os.environ.get("META_WHATSAPP_TOKEN", "")
    phone_number_id = os.environ.get("META_PHONE_NUMBER_ID", "")

    # --- Print template details before sending ---
    print("  Template Info")
    print("  " + "-" * 40)
    waba_id = await fetch_waba_id(token, phone_number_id)
    if waba_id:
        await fetch_template_info(template_name, token, waba_id)
    else:
        print("  [could not resolve WABA ID — skipping template lookup]\n")

    try:
        result = await send_template_message(to, template_name, lang)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a WhatsApp template message.")
    parser.add_argument("--to", required=True, help="Recipient in E.164 format, e.g. +447717207677")
    parser.add_argument("--template", default="hello_world", help="Template name (default: hello_world)")
    parser.add_argument("--lang", default="en_US", help="Language code (default: en_US)")
    args = parser.parse_args()

    asyncio.run(main(args.to, args.template, args.lang))
