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
from src.tools.calendar import calendar_tools, CALENDAR_TOOL_NAMES
from src.tools.email import email_tools, EMAIL_TOOL_NAMES
from src.tools.notes import build_notes_tools, NOTES_TOOL_NAMES
from src.tools.research import research_tools, RESEARCH_TOOL_NAMES

logger = logging.getLogger(__name__)

USER_TIMEZONE = "Asia/Singapore"

ALL_TOOL_NAMES = CALENDAR_TOOL_NAMES + EMAIL_TOOL_NAMES + NOTES_TOOL_NAMES + RESEARCH_TOOL_NAMES


class PersonalAssistant:
    """Wires a Claude Agent SDK manager agent with four specialist subagents.

    Runs through the Claude Agent SDK, which drives the same Claude Code CLI
    this environment is authenticated with, so usage is billed against that
    account's own subscription rather than a separate metered API key.
    """

    def __init__(self):
        # Per-user session continuity: phone -> Claude Agent SDK session_id.
        # In-memory only; lost on restart. Fine for an MVP, but a production
        # deployment should persist this map (e.g. in pa_users.profile).
        self._sessions: dict[str, str] = {}

    def _build_options(self, user_phone: str) -> ClaudeAgentOptions:
        current_time = datetime.now(timezone.utc).isoformat()
        format_kwargs = {"current_time": current_time, "user_timezone": USER_TIMEZONE}

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

        mcp_servers = {
            "calendar": create_sdk_mcp_server("calendar", tools=calendar_tools),
            "email": create_sdk_mcp_server("email", tools=email_tools),
            "notes": create_sdk_mcp_server("notes", tools=notes_tools),
            "research": create_sdk_mcp_server("research", tools=research_tools),
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
        options = self._build_options(user_phone)
        result_text = ""

        try:
            async for msg in query(prompt=message, options=options):
                if isinstance(msg, ResultMessage):
                    if msg.result:
                        result_text = msg.result
                    self._sessions[user_phone] = msg.session_id
        except Exception as e:
            logger.error("Assistant error for %s: %s", user_phone, e)
            return "Something went wrong processing your message. Please try again."

        return result_text or "No response generated."

    def invoke(self, message: str, user_phone: str) -> str:
        """Sync convenience wrapper. Do not call from inside a running event loop."""
        return asyncio.run(self.ainvoke(message, user_phone))
