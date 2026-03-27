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

Default technician: +17692188324 (Joe Ronie)

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

  Interactive (defaults to Joe Ronie +17692188324):
    python tools/simulate_chat.py

  Interactive (specify different technician phone):
    python tools/simulate_chat.py --phone +15551234567

  One-shot mode (send message and exit with default technician):
    python tools/simulate_chat.py --message "WEG-MACHINE-0042"

  One-shot mode (specify technician):
    python tools/simulate_chat.py --phone +15551234567 --message "WEG-MACHINE-0042"

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
# Webcam photo capture (fun feature!)
# ─────────────────────────────────────────────────────────────────────────────

def capture_photo_from_webcam(timeout_sec: int = 3) -> bytes | None:
    """Try to capture a photo from the webcam. Returns image bytes or None if failed."""
    try:
        import cv2
    except ImportError:
        print("  ℹ️  OpenCV not installed. Skipping webcam capture.")
        print("     To enable: pip install opencv-python\n")
        return None
    
    try:
        cap = cv2.VideoCapture(0)  # 0 = default camera
        if not cap.isOpened():
            print("  ⚠️  Webcam not available (or permissions denied)\n")
            return None
        
        # Give camera a moment to warm up
        for _ in range(5):
            cap.read()
        
        # Capture frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            print("  ⚠️  Failed to capture from webcam\n")
            return None
        
        # Encode as JPEG
        success, encoded_image = cv2.imencode(".jpg", frame)
        if not success:
            return None
        
        print("  📸 Captured photo from webcam!")
        return encoded_image.tobytes()
    
    except Exception as e:
        print(f"  ⚠️  Webcam capture failed: {e}\n")
        return None


