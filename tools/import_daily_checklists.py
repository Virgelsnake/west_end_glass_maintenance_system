#!/usr/bin/env python3
"""
import_daily_checklists.py — Import 13 machines and daily checklist templates from JSON.

Creates:
  - 13 machines with human-readable IDs
  - 13 daily_checklist_templates (one per machine), all assigned to Bob Wilson at 00:00 UTC

Usage:
  python tools/import_daily_checklists.py [--api-url http://localhost:8000]

Prerequisites:
  - Run tools/reset_db.py first to clear existing machines/tickets
  - Backend must be running
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Run: pip install requests")
    sys.exit(1)

DEFAULT_API_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Monday001!"

# Mapping: JSON filename stem → (machine_id, machine_name)
MACHINE_MAP = {
    "arrisor_machine_daily_checklist":       ("WEG-ARRISOR-01",    "Arrisor Machine"),
    "cutting_table_daily_checklist":         ("WEG-CUTTING-01",    "Cutting Table"),
    "daily_forklift_checklist":              ("WEG-FORKLIFT-01",   "Forklift"),
    "generator_daily_checklist":             ("WEG-GENERATOR-01",  "Generator"),
    "glass_washer_daily_checklist":          ("WEG-WASHER-01",     "Glass Washer"),
    "laminating_machine_daily_checklist":    ("WEG-LAMINATOR-01",  "Laminating Machine"),
    "paint_booth_daily_checklist":           ("WEG-PAINTBOOTH-01", "Paint Booth"),
    "polisher_daily_checklist":              ("WEG-POLISHER-01",   "Polisher"),
    "radius_corner_machine_daily_checklist": ("WEG-RADIUS-01",     "Radius Corner Machine"),
    "sand_blaster_daily_checklist":          ("WEG-SANDBLAST-01",  "Sand Blaster"),
    "silicon_sealer_machine_daily_checklist":("WEG-SILICONER-01",  "Silicon Sealer Machine"),
    "toughening_plant_daily_checklist":      ("WEG-TOUGHENING-01", "Toughening Plant"),
    "waterjet_cutter_daily_checklist":       ("WEG-WATERJET-01",   "Waterjet Cutter"),
}

CHECKLIST_DIR = Path(__file__).parent.parent / "Documentation" / "import"


def main():
    parser = argparse.ArgumentParser(description="Import machines and daily checklist templates.")
    parser.add_argument("--api-url", default=os.environ.get("API_BASE_URL", DEFAULT_API_URL))
    args = parser.parse_args()
    base = args.api_url.rstrip("/")

    # ── 1. Authenticate ──────────────────────────────────────────────────────
    print(f"\nConnecting to {base} ...")
    resp = requests.post(f"{base}/auth/login", data={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Authenticated")

    # ── 2. Find Bob Wilson's phone number ────────────────────────────────────
    resp = requests.get(f"{base}/users", headers=headers)
    resp.raise_for_status()
    users = resp.json()
    bob = next((u for u in users if "bob" in u.get("name", "").lower()), None)
    if not bob:
        print("✗ Bob Wilson not found in users. Run seed_test_data.py first or create user manually.")
        sys.exit(1)
    bob_phone = bob["phone_number"]
    print(f"✓ Found Bob Wilson: {bob_phone}")

    # ── 3. Load and parse all JSON checklist files ───────────────────────────
    json_files = sorted(CHECKLIST_DIR.glob("*.json"))
    if not json_files:
        print(f"✗ No JSON files found in {CHECKLIST_DIR}")
        sys.exit(1)

    print(f"\nFound {len(json_files)} checklist JSON file(s)")

    created_machines = 0
    created_templates = 0
    errors = []

    for json_path in json_files:
        stem = json_path.stem
        if stem not in MACHINE_MAP:
            print(f"  [SKIP] {json_path.name} — no machine mapping defined")
            continue

        machine_id, machine_name = MACHINE_MAP[stem]

        try:
            with open(json_path) as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"{json_path.name}: {e}")
            continue

        # ── 4. Create machine ────────────────────────────────────────────────
        resp = requests.post(f"{base}/machines", headers=headers, json={
            "machine_id": machine_id,
            "name": machine_name,
            "location": "West End Glass Factory",
            "notes": f"Imported from {data.get('source_file', json_path.name)}",
        })
        if resp.status_code == 201:
            print(f"  [machine] Created {machine_id} — {machine_name}")
            created_machines += 1
        elif resp.status_code == 409:
            print(f"  [machine] Already exists: {machine_id}")
        else:
            err = f"Machine {machine_id}: HTTP {resp.status_code} — {resp.text[:120]}"
            errors.append(err)
            print(f"  ✗ {err}")
            continue

        # ── 5. Flatten checklist sections into ordered items ─────────────────
        items = []
        idx = 0
        for section in data.get("sections", []):
            section_name = section.get("name", "General")
            for item_text in section.get("items", []):
                items.append({
                    "item_index": idx,
                    "label": item_text,
                    "section_name": section_name,
                    "completion_type": "confirmation",
                })
                idx += 1

        # ── 6. Create daily template ─────────────────────────────────────────
        template_title = f"{machine_name} Daily Checklist"
        resp = requests.post(f"{base}/dailys", headers=headers, json={
            "machine_id": machine_id,
            "title": template_title,
            "items": items,
            "assigned_to": bob_phone,
            "schedule_time": "00:00",
            "active": True,
        })
        if resp.status_code == 201:
            print(f"  [daily]   Created template for {machine_name} ({len(items)} items)")
            created_templates += 1
        else:
            err = f"Template {machine_name}: HTTP {resp.status_code} — {resp.text[:120]}"
            errors.append(err)
            print(f"  ✗ {err}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"Machines created:  {created_machines}")
    print(f"Templates created: {created_templates}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("\n✓ Import complete — navigate to /dailys in the admin UI to review.")


if __name__ == "__main__":
    main()
