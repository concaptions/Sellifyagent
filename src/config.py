import os
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MANAGER_MODEL = "claude-sonnet-4-20250514"
AGENT_MODEL = "claude-sonnet-4-20250514"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM_WHATSAPP_NUMBER = os.getenv("FROM_WHATSAPP_NUMBER", "")

DATABASE_URL = os.getenv("DATABASE_URL", "")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

WHATSAPP_CHAR_LIMIT = 1600

PORT = int(os.getenv("PORT", "5000"))
