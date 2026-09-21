from src.tools.email.read_emails import read_emails
from src.tools.email.send_email import send_email

email_tools = [read_emails, send_email]
EMAIL_TOOL_NAMES = [f"mcp__email__{t.name}" for t in email_tools]
