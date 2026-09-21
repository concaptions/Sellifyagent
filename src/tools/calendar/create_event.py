from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils.google_auth import get_calendar_service


class CreateEventInput(BaseModel):
    summary: str = Field(description="Event title. String.")
    start_time: str = Field(
        description="Start time in ISO 8601 format, e.g. '2026-09-20T14:00:00+08:00'. String."
    )
    end_time: str = Field(
        description="End time in ISO 8601 format, e.g. '2026-09-20T15:00:00+08:00'. String."
    )
    location: Optional[str] = Field(default=None, description="Event location. String.")
    description: Optional[str] = Field(default=None, description="Event description. String.")


@tool(args_schema=CreateEventInput)
def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    description: str | None = None,
) -> str:
    """Create a new Google Calendar event. Call this the moment you have all required fields."""
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
