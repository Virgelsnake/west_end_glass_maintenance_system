"""
Claude agentic loop for West End Glass.

Each inbound WhatsApp message triggers this loop. Claude is given:
  - The ticket's current step list
  - The conversation history
  - A set of agent tools to check off steps

The loop runs until Claude sends a final text response to the technician.
"""

import json
from typing import Optional
import anthropic

from ..config import settings
from ..services import ticket_service, whatsapp as wa_service
from ..services.audit_service import log_event

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT_TEMPLATE = """You are a helpful field service assistant for West End Glass.
You are guiding a field technician through a maintenance ticket via WhatsApp.

Current ticket information:
- Ticket ID: {ticket_id}
- Machine ID: {machine_id}
- Ticket title: {title}
- Technician name: {technician_name}
- Technician phone: {technician_phone}

Steps to complete:
{steps_summary}

Instructions:
- Respond ONLY in {language}.
- Be brief, clear, and friendly. This is a WhatsApp conversation.
- Work through the steps ONE AT A TIME in order.
- Do NOT skip steps or advance until the current step is satisfied.
- When you check off a step, immediately tell the technician what they've completed and what comes next.
- If the technician sends something unexpected, acknowledge it and re-present the current step.
- When all steps are complete, prompt the technician to close the ticket by replying 'close'.
- If the technician asks what tickets they have, call list_open_tickets.
"""

AGENT_TOOLS = [
    {
        "name": "check_off_step",
        "description": "Mark the current step as complete when the technician has confirmed it (e.g. arrived on site, done a task).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "step_index": {"type": "integer"},
            },
            "required": ["ticket_id", "step_index"],
        },
    },
    {
        "name": "attach_note",
        "description": "Save a text note from the technician and mark the note step as complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "step_index": {"type": "integer"},
                "note_text": {"type": "string"},
            },
            "required": ["ticket_id", "step_index", "note_text"],
        },
    },
    {
        "name": "attach_photo",
        "description": "Download the technician's photo and attach it to this step, marking it complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "step_index": {"type": "integer"},
                "media_id": {"type": "string"},
            },
            "required": ["ticket_id", "step_index", "media_id"],
        },
    },
    {
        "name": "close_ticket",
        "description": "Close the ticket when all steps are complete and technician confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
            },
            "required": ["ticket_id"],
        },
    },
    {
        "name": "list_open_tickets",
        "description": "List all open tickets assigned to the technician's phone number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string"},
            },
            "required": ["phone_number"],
        },
    },
]


def _build_steps_summary(steps: list) -> str:
    lines = []
    for step in steps:
        status = "✓" if step.get("completed") else "○"
        lines.append(f"  {status} Step {step['step_index']}: {step['label']} [{step['completion_type']}]")
    return "\n".join(lines)


def _build_conversation_messages(history: list, new_message: str, media_id: Optional[str] = None) -> list:
    """Convert stored message history to Claude messages format."""
    messages = []
    for msg in history:
        role = "user" if msg["direction"] == "inbound" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    # Add the new inbound message
    if media_id:
        messages.append({"role": "user", "content": f"[Photo sent — media_id: {media_id}]"})
    else:
        messages.append({"role": "user", "content": new_message})

    return messages


async def _execute_tool(
    db,
    tool_name: str,
    tool_input: dict,
    phone_number: str,
) -> str:
    """Execute an agent tool call and return a result string."""
    if tool_name == "check_off_step":
        ticket = await ticket_service.check_off_step(
            db, tool_input["ticket_id"], tool_input["step_index"], phone_number
        )
        return f"Step {tool_input['step_index']} checked off."

    elif tool_name == "attach_note":
        ticket = await ticket_service.attach_note_to_step(
            db,
            tool_input["ticket_id"],
            tool_input["step_index"],
            tool_input["note_text"],
            phone_number,
        )
        return f"Note saved and step {tool_input['step_index']} checked off."

    elif tool_name == "attach_photo":
        try:
            photo_path = await wa_service.download_media(
                tool_input["media_id"],
                tool_input["ticket_id"],
                tool_input["step_index"],
            )
            ticket = await ticket_service.attach_photo_to_step(
                db,
                tool_input["ticket_id"],
                tool_input["step_index"],
                photo_path,
                phone_number,
            )
            return f"Photo downloaded and attached to step {tool_input['step_index']}."
        except Exception as e:
            # In simulator/test mode or if download fails, return error message
            return f"Could not download photo (media_id: {tool_input['media_id']}). This may happen in test mode. Please try resending the photo or continue with the next step."

    elif tool_name == "close_ticket":
        ticket = await ticket_service.close_ticket(db, tool_input["ticket_id"], phone_number)
        return f"Ticket {tool_input['ticket_id']} closed successfully."

    elif tool_name == "list_open_tickets":
        tickets = await ticket_service.get_open_tickets_for_phone(db, tool_input["phone_number"])
        if not tickets:
            return "No open tickets found for this technician."
        lines = [f"- {t['machine_id']}: {t['title']}" for t in tickets]
        return "Open tickets:\n" + "\n".join(lines)

    return "Unknown tool."


