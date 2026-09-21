import asyncio

from claude_agent_sdk import tool

from src.config import TAVILY_API_KEY


def _search_web(query: str, max_results: int) -> str:
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


SEARCH_WEB_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "The search query."},
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results. Default 5.",
        },
    },
    "required": ["query"],
}


@tool(
    "search_web",
    "Search the web for current information. Use for questions about recent events, facts, or anything not in the user's data.",
    SEARCH_WEB_SCHEMA,
)
async def search_web(args: dict) -> dict:
    query = args["query"]
    max_results = args.get("max_results") or 5
    result = await asyncio.to_thread(_search_web, query, max_results)
    return {"content": [{"type": "text", "text": result}]}
