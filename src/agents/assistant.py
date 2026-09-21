import logging
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from src.agents.base import Agent
from src.agents.orchestrator import AgentsOrchestrator
from src.config import MANAGER_MODEL, AGENT_MODEL
from src.prompts.manager import MANAGER_PROMPT
from src.prompts.email_agent import EMAIL_AGENT_PROMPT
from src.prompts.calendar_agent import CALENDAR_AGENT_PROMPT
from src.prompts.notes_agent import NOTES_AGENT_PROMPT
from src.prompts.research_agent import RESEARCH_AGENT_PROMPT
from src.tools.calendar import calendar_tools
from src.tools.email import email_tools
from src.tools.notes import notes_tools
from src.tools.research import research_tools

logger = logging.getLogger(__name__)


class PersonalAssistant:
    def __init__(self, db_path: str = "db/checkpoints.sqlite"):
        self.db_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self.db_conn)
        self.orchestrator = self._build()

    def _build(self) -> AgentsOrchestrator:
        default_kwargs = {"user_timezone": "Asia/Singapore"}

        email_agent = Agent(
            name="email_agent",
            model=AGENT_MODEL,
            system_prompt=EMAIL_AGENT_PROMPT,
            tools=email_tools,
            format_kwargs=default_kwargs,
        )

        calendar_agent = Agent(
            name="calendar_agent",
            model=AGENT_MODEL,
            system_prompt=CALENDAR_AGENT_PROMPT,
            tools=calendar_tools,
            format_kwargs=default_kwargs,
        )

        notes_agent = Agent(
            name="notes_agent",
            model=AGENT_MODEL,
            system_prompt=NOTES_AGENT_PROMPT,
            tools=notes_tools,
            format_kwargs=default_kwargs,
        )

        research_agent = Agent(
            name="research_agent",
            model=AGENT_MODEL,
            system_prompt=RESEARCH_AGENT_PROMPT,
            tools=research_tools,
            format_kwargs=default_kwargs,
        )

        manager = Agent(
            name="manager",
            model=MANAGER_MODEL,
            system_prompt=MANAGER_PROMPT,
            tools=[],
            format_kwargs=default_kwargs,
        )

        return AgentsOrchestrator(
            manager_agent=manager,
            sub_agents={
                "email_agent": email_agent,
                "calendar_agent": calendar_agent,
                "notes_agent": notes_agent,
                "research_agent": research_agent,
            },
            checkpointer=self.checkpointer,
        )

    def invoke(self, message: str, user_phone: str) -> str:
        config = {
            "configurable": {"thread_id": user_phone},
        }
        try:
            response = self.orchestrator.invoke(message, config)
            return response
        except Exception as e:
            logger.error("Assistant error for %s: %s", user_phone, e)
            return "Something went wrong processing your message. Please try again."

    async def ainvoke(self, message: str, user_phone: str) -> str:
        config = {
            "configurable": {"thread_id": user_phone},
        }
        try:
            response = await self.orchestrator.ainvoke(message, config)
            return response
        except Exception as e:
            logger.error("Assistant error for %s: %s", user_phone, e)
            return "Something went wrong processing your message. Please try again."
