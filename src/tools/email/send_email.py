import asyncio
import base64
from email.mime.text import MIMEText

from claude_agent_sdk import tool

from src.utils.google_auth import get_gmail_service, not_connected


def _send_email(to: str, subject: str, body: str) -> str:
    # Sends through the Gmail API using the same OAuth token read_emails uses
    # (the gmail.send scope was requested alongside gmail.readonly/calendar
    # specifically for this). This used to go over SMTP with a separate
    # GMAIL_ADDRESS/GMAIL_APP_PASSWORD pair, which is a second credential to
    # keep valid on top of the OAuth connection and rejects outright if that
    # value isn't a real 16-character Google App Password (a regular account
    # password, or an app password generated without 2FA on, fails the same
    # way: SMTPAuthenticationError 535). Routing through the OAuth token
    # instead means there's one Google connection for this whole app, not two.
    service = get_gmail_service()
    if not service:
        return not_connected("Gmail")

    try:
        msg = MIMEText(body)
        msg["To"] = to
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        return f"Email sent to {to} with subject '{subject}'."

    except Exception as e:
        return f"Error sending email: {e}"


SEND_EMAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {"type": "string", "description": "Recipient email address."},
        "subject": {"type": "string", "description": "Email subject line."},
        "body": {"type": "string", "description": "Email body text."},
    },
    "required": ["to", "subject", "body"],
}


@tool(
    "send_email",
    "Send an email via Gmail. Call only when the user explicitly asks to send an email.",
    SEND_EMAIL_SCHEMA,
)
async def send_email(args: dict) -> dict:
    result = await asyncio.to_thread(_send_email, args["to"], args["subject"], args["body"])
    return {"content": [{"type": "text", "text": result}]}
