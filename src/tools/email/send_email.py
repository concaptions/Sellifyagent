import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from claude_agent_sdk import tool

from src.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD


def _send_email(to: str, subject: str, body: str) -> str:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return "Email sending is not configured. GMAIL_ADDRESS and GMAIL_APP_PASSWORD are required."

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

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
    "Send an email via Gmail SMTP. Call only when the user explicitly asks to send an email.",
    SEND_EMAIL_SCHEMA,
)
async def send_email(args: dict) -> dict:
    result = await asyncio.to_thread(_send_email, args["to"], args["subject"], args["body"])
    return {"content": [{"type": "text", "text": result}]}