def upload_photo_to_ticket(
    api_url: str,
    ticket_id: str,
    step_index: int,
    photo_bytes: bytes,
    phone_number: str,
) -> bool:
    """Upload a photo to a ticket step. Returns True if successful."""
    try:
        files = {"photo": ("photo.jpg", photo_bytes, "image/jpeg")}
        params = {
            "ticket_id": ticket_id,
            "step_index": step_index,
            "phone_number": phone_number,
        }
        resp = requests.post(
            f"{api_url}/simulate/photo",
            files=files,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        print("  ✅ Photo uploaded and attached to step!")
        return True
    except requests.HTTPError as e:
        print(f"  ❌ Failed to upload photo: {e.response.status_code}")
        if e.response.text:
            print(f"     {e.response.text}")
        return False
    except Exception as e:
        print(f"  ⚠️  Upload error: {e}")
        return False


def upload_ref_photo_to_ticket(
    api_url: str,
    ticket_id: str,
    photo_bytes: bytes,
    phone_number: str,
    filename: str = "ref_photo.jpg",
) -> bool:
    """Upload a reference photo to a ticket and mock WhatsApp delivery."""
    try:
        files = {"photo": (filename, photo_bytes, "image/jpeg")}
        params = {"ticket_id": ticket_id, "phone_number": phone_number}
        resp = requests.post(
            f"{api_url}/simulate/ref-photo",
            files=files,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"  ✅ Reference photo saved: {data.get('filename')}")
        assigned_to = data.get("would_send_to")
        if assigned_to:
            print(f"  📲 [WhatsApp SIMULATED] Would have sent to {assigned_to}")
        else:
            print("  ℹ️  No technician assigned — WhatsApp delivery skipped.")
        return True
    except requests.HTTPError as e:
        print(f"  ❌ Failed to upload reference photo: {e.response.status_code}")
        if e.response.text:
            print(f"     {e.response.text}")
        return False
    except Exception as e:
        print(f"  ⚠️  Upload error: {e}")
        return False


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
    print("  │  /test-photo [step#]         Capture from webcam & attach   │")
    print("  │  /test-note [step#] [text]   Simulate a text note           │")
    print("  │  /ref-photo [ticket_id]      Attach admin reference photo   │")
    print("  │    → Tries webcam first; falls back to local file path      │")
    print("  │    → Mocks WhatsApp: prints would-send info (no real call)  │")
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
    print("  │  5. Attach photos from webcam (for testing):               │")
    print("  │     /test-photo 2     ← Captures real photo from webcam    │")
    print("  │     Falls back to test mode if webcam unavailable          │")
    print("  │                                                             │")
    print("  │  6. Attach notes:                                           │")
    print("  │     /test-note 2 Sealed all cracks                         │")
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
    print("  • /test-photo [step #] — Capture photo from webcam & attach (or fallback to test)")
    print("  • /test-note [step #] [text] — Simulate a note (testing only)")
    print("  • /ref-photo [ticket_id] — Attach reference photo to any ticket (mocks WhatsApp)\n")

    current_ticket_id = None

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

        # Handle /test-photo specially - try to capture from webcam
        if raw.startswith("/test-photo"):
            if not current_ticket_id:
                print("  ⚠️  No active ticket. Start a ticket first (send a machine ID).\n")
                continue
            
            try:
                step_str = raw.split()[-1]
                step_index = int(step_str)
            except (ValueError, IndexError):
                print("  ❌ Usage: /test-photo [step_number]\n")
                continue
            
            print("  🎥 Attempting to capture photo from webcam...\n")
            photo_bytes = capture_photo_from_webcam()
            
            if photo_bytes:
                if upload_photo_to_ticket(api_url, current_ticket_id, step_index, photo_bytes, phone):
                    print()
                    continue
                else:
                    print("  Falling back to test mode...\n")
            
            # Fallback to test command
            message_to_send = f"[TEST_PHOTO] {raw}"
            print()
        elif raw.startswith("/ref-photo"):
            parts = raw.split()
            ticket_id_arg = parts[1] if len(parts) > 1 else current_ticket_id
            if not ticket_id_arg:
                print("  ❌ Usage: /ref-photo [ticket_id]  (or have an active ticket)\n")
                continue
            print("  🎥 Attempting to capture reference photo from webcam...\n")
            photo_bytes = capture_photo_from_webcam()
            if not photo_bytes:
                file_path = input("  Enter local image file path (or press Enter to cancel): ").strip()
                if not file_path:
                    print("  ❌ Cancelled.\n")
                    continue
                try:
                    with open(file_path, "rb") as f:
                        photo_bytes = f.read()
                    print(f"  📁 Loaded from file: {file_path}")
                except OSError as e:
                    print(f"  ❌ Could not read file: {e}\n")
                    continue
            upload_ref_photo_to_ticket(api_url, ticket_id_arg, photo_bytes, phone)
            print()
            continue
        elif raw.startswith("/test-note"):
            message_to_send = f"[TEST_NOTE] {raw}"
            print("  ℹ️  Creating note in test mode...\n")
        else:
            message_to_send = raw

        try:
            result = send_message(api_url, phone, message_to_send)
            if result.get("ticket_id"):
                current_ticket_id = result["ticket_id"]
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
    current_ticket_id = None
    try:
        result = send_message(api_url, phone, machine_id)
        current_ticket_id = result.get("ticket_id")
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
    print("  • /test-photo [step #] — Capture photo from webcam & attach (or fallback to test)")
    print("  • /test-note [step #] [text] — Simulate a note (testing only)")
    print("  • /ref-photo [ticket_id] — Attach reference photo to a ticket (mocks WhatsApp)\n")

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

        # Handle /test-photo specially - try to capture from webcam
        if raw.startswith("/test-photo"):
            if not current_ticket_id:
                print("  ⚠️  No active ticket found.\n")
                continue
            
            try:
                step_str = raw.split()[-1]
                step_index = int(step_str)
            except (ValueError, IndexError):
                print("  ❌ Usage: /test-photo [step_number]\n")
                continue
            
            print("  🎥 Attempting to capture photo from webcam...\n")
            photo_bytes = capture_photo_from_webcam()
            
            if photo_bytes:
                if upload_photo_to_ticket(api_url, current_ticket_id, step_index, photo_bytes, phone):
                    print()
                    continue
                else:
                    print("  Falling back to test mode...\n")
            
            # Fallback to test command
            message_to_send = f"[TEST_PHOTO] {raw}"
            print()
        elif raw.startswith("/ref-photo"):
            parts = raw.split()
            ticket_id_arg = parts[1] if len(parts) > 1 else current_ticket_id
            if not ticket_id_arg:
                print("  ❌ Usage: /ref-photo [ticket_id]  (or have an active ticket)\n")
                continue
            print("  🎥 Attempting to capture reference photo from webcam...\n")
            photo_bytes = capture_photo_from_webcam()
            if not photo_bytes:
                file_path = input("  Enter local image file path (or press Enter to cancel): ").strip()
                if not file_path:
                    print("  ❌ Cancelled.\n")
                    continue
                try:
                    with open(file_path, "rb") as f:
                        photo_bytes = f.read()
                    print(f"  📁 Loaded from file: {file_path}")
                except OSError as e:
                    print(f"  ❌ Could not read file: {e}\n")
                    continue
            upload_ref_photo_to_ticket(api_url, ticket_id_arg, photo_bytes, phone)
            print()
            continue
        elif raw.startswith("/test-note"):
            message_to_send = f"[TEST_NOTE] {raw}"
            print("  ℹ️  Creating note in test mode...\n")
        else:
            message_to_send = raw

        try:
            result = send_message(api_url, phone, message_to_send)
            if result.get("ticket_id"):
                current_ticket_id = result["ticket_id"]
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
        # Default to Joe Ronie's phone number
        phone = "+17692188324"
        print(f"\n✓ Using default technician: +17692188324 (Joe Ronie)")
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
