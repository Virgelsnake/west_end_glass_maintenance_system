#!/usr/bin/env python3
"""
admin_cli.py — Command-line tool for remote admin dashboard operations.

Allows administrators to manage the West End Glass system without a web browser:
- Create and manage tickets
- Register machines
- Manage technician users
- View audit logs
- Monitor system stats

Usage:
    python tools/admin_cli.py --help
    python tools/admin_cli.py tickets list --status open
    python tools/admin_cli.py tickets create --machine WEG-MACHINE-0042 --title "Maintenance"
    python tools/admin_cli.py users list --active
    python tools/admin_cli.py machines create --id WEG-MACHINE-0042 --name "Test Machine"
    python tools/admin_cli.py audit log --limit 20

Environment:
    API_BASE_URL  Backend API endpoint (default: http://localhost:8000)
    ADMIN_TOKEN   JWT auth token (login first if not set)
"""

import argparse
import os
import sys
import json
from datetime import datetime
from functools import wraps

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Run: pip install requests")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_API_URL = "http://localhost:8000"
TOKEN_FILE = os.path.expanduser("~/.west_end_glass_token")
HR = "─" * 70


# ─────────────────────────────────────────────────────────────────────────────
# Token Management
# ─────────────────────────────────────────────────────────────────────────────

def save_token(token):
    """Save JWT token to file for reuse."""
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
        os.chmod(TOKEN_FILE, 0o600)  # Restrict permissions
    except Exception as e:
        print(f"Warning: Could not save token: {e}")


def load_token():
    """Load saved JWT token."""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def clear_token():
    """Remove saved token."""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# API Client
# ─────────────────────────────────────────────────────────────────────────────

