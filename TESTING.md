# Development Workflow & Testing Guide

This document explains how to use the West End Glass testing tools as part of your development workflow.

## Three Types of Testing

### 1. 🤖 WhatsApp Bot Testing (CLI Simulator)

**What to test:** The WhatsApp bot that field technicians use  
**Tool:** `python tools/simulate_chat.py`  
**Auth:** Phone whitelist (no password needed)  
**Use cases:**
- Test bot responses to technician messages
- Verify ticket routing works correctly
- Test multi-turn conversations with Claude AI
- Check error handling for edge cases

**Example workflow:**
```bash
# Start interactive session
python tools/simulate_chat.py

# Pick a technician from the list, then:
[+15551234567] > WEG-MACHINE-0042      # Start ticket
[+15551234567] > The pump looks normal  # Reply to bot
[+15551234567] > All steps done         # Complete ticket
```

See [tools/README.md](tools/README.md) for detailed examples.

### 2. 🔧 Admin Dashboard Testing

**What to test:** Ticket management, user administration, audit logs  
**Interface:** Web browser at http://localhost:3030  
**Auth:** Username + password (role-based: super_admin, editor, viewer)  
**Use cases:**
- Create and assign tickets
- Manage technician users
- Register machines in the system
- View audit trail of all system events

**Typical workflow:**
1. Log in as super_admin
2. Create a machine (go to **Machines** → **Add**)
3. Create a technician user (go to **Users** → **Add**)
4. Create a ticket (go to **Tickets** → **New Ticket**)
5. Assign to the technician you created
6. Use the simulator to test the technician's interaction

### 3. 🔌 Real WhatsApp Testing (Meta Cloud API)

**What to test:** Actual WhatsApp message delivery  
**Tool:** `python test/test_whatsapp_text.py`  
**Auth:** Meta Cloud API credentials in `backend_api/.env`  
**Use cases:**
- Test real message delivery to WhatsApp numbers
- Verify webhook integration with Meta
- Test end-to-end production flow

**⚠️ WARNING:** This sends real WhatsApp messages. Use test numbers only.

See [test/test_whatsapp_text.py](test/test_whatsapp_text.py) for instructions.

---

## Recommended Development Workflow

### For Bot Development

```
1. Create test data in Admin Dashboard
   ├─ At least one active technician user
   ├─ At least one machine
   └─ At least one ticket assigned to the technician

2. Run the CLI simulator locally
   python tools/simulate_chat.py

3. Test various messages and scenarios
   ├─ Valid machine IDs (WEG-MACHINE-XXXX)
   ├─ Invalid machine IDs
   ├─ Messages without a ticket
   └─ Multi-turn conversations

4. Check results
   ├─ Did bot respond correctly?
   ├─ Was ticket routed properly?
   ├─ Did Claude process the message?
   ├─ Are responses formatted correctly?
   └─ Are all interactions in the audit log?

5. Debug via logs
   docker compose logs fastapi-app
```

### For Admin Dashboard Development

```
1. Access the dashboard at http://localhost:3030

2. Test each feature
   ├─ Create/edit/delete machines
   ├─ Create/edit/deactivate users
   ├─ Create/edit/reassign tickets
   ├─ View audit logs
   ├─ Check dashboard stats
   └─ Generate reports

3. Verify changes persist
   ├─ Restart backend
   ├─ Re-login to dashboard
   ├─ Confirm data is still there
```

### For Field Technician Portal Development

```
1. Log in with technician credentials
   ├─ Phone number + PIN

2. Test technician-facing features
   ├─ View assigned tickets
   ├─ Complete steps
   ├─ Upload photos
   ├─ Add notes

3. Verify data is reflected in admin dashboard
   ├─ Admin sees completed steps
   ├─ Audit log shows techniciam actions
```

---

## Testing Scenarios

### ✅ Happy Path: Complete Ticket

```bash
# 1. Admin creates ticket for WEG-MACHINE-0042
#    Dashboard → Tickets → New Ticket
#    - Machine: WEG-MACHINE-0042
#    - Assigned: John Smith (+15551234567)
#    - Steps: [Inspect pump, Check filter, Lubricate bearings]

# 2. Technician starts work via WhatsApp
python tools/simulate_chat.py --phone +15551234567 --message "WEG-MACHINE-0042"

# 3. Bot responds with first step
# 🤖 Bot Response:
# ├────────────────────────────────────────────────────────────
# │ Hi John! I found an open ticket for WEG-MACHINE-0042
# │ Step 1/3: Inspect the pump for any visible damage or leaks
# └────────────────────────────────────────────────────────────

# 4. Technician responds
[+15551234567] > Pump looks normal, no damage

# 5. Bot continues
# 🤖 Bot Response:
# ├────────────────────────────────────────────────────────────
# │ Great! Moving to the next step...
# │ Step 2/3: Check the filter and replace if needed
# └────────────────────────────────────────────────────────────

# ... continue through all steps ...

# 6. Technician closes ticket
[+15551234567] > All steps complete

# 7. Admin sees ticket marked as closed in dashboard
#    Dashboard → Tickets (status changed to "closed")
```

