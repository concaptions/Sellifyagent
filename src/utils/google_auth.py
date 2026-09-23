"""Google OAuth for Calendar and Gmail, per WhatsApp user.

Each user connects their own Google account through a personal link; the
resulting tokens are stored in that user's profile row. The one shared
token file from the single-account era is kept only as a fallback for the
owner numbers (BUSINESS_DATA_PHONES), so the client's existing connection
keeps working while other users connect their own.
"""
import hashlib
import hmac
import json
import os
import secrets
import time
import logging
import threading

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

from src import database as db
from src.config import (
    BUSINESS_DATA_PHONES,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    PUBLIC_BASE_URL,
    TEST_WEBHOOK_TOKEN,
    TWILIO_AUTH_TOKEN,
)

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Shared (legacy) token: configurable so a persistent volume can be mounted
# (e.g. /data/token.json) on hosts with an ephemeral filesystem.
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
# rejects the exchange with "invalid_grant: Missing code verifier". Stash it
# here keyed by the flow's `state` (which round-trips through Google
# unchanged), together with the phone number the link was issued to, so the
# callback knows whose tokens it is saving.
_PKCE_TTL_SECONDS = 600
_pkce_lock = threading.Lock()
_pkce_store: dict[str, tuple[str, str | None, float]] = {}


def _save_pkce(state: str, code_verifier: str, phone: str | None) -> None:
    with _pkce_lock:
        now = time.time()
        for k in [k for k, (_, _, saved_at) in _pkce_store.items() if now - saved_at > _PKCE_TTL_SECONDS]:
            del _pkce_store[k]
        _pkce_store[state] = (code_verifier, phone, now)


def _pop_pkce(state: str | None) -> tuple[str | None, str | None]:
    if not state:
        return None, None
    with _pkce_lock:
        entry = _pkce_store.pop(state, None)
    if not entry:
        return None, None
    code_verifier, phone, saved_at = entry
    if time.time() - saved_at > _PKCE_TTL_SECONDS:
        return None, None
    return code_verifier, phone


# --- Personal connect links ---------------------------------------------------
# /oauth/google/start connects whichever Google account completes the consent
# screen to the WhatsApp number the link was issued for, so the link must be
# unguessable and short-lived, and must not carry the phone number itself
# (URLs end up in proxy logs). An opaque nonce maps to the phone in memory;
# the nonce is signed so a lost map can only mean "ask for a fresh link".
_LINK_TTL_SECONDS = 30 * 60
_LINK_SECRET = (TEST_WEBHOOK_TOKEN or TWILIO_AUTH_TOKEN or "").encode()
_link_lock = threading.Lock()
_links: dict[str, tuple[str, float]] = {}


def make_link_token(phone: str) -> str:
    nonce = secrets.token_hex(12)
    exp = str(int(time.time()) + _LINK_TTL_SECONDS)
    sig = hmac.new(_LINK_SECRET, f"{nonce}|{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    with _link_lock:
        now = time.time()
        for k in [k for k, (_, e) in _links.items() if e < now]:
            del _links[k]
        _links[nonce] = (phone, float(exp))
    return f"{nonce}.{exp}.{sig}"


def resolve_link_token(token: str | None) -> str | None:
    """The phone a valid, unexpired link was issued to, else None."""
    try:
        nonce, exp, sig = (token or "").split(".", 2)
        expected = hmac.new(_LINK_SECRET, f"{nonce}|{exp}".encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected) or int(exp) <= time.time():
            return None
    except (ValueError, AttributeError):
        return None
    with _link_lock:
        entry = _links.get(nonce)
    return entry[0] if entry else None


def connect_link(phone: str) -> str:
    return f"{PUBLIC_BASE_URL}/oauth/google/start?t={make_link_token(phone)}"


def not_connected(service_name: str, phone: str) -> str:
    """The message a Google tool returns when this user has no usable token:
    it carries their personal connect link so they can fix it themselves."""
    if not PUBLIC_BASE_URL:
        return f"{service_name} is not connected for this user, and no public URL is configured to offer a connect link."
    return (
        f"{service_name} is not connected for this user. Tell them to connect their Google account by "
        f"opening this personal link (valid 30 minutes) and signing in: {connect_link(phone)}"
    )


# --- Credentials --------------------------------------------------------------

def _client_config() -> dict:
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        return {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
    with open(_CREDENTIALS_FILE) as f:
        return json.load(f)


def _refresh(creds: Credentials | None, save) -> Credentials | None:
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save(creds.to_json())
        except Exception:
            logger.warning("Token refresh failed", exc_info=True)
            return None
    return creds if creds and creds.valid else None


def _shared_credentials() -> Credentials | None:
    if not os.path.exists(_TOKEN_FILE):
        return None
    creds = Credentials.from_authorized_user_file(_TOKEN_FILE, SCOPES)

    def save(text: str) -> None:
        with open(_TOKEN_FILE, "w") as f:
            f.write(text)

    return _refresh(creds, save)


def get_google_credentials(phone: str | None = None) -> Credentials | None:
    """This user's own Google credentials, refreshed if needed. Owner numbers
    fall back to the shared token; anyone else without their own gets None
    and the calling tool reports "not connected" with a personal link."""
    if phone:
        try:
            stored = db.get_google_tokens(phone)
        except Exception:
            logger.debug("Google token lookup skipped (no DB)", exc_info=True)
            stored = None
        if stored:
            creds = Credentials.from_authorized_user_info(json.loads(stored), SCOPES)
            creds = _refresh(creds, lambda text: db.set_google_tokens(phone, text))
            if creds:
                return creds
        if phone not in BUSINESS_DATA_PHONES:
            return None
    return _shared_credentials()


def google_connection_status(phone: str) -> str:
    creds = get_google_credentials(phone)
    if not creds:
        return not_connected("Google (Calendar and Gmail)", phone)
    try:
        stored = db.get_google_tokens(phone)
    except Exception:
        stored = None
    which = "their own Google account" if stored else "the shared Google account"
    return f"Google is connected for this user via {which}. To switch accounts, open: {connect_link(phone)}"


# --- Web OAuth flow -----------------------------------------------------------

def get_authorization_url(redirect_uri: str, phone: str | None) -> str:
    """Build the Google consent screen URL for the web OAuth flow, for the
    given WhatsApp user (None = the shared account)."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    _save_pkce(state, flow.code_verifier or "", phone)
    return auth_url


def exchange_code_for_token(code: str, redirect_uri: str, state: str | None = None) -> str | None:
    """Complete the web OAuth flow and store the tokens for the user the
    link was issued to (or the shared file when there is none). Returns the
    phone the tokens were saved for."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect_uri)
    code_verifier, phone = _pop_pkce(state)
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    text = flow.credentials.to_json()
    if phone:
        db.set_google_tokens(phone, text)
    else:
        with open(_TOKEN_FILE, "w") as f:
            f.write(text)
    return phone


def run_local_console_auth() -> None:
    """One-time interactive helper for a machine WITH a browser to produce a
    shared token.json. Not used by the running server."""
    flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(_TOKEN_FILE, "w") as f:
        f.write(creds.to_json())


def get_calendar_service(phone: str | None = None):
    creds = get_google_credentials(phone)
    return build("calendar", "v3", credentials=creds) if creds else None


def get_gmail_service(phone: str | None = None):
    creds = get_google_credentials(phone)
    return build("gmail", "v1", credentials=creds) if creds else None
