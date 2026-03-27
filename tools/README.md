# West End Glass — Tools & Testing

This directory contains CLI tools for testing, simulating, and managing the West End Glass Maintenance System from the command line without needing a web browser.

## 📋 Available Tools

| Tool | Purpose | Use Case |
|------|---------|----------|
| `simulate_chat.py` | Simulate WhatsApp bot interactions | Test technician workflows, bot responses |
| `admin_cli.py` | Remote dashboard management | Create tickets, manage users, view logs from CLI |

---

## 🤖 WhatsApp Bot Simulator (`simulate_chat.py`)

**What it does:** Tests the WhatsApp bot that technicians interact with in the field. Simulates the complete message processing pipeline:
- Phone number whitelist auth
- Ticket routing
- Claude AI agent processing
- Message & audit logging

### Quick Start

```bash
# Interactive mode (defaults to John Smith +15551234567)
python tools/simulate_chat.py

# Interactive mode (specify different technician)
python tools/simulate_chat.py --phone +15559876543

# Send a single message and exit (uses default technician)
python tools/simulate_chat.py --message "WEG-MACHINE-0042"

# Custom API endpoint
python tools/simulate_chat.py --api-url http://localhost:8001
```

### Interactive Commands

| Command | Purpose |
|---------|---------|
| `.help` | Show help and examples |
| `.quit` / `.exit` | Exit the simulator |
| Send machine ID (e.g., `WEG-MACHINE-0042`) | Start a ticket session |
| Send any message | Chat with Claude about the active ticket |

### Examples

```
[+15551234567] > WEG-MACHINE-0042
🤖 Bot Response:
├────────────────────────────────────────────────
│ Hi! I found an open ticket for WEG-MACHINE-0042.
│ Here are the steps I need you to complete:
│ 1. Inspect the pump...
└────────────────────────────────────────────────

📋 Ticket Context:
   ID:      [abc12345]
   Title:   Monthly Maintenance
   Machine: WEG-MACHINE-0042
   Status:  in_progress

[+15551234567] > The pump looks normal
🤖 Bot Response:
├────────────────────────────────────────────────
│ Great! Let's move to the next step...
└────────────────────────────────────────────────

[+15551234567] > .help
┌──────────────────────────────────────────────┐
│ COMMANDS                                      │
│ .quit / .exit      Exit the simulator         │
│ .help              Show this message          │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│ HOW TO USE                                    │
│ 1. Start by sending a machine ID              │
│ 2. Chat with Claude about the work            │
│ 3. Claude guides you through ticket steps     │
│ 4. Close when all steps complete              │
└──────────────────────────────────────────────┘
```

### Prerequisites

- Python 3.8+
- `requests` library: `pip install requests`
- Backend running at `http://localhost:8000` (or custom URL)
- At least one active technician in the database

### How It Works

1. **Auth:** Your phone number must be in the `users` collection with `active=true`
2. **Routing:** Messages starting with `WEG-MACHINE-` trigger ticket lookup
3. **Processing:** Without a machine ID, the system finds your most recent in-progress ticket
4. **Claude Loop:** Each message is sent to Claude AI who processes it in ticket context
5. **Response:** The bot's response is displayed with ticket metadata

---

## 👨‍💼 Admin Dashboard CLI (`admin_cli.py`)

**What it does:** Manage the West End Glass system entirely from the command line. Create tickets, register machines, manage technicians, and view audit logs without needing a web browser.

**Use cases:**
- Remote administration without web access
- Scripting and automation
- Integration with other tools
- Batch operations (create multiple users, tickets, etc.)

### Quick Start

```bash
# Login with admin credentials
python tools/admin_cli.py login

# List all open tickets
python tools/admin_cli.py tickets list --status open

# Create a new ticket
python tools/admin_cli.py tickets create --machine WEG-MACHINE-0042 --title "Maintenance"

# List active technicians
python tools/admin_cli.py users list --active

# Create a new technician
python tools/admin_cli.py users create --phone +15551234567 --name "John Smith"

# Register a new machine
python tools/admin_cli.py machines create --id WEG-MACHINE-0042 --name "Test Machine"

# View recent audit logs
python tools/admin_cli.py audit log --limit 20

# View dashboard statistics
python tools/admin_cli.py stats dashboard
```

### Commands

#### Authentication

```bash
python tools/admin_cli.py login          # Login and save token
python tools/admin_cli.py logout         # Clear saved token
```

