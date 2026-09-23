import asyncio

from claude_agent_sdk import tool

from src.utils.google_auth import get_calendar_service, not_connected


def _delete_calendar_event(event_id: str) -> str:
    service = get_calendar_service()
    if not service:
        return not_connected("Google Calendar")

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"Event {event_id} deleted successfully."
    except Exception as e:
        return f"Error deleting event: {e}"


DELETE_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string", "description": "The Google Calendar event ID to delete."},
    },
    "required": ["event_id"],
}


@tool(
    "delete_calendar_event",
    "Delete a Google Calendar event by its ID.",
    DELETE_EVENT_SCHEMA,
)
async def delete_calendar_event(args: dict) -> dict:
    result = await asyncio.to_thread(_delete_calendar_event, args["event_id"])
    return {"content": [{"type": "text", "text": result}]}
