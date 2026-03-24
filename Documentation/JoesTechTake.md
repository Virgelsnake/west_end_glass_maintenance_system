# West End Glass Maintenance System — Technical Overview

**Author:** Joe  
**Date:** March 24, 2026  
**Status:** Planning / Pre-Development

---

## 1. System Overview

The West End Glass Maintenance System is a field-service ticketing platform built around WhatsApp as the primary interface for field technicians. Rather than requiring technicians to learn a new app, they interact with work tickets entirely through WhatsApp — reading task lists, adding notes, attaching photos, and closing tickets — all from their phone.

The system serves two distinct audiences:

| Audience | Interface | Primary Use |
|---|---|---|
| Field Technicians | WhatsApp | Read ticket tasks, add notes/photos, close tickets |
| Administrators | React Web App | Manage tickets, users, machines, and audit logs |

The workflow is built around **NFC tags mounted on machines**. A technician taps the tag with their phone and is immediately connected to the open ticket for that machine via WhatsApp — no app install, no login, no manual lookup.

---

## 2. NFC Tag Specification

Each machine in the field has an NFC tag physically attached to it. The tag encodes a WhatsApp deep link that, when tapped, causes the phone's OS to open WhatsApp with a pre-filled message ready to send.

**Deep link format:**
```
https://wa.me/<BUSINESS_PHONE_NUMBER>?text=<MACHINE_ID>
```

**Example:**
```
https://wa.me/15551234567?text=WEG-MACHINE-0042
```

**Behavior on tap:**
1. Technician's phone detects the NFC tag
2. OS reads the URL and opens WhatsApp (no app required beyond WhatsApp being installed)
3. WhatsApp opens a chat with the West End Glass Business number, pre-filled message containing the machine ID
4. Technician taps **Send** — conversation begins

**Machine ID format:** `WEG-MACHINE-XXXX` — a unique identifier assigned to each piece of equipment. This ID is the bridge between the physical machine and its ticket in the system.

> **Note:** No custom app is required on the technician's device. Standard NFC Deep Link support is built into iOS and Android.

---

## 3. End-User Flow (NFC → WhatsApp → Ticket)

```
[Technician taps NFC tag]
        │
        ▼
[OS opens WhatsApp deep link]
[Pre-filled: Machine ID → West End Glass number]
        │
        ▼
[Technician taps Send]
        │
        ▼
[Meta Cloud API webhook fires → FastAPI backend receives message]
        │
        ├─ Phone number NOT in authorized users list?
        │       └─ Return: "Sorry, this number is not registered. Contact your admin."
        │
        └─ Phone number IS authorized
                │
                ▼
        [Backend looks up open ticket(s) for this Machine ID]
                │
                ├─ No open ticket found?
                │       └─ Return: "No open ticket found for [MACHINE_ID]."
                │
                └─ Ticket(s) found
                        │
                        ▼
                [Claude AI Agent evaluates current unchecked step]
                [Presents step to technician with clear instructions]
                        │
                        ▼
                [Backend sends response back to technician via WhatsApp]
                        │
                        ▼
                [Conversation continues — AI checks off steps one by one]
                        │
                        ▼
                [All steps checked → AI prompts technician to close ticket]
```

### Tapping a New NFC Tag (New Machine)

If a technician taps a **different** NFC tag mid-shift:

```
[Technician taps new NFC tag]
        │
        ▼
[New machine ID sent to backend]
        │
        ├─ Previous ticket still OPEN?
        │       └─ Notify: "You have an open ticket on [PREV_MACHINE_ID].
        │                   Reply 'switch' to move to new machine or 'go back' to continue."
        │
        └─ Previous ticket CLOSED (or none)
                └─ Look up ticket for new machine ID → begin step flow normally
```

### Post-Close: Asking for Next Assignment

After a ticket is closed the technician can ask what to do next:

| User Message | System Response |
|---|---|
| `"What tickets do I have?"` | Lists all open tickets assigned to their phone number (machine ID + summary) |
| `"Where am I going next?"` | Returns the next open ticket in priority/creation order |
| _(taps new NFC tag)_ | Immediately opens that machine's ticket and resumes step flow |

All actions are logged to the audit trail (see Section 3a and Section 8).

---

## 3a. AI Agent Step Execution

### Overview

