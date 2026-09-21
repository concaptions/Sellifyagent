import asyncio
from datetime import datetime, timedelta, timezone

from claude_agent_sdk import tool

from src.utils.google_auth import get_calendar_service


def _get_calendar_events(days_ahead: int, query: str | None) -> str:
    service = get_calendar_service()
    if not service:
        return "Google Calendar is not connected. The user needs to set up Google OAuth first."

    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=days_ahead)

    try:
        params = {
            "calendarId": "primary",
            "timeMin": now.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 20,
        }
        if query:
            params["q"] = query

        result = service.events().list(**params).execute()
        events = result.get("items", [])

        if not events:
            return f"No events found in the next {days_ahead} days."

        lines = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "(No title)")
            location = event.get("location", "")
            event_id = event.get("id", "")

            line = f"- {summary}: {start} to {end}"
            if location:
                line += f" at {location}"
            line += f" [id: {event_id}]"
            lines.append(line)

        return f"Found {len(events)} event(s):\n" + "\n".join(lines)

    except Exception as e:
        return f"Error fetching calendar events: {e}"


GET_EVENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "days_ahead": {
            "type": "integer",
            "description": "Number of days ahead to fetch events for. Default 7.",
        },
        "query": {
            "type": "string",
            "description": "Optional search query to filter events by summary or description.",
        },
    },
    "required": [],
}


@tool(
    "get_calendar_events",
    "Fetch upcoming Google Calendar events. Returns event summaries, times, and locations.",
    GET_EVENTS_SCHEMA,
)
async def get_calendar_events(args: dict) -> dict:
    days_ahead = args.get("days_ahead") or 7
    query = args.get("query") or None
    result = await asyncio.to_thread(_get_calendar_events, days_ahead, query)
    return {"content": [{"type": "text", "text": result}]}
