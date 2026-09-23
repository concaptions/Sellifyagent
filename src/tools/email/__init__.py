"""Gmail tools, built per user so each turn uses that user's own Google
account (closure over the phone, like the notes tools)."""
import asyncio

from claude_agent_sdk import tool, SdkMcpTool

from src.tools.email.read_emails import read_emails as _read_emails, READ_EMAILS_SCHEMA
from src.tools.email.send_email import send_email as _send_email, SEND_EMAIL_SCHEMA


def _text(t: str) -> dict:
    return {"content": [{"type": "text", "text": t}]}


def build_email_tools(user_phone: str) -> list[SdkMcpTool]:
    @tool("read_emails", "Search and read Gmail messages. Returns sender, subject, date, and a snippet of each.", READ_EMAILS_SCHEMA)
    async def read_emails(args: dict) -> dict:
        return _text(await asyncio.to_thread(_read_emails, user_phone, args.get("query") or "is:unread", args.get("max_results") or 5))

    @tool("send_email", "Send an email via Gmail. Call only when the user explicitly asks to send an email.", SEND_EMAIL_SCHEMA)
    async def send_email(args: dict) -> dict:
        return _text(await asyncio.to_thread(_send_email, user_phone, args["to"], args["subject"], args["body"]))

    return [read_emails, send_email]


EMAIL_TOOL_NAMES = ["mcp__email__read_emails", "mcp__email__send_email"]
