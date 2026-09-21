from src.tools.research.search_web import search_web

research_tools = [search_web]
RESEARCH_TOOL_NAMES = [f"mcp__research__{t.name}" for t in research_tools]
