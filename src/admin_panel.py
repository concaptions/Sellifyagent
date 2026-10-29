"""/admin: the client submits a new user's Gmail, and the developer gets an
email to add it as a Google OAuth test user.

While the OAuth consent screen is in Testing, Google only lets listed test
users connect, and it has no API for adding them, so this is a one-click
hand-off rather than full automation. The client signs in on /admin/login
(a signed, HttpOnly session cookie, 12 h), can submit several users at once,
and all of them go to the developer in one email.

Sending prefers a Gmail App Password over SMTP: the shared OAuth token dies
every ~7 days while the consent screen is in Testing (seen live: invalid_grant
on 2026-10-28), so it is only the fallback.
"""
import asyncio
import base64
import hashlib
import hmac
import html
import logging
import re
import secrets
import smtplib
import time
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from googleapiclient.discovery import build

from src.config import (
    ADMIN_NOTIFY_EMAIL, ADMIN_PANEL_PASSWORD, ADMIN_SMTP_ADDRESS, ADMIN_SMTP_APP_PASSWORD, GOOGLE_CLOUD_PROJECT,
)
from src.utils.google_auth import GMAIL_SEND_SCOPE, _shared_credentials, has_scope

logger = logging.getLogger(__name__)
router = APIRouter()

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


# --- session (sign-in page instead of the browser's Basic-auth pop-up) -------
_COOKIE = "cue_admin"
_SESSION_TTL = 12 * 60 * 60
# Most users one submission may carry, so a single post can't produce a wall of text.
_MAX_USERS = 25


def _session_key() -> bytes:
    # Derived from the password, so changing ADMIN_PANEL_PASSWORD signs everyone out.
    return hashlib.sha256(b"cue-admin-session:" + ADMIN_PANEL_PASSWORD.encode()).digest()


