import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM_WHATSAPP_NUMBER = os.getenv("FROM_WHATSAPP_NUMBER", "")

DATABASE_URL = os.getenv("DATABASE_URL", "")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

WHATSAPP_CHAR_LIMIT = 1600

PORT = int(os.getenv("PORT", "5000"))
