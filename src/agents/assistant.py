import asyncio
import logging
import uuid
from datetime import datetime, timezone

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
)

from src.prompts.manager import MANAGER_PROMPT
from src.prompts.email_agent import EMAIL_AGENT_PROMPT
from src.prompts.calendar_agent import CALENDAR_AGENT_PROMPT
from src.prompts.notes_agent import NOTES_AGENT_PROMPT
from src.prompts.research_agent import RESEARCH_AGENT_PROMPT
from src.prompts.documents_agent import DOCUMENTS_AGENT_PROMPT
from src.prompts.reminders_agent import REMINDERS_AGENT_PROMPT
from src.prompts.browser_agent import BROWSER_AGENT_PROMPT
from src.prompts.memory_agent import MEMORY_AGENT_PROMPT
from src.prompts.data_agent import DATA_AGENT_PROMPT
from src.config import BUSINESS_DATA_PHONES
from src.tools.calendar import calendar_tools, CALENDAR_TOOL_NAMES
from src.tools.email import email_tools, EMAIL_TOOL_NAMES
from src.tools.notes import build_notes_tools, NOTES_TOOL_NAMES
from src.tools.documents import build_document_tools, DOCUMENT_TOOL_NAMES
from src.tools.reminders import build_reminder_tools, REMINDER_TOOL_NAMES
from src.tools.browser import build_browser_tools, BROWSER_TOOL_NAMES
from src.tools.memory import build_memory_tools, MEMORY_TOOL_NAMES
from src.tools.data import build_data_tools, DATA_TOOL_NAMES, BUSINESS_TOOL_NAMES
from src.tools.memory.profile import format_profile
from src import database as db

logger = logging.getLogger(__name__)

USER_TIMEZONE = "Asia/Singapore"

# Returned instead of raising so a WhatsApp turn always gets a reply; the
# scheduler compares against it to tell a failed turn from a real answer.
AGENT_ERROR_REPLY = "Something went wrong processing your message. Please try again."

# Web research uses Claude Code's built-in tools (Anthropic's server-side web
# search, billed on the same API key) instead of a third-party search API.
RESEARCH_TOOL_NAMES = ["WebSearch", "WebFetch"]

ALL_TOOL_NAMES = (
    CALENDAR_TOOL_NAMES + EMAIL_TOOL_NAMES + NOTES_TOOL_NAMES + RESEARCH_TOOL_NAMES + DOCUMENT_TOOL_NAMES
    + REMINDER_TOOL_NAMES + BROWSER_TOOL_NAMES + MEMORY_TOOL_NAMES + DATA_TOOL_NAMES + BUSINESS_TOOL_NAMES
)


