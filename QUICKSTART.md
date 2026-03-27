# West End Glass Maintenance System — Quick Start Guide

## 🚀 Getting Started

This guide will help you set up and test the West End Glass Maintenance System locally.

### Prerequisites

- Docker & Docker Compose
- Python 3.8+
- `requests` library: `pip install requests`

### 1. Start the System

```bash
# From the project root
docker compose up -d

# Verify services are running
docker compose ps
```

You should see:
- `mongo` (MongoDB database)
- `fastapi-app` (Backend API at http://localhost:8000)
- `admin-frontend` (Admin Dashboard at http://localhost:3030)

### 2. Access the Admin Dashboard

Open your browser and go to: **http://localhost:3030**

**Default credentials:**
- Username: `admin`
- Password: (see `backend_api/.env` for ADMIN_PASSWORD)

### 3. Create Test Data

In the Admin Dashboard:

1. **Create a Machine:**
   - Go to **Machines** → **Add Machine**
   - ID: `WEG-MACHINE-0042`
   - Name: `Test Machine`
   - Location: `Field`

2. **Create Technicians:**
   - Go to **Users** → **Add User**
   - Name: `John Smith`
   - Phone: `+15551234567`
   - Status: **Active**
   - Repeat for additional technicians

3. **Create a Ticket:**
   - Go to **Tickets** → **New Ticket**
   - Machine: `WEG-MACHINE-0042`
   - Assigned To: `John Smith`
   - Status: `Open`
   - Priority: `5`
   - Add step(s) for the technician to complete

### 4. Test the WhatsApp Bot Simulator

Now test the bot using the CLI simulator:

```bash
# Interactive mode (pick technician from list)
python tools/simulate_chat.py

# Or specify directly
python tools/simulate_chat.py --phone +15551234567

# Send a test message
python tools/simulate_chat.py --phone +15551234567 --message "WEG-MACHINE-0042"
```

The simulator will:
1. Authenticate the technician (phone whitelist)
2. Route to the correct ticket
3. Process the message through Claude AI
4. Display the bot's response

For more details, see [tools/README.md](tools/README.md).

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Field Technician                         │
│                  (WhatsApp on Phone)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼ Real WhatsApp API      ▼ CLI Simulator
    ┌──────────────────┐    ┌──────────────────┐
    │  Meta Cloud API  │    │  tools/simulate  │
    │  Webhook Handler │    │  _chat.py        │
    └────────┬─────────┘    └────────┬─────────┘
             │                       │
             └───────────┬───────────┘
                         │
                         ▼
         ┌──────────────────────────────────┐
         │  FastAPI Backend                 │
         │  (Process messages, route,       │
         │   call Claude AI, audit logs)    │
         └──────────────────┬───────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    ┌─────────┐        ┌─────────┐      ┌──────────┐
    │ MongoDB │        │  Claude │      │ Response │
    │Database │        │   API   │      │to Tech   │
    └─────────┘        └─────────┘      └──────────┘
         │
         ▼
    ┌──────────────────┐        ┌──────────────────┐
    │ Admin Dashboard  │        │ Tech Portal      │
    │ (React Web App)  │        │ (React Web App)  │
    └──────────────────┘        └──────────────────┘
```

---

## 🧪 Testing Scenarios

### Scenario 1: Basic Ticket Workflow

1. Create a ticket for `WEG-MACHINE-0042` in the admin dashboard
2. Assign to `+15551234567`
3. Run: `python tools/simulate_chat.py --phone +15551234567 --message "WEG-MACHINE-0042"`
4. Bot responds with first step
5. Continue chatting with bot to complete steps

### Scenario 2: Error Cases

Test how the system handles errors:

```bash
# Invalid machine ID
python tools/simulate_chat.py --phone +15551234567 --message "WEG-MACHINE-INVALID"

# Unauthorized technician (phone not in system)
python tools/simulate_chat.py --phone +12025551234 --message "test"

# No assigned tickets
python tools/simulate_chat.py --phone +15551234567 --message "random message"
```

### Scenario 3: Multi-Turn Conversation

```bash
# Start session
python tools/simulate_chat.py --phone +15551234567

# In the interactive prompt:
[+15551234567] > WEG-MACHINE-0042
# Bot shows first step

[+15551234567] > The pump looks normal
# Bot acknowledges, moves to next step

[+15551234567] > I've replaced the filter
# Bot continues through steps

[+15551234567] > All done
# Bot closes ticket
```

---

## 📚 Key Files & Directories

| Path | Purpose |
|------|---------|
| `backend_api/` | FastAPI backend, message processing, Claude integration |
| `backend_admin_page/` | React admin dashboard |
| `tools/simulate_chat.py` | WhatsApp bot simulator CLI |
| `tools/README.md` | Complete tools documentation |
| `Documentation/` | Architecture & design docs |
| `docker-compose.yml` | Service configuration |

---

## 🔍 Monitoring

### View Backend Logs
```bash
docker compose logs fastapi-app -f
```

### View Database
```bash
# Connect to MongoDB
docker compose exec mongo mongosh

# In MongoDB shell:
use maintenance_system
db.tickets.find()
db.messages.find()
db.audit_logs.find()
```

### Check API Health
```bash
curl http://localhost:8000/health
```

### OpenAPI Docs
Open http://localhost:8000/docs in your browser for interactive API documentation.

---

## 🛑 Stopping the System

```bash
docker compose down
```

---

## 📖 Further Reading

- [Tools Documentation](tools/README.md) — Detailed guide to CLI tools
- [Architecture Overview](Documentation/JoesTechTake.md) — System design & NFC flows
- [Backend API Docs](http://localhost:8000/docs) — Interactive API reference

---

## ❓ Troubleshooting

**Backend won't start?**
```bash
# Check logs
docker compose logs fastapi-app

# Restart all services
docker compose down && docker compose up -d
```

**Simulator says "No active technicians"?**
- Go to Admin Dashboard → Users
- Ensure at least one user has status=**Active**

**Claude API errors?**
- Check that `ANTHROPIC_API_KEY` is set in `backend_api/.env`
- Verify API key is valid and hasn't expired

**Port conflicts?**
- Change ports in `docker-compose.yml`:
  - `8000` → FastAPI
  - `3030` → Admin Dashboard
  - `27017` → MongoDB

---

## ✅ Verification Checklist

- [ ] Docker containers running (`docker compose ps`)
- [ ] Admin Dashboard accessible at http://localhost:3030
- [ ] Can login with default admin credentials
- [ ] Created at least one machine in database
- [ ] Created at least one active technician
- [ ] Created a test ticket
- [ ] Simulator loads technicians list without errors
- [ ] Simulator successfully sends messages
- [ ] Bot responses display with proper formatting

---

**Happy testing! 🎉**
