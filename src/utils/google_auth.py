import os
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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
    creds = None

    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                logger.warning("Token refresh failed, re-authenticating")
                creds = None

        if not creds:
            if not os.path.exists(_CREDENTIALS_FILE):
                logger.error(
                    "credentials.json not found. Download it from Google Cloud Console."
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


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
