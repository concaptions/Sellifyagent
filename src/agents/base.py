import logging
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        tools: list,
        checkpointer=None,
        format_kwargs: dict | None = None,
    ):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.checkpointer = checkpointer
        self.format_kwargs = format_kwargs or {}
        self._agent = None

    def _build(self):
        llm = ChatAnthropic(model=self.model, temperature=0.2)

        kwargs = {
            "current_time": datetime.now(timezone.utc).isoformat(),
            **self.format_kwargs,
        }
        formatted_prompt = self.system_prompt.format(**kwargs)

        agent_kwargs = {
            "model": llm,
            "tools": self.tools,
            "prompt": formatted_prompt,
        }
        if self.checkpointer:
            agent_kwargs["checkpointer"] = self.checkpointer

        self._agent = create_react_agent(**agent_kwargs)

    def invoke(self, message: str, config: dict | None = None) -> str:
        if self._agent is None:
            self._build()

        result = self._agent.invoke(
            {"messages": [("human", message)]},
            config=config or {},
        )

        ai_messages = [m for m in result["messages"] if m.type == "ai" and m.content]
        if ai_messages:
            return ai_messages[-1].content

        return "No response generated."

    async def ainvoke(self, message: str, config: dict | None = None) -> str:
        if self._agent is None:
            self._build()

        result = await self._agent.ainvoke(
            {"messages": [("human", message)]},
            config=config or {},
        )

        ai_messages = [m for m in result["messages"] if m.type == "ai" and m.content]
        if ai_messages:
            return ai_messages[-1].content

        return "No response generated."
