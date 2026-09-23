import asyncio
import uuid

from claude_agent_sdk import tool

from src.utils.google_auth import get_calendar_service, not_connected


def describe_event(event: dict, prefix: str = "Event created") -> str:
    start = event["start"].get("dateTime", event["start"].get("date"))
    end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date"))
    when = f"{start} to {end}" if end else start
    parts = [f"{prefix}: {event.get('summary')} on {when} [id: {event.get('id')}]"]
    attendees = [a.get("email") for a in event.get("attendees", []) if a.get("email")]
    if attendees:
        parts.append("Invitations sent to: " + ", ".join(attendees))
    meet = event.get("hangoutLink")
    if meet:
        parts.append(f"Google Meet link: {meet}")
    return "\n".join(parts)


def _create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    location: str | None,
    description: str | None,
    attendees: list[str] | None,
    add_meet_link: bool,
) -> str:
    service = get_calendar_service()
    if not service:
        return not_connected("Google Calendar")

    event_body: dict = {
        "summary": summary,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if location:
        event_body["location"] = location
    if description:
        event_body["description"] = description
    attendees = [a.strip() for a in (attendees or []) if a and "@" in a]
    if attendees:
        event_body["attendees"] = [{"email": a} for a in attendees]
    if add_meet_link:
        event_body["conferenceData"] = {
            "createRequest": {"requestId": uuid.uuid4().hex, "conferenceSolutionKey": {"type": "hangoutsMeet"}}
        }

    try:
        event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event_body,
                # Google emails the invitation itself when sendUpdates is set;
                # without it, attendees are on the event but never hear about it.
                sendUpdates="all" if attendees else "none",
                conferenceDataVersion=1 if add_meet_link else 0,
            )
            .execute()
        )
        return describe_event(event)
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
        "attendees": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Email addresses of people to invite. Each receives a Google Calendar invitation.",
        },
        "add_meet_link": {
            "type": "boolean",
            "description": "Attach a Google Meet video link. Default true when there are attendees and no physical location.",
        },
    },
    "required": ["summary", "start_time", "end_time"],
}


@tool(
    "create_calendar_event",
    "Create a Google Calendar event, optionally inviting people by email (they get the invitation) and with a Google Meet link. Call this the moment you have all required fields.",
    CREATE_EVENT_SCHEMA,
)
async def create_calendar_event(args: dict) -> dict:
    attendees = args.get("attendees") or []
    add_meet = args.get("add_meet_link")
    if add_meet is None:
        add_meet = bool(attendees) and not args.get("location")
    result = await asyncio.to_thread(
        _create_calendar_event,
        args["summary"],
        args["start_time"],
        args["end_time"],
        args.get("location"),
        args.get("description"),
        attendees,
        bool(add_meet),
    )
    return {"content": [{"type": "text", "text": result}]}