class AdminClient:
    def __init__(self, api_url):
        self.api_url = api_url.rstrip('/')
        self.token = load_token()
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})

    def request(self, method, endpoint, **kwargs):
        """Make authenticated API request."""
        url = f"{self.api_url}{endpoint}"
        try:
            resp = self.session.request(method, url, timeout=10, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.text else None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                clear_token()
                print("\n❌ Authentication failed. Please login again.")
                sys.exit(1)
            raise
        except requests.exceptions.ConnectionError:
            print(f"\n❌ Cannot connect to {self.api_url}")
            print("   Is the backend running? Check: docker compose ps")
            sys.exit(1)

    def login(self, username, password):
        """Authenticate and save token."""
        try:
            resp = self.session.post(
                f"{self.api_url}/auth/login",
                data={"username": username, "password": password},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            self.token = data['access_token']
            save_token(self.token)
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid username or password")
            raise

    def get(self, endpoint, **kwargs):
        return self.request('GET', endpoint, **kwargs)

    def post(self, endpoint, data=None, **kwargs):
        return self.request('POST', endpoint, json=data, **kwargs)

    def patch(self, endpoint, data=None, **kwargs):
        return self.request('PATCH', endpoint, json=data, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Command Handlers
# ─────────────────────────────────────────────────────────────────────────────

def require_auth(func):
    """Decorator to ensure user is authenticated."""
    @wraps(func)
    def wrapper(args, client):
        if not client.token:
            print("\n❌ Not authenticated. Please login first:")
            print("   python tools/admin_cli.py login")
            sys.exit(1)
        return func(args, client)
    return wrapper


def cmd_login(args, client):
    """Login with admin credentials."""
    print("\n🔐 Admin Login")
    print(HR)
    username = input("Username: ").strip()
    import getpass
    password = getpass.getpass("Password: ")

    try:
        data = client.login(username, password)
        print(f"\n✓ Logged in as {data.get('full_name', username)}")
        print(f"  Role: {data.get('role', 'unknown')}")
    except ValueError as e:
        print(f"\n❌ {e}")
        sys.exit(1)


@require_auth
def cmd_logout(args, client):
    """Clear saved authentication token."""
    clear_token()
    print("\n✓ Logged out")


@require_auth
def cmd_tickets_list(args, client):
    """List tickets with optional filters."""
    params = {}
    if args.status:
        params['status'] = args.status
    if args.machine:
        params['machine_id'] = args.machine
    if args.assigned_to:
        params['assigned_to'] = args.assigned_to

    tickets = client.get('/tickets', params=params)

    print(f"\n📋 Tickets ({len(tickets)} found)")
    print(HR)

    if not tickets:
        print("No tickets found.")
        return

    for t in tickets:
        status_icon = {
            'open': '🔴',
            'in_progress': '🟡',
            'closed': '🟢'
        }.get(t.get('status'), '⚪')

        print(f"{status_icon} [{t['_id'][-8:]}] {t['title']}")
        print(f"   Machine: {t.get('machine_id', '—')} | Priority: {t.get('priority', '—')}")
        print(f"   Status: {t.get('status', '—')} | Assigned: {t.get('assigned_to', 'Unassigned')}")
        print()


@require_auth
def cmd_tickets_create(args, client):
    """Create a new ticket."""
    data = {
        'machine_id': args.machine,
        'title': args.title,
        'description': args.description or None,
        'priority': args.priority or 5,
        'category': args.category or None,
        'assigned_to': args.assigned_to or None,
        'steps': []
    }

    # Add steps
    if args.steps:
        for i, step in enumerate(args.steps):
            data['steps'].append({
                'step_index': i,
                'label': step,
                'completion_type': 'confirmation',
                'completed': False
            })

    result = client.post('/tickets', data)
    print(f"\n✓ Ticket created: {result['_id'][-8:]}")
    print(f"  Title: {result['title']}")
    print(f"  Machine: {result['machine_id']}")


@require_auth
def cmd_users_list(args, client):
    """List technician users."""
    params = {}
    if args.active:
        params['active'] = 'true'

    users = client.get('/users', params=params)

    print(f"\n👥 Technicians ({len(users)} found)")
    print(HR)

    if not users:
        print("No users found.")
        return

    for u in users:
        status = "✓ Active" if u.get('active') else "✗ Inactive"
        print(f"{u['name']:<25} {u['phone_number']:<18} {status}")


@require_auth
def cmd_users_create(args, client):
    """Create a new technician user."""
    data = {
        'phone_number': args.phone,
        'name': args.name,
        'active': True,
        'language': args.language or 'en'
    }

    result = client.post('/users', data)
    print(f"\n✓ User created: {result['name']} ({result['phone_number']})")


@require_auth
def cmd_machines_list(args, client):
    """List registered machines."""
    machines = client.get('/machines')

    print(f"\n🔧 Machines ({len(machines)} found)")
    print(HR)

    if not machines:
        print("No machines found.")
        return

    for m in machines:
        print(f"{m['machine_id']:<20} {m['name']:<25} {m.get('location', '—')}")


@require_auth
def cmd_machines_create(args, client):
    """Register a new machine."""
    data = {
        'machine_id': args.id,
        'name': args.name,
        'location': args.location or 'Unknown'
    }

    result = client.post('/machines', data)
    print(f"\n✓ Machine registered: {result['machine_id']}")
    print(f"  Name: {result['name']}")


@require_auth
def cmd_audit_log(args, client):
    """View audit log."""
    params = {'limit': args.limit or 50}
    events = client.get('/audit', params=params)

    print(f"\n📋 Audit Log ({len(events)} events)")
    print(HR)

    for e in events:
        timestamp = e.get('timestamp', '')[:16]
        actor = e.get('actor', '—')
        event_type = e.get('event_type', '—')
        print(f"{timestamp} | {actor:<20} | {event_type:<15}")


@require_auth
def cmd_dashboard_stats(args, client):
    """View dashboard statistics."""
    stats = client.get('/dashboard/stats')

    print(f"\n📊 Dashboard Statistics")
    print(HR)

    # Ticket counts
    counts = stats.get('tickets_by_status', {})
    print("\n🎟️  Tickets:")
    print(f"  Open: {counts.get('open', 0)}")
    print(f"  In Progress: {counts.get('in_progress', 0)}")
    print(f"  Closed: {counts.get('closed', 0)}")
    print(f"  Overdue: {stats.get('overdue_count', 0)}")

    # Technician workload
    workload = stats.get('technician_workload', {})
    if workload:
        print("\n👥 Technician Workload:")
        for tech, counts in workload.items():
            total = counts.get('open', 0) + counts.get('in_progress', 0)
            print(f"  {tech}: {total} active tickets")


# ─────────────────────────────────────────────────────────────────────────────
# CLI Parser
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="West End Glass — Admin CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/admin_cli.py login
  python tools/admin_cli.py tickets list --status open
  python tools/admin_cli.py tickets create --machine WEG-MACHINE-0042 --title "Maintenance"
  python tools/admin_cli.py users list --active
  python tools/admin_cli.py machines create --id WEG-MACHINE-0042 --name "Test Machine"
  python tools/admin_cli.py audit log --limit 20
  python tools/admin_cli.py stats dashboard

For more help: python tools/admin_cli.py <command> --help
        """
    )

    parser.add_argument(
        '--api-url',
        default=os.environ.get('API_BASE_URL', DEFAULT_API_URL),
        help='Backend API URL (default: %(default)s)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Login
    subparsers.add_parser('login', help='Login with admin credentials')
    subparsers.add_parser('logout', help='Logout and clear saved token')

    # Tickets
    tickets_parser = subparsers.add_parser('tickets', help='Manage tickets')
    tickets_sub = tickets_parser.add_subparsers(dest='subcommand')

    list_parser = tickets_sub.add_parser('list', help='List tickets')
    list_parser.add_argument('--status', help='Filter by status (open/in_progress/closed)')
    list_parser.add_argument('--machine', help='Filter by machine ID')
    list_parser.add_argument('--assigned-to', help='Filter by assignee phone')

    create_parser = tickets_sub.add_parser('create', help='Create ticket')
    create_parser.add_argument('--machine', required=True, help='Machine ID')
    create_parser.add_argument('--title', required=True, help='Ticket title')
    create_parser.add_argument('--description', help='Description')
    create_parser.add_argument('--priority', type=int, help='Priority (1-10)')
    create_parser.add_argument('--category', help='Category')
    create_parser.add_argument('--assigned-to', help='Technician phone number')
    create_parser.add_argument('--steps', nargs='+', help='Step descriptions')

    # Users
    users_parser = subparsers.add_parser('users', help='Manage technicians')
    users_sub = users_parser.add_subparsers(dest='subcommand')

    users_list = users_sub.add_parser('list', help='List technicians')
    users_list.add_argument('--active', action='store_true', help='Only active users')

    users_create = users_sub.add_parser('create', help='Create technician')
    users_create.add_argument('--phone', required=True, help='Phone number (E.164)')
    users_create.add_argument('--name', required=True, help='Full name')
    users_create.add_argument('--language', help='Preferred language (en/es/etc)')

    # Machines
    machines_parser = subparsers.add_parser('machines', help='Manage machines')
    machines_sub = machines_parser.add_subparsers(dest='subcommand')

    machines_list = machines_sub.add_parser('list', help='List machines')

    machines_create = machines_sub.add_parser('create', help='Register machine')
    machines_create.add_argument('--id', required=True, help='Machine ID (WEG-MACHINE-XXXX)')
    machines_create.add_argument('--name', required=True, help='Machine name')
    machines_create.add_argument('--location', help='Location')

    # Audit
    audit_parser = subparsers.add_parser('audit', help='View audit logs')
    audit_sub = audit_parser.add_subparsers(dest='subcommand')

    audit_log = audit_sub.add_parser('log', help='View recent events')
    audit_log.add_argument('--limit', type=int, help='Number of events to show')

    # Dashboard
    stats_parser = subparsers.add_parser('stats', help='View system statistics')
    stats_sub = stats_parser.add_subparsers(dest='subcommand')
    stats_sub.add_parser('dashboard', help='Dashboard KPIs')

    args = parser.parse_args()

    client = AdminClient(args.api_url)

    # Route commands
    if args.command == 'login':
        cmd_login(args, client)
    elif args.command == 'logout':
        cmd_logout(args, client)
    elif args.command == 'tickets':
        if args.subcommand == 'list':
            cmd_tickets_list(args, client)
        elif args.subcommand == 'create':
            cmd_tickets_create(args, client)
    elif args.command == 'users':
        if args.subcommand == 'list':
            cmd_users_list(args, client)
        elif args.subcommand == 'create':
            cmd_users_create(args, client)
    elif args.command == 'machines':
        if args.subcommand == 'list':
            cmd_machines_list(args, client)
        elif args.subcommand == 'create':
            cmd_machines_create(args, client)
    elif args.command == 'audit':
        if args.subcommand == 'log':
            cmd_audit_log(args, client)
    elif args.command == 'stats':
        if args.subcommand == 'dashboard':
            cmd_dashboard_stats(args, client)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
