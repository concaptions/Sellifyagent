import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD


class SendEmailInput(BaseModel):
    to: str = Field(description="Recipient email address. String.")
    subject: str = Field(description="Email subject line. String.")
    body: str = Field(description="Email body text. String.")


@tool(args_schema=SendEmailInput)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail SMTP. Call only when the user explicitly asks to send an email."""
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
