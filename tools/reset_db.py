#!/usr/bin/env python3
"""
reset_db.py — Clear machines and tickets from the database.
Leaves users, admins, audit_logs, and messages intact.

Usage:
  python tools/reset_db.py [--mongo-url mongodb://localhost:27017] [--db-name west_end_glass]

Environment variables (fallback):
  MONGO_URL or MONGODB_URL
  MONGODB_DB_NAME
"""

import argparse
import os
import sys

try:
    from pymongo import MongoClient
except ImportError:
    print("Error: 'pymongo' package required. Run: pip install pymongo")
    sys.exit(1)


DEFAULT_MONGO_URL = "mongodb://localhost:27017"
DEFAULT_DB_NAME = "west_end_glass"

DOCKER_NOTE = """
NOTE: If MongoDB is running in Docker without a host port mapping, run via:
  docker exec mongo mongosh west_end_glass --eval "\\
    db.machines.deleteMany({}); \\
    db.tickets.deleteMany({}); \\
    db.daily_checklist_templates.deleteMany({}); \\
    print('done')"
"""


def main():
    parser = argparse.ArgumentParser(description="Reset machines and tickets collections.")
    parser.add_argument(
        "--mongo-url",
        default=os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL") or DEFAULT_MONGO_URL,
    )
    parser.add_argument(
        "--db-name",
        default=os.environ.get("MONGODB_DB_NAME", DEFAULT_DB_NAME),
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    print(f"\nTarget:   {args.mongo_url}  /  {args.db_name}")
    print("This will DELETE all documents in 'machines' and 'tickets'.")
    print("Users, admins, audit_logs, and messages will NOT be touched.\n")

    if not args.yes:
        confirm = input("Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)

    client = MongoClient(args.mongo_url)
    db = client[args.db_name]

    # Count before
    machines_before = db.machines.count_documents({})
    tickets_before = db.tickets.count_documents({})
    print(f"\nBefore: {machines_before} machines, {tickets_before} tickets")

    # Delete
    db.machines.delete_many({})
    db.tickets.delete_many({})

    # Also clear any daily_checklist_templates from previous runs
    daily_before = db.daily_checklist_templates.count_documents({})
    if daily_before:
        db.daily_checklist_templates.delete_many({})
        print(f"        {daily_before} daily_checklist_templates cleared")

    machines_after = db.machines.count_documents({})
    tickets_after = db.tickets.count_documents({})
    print(f"After:  {machines_after} machines, {tickets_after} tickets")
    print("\nDone. Database is ready for import.")

    client.close()


if __name__ == "__main__":
    main()
