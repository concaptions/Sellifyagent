import base64
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.utils.google_auth import get_gmail_service


class ReadEmailsInput(BaseModel):
    query: str = Field(
        default="is:unread",
        description="Gmail search query. String. Examples: 'is:unread', 'from:boss@example.com', 'subject:invoice'.",
    )
    max_results: int = Field(default=5, description="Maximum number of emails to return. Integer.")


@tool(args_schema=ReadEmailsInput)
def read_emails(query: str = "is:unread", max_results: int = 5) -> str:
    """Search and read Gmail messages. Returns sender, subject, date, and a snippet of each."""
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