def _make_session() -> str:
    exp = str(int(time.time()) + _SESSION_TTL)
    sig = hmac.new(_session_key(), f"admin|{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def _signed_in(request: Request) -> bool:
    exp, _, sig = request.cookies.get(_COOKIE, "").partition(".")
    if not exp.isdigit() or int(exp) < time.time():
        return False
    good = hmac.new(_session_key(), f"admin|{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good)


def _is_https(request: Request) -> bool:
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def _enabled() -> None:
    if not ADMIN_PANEL_PASSWORD:
        raise HTTPException(status_code=404)


def _audience_url() -> str:
    return f"https://console.cloud.google.com/auth/audience?project={GOOGLE_CLOUD_PROJECT}"


# --- the email -----------------------------------------------------------------
def _build_message(users: list[dict]) -> MIMEText:
    n = len(users)
    lines = [
        f"{n} new Cue user{'s need' if n > 1 else ' needs'} to be added as Google test user{'s' if n > 1 else ''}.",
        "",
    ]
    for i, u in enumerate(users, 1):
        lines.append(f"{i}. {u['gmail']}   Name: {u['name'] or '-'}   WhatsApp: {u['phone'] or '-'}")
    lines += [
        "",
        "Add them here (Audience > Test users > Add users). You can paste all addresses at once:",
        ", ".join(u["gmail"] for u in users),
        "",
        _audience_url(),
        "",
        "Once added, each user can text Cue \"connect my Google\" to get their link.",
    ]
    msg = MIMEText("\n".join(lines))
    msg["To"] = ADMIN_NOTIFY_EMAIL
    if n == 1:
        msg["Subject"] = f"Add Google test user: {users[0]['gmail']}"
    else:
        shown = ", ".join(u["gmail"] for u in users[:2])
        more = f" (+{n - 2} more)" if n > 2 else ""
        msg["Subject"] = f"Add {n} Google test users: {shown}{more}"
    return msg


def _send_smtp(msg: MIMEText) -> str | None:
    if not (ADMIN_SMTP_ADDRESS and ADMIN_SMTP_APP_PASSWORD):
        return "no App Password sender configured"
    msg["From"] = f"Cue admin <{ADMIN_SMTP_ADDRESS}>"
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(ADMIN_SMTP_ADDRESS, ADMIN_SMTP_APP_PASSWORD)
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        logger.warning("Admin email: SMTP login rejected (check the App Password)")
        return "the sender's App Password was rejected"
    except Exception:
        logger.warning("Admin email: SMTP send failed", exc_info=True)
        return "the email server refused the message"
    return None


def _send_gmail_api(msg: MIMEText) -> str | None:
    creds = _shared_credentials()
    if not creds or not has_scope(creds, GMAIL_SEND_SCOPE):
        return "the owner Google account isn't connected with email sending"
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        service = build("gmail", "v1", credentials=creds)
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except Exception:
        logger.warning("Admin test-user email failed", exc_info=True)
        return "Gmail refused the message"
    return None


def _send_notification(users: list[dict]) -> str | None:
    """Emails the developer. Returns None on success, else a short reason."""
    smtp_reason = _send_smtp(_build_message(users))
    if smtp_reason is None:
        return None
    api_reason = _send_gmail_api(_build_message(users))
    if api_reason is None:
        return None
    return smtp_reason if ADMIN_SMTP_ADDRESS else api_reason


def _clean(gmail: str, name: str = "", phone: str = "") -> dict:
    # Single line only: these values go into the email.
    return {
        "gmail": gmail.strip().lower(),
        "name": " ".join(name.split())[:80],
        "phone": re.sub(r"[^0-9+ ]", "", phone)[:20].strip(),
    }


def _parse_paste(text: str) -> list[dict]:
    """One user per line: "email" or "email, name, phone" (commas, tabs or semicolons)."""
    out = []
    for line in text.splitlines():
        parts = [p.strip() for p in re.split(r"[,\t;]", line) if p.strip()]
        if parts:
            out.append(_clean(parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else ""))
    return out


# --- pages -----------------------------------------------------------------------
_STYLE = """
:root{--ink:#14181d;--body:#3a4049;--muted:#6b7280;--line:#e3e6ea;--bg:#f4f5f7;--accent:#b8935a;--ok:#1d6b35;--okbg:#ecf7ef;--err:#a12626;--errbg:#fdecec}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink)}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px}
.mark{width:34px;height:34px;border-radius:9px;background:var(--ink);color:#fff;display:grid;place-items:center;font-size:16px}
.mark{box-shadow:inset 0 -3px 0 var(--accent)}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
h1{font-size:22px;margin:0 0 6px} p.sub{color:var(--muted);font-size:14px;line-height:1.55;margin:0 0 22px}
label{display:block;font-size:13px;font-weight:600;margin:0 0 6px;color:var(--body)}
input,textarea{width:100%;padding:11px 12px;border:1px solid #cfd4da;border-radius:9px;font-size:15px;font-family:inherit;background:#fff}
input:focus,textarea:focus{outline:none;border-color:var(--ink);box-shadow:0 0 0 3px rgba(20,24,29,.08)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 18px;border:0;border-radius:9px;background:var(--ink);color:#fff;font-size:15px;font-weight:600;cursor:pointer}
.btn:hover{background:#2a3038} .btn.full{width:100%}
.btn.ghost{background:transparent;color:var(--ink);border:1px dashed #b9bec5}
.btn.ghost:hover{background:#f7f8f9}
.link{background:none;border:0;color:var(--muted);font-size:14px;cursor:pointer;padding:6px}
.link:hover{color:var(--ink)}
.notice{border-radius:9px;padding:12px 14px;font-size:14px;line-height:1.5;margin-bottom:18px}
.ok{background:var(--okbg);color:var(--ok)} .err{background:var(--errbg);color:var(--err)}
small{color:#8a929c;font-weight:400}
"""

_LOGIN = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in · Cue Admin</title>
<style>%STYLE%
.wrap{min-height:100vh;display:grid;place-items:center;padding:24px 16px}
.login{width:100%;max-width:400px;padding:32px}
.login .brand{margin-bottom:26px}
.pw{position:relative} .pw input{padding-right:64px}
.pw button{position:absolute;right:6px;top:50%;transform:translateY(-50%);background:none;border:0;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;padding:6px 8px}
.foot{text-align:center;color:#9aa0a8;font-size:12px;margin-top:18px}
</style></head><body><div class="wrap"><div>
<div class="card login">
<div class="brand"><div class="mark">C</div>Cue Admin</div>
<h1>Sign in</h1><p class="sub">Enter the admin password to manage Cue users.</p>
%NOTICE%
<form method="post" action="/admin/login">
<label for="password">Password</label>
<div class="pw"><input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
<button type="button" onclick="var i=document.getElementById('password');var s=i.type==='password';i.type=s?'text':'password';this.textContent=s?'Hide':'Show'">Show</button></div>
<div style="height:20px"></div>
<button class="btn full" type="submit">Sign in</button>
</form></div>
<div class="foot">Cue · private admin area</div>
</div></div></body></html>"""

_DASH = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Add users · Cue Admin</title>
<style>%STYLE%
header{background:#fff;border-bottom:1px solid var(--line)}
.bar{max-width:760px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;justify-content:space-between}
main{max-width:760px;margin:32px auto;padding:0 16px 48px}
.panel{padding:28px}
.row{display:grid;grid-template-columns:1.4fr 1fr .9fr 36px;gap:10px;align-items:end;margin-bottom:12px}
.row .x{height:44px;border:0;background:none;color:#9aa0a8;font-size:22px;cursor:pointer;border-radius:8px}
.row .x:hover{background:#f3f4f6;color:var(--err)}
.row:only-child .x{visibility:hidden}
.heads{display:grid;grid-template-columns:1.4fr 1fr .9fr 36px;gap:10px;margin-bottom:6px}
.actions{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-top:18px;flex-wrap:wrap}
details{margin-top:20px;border-top:1px solid var(--line);padding-top:16px}
summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--body)}
details textarea{margin-top:10px;min-height:120px}
.hint{color:var(--muted);font-size:13px;margin-top:6px}
.count{color:var(--muted);font-size:13px}
@media (max-width:640px){.heads{display:none}.row{grid-template-columns:1fr;gap:6px;padding:12px;border:1px solid var(--line);border-radius:10px}
.row .x{visibility:visible!important;height:auto;justify-self:end}.row label.m{display:block}}
label.m{display:none;font-size:12px}
</style></head><body>
<header><div class="bar"><div class="brand"><div class="mark">C</div>Cue Admin</div>
<form method="post" action="/admin/logout"><button class="link" type="submit">Sign out</button></form></div></header>
<main><div class="card panel">
<h1>Add Cue users</h1>
<p class="sub">Enter each new user's Gmail address. We'll add them in Google so they can connect their account to Cue. You can add several people at once.</p>
%NOTICE%
<form method="post" action="/admin/test-user" id="f">
<div class="heads"><label>Gmail address</label><label>Name <small>(optional)</small></label><label>WhatsApp <small>(optional)</small></label><span></span></div>
<div id="rows">%ROWS%</div>
<button class="btn ghost" type="button" id="add">+ Add another user</button>
<details %OPEN%><summary>Paste a list instead</summary>
<textarea name="bulk" placeholder="one per line, e.g.&#10;jane@gmail.com, Jane Tan, +65 9123 4567&#10;sam@gmail.com">%BULK%</textarea>
<div class="hint">One person per line: Gmail first, then name and WhatsApp (optional), separated by commas. Up to %MAX% people per send.</div>
</details>
<div class="actions"><span class="count" id="count"></span><button class="btn" type="submit">Send</button></div>
</form></div></main>
<template id="tpl">%ROW_TEMPLATE%</template>
<script>
(function(){var rows=document.getElementById('rows'),tpl=document.getElementById('tpl'),count=document.getElementById('count');
function upd(){var n=[].filter.call(rows.querySelectorAll('input[name=gmail]'),function(i){return i.value.trim()}).length;count.textContent=n?(n+(n>1?' users':' user')+' ready'):'';}
document.getElementById('add').onclick=function(){if(rows.children.length>=%MAX%)return;rows.appendChild(tpl.content.cloneNode(true));var a=rows.lastElementChild.querySelector('input');a&&a.focus();upd();};
rows.addEventListener('click',function(e){if(e.target.classList.contains('x')&&rows.children.length>1){e.target.closest('.row').remove();upd();}});
rows.addEventListener('input',upd);upd();})();
</script></body></html>"""

_ROW = ('<div class="row"><div><label class="m">Gmail address</label>'
        '<input name="gmail" type="email" placeholder="name@gmail.com" value="%G%"></div>'
        '<div><label class="m">Name</label><input name="name" maxlength="80" value="%N%"></div>'
        '<div><label class="m">WhatsApp</label><input name="phone" maxlength="20" placeholder="+65..." value="%P%"></div>'
        '<button class="x" type="button" title="Remove" aria-label="Remove">&times;</button></div>')

_HEADERS = {"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"}


def _row(u: dict | None = None) -> str:
    u = u or {"gmail": "", "name": "", "phone": ""}
    return (_ROW.replace("%G%", html.escape(u["gmail"])).replace("%N%", html.escape(u["name"]))
            .replace("%P%", html.escape(u["phone"])))


def _login_page(notice: str = "", status: int = 200) -> HTMLResponse:
    page = _LOGIN.replace("%STYLE%", _STYLE).replace("%NOTICE%", notice)
    return HTMLResponse(page, status_code=status, headers=_HEADERS)


def _dash_page(notice: str = "", rows: list[dict] | None = None, bulk: str = "", status: int = 200) -> HTMLResponse:
    page = (_DASH.replace("%STYLE%", _STYLE).replace("%NOTICE%", notice)
            .replace("%ROWS%", "".join(_row(u) for u in rows) if rows else _row())
            .replace("%ROW_TEMPLATE%", _row()).replace("%BULK%", html.escape(bulk))
            .replace("%OPEN%", "open" if bulk else "").replace("%MAX%", str(_MAX_USERS)))
    return HTMLResponse(page, status_code=status, headers=_HEADERS)


def _to_login() -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/admin/login")
async def admin_login_page(request: Request):
    _enabled()
    if _signed_in(request):
        return RedirectResponse("/admin", status_code=303)
    return _login_page()


@router.post("/admin/login")
async def admin_login(request: Request):
    _enabled()
    ip = _client_ip(request)
    fails = _recent(_failures.get(ip, []), _FAIL_WINDOW)
    if len(fails) >= _FAIL_LIMIT:
        return _login_page('<div class="notice err">Too many attempts. Please wait 15 minutes and try again.</div>', 429)
    password = str((await request.form()).get("password", ""))
    if not secrets.compare_digest(password.encode(), ADMIN_PANEL_PASSWORD.encode()):
        _failures[ip] = fails + [time.time()]
        return _login_page('<div class="notice err">That password isn\'t right. Please try again.</div>', 401)
    _failures.pop(ip, None)
    resp = RedirectResponse("/admin", status_code=303)
    resp.set_cookie(_COOKIE, _make_session(), max_age=_SESSION_TTL, httponly=True,
                    secure=_is_https(request), samesite="strict", path="/admin")
    return resp


@router.post("/admin/logout")
async def admin_logout():
    resp = _to_login()
    resp.delete_cookie(_COOKIE, path="/admin")
    return resp


@router.get("/admin")
async def admin_page(request: Request):
    _enabled()
    if not _signed_in(request):
        return _to_login()
    return _dash_page()


@router.post("/admin/test-user")
async def admin_test_user(request: Request):
    _enabled()
    if not _signed_in(request):
        return _to_login()
    form = await request.form()
    gmails, names, phones = form.getlist("gmail"), form.getlist("name"), form.getlist("phone")
    rows = [_clean(str(g), str(names[i]) if i < len(names) else "", str(phones[i]) if i < len(phones) else "")
            for i, g in enumerate(gmails)]
    bulk = str(form.get("bulk", ""))
    entries = [r for r in rows if r["gmail"]] + _parse_paste(bulk)

    users, invalid, seen = [], [], set()
    for e in entries:
        if not _EMAIL_RE.match(e["gmail"]):
            invalid.append(e["gmail"])
        elif e["gmail"] not in seen:
            seen.add(e["gmail"])
            users.append(e)
    keep_rows = [r for r in rows if r["gmail"]] or None

    if invalid:
        bad = ", ".join(html.escape(x) for x in invalid[:5]) + ("…" if len(invalid) > 5 else "")
        return _dash_page(f'<div class="notice err">Please fix {len(invalid)} address{"es" if len(invalid) > 1 else ""} '
                          f'that don\'t look valid: <b>{bad}</b></div>', keep_rows, bulk, 400)
    if not users:
        return _dash_page('<div class="notice err">Add at least one Gmail address.</div>', keep_rows, bulk, 400)
    if len(users) > _MAX_USERS:
        return _dash_page(f'<div class="notice err">That\'s {len(users)} people; please send at most {_MAX_USERS} at a time.</div>',
                          keep_rows, bulk, 400)

    global _sends
    _sends = _recent(_sends, _SEND_WINDOW)
    if len(_sends) >= _SEND_LIMIT:
        return _dash_page('<div class="notice err">Too many sends this hour. Please try again later.</div>', keep_rows, bulk, 429)
    # Blocking network I/O; keep it off the event loop that serves WhatsApp.
    reason = await asyncio.to_thread(_send_notification, users)
    if reason:
        return _dash_page(f'<div class="notice err">Couldn\'t send right now ({html.escape(reason)}). '
                          'Please try again later.</div>', keep_rows, bulk, 503)
    _sends.append(time.time())
    listed = ", ".join(f"<b>{html.escape(u['gmail'])}</b>" for u in users)
    return _dash_page(f'<div class="notice ok">Sent {len(users)} user{"s" if len(users) > 1 else ""}: {listed}. '
                      f'They will be added shortly; each person can then text Cue "connect my Google".</div>')
