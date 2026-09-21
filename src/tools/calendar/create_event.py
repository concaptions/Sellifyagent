import asyncio

from claude_agent_sdk import tool

from src.utils.google_auth import get_calendar_service


def _create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    location: str | None,
    description: str | None,
) -> str:
    service = get_calendar_service()
    if not service:
        return "Google Calendar is not connected. The user needs to set up Google OAuth first."

    event_body = {
        "summary": summary,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if location:
        event_body["location"] = location
    if description:
        event_body["description"] = description

    try:
        event = service.events().insert(calendarId="primary", body=event_body).execute()
        return (
            f"Event created: {event.get('summary')} on {event['start'].get('dateTime')} "
            f"[id: {event.get('id')}]"
        )
    except Exception as e:
        return f"Error creating calendar event: {e}"


CREATE_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "Event title."},
        "start_time": {
            "type": "string",
            "description": "Start time in ISO 8601 format, e.g. '2026-09-20T14:00:00+08:00'.",
        },
        "end_time": {
            "type": "string",
            "description": "End time in ISO 8601 format, e.g. '2026-09-20T15:00:00+08:00'.",
        },
        "location": {"type": "string", "description": "Event location."},
        "description": {"type": "string", "description": "Event description."},
    },
    "required": ["summary", "start_time", "end_time"],
}


@tool(
    "create_calendar_event",
    "Create a new Google Calendar event. Call this the moment you have all required fields.",
    CREATE_EVENT_SCHEMA,
)
async def create_calendar_event(args: dict) -> dict:
    result = await asyncio.to_thread(
        _create_calendar_event,
        args["summary"],
        args["start_time"],
        args["end_time"],
        args.get("location"),
        args.get("description"),
    )
    return {"content": [{"type": "text", "text": result}]}