### ⚠️ Error Case: Invalid Machine

```bash
python tools/simulate_chat.py --phone +15551234567 --message "WEG-MACHINE-INVALID"

# Expected response:
# 🤖 Bot Response:
# ├────────────────────────────────────────────────────────────
# │ No open ticket found for WEG-MACHINE-INVALID.
# └────────────────────────────────────────────────────────────
```

### 🔒 Auth Case: Unauthorized Phone

```bash
python tools/simulate_chat.py --phone +12025551234

# Expected response:
# ⛔ UNAUTHORIZED
# Sorry, this number is not registered.
# Please contact your administrator.
```

---

## Debugging Guide

### Check if Backend is Running
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### Check Active Technicians
```bash
curl http://localhost:8000/simulate/users
# Expected: JSON array of active users
```

### Monitor Messages in Database
```bash
docker compose exec mongo mongosh
use maintenance_system
db.messages.find().pretty()    # See all messages
db.tickets.find().pretty()     # See all tickets
db.audit_logs.find().pretty()  # See all events
```

### Check Claude API Integration
```bash
# Check if API key is set
docker compose exec fastapi-app printenv | grep ANTHROPIC

# Check backend logs for Claude errors
docker compose logs fastapi-app | grep -i claude
```

### Verbose Simulator Output
```bash
# Add debugging to see HTTP requests
HTTP_DEBUG=1 python tools/simulate_chat.py --phone +15551234567
```

---

## Database Schema Reference

### Technician Users (Active)
```json
{
  "_id": ObjectId,
  "phone_number": "+15551234567",
  "name": "John Smith",
  "active": true,
  "language": "en",
  "last_activity": ISODate,
  "created_at": ISODate
}
```

### Machines
```json
{
  "_id": ObjectId,
  "machine_id": "WEG-MACHINE-0042",
  "name": "Test Machine",
  "location": "Field",
  "created_at": ISODate
}
```

### Tickets
```json
{
  "_id": ObjectId,
  "machine_id": "WEG-MACHINE-0042",
  "title": "Monthly Maintenance",
  "description": "...",
  "status": "open|in_progress|closed",
  "assigned_to": "+15551234567",
  "secondary_assigned_to": null,
  "priority": 5,
  "category": "maintenance",
  "steps": [
    {
      "step_index": 0,
      "label": "Inspect the pump",
      "completion_type": "confirmation",
      "completed": false,
      "completed_at": null,
      "completed_by": null
    }
  ],
  "due_date": ISODate,
  "created_at": ISODate,
  "created_by": "admin"
}
```

### Messages
```json
{
  "_id": ObjectId,
  "ticket_id": ObjectId,
  "direction": "inbound|outbound",
  "phone_number": "+15551234567",
  "content": "...",
  "ai_generated": false,
  "timestamp": ISODate
}
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Simulator says "No active technicians" | Create a user in Admin Dashboard with status=Active |
| Simulator shows "500 Internal Server Error" | Check ANTHROPIC_API_KEY in backend_api/.env |
| Backend won't start | Run `docker compose down && docker compose up -d` |
| Simulator can't connect to API | Ensure backend is running: `docker compose ps` |
| Admin dashboard won't load | Clear browser cache and retry |
| Messages not appearing in database | Check MongoDB is running: `docker compose logs mongo` |

---

## CI/CD Integration

When integrating with CI/CD:

```bash
# Run simulator test
python tools/simulate_chat.py \
  --api-url http://test-backend:8000 \
  --phone +15551234567 \
  --message "WEG-MACHINE-TEST"

# Check exit code
echo $?  # 0 = success, non-zero = failure
```

---

## Quick Reference

```bash
# Start everything
docker compose up -d

# View status
docker compose ps

# View logs
docker compose logs -f fastapi-app

# Test bot simulator
python tools/simulate_chat.py

# Test real WhatsApp delivery (with credentials)
python test/test_whatsapp_text.py

# Check API health
curl http://localhost:8000/health

# View OpenAPI docs
open http://localhost:8000/docs

# Stop everything
docker compose down
```

---

**Last Updated:** March 27, 2026
