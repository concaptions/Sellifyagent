import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM_WHATSAPP_NUMBER = os.getenv("FROM_WHATSAPP_NUMBER", "")

DATABASE_URL = os.getenv("DATABASE_URL", "")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Google OAuth client (Web application type) — used to build the client
# config in-memory rather than requiring a credentials.json file on the
# deployed host (that file is never committed since it holds the secret).
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

WHATSAPP_CHAR_LIMIT = 1600

PORT = int(os.getenv("PORT", "5000"))

# The app's own public HTTPS base URL once deployed (e.g.
# "https://sellify-agent-production.up.railway.app"), no trailing slash.
# Used to build a fixed Google OAuth redirect_uri rather than guessing it
# from request headers, which is unreliable behind a reverse proxy.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
