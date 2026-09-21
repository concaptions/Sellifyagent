from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils.google_auth import get_calendar_service


class DeleteEventInput(BaseModel):
    event_id: str = Field(description="The Google Calendar event ID to delete. String.")


@tool(args_schema=DeleteEventInput)
def delete_calendar_event(event_id: str) -> str:
    """Delete a Google Calendar event by its ID."""
    service = get_calendar_service()
    if not service:
        return "Google Calendar is not connected."

    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"Event {event_id} deleted successfully."
    except Exception as e:
        return f"Error deleting event: {e}"