async def run_agent_loop(
    db,
    ticket: dict,
    user: dict,
    message_text: str,
    media_id: Optional[str],
    conversation_history: list,
) -> str:
    """
    Run the Claude agentic loop for one inbound message.
    Returns the final text response to send to the technician.
    """
    ticket_id = str(ticket["_id"])
    language = user.get("language", "en")
    technician_name = user.get("name", "Technician")

    # ── Special handling for test commands (testing only) ───────────────
    if message_text.startswith("[TEST_PHOTO]"):
        # Extract step number from /test-photo [step #]
        parts = message_text.split()
        if len(parts) >= 3 and parts[1] == "/test-photo":
            try:
                step_index = int(parts[2])
                # Mark this step as complete
                await ticket_service.attach_photo_to_step(
                    db,
                    ticket_id,
                    step_index,
                    "[TEST_PHOTO_SIMULATED]",
                    user["phone_number"],
                )
                return f"✅ **Test Mode**: Simulated photo upload for step {step_index}. This is testing only and won't be saved in production."
            except (ValueError, IndexError):
                return "❌ Invalid /test-photo command. Usage: /test-photo [step_number]"

    elif message_text.startswith("[TEST_NOTE]"):
        # Extract step number and note text from /test-note [step #] [text]
        parts = message_text.split(maxsplit=3)
        if len(parts) >= 4 and parts[1] == "/test-note":
            try:
                step_index = int(parts[2])
                note_text = " ".join(parts[3:])
                # Attach note to step
                await ticket_service.attach_note_to_step(
                    db,
                    ticket_id,
                    step_index,
                    note_text,
                    user["phone_number"],
                )
                return f"✅ **Test Mode**: Saved note for step {step_index}: \"{note_text}\""
            except (ValueError, IndexError):
                return "❌ Invalid /test-note command. Usage: /test-note [step_number] [note text]"

    # ── Normal message processing ─────────────────────────────────────
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        ticket_id=ticket_id,
        machine_id=ticket["machine_id"],
        title=ticket["title"],
        technician_name=technician_name,
        technician_phone=user["phone_number"],
        steps_summary=_build_steps_summary(ticket.get("steps", [])),
        language=language,
    )

    messages = _build_conversation_messages(conversation_history, message_text, media_id)

    # Agentic loop — continue until Claude returns a text response (no tool calls)
    while True:
        response = await client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system_prompt,
            tools=AGENT_TOOLS,
            messages=messages,
        )

        # Collect all tool calls from this response
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        text_blocks = [block for block in response.content if block.type == "text"]

        if not tool_calls:
            # Claude is done — return the final text
            return text_blocks[0].text if text_blocks else "Done."

        # Execute each tool call and build tool results
        tool_results = []
        for tool_call in tool_calls:
            result_text = await _execute_tool(db, tool_call.name, tool_call.input, user["phone_number"])
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result_text,
            })

        # Reload the ticket so Claude has fresh step state
        ticket = await db.tickets.find_one({"_id": ticket["_id"]})
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            ticket_id=ticket_id,
            machine_id=ticket["machine_id"],
            title=ticket["title"],
            technician_name=technician_name,
            technician_phone=user["phone_number"],
            steps_summary=_build_steps_summary(ticket.get("steps", [])),
            language=language,
        )

        # Append assistant response and tool results to messages and loop
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