Each ticket contains an **ordered checklist of steps** defined by an admin when the ticket is created. The backend AI agent works through this checklist step by step, driving the conversation with the technician until every step is checked off. The AI does not advance to the next step until the current step's completion criteria are satisfied.

This is implemented as a **server-side agentic loop**: after every inbound WhatsApp message, the backend evaluates the current step, calls the appropriate agent tool to check it off (or prompt for missing information), then sends the next prompt to the user.

### Ticket Step Schema (MongoDB)

Each step in a ticket is stored as an object in the ticket's `steps` array:

```json
{
  "step_index": 1,
  "label": "Technician arrived on site",
  "completion_type": "confirmation",
  "completed": false,
  "completed_at": null,
  "completed_by": null
}
```

**`completion_type` values:**

| Type | What satisfies this step |
|---|---|
| `confirmation` | Technician sends any affirmative reply or AI infers arrival |
| `note` | Technician sends a text note describing what was done |
| `photo` | Technician sends an image — downloaded, stored, and attached to the ticket |
| `manual` | Admin marks complete from the admin panel |

### Agent Tool Set

The FastAPI backend exposes a set of internal **agent tools** that Claude invokes during the agentic loop. Claude is given the ticket's current step list and selects the appropriate tool based on what the technician sent:

| Tool | Action |
|---|---|
| `check_off_step(ticket_id, step_index)` | Marks a step complete with timestamp and actor |
| `attach_note(ticket_id, step_index, note_text)` | Saves a technician note and checks off the step |
| `attach_photo(ticket_id, step_index, media_id)` | Downloads WhatsApp media, stores file, attaches reference to ticket, checks off step |
| `get_current_step(ticket_id)` | Returns the first incomplete step |
| `all_steps_complete(ticket_id)` | Returns true if all steps are checked off |
| `close_ticket(ticket_id, closed_by)` | Marks ticket closed and writes audit event |
| `list_open_tickets(phone_number)` | Returns all open tickets assigned to this technician |

### Step-by-Step Conversation Flow (Example)

**Ticket for WEG-MACHINE-0042 — steps defined by admin:**
1. Technician arrived on site _(confirmation)_
2. Technician provided written notes on condition _(note)_
3. Technician submitted a photo of the repair area _(photo)_

```
Technician taps NFC → sends "WEG-MACHINE-0042"

AI:   "Hi [Name], you're on ticket #142 for Machine 0042.
       Step 1 of 3: Please confirm you've arrived on site."

Tech: "I'm here"

[Agent calls: check_off_step(ticket_id, step_index=1)]

AI:   "Got it, arrival confirmed. ✓
       Step 2 of 3: Please send notes on the condition of the machine."

Tech: "Left seal shows wear, replaced with new gasket. Applied sealant."

[Agent calls: attach_note(ticket_id, step_index=2, note_text="Left seal shows wear...")]

AI:   "Notes saved. ✓
       Step 3 of 3: Please send a photo of the repair area."

Tech: [sends image]

[Agent calls: attach_photo(ticket_id, step_index=3, media_id="whatsapp_media_xyz")]
[Photo downloaded from Meta Cloud API, stored on server, reference written to ticket]

AI:   "Photo attached. ✓ All steps are complete!
       You're all done with this machine. Reply 'close' to close the ticket,
       or add any final notes before closing."

Tech: "close"

[Agent calls: close_ticket(ticket_id, closed_by="+15559876543")]

AI:   "Ticket #142 closed. Great work!
       Reply 'next' or tap your next machine to continue."
```

### Photo Attachment — How It Works

When a technician sends an image via WhatsApp:

1. Meta Cloud API delivers a webhook containing a `media_id` (not the binary file)
2. FastAPI calls the Meta Cloud API **media download endpoint** using the `media_id` to fetch the actual file
3. The file is saved to **local disk on the on-prem server** under a structured path (e.g. `/data/photos/<ticket_id>/<step_index>_<timestamp>.<ext>`)
4. The local file path is written to the ticket step and to the `audit_logs` collection in MongoDB
5. The step is checked off via the `attach_photo` agent tool
6. The FastAPI backend serves the photo file directly via an authenticated endpoint (e.g. `GET /tickets/{ticket_id}/photos/{filename}`)
7. The admin panel loads photos from the FastAPI backend — no separate file server required

> **Photos are fully attached to the ticket** — not just referenced by a transient WhatsApp `media_id` (which expires). The backend downloads and stores them permanently on local disk at the time of receipt.

### Agentic Loop — Server-Side Logic

