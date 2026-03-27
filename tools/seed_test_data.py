#!/usr/bin/env python3
"""
seed_test_data.py — Populate database with test data for development/testing.

Creates:
  - 3 machines
  - 3 technicians
  - 6 tickets (2 per technician with different statuses and steps)

Usage:
  python tools/seed_test_data.py [--api-url http://localhost:8000]
"""

import argparse
import sys
import os

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Run: pip install requests")
    sys.exit(1)


DEFAULT_API_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Monday001!"


def main():
    parser = argparse.ArgumentParser(description="Seed test data")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_BASE_URL", DEFAULT_API_URL),
        help="Backend API URL (default: %(default)s)",
    )
    args = parser.parse_args()
    
    session = requests.Session()
    api_url = args.api_url.rstrip("/")
    
    print("🌱 Seeding test data...")
    print(f"   API: {api_url}")
    
    # Step 1: Authenticate
    print("\n[1/4] Authenticating...")
    try:
        resp = session.post(
            f"{api_url}/auth/login",
            data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        print("     ✓ Authenticated")
    except Exception as e:
        print(f"     ✗ Auth failed: {e}")
        sys.exit(1)
    
    # Step 2: Create machines
    print("\n[2/4] Creating 3 machines...")
    machines = [
        {"machine_id": "WEG-MACHINE-0042", "name": "Test Machine 1", "location": "Floor 1"},
        {"machine_id": "WEG-MACHINE-0043", "name": "Test Machine 2", "location": "Floor 2"},
        {"machine_id": "WEG-MACHINE-0044", "name": "Test Machine 3", "location": "Floor 3"},
    ]
    machine_ids = []
    for m in machines:
        try:
            resp = session.post(f"{api_url}/machines", json=m, timeout=10)
            if resp.status_code in [201, 409]:  # 409 = already exists
                machine_ids.append(m["machine_id"])
                print(f"     ✓ {m['machine_id']}")
            else:
                print(f"     ⚠ {m['machine_id']}: {resp.text}")
        except Exception as e:
            print(f"     ✗ {m['machine_id']}: {e}")
    
    # Step 3: Create technicians
    print("\n[3/4] Creating 3 technicians...")
    technicians = [
        {"phone_number": "+15551234567", "name": "John Smith", "active": True},
        {"phone_number": "+15559876543", "name": "Jane Doe", "active": True},
        {"phone_number": "+15552468101", "name": "Bob Wilson", "active": True},
    ]
    tech_phones = []
    for t in technicians:
        try:
            resp = session.post(f"{api_url}/users", json=t, timeout=10)
            if resp.status_code in [201, 409]:  # 409 = already exists
                tech_phones.append(t["phone_number"])
                print(f"     ✓ {t['name']} ({t['phone_number']})")
            else:
                print(f"     ⚠ {t['name']}: {resp.text}")
        except Exception as e:
            print(f"     ✗ {t['name']}: {e}")
    
    # Step 4: Create tickets (2 per technician)
    print("\n[4/4] Creating 6 tickets...")
    tickets = [
        # Tech 1 tickets
        {
            "machine_id": machine_ids[0] if machine_ids else "WEG-MACHINE-0042",
            "title": "Monthly Maintenance",
            "description": "Regular maintenance check",
            "assigned_to": tech_phones[0] if tech_phones else "+15551234567",
            "priority": 5,
            "category": "maintenance",
            "steps": [
                {"step_index": 0, "label": "Inspect pump", "completion_type": "confirmation"},
                {"step_index": 1, "label": "Check oil level", "completion_type": "photo"},
                {"step_index": 2, "label": "Test operation", "completion_type": "note"},
            ],
        },
        {
            "machine_id": machine_ids[1] if len(machine_ids) > 1 else "WEG-MACHINE-0043",
            "title": "Emergency Repair",
            "description": "Unit not starting",
            "assigned_to": tech_phones[0] if tech_phones else "+15551234567",
            "priority": 10,
            "category": "emergency",
            "steps": [
                {"step_index": 0, "label": "Diagnose issue", "completion_type": "note"},
                {"step_index": 1, "label": "Replace part", "completion_type": "photo"},
            ],
        },
        # Tech 2 tickets
        {
            "machine_id": machine_ids[2] if len(machine_ids) > 2 else "WEG-MACHINE-0044",
            "title": "Installation",
            "description": "New equipment setup",
            "assigned_to": tech_phones[1] if len(tech_phones) > 1 else "+15559876543",
            "priority": 7,
            "category": "installation",
            "steps": [
                {"step_index": 0, "label": "Unpack equipment", "completion_type": "confirmation"},
                {"step_index": 1, "label": "Install frame", "completion_type": "photo"},
                {"step_index": 2, "label": "Connect power", "completion_type": "confirmation"},
            ],
        },
        {
            "machine_id": machine_ids[0] if machine_ids else "WEG-MACHINE-0042",
            "title": "Inspection",
            "description": "Safety inspection required",
            "assigned_to": tech_phones[1] if len(tech_phones) > 1 else "+15559876543",
            "priority": 6,
            "category": "inspection",
            "steps": [
                {"step_index": 0, "label": "Visual inspection", "completion_type": "photo"},
                {"step_index": 1, "label": "Test safety features", "completion_type": "note"},
            ],
        },
        # Tech 3 tickets
        {
            "machine_id": machine_ids[1] if len(machine_ids) > 1 else "WEG-MACHINE-0043",
            "title": "Repair - Hydraulic Leak",
            "description": "Hydraulic system leak detected",
            "assigned_to": tech_phones[2] if len(tech_phones) > 2 else "+15552468101",
            "priority": 9,
            "category": "repair",
            "steps": [
                {"step_index": 0, "label": "Locate leak source", "completion_type": "photo"},
                {"step_index": 1, "label": "Replace seal", "completion_type": "confirmation"},
                {"step_index": 2, "label": "Test pressure", "completion_type": "note"},
            ],
        },
        {
            "machine_id": machine_ids[2] if len(machine_ids) > 2 else "WEG-MACHINE-0044",
            "title": "Preventive Maintenance",
            "description": "Scheduled preventive maintenance",
            "assigned_to": tech_phones[2] if len(tech_phones) > 2 else "+15552468101",
            "priority": 3,
            "category": "maintenance",
            "steps": [
                {"step_index": 0, "label": "Change filters", "completion_type": "confirmation"},
                {"step_index": 1, "label": "Clean vents", "completion_type": "photo"},
                {"step_index": 2, "label": "Lubricate joints", "completion_type": "confirmation"},
            ],
        },
    ]
    
    for i, t in enumerate(tickets, 1):
        try:
            resp = session.post(f"{api_url}/tickets", json=t, timeout=10)
            if resp.status_code == 201:
                print(f"     ✓ Ticket {i}: {t['title']}")
            else:
                print(f"     ⚠ Ticket {i}: {resp.text}")
        except Exception as e:
            print(f"     ✗ Ticket {i}: {e}")
    
    print("\n✅ Seeding complete!")
    print("\n📋 Next steps:")
    print("   1. Open Admin Dashboard: http://localhost:3030")
    print(f"   2. Login: admin / {ADMIN_PASSWORD}")
    print("   3. View machines, users, and tickets")
    print("   4. Test with simulator: python tools/simulate_chat.py")


if __name__ == "__main__":
    main()
