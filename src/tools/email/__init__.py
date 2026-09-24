"""Gmail tools, built per user so each turn uses that user's own Google
account (closure over the phone, like the notes tools)."""
import asyncio

from claude_agent_sdk import tool, SdkMcpTool

from src.tools.email.read_emails import read_emails as _read_emails, READ_EMAILS_SCHEMA
from src.tools.email.read_email import read_email as _read_email, READ_EMAIL_SCHEMA
from src.tools.email.read_attachment import read_attachment as _read_attachment, READ_ATTACHMENT_SCHEMA
from src.tools.email.send_email import send_email as _send_email, SEND_EMAIL_SCHEMA


def _text(t: str) -> dict:
    return {"content": [{"type": "text", "text": t}]}


def build_email_tools(user_phone: str) -> list[SdkMcpTool]:
    @tool("read_emails", "Search Gmail. Returns sender, subject, date, a ~200-character preview and the id of each match; call read_email with the id for the full text.", READ_EMAILS_SCHEMA)
    async def read_emails(args: dict) -> dict:
        return _text(await asyncio.to_thread(_read_emails, user_phone, args.get("query") or "is:unread", args.get("max_results") or 5))

    @tool("read_email", "Read one email in full (headers, whole body, attachment names) by the id from read_emails. Use this whenever the preview is not enough.", READ_EMAIL_SCHEMA)
    async def read_email(args: dict) -> dict:
        return _text(await asyncio.to_thread(_read_email, user_phone, args["message_id"]))

    @tool("read_email_attachment", "Read the text of a PDF, Word or text attachment on an email (by message id and the attachment name read_email listed).", READ_ATTACHMENT_SCHEMA)
    async def read_email_attachment(args: dict) -> dict:
        return _text(await asyncio.to_thread(_read_attachment, user_phone, args["message_id"], args.get("filename")))

    @tool("send_email", "Send an email via Gmail. Call only when the user explicitly asks to send an email.", SEND_EMAIL_SCHEMA)
    async def send_email(args: dict) -> dict:
        return _text(await asyncio.to_thread(_send_email, user_phone, args["to"], args["subject"], args["body"]))

    return [read_emails, read_email, read_email_attachment, send_email]


EMAIL_TOOL_NAMES = [
    "mcp__email__read_emails",
    "mcp__email__read_email",
    "mcp__email__read_email_attachment",
    "mcp__email__send_email",
]
