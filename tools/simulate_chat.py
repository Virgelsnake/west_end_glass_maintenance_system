#!/usr/bin/env python3
"""
simulate_chat.py — WhatsApp Bot Testing Tool for West End Glass Maintenance System

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This CLI tool simulates WhatsApp messages through the complete bot pipeline:
  1. Phone number whitelist check (technician must be active in database)
  2. Ticket routing (machine ID → open tickets)
  3. Claude AI agent processing
  4. Message & audit log persistence
  5. Response display with ticket context

Default technician: +15551234567 (John Smith)

The bot is the primary interface for technicians in the field. You can test:
  • Ticket start (send "WEG-MACHINE-XXXX")
  • Multi-turn conversations with Claude agent
  • Step completion workflows
  • Photo descriptions & notes
  • Error handling & edge cases

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM ARCHITECTURE (Three Interfaces)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🤖 WhatsApp Bot (this tool)
     └─ Technicians chat with Claude AI agent
     └─ Guided through ticket steps
     └─ Uses phone # whitelist auth

  🔧 Technician Portal (web app)
     └─ Login: phone # + PIN
     └─ View/complete tickets
     └─ Upload photos
     └─ Manual step tracking

  👨‍💼 Admin Dashboard (web app)
     └─ Login: username + password
     └─ Create tickets, assign techs
     └─ View audit logs
     └─ Manage users & machines

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Interactive (defaults to John Smith +15551234567):
    python tools/simulate_chat.py

  Interactive (specify different technician phone):
    python tools/simulate_chat.py --phone +15559876543

  One-shot mode (send message and exit with default technician):
    python tools/simulate_chat.py --message "WEG-MACHINE-0042"

  One-shot mode (specify technician):
    python tools/simulate_chat.py --phone +15559876543 --message "WEG-MACHINE-0042"

  Custom API endpoint:
    python tools/simulate_chat.py --api-url http://localhost:8001

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Start a new ticket for a machine:
     [phone] > WEG-MACHINE-0042

  2. Chat with Claude agent about the work:
     [phone] > I've checked the pump. It looks normal.

  3. Complete a step:
     [phone] > Step 1 complete ✓

  4. Attach a photo description:
     [phone] > I've attached a photo of the problem

  5. Close the ticket:
     [phone] > All steps done, ticket complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENVIRONMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  API_BASE_URL   Backend URL (default: http://localhost:8000)

Requires: pip install requests
"""

import argparse
import os
import sys
import textwrap

try:
    import requests
except ImportError:
    print("Error: 'requests' package required.  Run: pip install requests")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_API_URL = "http://localhost:8000"
HR = "─" * 64


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="West End Glass — WhatsApp CLI Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--api-url",
        default=os.environ.get("API_BASE_URL", DEFAULT_API_URL),
        help="Backend API base URL (default: %(default)s)",
    )
    p.add_argument(
        "--phone",
        metavar="PHONE",
        help="Technician phone number in E.164 format, e.g. +15551234567",
    )
    p.add_argument(
        "--message",
        metavar="TEXT",
        help="One-shot mode: send this message and exit",
    )
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# API calls
# ─────────────────────────────────────────────────────────────────────────────

def get_active_users(api_url: str) -> list:
    resp = requests.get(f"{api_url}/simulate/users", timeout=10)
    resp.raise_for_status()
    return resp.json()


