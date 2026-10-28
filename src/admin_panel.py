"""/admin: the client submits a new user's Gmail, and the developer gets an
email to add it as a Google OAuth test user.

While the OAuth consent screen is in Testing, Google only lets listed test
users connect, and it has no API for adding them, so this is a one-click
hand-off rather than full automation. The email is sent from the shared owner
token (the account the app already uses for owner numbers).
"""
import base64
import html
import logging
import re
import secrets
import time
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from googleapiclient.discovery import build

from src.config import ADMIN_NOTIFY_EMAIL, ADMIN_PANEL_PASSWORD, GOOGLE_CLOUD_PROJECT
from src.utils.google_auth import GMAIL_SEND_SCOPE, _shared_credentials, has_scope

logger = logging.getLogger(__name__)
router = APIRouter()
_basic = HTTPBasic(auto_error=False)

# Simple, single-line address check; it also rules out header injection,
# since the address goes into the email subject.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# Brute-force brake on the password: per client IP, in memory (reset on deploy).
_FAIL_LIMIT, _FAIL_WINDOW = 10, 15 * 60
_failures: dict[str, list[float]] = {}
# Cap on emails sent, so a leaked password can't be used to flood the inbox.
_SEND_LIMIT, _SEND_WINDOW = 30, 60 * 60
_sends: list[float] = []


def _client_ip(request: Request) -> str:
    # Railway terminates TLS at its proxy; the first X-Forwarded-For hop is the caller.
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _recent(stamps: list[float], window: int) -> list[float]:
    now = time.time()
    return [t for t in stamps if now - t < window]


def require_admin(request: Request, creds: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    if not ADMIN_PANEL_PASSWORD:
        raise HTTPException(status_code=404)
    ip = _client_ip(request)
    fails = _recent(_failures.get(ip, []), _FAIL_WINDOW)
    if len(fails) >= _FAIL_LIMIT:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    if not creds or not secrets.compare_digest(creds.password.encode(), ADMIN_PANEL_PASSWORD.encode()):
        _failures[ip] = fails + [time.time()]
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Cue admin"'})
    _failures.pop(ip, None)


def _audience_url() -> str:
    return f"https://console.cloud.google.com/auth/audience?project={GOOGLE_CLOUD_PROJECT}"


def _send_notification(gmail: str, name: str, phone: str) -> str | None:
    """Emails the developer. Returns None on success, else a short reason."""
    creds = _shared_credentials()
    if not creds or not has_scope(creds, GMAIL_SEND_SCOPE):
        return "the owner Google account isn't connected with email sending"
    lines = [
        "A new Cue user needs to be added as a Google test user.",
        "",
        f"Gmail: {gmail}",
        f"Name: {name or '-'}",
        f"WhatsApp: {phone or '-'}",
        "",
        "Add it here (Audience > Test users > Add users):",
        _audience_url(),
        "",
        "Once added, the user can text Cue \"connect my Google\" to get their link.",
    ]
    msg = MIMEText("\n".join(lines))
    msg["To"] = ADMIN_NOTIFY_EMAIL
    msg["Subject"] = f"Add Google test user: {gmail}"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except Exception:
        logger.warning("Admin test-user email failed", exc_info=True)
        return "Gmail refused the message"
    return None


_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Cue admin</title>
<style>
body{{margin:0;background:#f5f6f8;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1b1f24}}
main{{max-width:460px;margin:48px auto;padding:0 16px}}
.card{{background:#fff;border:1px solid #e3e6ea;border-radius:12px;padding:28px}}
h1{{font-size:20px;margin:0 0 6px}} p{{color:#5b6470;font-size:14px;line-height:1.5;margin:0 0 18px}}
label{{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}}
input{{width:100%;box-sizing:border-box;padding:11px 12px;border:1px solid #cfd4da;border-radius:8px;font-size:15px}}
button{{margin-top:20px;width:100%;padding:12px;border:0;border-radius:8px;background:#14181d;color:#fff;font-size:15px;font-weight:600;cursor:pointer}}
.ok,.err{{border-radius:8px;padding:12px 14px;font-size:14px;margin-bottom:16px}}
.ok{{background:#ecf7ef;color:#1d6b35}} .err{{background:#fdecec;color:#a12626}}
small{{color:#8a929c}}
</style></head><body><main><div class="card">
<h1>Add a Cue user</h1>
<p>Enter the new user's Gmail address. We'll add it to Google so they can connect their account to Cue.</p>
{notice}
<form method="post" action="/admin/test-user">
<label for="gmail">Gmail address</label>
<input id="gmail" name="gmail" type="email" required placeholder="name@gmail.com" value="{gmail}">
<label for="name">Name <small>(optional)</small></label>
<input id="name" name="name" maxlength="80" value="{name}">
<label for="phone">WhatsApp number <small>(optional)</small></label>
<input id="phone" name="phone" maxlength="20" placeholder="+65..." value="{phone}">
<button type="submit">Send</button>
</form></div></main></body></html>"""


def _render(notice: str = "", gmail: str = "", name: str = "", phone: str = "", status: int = 200) -> HTMLResponse:
    page = _PAGE.format(notice=notice, gmail=html.escape(gmail), name=html.escape(name), phone=html.escape(phone))
    return HTMLResponse(page, status_code=status, headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY"})


@router.get("/admin", dependencies=[Depends(require_admin)])
async def admin_page():
    return _render()


@router.post("/admin/test-user", dependencies=[Depends(require_admin)])
async def admin_test_user(gmail: str = Form(...), name: str = Form(""), phone: str = Form("")):
    gmail = gmail.strip().lower()
    # Single line only: these values go into the email body.
    name = " ".join(name.split())[:80]
    phone = re.sub(r"[^0-9+ ]", "", phone)[:20].strip()
    if not _EMAIL_RE.match(gmail):
        return _render('<div class="err">That doesn\'t look like a valid email address.</div>', gmail, name, phone, 400)
    global _sends
    _sends = _recent(_sends, _SEND_WINDOW)
    if len(_sends) >= _SEND_LIMIT:
        return _render('<div class="err">Too many requests this hour. Please try again later.</div>', gmail, name, phone, 429)
    reason = _send_notification(gmail, name, phone)
    if reason:
        return _render(f'<div class="err">Couldn\'t send right now ({html.escape(reason)}). Please try again later.</div>',
                       gmail, name, phone, 503)
    _sends.append(time.time())
    return _render(f'<div class="ok">Sent. <b>{html.escape(gmail)}</b> will be added shortly; the user can then '
                   'text Cue "connect my Google".</div>')
