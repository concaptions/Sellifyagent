from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config import TAVILY_API_KEY


class SearchWebInput(BaseModel):
    query: str = Field(description="The search query. String.")
    max_results: int = Field(default=5, description="Maximum number of results. Integer.")


@tool(args_schema=SearchWebInput)
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for current information. Use for questions about recent events, facts, or anything not in the user's data."""
    if not TAVILY_API_KEY:
        return "Web search is not configured. TAVILY_API_KEY is required."

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query=query, max_results=max_results)

        results = response.get("results", [])
        if not results:
            return f"No results found for: {query}"

        lines = []
        for r in results:
            lines.append(
                f"- {r.get('title', 'Untitled')}\n"
                f"  {r.get('content', '')[:300]}\n"
                f"  Source: {r.get('url', '')}"
            )

        return f"Search results for '{query}':\n\n" + "\n\n".join(lines)

    except Exception as e:
        return f"Error searching the web: {e}"
