from src.tools.calendar.get_events import get_calendar_events
from src.tools.calendar.create_event import create_calendar_event
from src.tools.calendar.update_event import update_calendar_event
from src.tools.calendar.delete_event import delete_calendar_event

calendar_tools = [get_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event]
CALENDAR_TOOL_NAMES = [f"mcp__calendar__{t.name}" for t in calendar_tools]