```
Inbound WhatsApp message received
        │
        ▼
Validate webhook signature (X-Hub-Signature-256)
        │
        ▼
Authorize phone number against user whitelist
        │
        ▼
Load active ticket + step list + conversation history
        │
        ▼
Pass to Claude with:
  - System prompt (ticket type instructions)
  - Step list (with checked/unchecked state and completion_type per step)
  - Full conversation history
  - Available agent tools
        │
        ▼
Claude decides:
  ├─ Inbound message satisfies current step?
  │       └─ Call appropriate agent tool to check it off, present next step
  │
  ├─ Inbound message is a question?
  │       └─ Answer it, then re-present the current step
  │
  └─ All steps complete?
          └─ Prompt technician to close ticket
        │
        ▼
Send Claude's response back to technician via Meta Cloud API Send API
        │
        ▼
Write all events (step checks, notes, photos, messages) to audit log
```

---

## 4. System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FIELD                                 │
│                                                              │
│   [Machine + NFC Tag]  ──tap──►  [Technician's Phone]        │
│                                         │                    │
│                                   WhatsApp App               │
└─────────────────────────────────────────────────────────────┘
                                          │
                                    (HTTPS / TLS)
                                          │
┌─────────────────────────────────────────────────────────────┐
│                   META CLOUD API                             │
│              (WhatsApp Business Platform)                    │
│                  Webhook → Inbound messages                  │
│                  Send API → Outbound messages                │
└─────────────────────────────────────────────────────────────┘
                                          │
                                    (HTTPS / TLS)
                                          │
┌─────────────────────────────────────────────────────────────┐
│              ON-PREM SERVER                                  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Reverse Proxy (TLS termination — wildcard cert)      │  │
│  │  api.west_end_glass.customertest.digitalbullet.net    │  │
│  │  admin.west_end_glass.customertest.digitalbullet.net  │  │
│  │  No auth at proxy layer — passes through to Docker    │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                              │ HTTP (internal)               │
│          ┌───────────────────┴────────────────┐             │
│          ▼                                    ▼             │
│  ┌───────────────────┐          ┌─────────────────────────┐ │
│  │ Docker: fastapi-  │◄────────►│  Docker: MongoDB         │ │
│  │ app (:8000)       │          │  (internal only, :27017) │ │
│  │                   │          │  - Users                 │ │
│  │ - Webhook handler │          │  - Machines              │ │
│  │ - Auth (internal  │          │  - Tickets               │ │
│  │   auth platform)  │          │  - Messages              │ │
│  │ - Ticket logic    │          │  - Audit Logs            │ │
│  │ - AI orchestration│          └─────────────────────────┘ │
│  └───────────────────┘                                      │
│          │  (HTTPS / API key)                               │
│          ▼                                                   │
│  ┌───────────────────┐                                      │
│  │  Docker: admin-   │                                      │
│  │  frontend (:3000) │                                      │
│  │  React SPA        │                                      │
│  └───────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
                          │
                    (HTTPS / API key)
                          │
              ┌───────────────────────┐
              │   Claude API          │
              │   (Anthropic Cloud)   │
              └───────────────────────┘
```

### Data Flow Summary

1. Technician taps NFC → WhatsApp sends message to Meta Cloud API
2. Meta Cloud API fires webhook to FastAPI backend
3. FastAPI validates webhook signature, identifies sender phone number
4. Backend checks authorization, looks up machine ID and associated ticket
5. Ticket context + conversation history is assembled and sent to Claude API
6. Claude API returns a response; FastAPI sends it via Meta Cloud API Send API back to the user
7. Each message and action is written to MongoDB with full audit logging
8. Admin panel queries FastAPI to display tickets, users, and audit logs in real time

---

## 5. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Backend API** | Python — FastAPI | REST API + WhatsApp webhook handler |
| **Database** | MongoDB | Document model fits ticket/message structure |
| **AI** | Claude API (Anthropic) | Cloud-hosted; no local model inference |
| **Admin Frontend** | React | SPA served by FastAPI or standalone |
| **Messaging** | Meta Cloud API | WhatsApp Business Platform, direct integration |
| **NFC** | Standard NFC deep link | No custom app — uses OS-native NFC + WhatsApp |
| **Deployment** | Self-hosted on-premises — Docker | API and services run in Docker containers on-prem |
| **Reverse Proxy** | On-prem reverse proxy | Terminates TLS; forwards to Docker containers; no auth at proxy layer |
| **TLS Certificates** | Wildcard cert — `*.customertest.digitalbullet.net` | Covers both API and admin subdomains |
| **Authentication** | Internal auth platform | Custom auth — not delegated to proxy or middleware |

### Key Dependencies

- `fastapi` + `uvicorn` — ASGI server and API framework
- `motor` or `pymongo` — async MongoDB driver
- `anthropic` — Claude API Python SDK
- `httpx` — HTTP client for Meta Cloud API calls
- `python-jose` or `passlib` — admin auth / JWT
- `pydantic` — request/response validation

---

## 5a. Deployment & Infrastructure

### URLs

| Service | URL |
|---|---|
| **Backend API** | `https://api.west_end_glass.customertest.digitalbullet.net` |
| **Admin Control Panel** | `https://admin.west_end_glass.customertest.digitalbullet.net` |

### Infrastructure Overview

```
[Internet / Meta Cloud API]
          │
          │ HTTPS (443)
          ▼
[Reverse Proxy — On-Prem]
  - Wildcard TLS cert: *.customertest.digitalbullet.net
  - SNI routing:
      api.west_end_glass.*   → Docker container: FastAPI (port 8000)
      admin.west_end_glass.* → Docker container: React / static (port 3000)
  - No authentication at the proxy layer
  - Auth is enforced inside the application
          │
          │ HTTP (internal network)
          ▼
[Docker Host — On-Prem]
  ┌─────────────────────────────────────┐
  │  Container: fastapi-app             │
  │  Image: west-end-glass/api          │
  │  Port: 8000                         │
  │  Env vars: secrets injected at run  │
  ├─────────────────────────────────────┤
  │  Container: mongo                   │
  │  Port: 27017 (internal only)        │
  ├─────────────────────────────────────┤
  │  Container: admin-frontend (opt.)   │
  │  Port: 3000                         │
  └─────────────────────────────────────┘
```

### TLS / Certificates

- **Wildcard certificate** covers `*.customertest.digitalbullet.net`
- Applies to both `api.west_end_glass.customertest.digitalbullet.net` and `admin.west_end_glass.customertest.digitalbullet.net`
- Certificate is terminated at the **reverse proxy** — Docker containers receive plain HTTP internally
- Certificate renewal is managed at the proxy level; no cert changes required inside Docker

### Reverse Proxy Behavior

- The proxy performs **TLS termination only** — it does not handle authentication, rate limiting, or token validation
- All auth logic lives inside the FastAPI application using the internal authentication platform
- The proxy forwards the client's real IP via `X-Forwarded-For` so the API can log it correctly
- MongoDB port is **not exposed** through the proxy; it is only reachable within the Docker network

### Authentication

- Authentication is handled by **West End Glass's own authentication platform** — not delegated to any middleware, proxy, or third-party identity provider
- The FastAPI application integrates directly with the internal auth platform for all admin panel access
- The reverse proxy passes requests through without any auth headers being added or validated at that layer

---

## 6. Admin Control Panel

The React admin panel is the **source of truth** for all system data. It is used exclusively by West End Glass staff and requires authenticated login.

### Feature Set

#### Ticket Management
- Create new tickets manually, assign to a machine ID
- View all open, in-progress, and closed tickets
- View full ticket details: work items, notes, photos, timestamps
- Edit ticket work items and descriptions
- Manually close or reopen a ticket

#### User Management
- Add technicians to the system by **phone number** (the phone number is the identity and the whitelist entry)
- Set the technician's **preferred language** at account creation — the AI uses this language for all WhatsApp messages to that user
- Remove or deactivate users
- View last activity per user

#### Machine Management
- Register machines with a unique Machine ID
- Associate machines with locations or job sites
- View ticket history per machine

#### Conversation & Message View
- View the full WhatsApp conversation thread for any ticket
- See messages sent by the technician and responses sent by the AI
- Manually send a message into a conversation if needed

#### AI Configuration
- Manage Claude system prompt templates
- Configure per-machine or per-ticket-type prompt overrides
- View AI response logs

#### Audit Log
- Searchable, filterable log of every action in the system (see Section 8)

---

## 7. Security & Access Control

### WhatsApp / Technician Side

- **Phone number whitelist:** Only phone numbers registered by an admin can interact with the system. Any unrecognized number receives a polite rejection message.
- **Ticket scoping:** When a ticket is looked up by machine ID, it is only returned if the requesting phone number is authorized. A technician cannot access another user's tickets.
- **Webhook signature validation:** Every inbound webhook from Meta Cloud API is verified using the `X-Hub-Signature-256` header before any processing occurs. Requests with invalid signatures are rejected with `403 Forbidden`.
- **Webhook rate limiting:** Basic rate limiting is applied to the webhook endpoint to prevent abuse. Excessive requests from a single phone number or IP are rejected with `429 Too Many Requests`. This is sufficient for the POC stage.
- **No sensitive data in WhatsApp messages:** Ticket IDs, internal references, and PII are not exposed in WhatsApp responses beyond what is operationally necessary.

### Admin Panel Side

- **Authentication required:** All admin routes are protected by the internal authentication platform. Unauthenticated requests are rejected at the application layer — not at the proxy.
- **No proxy-layer auth:** The reverse proxy does not enforce authentication. Auth is the sole responsibility of the FastAPI application and internal auth platform.
- **Role-based access (future consideration):** Currently a single admin role; structure should allow for role expansion.
- **HTTPS only:** TLS is terminated at the reverse proxy using the wildcard cert for `*.customertest.digitalbullet.net`. Internal Docker-to-proxy traffic is over HTTP on the private network.
- **Environment secrets:** API keys (Claude, Meta Cloud API, MongoDB credentials) are injected as Docker environment variables at container runtime — never hardcoded in source code or committed to version control.
- **MongoDB not externally exposed:** The MongoDB container port is bound to the internal Docker network only and is not reachable via the reverse proxy or the internet.

---

## 8. Audit Trail

Every action that occurs in the system is logged to a dedicated `audit_logs` collection in MongoDB. Audit records are **append-only** and are never modified or deleted.

### Logged Events

| Event | Logged Fields |
|---|---|
| `ticket_created` | ticket_id, machine_id, created_by (admin), timestamp |
| `ticket_updated` | ticket_id, field changed, old value, new value, actor, timestamp |
| `message_received` | ticket_id, phone_number, message content, timestamp |
| `message_sent` | ticket_id, message content, ai_generated (bool), timestamp |
| `note_added` | ticket_id, phone_number, note text, timestamp |
| `photo_attached` | ticket_id, phone_number, file reference, timestamp |
| `ticket_closed` | ticket_id, closed_by (phone or admin), timestamp |
| `ticket_reopened` | ticket_id, reopened_by, timestamp |
| `user_added` | phone_number, added_by (admin), timestamp |
| `user_deactivated` | phone_number, deactivated_by, timestamp |
| `auth_failure` | phone_number, reason, timestamp |

### Audit Log Schema (MongoDB)

```json
{
  "_id": "ObjectId",
  "event": "note_added",
  "ticket_id": "ObjectId",
  "machine_id": "WEG-MACHINE-0042",
  "actor": "+15559876543",
  "actor_type": "technician",
  "payload": {
    "note": "Replaced left seal, sealant applied."
  },
  "timestamp": "2026-03-24T14:32:11Z"
}
```

Audit logs are accessible in the admin panel with full search and filter capabilities (by ticket, machine, user, event type, and date range).

---

## 9. Resolved Design Decisions

| Decision | Resolution |
|---|---|
| **Max concurrent tickets per machine** | No maximum. Multiple tickets can exist per machine and are worked in order. Priority can be changed from the admin control panel — the AI will present the highest-priority open ticket when a technician scans a machine. |
| **Photo storage** | Local disk on the on-prem server. The file path is stored in MongoDB. Photos are served directly by the FastAPI backend API (not a separate file server). |
| **Rate limiting** | Basic rate limiting on the webhook endpoint is sufficient for the POC. No advanced DDoS protection required at this stage. |
| **Admin alert on ticket close** | No outbound notification. Closing a ticket marks it complete in MongoDB — admins see the updated status when they view the admin panel. |
| **Multi-language support** | Language is set on the user's profile in the admin control panel at the time the account is created. The AI uses the user's configured language for all WhatsApp responses. All phone numbers registered in the user profile are whitelisted for system access. |
| **Role-based access** | Full admin only. No read-only role for the control panel at this time. |
| **NFC tag provisioning** | Out of scope. A separate team uses separate software to write and print NFC tags ahead of deployment. Tags arrive pre-configured with the correct machine ID deep link. |
