import os
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

_TOKEN_FILE = "token.json"
_CREDENTIALS_FILE = "credentials.json"


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
    flow = Flow.from_client_secrets_file(_CREDENTIALS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
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
    flow = Flow.from_client_secrets_file(_CREDENTIALS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
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
