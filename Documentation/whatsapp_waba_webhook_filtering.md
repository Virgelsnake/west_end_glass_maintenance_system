# WhatsApp WABA Webhook Broadcasting & Phone Number Filtering

## The Problem

When you register a webhook URL with Meta's WhatsApp Cloud API, **Meta sends every event for every phone number in your WhatsApp Business Account (WABA) to that single URL**.

This means if your WABA contains 3 phone numbers — each belonging to a different application or team — all 3 numbers' events arrive at the same endpoint in one continuous stream:

- Inbound messages from users
- Delivery receipts (sent, delivered, read)
- Failed message notifications
- Status updates

Meta makes **no distinction** between which application owns which number. It is a flat broadcast to the registered webhook URL.

---

## What This Looks Like in Practice

A real example from our logs — three separate payloads arriving within seconds of each other, all at the same URL:

```
phone_number_id: 854471221084849  → our app (447345298985)
phone_number_id: 927521773767522  → someone else's app (447345298978)
phone_number_id: 831228796741822  → someone else's app (447769386204)
```

If your application does not filter, it will attempt to process messages intended for a completely different system — including replying to users who have nothing to do with your application.

---

## The Fix: Filter by `phone_number_id`

Every webhook payload from Meta contains a `metadata` block identifying which phone number the event is for:

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "metadata": {
          "display_phone_number": "447345298985",
          "phone_number_id": "854471221084849"
        },
        "messages": [...]
      }
    }]
  }]
}
```

Your application **must** check `phone_number_id` against your own configured number before doing anything with the payload.

### How we implement it (FastAPI / Python)

```python
incoming_phone_id = value.get("metadata", {}).get("phone_number_id")
if incoming_phone_id != settings.meta_phone_number_id:
    # Not for us — discard silently and return 200 to Meta
    return {"status": "ok"}
```

Your `META_PHONE_NUMBER_ID` environment variable holds your number's ID (e.g. `854471221084849`). Anything that doesn't match is dropped immediately.

---

## Why You Must Always Return 200

Regardless of whether you process the event or discard it, you **must always return HTTP 200** to Meta. If Meta receives a non-200 response it will retry the same webhook payload repeatedly, flooding your endpoint.

---

## The `+` Prefix Issue

Meta sends phone numbers in webhook payloads **without the leading `+`** (e.g. `447717207677`), but E.164 format requires the `+` (e.g. `+447717207677`). If your database stores numbers with a `+`, your lookup will silently fail every time.

Always normalise the incoming number before any database lookup:

```python
raw_number = message["from"]  # "447717207677"
phone_number = raw_number if raw_number.startswith("+") else "+" + raw_number
```

---

## Summary

| Rule | Why |
|---|---|
| Filter every payload by `phone_number_id` | Your WABA may have multiple numbers; Meta sends all events to one URL |
| Always return HTTP 200 to Meta | Non-200 causes endless retries |
| Normalise incoming numbers to E.164 (`+` prefix) | Meta omits the `+`; your DB likely stores it |
| Store your `META_PHONE_NUMBER_ID` in config | Used for both sending messages and filtering inbound events |