class PersonalAssistant:
    """Wires a Claude Agent SDK manager agent with nine specialist subagents.

    Authenticates with the ANTHROPIC_API_KEY in the environment (metered API
    usage); a deployed product may not run on a claude.ai subscription login.
    """

    def __init__(self):
        # Per-user session continuity: phone -> Claude Agent SDK session_id.
        # In-memory only; lost on restart. Fine for an MVP, but a production
        # deployment should persist this map (e.g. in pa_users.profile).
        self._sessions: dict[str, str] = {}
        # One turn at a time per user: the reminder scheduler can start a turn
        # while the user is mid-conversation, and two resumes of one session at
        # once corrupt its history.
        self._locks: dict[str, asyncio.Lock] = {}

    def _build_options(self, user_phone: str, profile: dict) -> ClaudeAgentOptions:
        current_time = datetime.now(timezone.utc).isoformat()
        user_timezone = profile.get("timezone") or USER_TIMEZONE
        format_kwargs = {
            "current_time": current_time,
            "user_timezone": user_timezone,
            "user_profile": format_profile(profile) or "(nothing yet — learn as you go)",
        }

        # Never rely on ambient session state (e.g. a CLAUDE_CODE_SESSION_ID
        # left in the process environment) to decide which conversation a
        # message belongs to — that risks one user's turn landing in another
        # user's session. Always assign and pin an explicit per-phone
        # session id instead: a fresh one on first contact, resumed after.
        existing_session_id = self._sessions.get(user_phone)
        if existing_session_id:
            resume_id = existing_session_id
            new_session_id = None
        else:
            resume_id = None
            new_session_id = str(uuid.uuid4())
            self._sessions[user_phone] = new_session_id

        notes_tools = build_notes_tools(user_phone)
        document_tools = build_document_tools(user_phone, profile.get("cue_user_id"))
        reminder_tools = build_reminder_tools(user_phone, user_timezone)
        browser_tools = build_browser_tools(user_phone)
        memory_tools = build_memory_tools(user_phone)
        owner = user_phone in BUSINESS_DATA_PHONES
        data_tools = build_data_tools(user_phone, profile.get("cue_user_id"), owner)

        mcp_servers = {
            "calendar": create_sdk_mcp_server("calendar", tools=calendar_tools),
            "email": create_sdk_mcp_server("email", tools=email_tools),
            "notes": create_sdk_mcp_server("notes", tools=notes_tools),
            "documents": create_sdk_mcp_server("documents", tools=document_tools),
            "reminders": create_sdk_mcp_server("reminders", tools=reminder_tools),
            "browser": create_sdk_mcp_server("browser", tools=browser_tools),
            "memory": create_sdk_mcp_server("memory", tools=memory_tools),
            "data": create_sdk_mcp_server("data", tools=data_tools),
        }

        agents = {
            "calendar_agent": AgentDefinition(
                description="Handles Google Calendar: viewing, creating, and deleting events.",
                prompt=CALENDAR_AGENT_PROMPT.format(**format_kwargs),
                tools=CALENDAR_TOOL_NAMES,
            ),
            "email_agent": AgentDefinition(
                description="Handles Gmail: reading and sending emails.",
                prompt=EMAIL_AGENT_PROMPT.format(current_time=current_time),
                tools=EMAIL_TOOL_NAMES,
            ),
            "notes_agent": AgentDefinition(
                description="Saves, lists, and searches the user's personal notes.",
                prompt=NOTES_AGENT_PROMPT.format(current_time=current_time),
                tools=NOTES_TOOL_NAMES,
            ),
            "research_agent": AgentDefinition(
                description="Searches the web for current information and facts.",
                prompt=RESEARCH_AGENT_PROMPT.format(current_time=current_time),
                tools=RESEARCH_TOOL_NAMES,
            ),
            "documents_agent": AgentDefinition(
                description="Finds answers in, lists, and deletes the documents (PDF/Word/text) the user has sent.",
                prompt=DOCUMENTS_AGENT_PROMPT.format(current_time=current_time),
                tools=DOCUMENT_TOOL_NAMES,
            ),
            "reminders_agent": AgentDefinition(
                description="Schedules, lists and cancels reminders and timed follow-ups for the user.",
                prompt=REMINDERS_AGENT_PROMPT.format(**format_kwargs),
                tools=REMINDER_TOOL_NAMES,
            ),
            "data_agent": AgentDefinition(
                description="Answers from the database: the user's earlier records (health log, personas, past reminders, past chats) and, for owners, the business tables (leads, products, knowledge base).",
                prompt=DATA_AGENT_PROMPT.format(**format_kwargs),
                tools=DATA_TOOL_NAMES + (BUSINESS_TOOL_NAMES if owner else []),
            ),
            "memory_agent": AgentDefinition(
                description="Saves, updates and recalls what is known about the user: name, age, weight, family, preferences, timezone.",
                prompt=MEMORY_AGENT_PROMPT.format(current_time=current_time),
                tools=MEMORY_TOOL_NAMES,
            ),
            "browser_agent": AgentDefinition(
                description="Makes guest bookings on public websites with a headless browser: restaurants, appointments, slots. No logins or payments.",
                prompt=BROWSER_AGENT_PROMPT.format(**format_kwargs),
                tools=BROWSER_TOOL_NAMES,
            ),
        }

        return ClaudeAgentOptions(
            system_prompt=MANAGER_PROMPT.format(**format_kwargs),
            mcp_servers=mcp_servers,
            allowed_tools=ALL_TOOL_NAMES,
            agents=agents,
            permission_mode="dontAsk",
            resume=resume_id,
            session_id=new_session_id,
            # Defense in depth: strip any ambient session id from this
            # process's own environment so it can never override the
            # explicit resume/session_id above.
            env={"CLAUDE_CODE_SESSION_ID": ""},
        )

    async def ainvoke(self, message: str, user_phone: str) -> str:
        lock = self._locks.setdefault(user_phone, asyncio.Lock())
        async with lock:
            try:
                profile = await asyncio.to_thread(db.get_profile, user_phone)
            except Exception:
                logger.debug("Profile load skipped (no DB)", exc_info=True)
                profile = {}
            options = self._build_options(user_phone, profile)
            result_text = ""

            try:
                async for msg in query(prompt=message, options=options):
                    if isinstance(msg, ResultMessage):
                        if msg.result:
                            result_text = msg.result
                        self._sessions[user_phone] = msg.session_id
            except Exception as e:
                logger.error("Assistant error for %s: %s", user_phone, e)
                return AGENT_ERROR_REPLY

            return result_text or "No response generated."

    def invoke(self, message: str, user_phone: str) -> str:
        """Sync convenience wrapper. Do not call from inside a running event loop."""
        return asyncio.run(self.ainvoke(message, user_phone))