def send_message(api_url: str, phone_number: str, message_text: str) -> dict:
    resp = requests.post(
        f"{api_url}/simulate/message",
        json={"phone_number": phone_number, "message_text": message_text},
        timeout=90,  # Claude agent loop can take several seconds
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def print_response(result: dict) -> None:
    print()
    if not result.get("authorized", True):
        print(f"  ⛔ UNAUTHORIZED")
        print(f"  {result['response_text']}")
    else:
        text = result.get("response_text", "")
        prefix = "  │ "
        lines = []
        for raw_line in text.split("\n"):
            if raw_line.strip():
                for wrapped in textwrap.wrap(raw_line, width=60):
                    lines.append(prefix + wrapped)
            else:
                lines.append(prefix)
        print("  🤖 Bot Response:")
        print("  ├" + "─" * 62)
        for line in lines:
            print(line)
        print("  └" + "─" * 62)

    ticket_id = result.get("ticket_id")
    if ticket_id:
        short_id = ticket_id[-8:]
        title = result.get("ticket_title") or "—"
        machine = result.get("machine_id") or "—"
        status = result.get("ticket_status") or "—"
        print()
        print(f"  📋 Ticket Context:")
        print(f"     ID:      [{short_id}]")
        print(f"     Title:   {title}")
        print(f"     Machine: {machine}")
        print(f"     Status:  {status}")
    print()


def pick_user(users: list) -> str:
    if not users:
        print("\n  ❌ No active technicians found.")
        print("     Add technicians via the Admin Dashboard first:")
        print("     • Navigate to dashboard → Users")
        print("     • Create a new user with status=active")
        sys.exit(1)

    print("\n  ┌─ ACTIVE TECHNICIANS ────────────────────────────────┐")
    print(f"  │  {'#':<3}  {'Name':<20}  {'Phone':<18}         │")
    print("  ├─────────────────────────────────────────────────────┤")
    for i, u in enumerate(users, 1):
        name = u['name'][:19].ljust(20)
        phone = u['phone_number'][:17].ljust(18)
        print(f"  │  {i:<3}  {name}  {phone} │")
    print("  └─────────────────────────────────────────────────────┘")
    print()

    while True:
        choice = input("  Select technician [number] or enter phone [+E.164]: ").strip()
        if choice.startswith("+"):
            return choice
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                selected = users[idx]
                print(f"\n  ✓ Selected: {selected['name']} ({selected['phone_number']})")
                return users[idx]["phone_number"]
        except ValueError:
            pass
        print("  ❌ Invalid — enter a number from the list or a +E.164 phone number.")


def print_help() -> None:
    print()
    print("  ┌─ COMMANDS ─────────────────────────────────────────────────┐")
    print("  │                                                             │")
    print("  │  .quit / .exit   Exit the simulator                         │")
    print("  │  .help           Show this message                          │")
    print("  │  .stats          Show recent ticket stats                   │")
    print("  │                                                             │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()
    print("  ┌─ HOW TO USE ────────────────────────────────────────────────┐")
    print("  │                                                             │")
    print("  │  1. Start a ticket by sending a machine ID:                │")
    print("  │     WEG-MACHINE-0042                                        │")
    print("  │     If multiple tickets exist, choose one by number: 1, 2  │")
    print("  │                                                             │")
    print("  │  2. Chat with Claude about the work:                       │")
    print("  │     I've checked the pump. It's working normally.          │")
    print("  │                                                             │")
    print("  │  3. Claude will guide you through the ticket steps.        │")
    print("  │     Confirm completed steps, attach notes, describe photos.│")
    print("  │                                                             │")
    print("  │  4. Close the ticket when all steps are done:             │")
    print("  │     All work complete                                       │")
    print("  │                                                             │")
    print("  │  5. Testing Only - Simulate photo/note:                    │")
    print("  │     /test-photo 2     (mark step 2 as photo complete)      │")
    print("  │     /test-note 2 Done (add note to step 2)                 │")
    print("  │                                                             │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()
    print("  💡 TIP: You can test different error scenarios by:")
    print("     • Sending an invalid machine ID")
    print("     • Sending a message without a ticket assigned")
    print("     • Testing the bot's responses to edge cases")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Mode Selection
# ─────────────────────────────────────────────────────────────────────────────

def prompt_mode_selection() -> int:
    """Prompt user to choose between Mode 1 (Chat) and Mode 2 (Deep-link)"""
    print()
    print("  ┌─ SELECT MODE ──────────────────────────────────────────────┐")
    print("  │                                                             │")
    print("  │  Mode 1: Chat-Based                                         │")
    print("  │  • Send any message                                         │")
    print("  │  • Bot auto-finds your assigned tickets                    │")
    print("  │  • Continue with ticket conversation                        │")
    print("  │                                                             │")
    print("  │  Mode 2: Deep-Link (NFC/QR Code)                           │")
    print("  │  • Specify a machine ID (WEG-MACHINE-XXXX)                 │")
    print("  │  • Immediately start that machine's ticket                  │")
    print("  │  • Continue with ticket conversation                        │")
    print("  │                                                             │")
    print("  └─────────────────────────────────────────────────────────────┘")
    print()

    while True:
        choice = input("  Choose mode [1 or 2]: ").strip()
        if choice == "1":
            print("\n  ✓ Mode 1: Chat-Based")
            return 1
        elif choice == "2":
            print("\n  ✓ Mode 2: Deep-Link")
            return 2
        else:
            print("  ❌ Invalid choice. Please enter 1 or 2.")


def mode_1_chat_based(api_url: str, phone: str) -> None:
    """Mode 1: Chat-based interaction - send any message, auto-find tickets"""
    print("\n💬 Interactive Chat Mode — type .help for commands\n")
    print("  Send any message. The bot will:")
    print("  • Find your assigned tickets")
    print("  • Route to appropriate ticket")
    print("  • Let Claude guide the conversation")
    print("\n  Testing Commands:")
    print("  • /test-photo [step #] — Simulate a photo upload (testing only)")
    print("  • /test-note [step #] [text] — Simulate a note (testing only)\n")

    while True:
        try:
            raw = input(f"[{phone}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye.")
            break

        if not raw:
            continue

        if raw in (".quit", ".exit", "quit", "exit"):
            print("👋 Bye.")
            break

        if raw == ".help":
            print_help()
            continue

        # Handle test commands for photo/note simulation
        message_to_send = raw
        if raw.startswith("/test-photo"):
            message_to_send = f"[TEST_PHOTO] {raw}"
            print("  ℹ️  Sending photo simulation command to backend...\n")
        elif raw.startswith("/test-note"):
            message_to_send = f"[TEST_NOTE] {raw}"
            print("  ℹ️  Sending note simulation command to backend...\n")

        try:
            result = send_message(api_url, phone, message_to_send)
            print_response(result)
        except requests.HTTPError as exc:
            print(f"\n  ❌ Error {exc.response.status_code}")
            print(f"     {exc.response.text}\n")
        except requests.ConnectionError:
            print(f"\n  ❌ Connection error — is the API running?\n")
        except requests.Timeout:
            print("\n  ⏱️  Request timed out (Claude may still be thinking)\n")


def mode_2_deeplink(api_url: str, phone: str) -> None:
    """Mode 2: Deep-link interaction - start with machine ID"""
    print("\n🔗 Deep-Link Mode — NFC/QR Code Entry\n")

    # Get machine ID
    while True:
        machine_id = input("  Enter machine ID (e.g., WEG-MACHINE-0042): ").strip()
        if machine_id:
            break
        print("  ❌ Please enter a valid machine ID.")

    print(f"\n  Starting ticket for: {machine_id}")
    print("  Chat mode — type .help for commands\n")

    # Send initial machine ID message to start ticket
    try:
        result = send_message(api_url, phone, machine_id)
        print_response(result)
    except requests.HTTPError as exc:
        print(f"\n  ❌ Error {exc.response.status_code}")
        print(f"     {exc.response.text}\n")
        return
    except requests.ConnectionError:
        print(f"\n  ❌ Connection error — is the API running?\n")
        return
    except requests.Timeout:
        print("\n  ⏱️  Request timed out\n")
        return

    # Continue interactive session with that ticket
    print("  Continue chatting about the ticket:")
    print("  Testing Commands:")
    print("  • /test-photo [step #] — Simulate a photo upload (testing only)")
    print("  • /test-note [step #] [text] — Simulate a note (testing only)\n")

    while True:
        try:
            raw = input(f"[{phone}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye.")
            break

        if not raw:
            continue

        if raw in (".quit", ".exit", "quit", "exit"):
            print("👋 Bye.")
            break

        if raw == ".help":
            print_help()
            continue

        # Handle test commands for photo/note simulation
        message_to_send = raw
        if raw.startswith("/test-photo"):
            message_to_send = f"[TEST_PHOTO] {raw}"
            print("  ℹ️  Sending photo simulation command to backend...\n")
        elif raw.startswith("/test-note"):
            message_to_send = f"[TEST_NOTE] {raw}"
            print("  ℹ️  Sending note simulation command to backend...\n")

        try:
            result = send_message(api_url, phone, message_to_send)
            print_response(result)
        except requests.HTTPError as exc:
            print(f"\n  ❌ Error {exc.response.status_code}")
            print(f"     {exc.response.text}\n")
        except requests.ConnectionError:
            print(f"\n  ❌ Connection error — is the API running?\n")
        except requests.Timeout:
            print("\n  ⏱️  Request timed out (Claude may still be thinking)\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    api_url = args.api_url.rstrip("/")

    print()
    print("╔" + "═" * 66 + "╗")
    print("║" + " " * 11 + "West End Glass — WhatsApp Bot Simulator" + " " * 15 + "║")
    print("╚" + "═" * 66 + "╝")
    print()
    print(f"  API Endpoint: {api_url}")
    print(f"  Mode: {'One-shot' if args.message else 'Interactive'}")
    print()
    print("  This tool tests the WhatsApp bot that technicians interact with")
    print("  in the field. Auth is phone whitelist (same as real WhatsApp).")
    print()
    print("  See .help in interactive mode for commands and examples.")
    print("─" * 68)

    # ── Pick or use provided phone number ────────────────────────
    phone = args.phone
    if not phone:
        # Default to John Smith's phone number
        phone = "+15551234567"
        print(f"\n✓ Using default technician: +15551234567 (John Smith)")
        print("  (Override with --phone +E.164 argument)")
    else:
        print(f"\n📱 Using specified phone: {phone}")

    print(f"\n✓ Simulating as: {phone}")
    print("  Auth: Phone whitelist (technician must be active)")
    print("─" * 68)

    # ── One-shot mode ────────────────────────────────────────────
    if args.message:
        try:
            result = send_message(api_url, phone, args.message)
            print_response(result)
        except requests.ConnectionError:
            print(f"\n  ❌ Cannot connect to {api_url}")
            sys.exit(1)
        except requests.HTTPError as exc:
            print(f"\n  ❌ Error {exc.response.status_code}")
            print(f"     {exc.response.text}")
            sys.exit(1)
        return

    # ── Interactive Mode: Prompt for Mode Selection ──────────────
    mode = prompt_mode_selection()

    if mode == 1:
        mode_1_chat_based(api_url, phone)
    elif mode == 2:
        mode_2_deeplink(api_url, phone)


if __name__ == "__main__":
    main()
