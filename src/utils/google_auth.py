import hashlib
import hmac
import os
import time
import logging
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from src.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, PUBLIC_BASE_URL, TEST_WEBHOOK_TOKEN, TWILIO_AUTH_TOKEN

logger = logging.getLogger(__name__)

# /oauth/google/start replaces the shared Google account with whichever
# account completes the consent screen, so the link handed out over
# WhatsApp is signed and short-lived rather than a bare public URL. The
# signing key is a server secret that never appears in a message.
_LINK_TTL_SECONDS = 30 * 60
_LINK_SECRET = (TEST_WEBHOOK_TOKEN or TWILIO_AUTH_TOKEN or "").encode()


def make_link_token() -> str:
    exp = str(int(time.time()) + _LINK_TTL_SECONDS)
    sig = hmac.new(_LINK_SECRET, exp.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{exp}.{sig}"


def verify_link_token(token: str | None) -> bool:
    if not _LINK_SECRET:
        return True  # local development: nothing to sign with
    try:
        exp, sig = (token or "").split(".", 1)
        expected = hmac.new(_LINK_SECRET, exp.encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(sig, expected) and int(exp) > time.time()
    except (ValueError, AttributeError):
        return False


def not_connected(service_name: str) -> str:
    """The message a Google tool returns when there is no usable token: it
    carries the reconnect link so the user can fix it themselves."""
    if not PUBLIC_BASE_URL:
        return f"{service_name} is not connected, and no public URL is configured to offer a reconnect link."
    return (
        f"{service_name} is not connected. Tell the user to reconnect Google by opening this link "
        f"(valid 30 minutes) and signing in: {PUBLIC_BASE_URL}/oauth/google/start?t={make_link_token()}"
    )

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

# google-auth-oauthlib's Flow defaults autogenerate_code_verifier=True, so
# authorization_url() silently turns on PKCE: it generates flow.code_verifier
# and embeds the matching code_challenge in the URL sent to Google. That
# verifier lives only on that one Flow instance in memory. /oauth/google/start
# and /oauth/google/callback are separate HTTP requests that each build a
# fresh Flow, so without carrying the verifier over, Google's token endpoint
# rejects the exchange with "invalid_grant: Missing code verifier" — the
# callback is presenting a code_verifier-less request against a
# code_challenge that demands one. Stash it here keyed by the flow's `state`
# (which round-trips through Google unchanged) so the callback can restore it
# onto its own Flow before calling fetch_token(). A short-lived in-memory
# store is enough: this is a one-time admin bootstrap flow, not per-message
# traffic, and it only needs to survive the seconds between visiting /start
# and Google redirecting back to /callback within the same running process.
_PKCE_TTL_SECONDS = 600
_pkce_lock = threading.Lock()
_pkce_store: dict[str, tuple[str, float]] = {}


def _save_code_verifier(state: str, code_verifier: str) -> None:
    with _pkce_lock:
        now = time.time()
        stale = [k for k, (_, saved_at) in _pkce_store.items() if now - saved_at > _PKCE_TTL_SECONDS]
        for k in stale:
            del _pkce_store[k]
        _pkce_store[state] = (code_verifier, now)


def _pop_code_verifier(state: str | None) -> str | None:
    if not state:
        return None
    with _pkce_lock:
        entry = _pkce_store.pop(state, None)
    if not entry:
        return None
    code_verifier, saved_at = entry
    if time.time() - saved_at > _PKCE_TTL_SECONDS:
        return None
    return code_verifier


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
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    # See the PKCE comment above _pkce_store: this Flow just generated a
    # code_verifier (PKCE is on by default) that the callback's separate
    # Flow instance has no way to know about unless we hand it over.
    if flow.code_verifier:
        _save_code_verifier(state, flow.code_verifier)
    return auth_url


def exchange_code_for_token(code: str, redirect_uri: str, state: str | None = None) -> None:
    """Complete the web OAuth flow: exchange the callback's code for tokens
    and persist them to token.json. redirect_uri must exactly match the one
    used in get_authorization_url() and the one registered in Google Cloud
    Console for this OAuth client. state should be the callback's ?state=
    query param, used to restore the code_verifier get_authorization_url()
    stashed for this same flow (see the PKCE comment above _pkce_store).
    """
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect_uri)
    code_verifier = _pop_code_verifier(state)
    if code_verifier:
        flow.code_verifier = code_verifier
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
