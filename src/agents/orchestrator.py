import logging
from enum import Enum
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.agents.base import Agent

logger = logging.getLogger(__name__)


def create_send_message_tool(agent_mapping: dict[str, Agent]):
    agent_names = list(agent_mapping.keys())
    descriptions = {name: agent.system_prompt.split("\n")[0] for name, agent in agent_mapping.items()}

    AgentName = Enum("AgentName", {name: name for name in agent_names})

    class SendMessageInput(BaseModel):
        recipient: str = Field(
            description=(
                "The agent to send the message to. One of: "
                + ", ".join(f"'{n}' ({descriptions[n][:80]})" for n in agent_names)
            )
        )
        message: str = Field(
            description="The task or question to send to the agent. String."
        )

    @tool(args_schema=SendMessageInput)
    def send_message(recipient: str, message: str) -> str:
        """Send a task to a specialist agent and get their response."""
        if recipient not in agent_mapping:
            return f"Unknown agent: {recipient}. Available: {', '.join(agent_names)}"

        try:
            agent = agent_mapping[recipient]
            response = agent.invoke(message)
            return response
        except Exception as e:
            logger.error("Agent %s failed: %s", recipient, e)
            return f"Agent {recipient} encountered an error: {e}"

    return send_message


class AgentsOrchestrator:
    def __init__(
        self,
        manager_agent: Agent,
        sub_agents: dict[str, Agent],
        checkpointer=None,
    ):
        self.sub_agents = sub_agents
        self.send_message_tool = create_send_message_tool(sub_agents)

        manager_agent.tools = [self.send_message_tool] + (manager_agent.tools or [])
        manager_agent.checkpointer = checkpointer
        self.manager = manager_agent

    def invoke(self, message: str, config: dict | None = None) -> str:
        return self.manager.invoke(message, config)

    async def ainvoke(self, message: str, config: dict | None = None) -> str:
        return await self.manager.ainvoke(message, config)
