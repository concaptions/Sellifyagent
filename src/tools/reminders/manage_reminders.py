"""Reminders and proactive follow-ups, stored per user in sellify_reminders
and delivered by the scheduler loop in app.py."""
import asyncio
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from claude_agent_sdk import tool, SdkMcpTool

from src import database as db

USER_TZ = ZoneInfo("Asia/Singapore")
RECURRENCES = ("none", "daily", "weekly", "monthly")
KINDS = ("reminder", "followup")

CREATE_REMINDER_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": (
                "For kind 'reminder': what to remind the user about, in their words. "
                "For kind 'followup': the instruction to carry out at that time, e.g. "
                "'Check Gmail for a reply from Sarah about the contract; if none, tell the user and offer to send a nudge.'"
            ),
        },
        "due_at": {
            "type": "string",
            "description": "When to fire, ISO 8601 with a UTC offset, e.g. 2026-09-24T09:00:00+08:00.",
        },
        "kind": {
            "type": "string",
            "enum": list(KINDS),
            "description": "'reminder' just nudges the user. 'followup' first does the work in text (checks email, calendar, the web), then messages the user with the outcome. Default 'reminder'.",
        },
        "recurrence": {
            "type": "string",
            "enum": list(RECURRENCES),
            "description": "Repeat schedule. Default 'none'.",
        },
    },
    "required": ["text", "due_at"],
}

LIST_REMINDERS_SCHEMA = {"type": "object", "properties": {}, "required": []}

CANCEL_REMINDER_SCHEMA = {
    "type": "object",
    "properties": {"reminder_id": {"type": "integer", "description": "The reminder's id from list_reminders."}},
    "required": ["reminder_id"],
}


def _parse_due(value: str) -> datetime:
    due = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if due.tzinfo is None:
        # The model was told to include an offset; if it didn't, the user's
        # local time is the only sensible reading.
        due = due.replace(tzinfo=USER_TZ)
    return due


def next_due(due: datetime, recurrence: str) -> datetime | None:
    """Next occurrence after `due`, stepping in the user's timezone so a
    9:00 reminder stays at 9:00 local. Returns None for one-off reminders."""
    if recurrence == "none":
        return None
    local = due.astimezone(USER_TZ)
    if recurrence == "daily":
        nxt = local + timedelta(days=1)
    elif recurrence == "weekly":
        nxt = local + timedelta(weeks=1)
    elif recurrence == "monthly":
        year, month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
        day = min(local.day, calendar.monthrange(year, month)[1])
        nxt = local.replace(year=year, month=month, day=day)
    else:
        return None
    # A reminder that fires late (app was down) must not replay every missed slot.
    now = datetime.now(USER_TZ)
    while nxt <= now:
        nxt = next_due(nxt, recurrence)
    return nxt


def _fmt(due: datetime) -> str:
    return due.astimezone(USER_TZ).strftime("%a %d %b %Y, %H:%M")


def _create(user_id: str, text: str, due_at: str, kind: str, recurrence: str) -> str:
    if kind not in KINDS or recurrence not in RECURRENCES:
        return f"Invalid kind or recurrence. kind: {KINDS}, recurrence: {RECURRENCES}."
    try:
        due = _parse_due(due_at)
    except ValueError:
        return f"Could not parse due_at '{due_at}'. Use ISO 8601 with an offset, e.g. 2026-09-24T09:00:00+08:00."
    if due <= datetime.now(USER_TZ):
        return f"That time ({_fmt(due)}) is in the past. Ask the user for a future time."
    try:
        reminder_id = db.create_reminder(user_id, kind, text.strip(), due, recurrence)
    except Exception as e:
        return f"Error saving reminder: {e}"
    repeat = "" if recurrence == "none" else f", repeats {recurrence}"
    return f"Scheduled {kind} [id: {reminder_id}] for {_fmt(due)}{repeat}: {text.strip()}"


def _list(user_id: str) -> str:
    try:
        rows = db.list_reminders(user_id)
    except Exception as e:
        return f"Error listing reminders: {e}"
    if not rows:
        return "No upcoming reminders."
    lines = []
    for r in rows:
        repeat = "" if r["recurrence"] == "none" else f" (repeats {r['recurrence']})"
        lines.append(f"- [id: {r['id']}] {_fmt(r['due_at'])}{repeat} — {r['kind']}: {r['text']}")
    return f"{len(rows)} upcoming:\n" + "\n".join(lines)


def _cancel(user_id: str, reminder_id: int) -> str:
    try:
        row = db.cancel_reminder(user_id, reminder_id)
    except Exception as e:
        return f"Error cancelling reminder: {e}"
    if not row:
        return f"No pending reminder with id {reminder_id}."
    return f"Cancelled reminder {row['id']} ({_fmt(row['due_at'])}): {row['text']}"


def build_reminder_tools(user_id: str) -> list[SdkMcpTool]:
    """Per-user tools via closure, same reason as build_notes_tools."""

    @tool(
        "create_reminder",
        "Schedule a reminder or a proactive follow-up for the user at a future time. Call it as soon as you know what and when.",
        CREATE_REMINDER_SCHEMA,
    )
    async def create_reminder(args: dict) -> dict:
        result = await asyncio.to_thread(
            _create, user_id, args["text"], args["due_at"], args.get("kind") or "reminder", args.get("recurrence") or "none"
        )
        return {"content": [{"type": "text", "text": result}]}

    @tool("list_reminders", "List the user's upcoming reminders and follow-ups.", LIST_REMINDERS_SCHEMA)
    async def list_reminders(args: dict) -> dict:
        result = await asyncio.to_thread(_list, user_id)
        return {"content": [{"type": "text", "text": result}]}

    @tool("cancel_reminder", "Cancel an upcoming reminder by id.", CANCEL_REMINDER_SCHEMA)
    async def cancel_reminder(args: dict) -> dict:
        result = await asyncio.to_thread(_cancel, user_id, int(args["reminder_id"]))
        return {"content": [{"type": "text", "text": result}]}

    return [create_reminder, list_reminders, cancel_reminder]


REMINDER_TOOL_NAMES = [
    "mcp__reminders__create_reminder",
    "mcp__reminders__list_reminders",
    "mcp__reminders__cancel_reminder",
]
