import asyncio

from claude_agent_sdk import tool

from src.utils.google_auth import get_gmail_service


def _read_emails(query: str, max_results: int) -> str:
    service = get_gmail_service()
    if not service:
        return "Gmail is not connected. The user needs to set up Google OAuth first."

    try:
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = result.get("messages", [])

        if not messages:
            return f"No emails found for query: {query}"

        lines = []
        for msg_meta in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")

            lines.append(
                f"- From: {headers.get('From', '?')}\n"
                f"  Subject: {headers.get('Subject', '(no subject)')}\n"
                f"  Date: {headers.get('Date', '?')}\n"
                f"  Preview: {snippet[:200]}\n"
                f"  [id: {msg_meta['id']}]"
            )

        return f"Found {len(messages)} email(s):\n\n" + "\n\n".join(lines)

    except Exception as e:
        return f"Error reading emails: {e}"


READ_EMAILS_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "Gmail search query. Examples: 'is:unread', 'from:boss@example.com', "
                "'subject:invoice'. Default 'is:unread'."
            ),
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of emails to return. Default 5.",
        },
    },
    "required": [],
}


@tool(
    "read_emails",
    "Search and read Gmail messages. Returns sender, subject, date, and a snippet of each.",
    READ_EMAILS_SCHEMA,
)
async def read_emails(args: dict) -> dict:
    query = args.get("query") or "is:unread"
    max_results = args.get("max_results") or 5
    result = await asyncio.to_thread(_read_emails, query, max_results)
    return {"content": [{"type": "text", "text": result}]}
