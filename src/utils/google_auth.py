import os
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from src.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Configurable so a persistent volume can be mounted (e.g. /data/token.json)
# on hosts with an ephemeral filesystem — otherwise a redeploy loses the
# saved Google token and /oauth/google/start must be visited again.
_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")

# credentials.json is never committed (it holds the OAuth client secret), so
# rather than requiring that file to exist on the deployed host, the client
# config is built in-memory from env vars. from_client_config() takes the
# exact same "web": {...} shape as the downloaded credentials.json.
_CREDENTIALS_FILE = "credentials.json"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_google_credentials() -> Credentials | None:
    """Load saved credentials and refresh them if needed.

    Does NOT run an interactive consent flow — that only works with a local
    browser (see get_authorization_url/exchange_code_for_token below for the
    headless-server-friendly path). If there is no valid token on disk, the
    caller gets None and the relevant tool reports "not connected".
    """
    creds = None

    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, SCOPES)

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(_TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except Exception:
            logger.warning("Token refresh failed", exc_info=True)
            return None

    if not creds or not creds.valid:
        return None

    return creds


def get_authorization_url(redirect_uri: str) -> str:
    """Build the Google consent screen URL for the web OAuth flow.

    Use this from a server route (e.g. GET /oauth/google/start) instead of
    InstalledAppFlow.run_local_server(), which requires a local browser and
    cannot work on a headless deployment.
    """
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return auth_url


def exchange_code_for_token(code: str, redirect_uri: str) -> None:
    """Complete the web OAuth flow: exchange the callback's code for tokens
    and persist them to token.json. redirect_uri must exactly match the one
    used in get_authorization_url() and the one registered in Google Cloud
    Console for this OAuth client.
    """
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(code=code)
    with open(_TOKEN_FILE, "w") as f:
        f.write(flow.credentials.to_json())


def run_local_console_auth() -> None:
    """One-time interactive helper for running on a machine WITH a browser
    (e.g. your laptop) to produce a token.json you can then copy to a
    headless deployment. Not used by the running server.
    """
    flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(_TOKEN_FILE, "w") as f:
        f.write(creds.to_json())


def get_calendar_service():
    creds = get_google_credentials()
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds)


def get_gmail_service():
    creds = get_google_credentials()
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)
