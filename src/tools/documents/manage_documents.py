import asyncio

from claude_agent_sdk import tool, SdkMcpTool

from src import database as db
from src.utils.documents import embed_query


LIST_DOCUMENTS_SCHEMA = {"type": "object", "properties": {}, "required": []}

SEARCH_DOCUMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "What to look for in the user's documents."},
        "max_results": {"type": "integer", "description": "Maximum passages to return. Default 5."},
    },
    "required": ["query"],
}

DELETE_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {"type": "integer", "description": "The id from list_documents."},
    },
    "required": ["document_id"],
}


def _list_documents(user_id: str) -> str:
    try:
        docs = db.list_documents(user_id)
    except Exception as e:
        return f"Error listing documents: {e}"
    if not docs:
        return "The user has no saved documents."
    lines = []
    for d in docs:
        status = "" if d["status"] == "active" else f" ({d['status']}, not searched)"
        lines.append(
            f"- [id: {d['id']}] {d['filename']} — uploaded {d['created_at']:%Y-%m-%d}, "
            f"{d['char_count'] or 0:,} characters{status}"
        )
    return f"{len(docs)} saved document(s):\n" + "\n".join(lines)


def _search_documents(user_id: str, query: str, max_results: int) -> str:
    try:
        rows = db.search_document_chunks(user_id, query, embed_query(query), max_results)
    except Exception as e:
        return f"Error searching documents: {e}"
    if not rows:
        return f"Nothing in the user's documents matches '{query}'."
    parts = []
    for r in rows:
        parts.append(f"[{r['filename']} (id {r['document_id']}), part {r['chunk_index'] + 1}]\n{r['content']}")
    return "\n\n---\n\n".join(parts)


def _delete_document(user_id: str, document_id: int) -> str:
    try:
        filename = db.delete_document(user_id, document_id)
    except Exception as e:
        return f"Error deleting document: {e}"
    if not filename:
        return f"No document with id {document_id} exists for this user. Nothing was deleted."
    return f"Deleted '{filename}' (id {document_id}) and all its stored text permanently."


def build_document_tools(user_id: str) -> list[SdkMcpTool]:
    """Document tools bound to one user's phone number via closure, like the
    notes tools, so a turn can only ever see or delete its own user's files."""

    @tool("list_documents", "List the documents the user has sent and that are stored for them.", LIST_DOCUMENTS_SCHEMA)
    async def list_documents(args: dict) -> dict:
        result = await asyncio.to_thread(_list_documents, user_id)
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "search_documents",
        "Find passages in the user's stored documents relevant to a question. Use before answering anything about their documents.",
        SEARCH_DOCUMENTS_SCHEMA,
    )
    async def search_documents(args: dict) -> dict:
        result = await asyncio.to_thread(_search_documents, user_id, args["query"], args.get("max_results") or 5)
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "delete_document",
        "Permanently delete one of the user's documents. Only when the user has clearly asked to delete that specific document.",
        DELETE_DOCUMENT_SCHEMA,
    )
    async def delete_document(args: dict) -> dict:
        result = await asyncio.to_thread(_delete_document, user_id, int(args["document_id"]))
        return {"content": [{"type": "text", "text": result}]}

    return [list_documents, search_documents, delete_document]


DOCUMENT_TOOL_NAMES = [
    "mcp__documents__list_documents",
    "mcp__documents__search_documents",
    "mcp__documents__delete_document",
]