**Token Storage:**
- Saved to `~/.west_end_glass_token` (user's home directory)
- Automatically included in all API requests
- Cleared on logout or 401 authentication error
- Restricted file permissions (0o600)

#### Tickets

```bash
# List tickets (with optional filters)
python tools/admin_cli.py tickets list [--status open|in_progress|closed]
python tools/admin_cli.py tickets list --machine WEG-MACHINE-0042
python tools/admin_cli.py tickets list --assigned-to +15551234567

# Create a ticket
python tools/admin_cli.py tickets create \
  --machine WEG-MACHINE-0042 \
  --title "Monthly Maintenance" \
  --description "Routine inspection and lubrication" \
  --priority 5 \
  --category maintenance \
  --assigned-to +15551234567 \
  --steps "Inspect pump" "Check filter" "Apply lubricant"
```

#### Users (Technicians)

```bash
# List technicians
python tools/admin_cli.py users list           # All users
python tools/admin_cli.py users list --active  # Active only

# Create a technician
python tools/admin_cli.py users create \
  --phone +15551234567 \
  --name "John Smith" \
  --language en
```

#### Machines

```bash
# List machines
python tools/admin_cli.py machines list

# Register a machine
python tools/admin_cli.py machines create \
  --id WEG-MACHINE-0042 \
  --name "Test Machine" \
  --location "Field Location"
```

#### Audit Log

```bash
# View recent events
python tools/admin_cli.py audit log        # Last 50 events
python tools/admin_cli.py audit log --limit 100
```

#### Dashboard

```bash
# View system statistics
python tools/admin_cli.py stats dashboard    # KPIs, workload, overdue
```

### Examples

#### Complete Workflow: Setup New Machine

```bash
# 1. Login
python tools/admin_cli.py login

# 2. Register the machine
python tools/admin_cli.py machines create --id WEG-MACHINE-0042 --name "Pump Assembly"

# 3. Create technician if needed
python tools/admin_cli.py users create --phone +15551234567 --name "John Smith"

# 4. Create ticket for the machine
python tools/admin_cli.py tickets create \
  --machine WEG-MACHINE-0042 \
  --title "Initial Setup & Testing" \
  --assigned-to +15551234567 \
  --steps "Inspect equipment" "Verify NFC tag" "Test WhatsApp connectivity"

# 5. View the ticket
python tools/admin_cli.py tickets list --machine WEG-MACHINE-0042

# 6. Check dashboard
python tools/admin_cli.py stats dashboard
```

#### Batch User Creation (with shell script)

```bash
#!/bin/bash
python tools/admin_cli.py login

# Create multiple technicians
while IFS=',' read -r phone name; do
  python tools/admin_cli.py users create --phone "$phone" --name "$name"
done < technicians.csv
```

### Integration

#### With Other Tools

```bash
# Get list of tickets in JSON for other processing
python tools/admin_cli.py tickets list --status open | jq .

# Pipe to grep for filtering
python tools/admin_cli.py users list | grep "Active"
```

#### Scheduled Tasks (cron)

```bash
# Daily backup of audit logs
0 2 * * * python /path/to/tools/admin_cli.py audit log --limit 1000 >> /backups/audit.log

# Weekly system report
0 9 * * 1 python /path/to/tools/admin_cli.py stats dashboard
```

### Authentication & Security

**Login Flow:**
1. Run `python tools/admin_cli.py login`
2. Enter admin username and password
3. JWT token is obtained and saved to `~/.west_end_glass_token`
4. Token is automatically used in all subsequent commands
5. Run `python tools/admin_cli.py logout` to clear token

**Token Expiration:**
- If token expires, you'll see: `❌ Authentication failed. Please login again.`
- Simply run `python tools/admin_cli.py login` to get a new token

**Security Notes:**
- Tokens are stored in user's home directory with restricted permissions (mode 0o600)
- Never commit tokens to git
- Use environment-specific credentials for different deployments
- For CI/CD, use `ADMIN_TOKEN` environment variable instead of file-based storage

### Errorhandling

The tool provides clear error messages:

```bash
# Connection error
❌ Cannot connect to http://localhost:8000
   Is the backend running? Check: docker compose ps

# Authentication error
❌ Authentication failed. Please login again.

# Invalid input
❌ Invalid argument: --status must be open, in_progress, or closed
```

### Prerequisites

- Python 3.8+
- `requests` library: `pip install -r tools/requirements.txt`
- Backend running at `http://localhost:8000` (or custom URL via `--api-url`)
- Admin credentials (set in `backend_api/.env`)

---

**What it does:** Tests **real** WhatsApp message delivery (requires Meta credentials).

### Setup

1. Add Meta Cloud API credentials to `backend_api/.env`:
   ```
   META_WHATSAPP_TOKEN=your_permanent_access_token_here
   META_PHONE_NUMBER_ID=your_phone_number_id_here
   ```

2. Install dependency:
   ```bash
   pip install httpx python-dotenv
   ```

### Usage

```bash
# Send a test message to a real WhatsApp number
python test/test_whatsapp_text.py --to +15551234567 --msg "Hello from West End Glass!"

# Or specify defaults in the script
python test/test_whatsapp_text.py
```

**⚠️ WARNING:** This sends **real WhatsApp messages**. Use test numbers only.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────┐
│   Technician in the Field            │
│   (WhatsApp Phone)                   │
└──────────────────┬────────────────────┘
                   │
                   │ Real WhatsApp API
                   ▼
   ┌──────────────────────────┐
   │  Webhook Handler         │
   │  /webhook/whatsapp       │
   └──────────────┬───────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
   ┌──────────────┐  ┌──────────────────┐
   │ Simulator    │  │ Message Pipeline │
   │ (this tool)  │  │ (real webhook)   │
   └──────────────┘  └─────────┬────────┘
                                │
                      ┌─────────┴──────────┐
                      │                    │
                      ▼                    ▼
              ┌───────────────┐  ┌──────────────┐
              │   CLI Test    │  │ Admin Panel  │
              │ Real WhatsApp │  │ Dashboard    │
              └───────────────┘  └──────────────┘
```

---

## 🔐 Authentication Flows

### WhatsApp Bot (this simulator)
```
Phone Number → Database Lookup → Whitelist Check → ✓ Authorized
     ↓
 Phone not in `users.active`? → ⛔ Rejected
```

### Technician Portal
```
Phone # + PIN → Hash Comparison → JWT Token → ✓ Authorized
     ↓
Invalid PIN? → ⛔ Rejected
```

### Admin Dashboard
```
Username + Password → Hash Comparison → JWT Token (with role) → ✓ Authorized
     ↓
Role Check (super_admin/editor/viewer) → Permission Check
```

---

## 🐛 Troubleshooting

### ❌ "Cannot connect to http://localhost:8000"
- Check backend is running: `docker compose ps`
- Start backend: `docker compose up -d`

### ❌ "No active technicians found"
- Log in to Admin Dashboard
- Go to Users → Add a new user with `active=true`
- It will appear in the simulator picker

### ❌ "No open tickets assigned to you"
- Create a ticket in the Admin Dashboard
- Assign it to your phone number
- Then send the machine ID or a regular message

### ❌ "Phone number not in whitelist"
- You're using a phone number not in the database
- Check the `users` collection in MongoDB
- Ensure `active=true` for your test phone number

---

## 📊 Testing Scenarios

### Scenario 1: Basic Ticket Workflow
```
1. Login to Admin Dashboard
2. Create a ticket for WEG-MACHINE-0042
3. Assign to your test phone number
4. Run: python tools/simulate_chat.py
5. Send "WEG-MACHINE-0042" to start ticket
6. Chat to complete steps
```

### Scenario 2: Error Handling
```
1. Send "WEG-MACHINE-INVALID" (machine doesn't exist)
   └─ Bot should indicate no tickets found

2. Send a message without any assigned tickets
   └─ Bot should ask for a machine ID

3. Send an invalid phone number
   └─ System should reject with "not in whitelist"
```

### Scenario 3: Multi-turn Conversation
```
1. Start a ticket with machine ID
2. Claude guides through steps
3. Respond with step completion messages
4. Test branch logic (e.g., if issue found, ask diagnostic questions)
5. Complete all steps
6. Confirm ticket closure
```

---

## 📝 Development Notes

- The simulator uses the **same auth logic** as real WhatsApp webhooks
- All messages and responses are saved to the database (audit trail)
- Claude AI processing is identical to production
- No actual WhatsApp messages are sent (unlike `test_whatsapp_text.py`)

For more details on the message pipeline, see:
- `backend_api/app/services/message_processor.py`
- `backend_api/app/services/claude_agent.py`
- `backend_api/app/routers/simulate.py`

---

## ✅ Prerequisites Checklist

- [ ] Backend running (`docker compose up`)
- [ ] MongoDB accessible
- [ ] At least one active technician in database
- [ ] Python 3.8+ with `requests` installed
- [ ] For real WhatsApp tests: Meta Cloud API credentials in `.env`

---

## 📚 Related Documentation

- Architecture: See `Documentation/` folder
- API Endpoints: Backend OpenAPI docs at `http://localhost:8000/docs`
- Admin Dashboard: `backend_admin_page/README.md`
- Tech Portal: `backend_tech_portal/` (if exists)
