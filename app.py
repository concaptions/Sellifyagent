import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
import uvicorn
from twilio.request_validator import RequestValidator

from src.agents.assistant import AGENT_ERROR_REPLY, PersonalAssistant
from src.channels.whatsapp import WhatsAppChannel
from src.config import PORT, PUBLIC_BASE_URL, TEST_WEBHOOK_TOKEN, TWILIO_AUTH_TOKEN
from src import database as db
from src.database import init_database, upsert_user, save_chat_message
from src.tools.reminders import next_due
from src.tools.reminders.manage_reminders import USER_TZ
from src.utils import documents, media_store
from src.utils.approvals import booking_gate
from src.utils.google_auth import (
    get_authorization_url,
    exchange_code_for_token,
    get_google_credentials,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

REMINDER_POLL_SECONDS = 60
_STOP_WORDS = re.compile(r"^\s*(stop|stop (the |my )?reminders?|stop reminding me)\s*[.!]*\s*$", re.IGNORECASE)

os.makedirs("db", exist_ok=True)
assistant = PersonalAssistant()
whatsapp = WhatsAppChannel()

try:
    init_database()
    _db_ready = True
except Exception as e:
    logger.warning("Database init skipped (configure DATABASE_URL to enable): %s", e)
    _db_ready = False


@asynccontextmanager
async def lifespan(_: FastAPI):
    poller = asyncio.create_task(_reminder_loop()) if _db_ready else None
    yield
    if poller:
        poller.cancel()


app = FastAPI(title="Sellify Personal Assistant", lifespan=lifespan)


def _twilio_signature_valid(url: str, params: dict, signature: str) -> bool:
    if not TWILIO_AUTH_TOKEN or not PUBLIC_BASE_URL:
        # Local development only: nothing to validate against.
        logger.warning("Twilio signature check skipped (TWILIO_AUTH_TOKEN/PUBLIC_BASE_URL unset)")
        return True
    return RequestValidator(TWILIO_AUTH_TOKEN).validate(url, params, signature)


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    # Only Twilio may post here. Without this, anyone could send messages as
    # any phone number (acting on that user's notes, documents and email) and
    # point MediaUrl at an arbitrary address for the server to fetch. Twilio
    # signs against the exact URL it was configured with, which is our public
    # URL, not the internal one this app sees behind Railway's proxy.
    form = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")
    if not _twilio_signature_valid(f"{PUBLIC_BASE_URL}/whatsapp/webhook", form, signature):
        logger.warning("Rejected webhook with invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    whatsapp_from = form.get("From", "")
    phone = whatsapp_from.replace("whatsapp:", "")
    message = (form.get("Body") or "").strip()
    media = [
        (form.get(f"MediaUrl{i}"), form.get(f"MediaContentType{i}", ""))
        for i in range(int(form.get("NumMedia") or 0))
        if form.get(f"MediaUrl{i}")
    ]

    logger.info("Incoming from %s: %s (%d attachment(s))", phone, message[:100], len(media))

    asyncio.create_task(_process_message(phone, message, whatsapp_from, media, form.get("MessageSid")))

    return Response(content="", media_type="text/xml")


def _ingest_attachment(
    phone: str, url: str, content_type: str, message_sid: str | None, caption_filename: str | None = None
) -> str:
    """Download and store one attachment; return the system line the agent
    sees, stating plainly what happened so it can't claim otherwise."""
    try:
        if content_type.split(";")[0].strip().lower() not in documents.SUPPORTED_TYPES:
            raise documents.DocumentError(
                "I can't read that file type yet. I can read PDF, Word (.docx) and plain-text files."
            )
        data, filename = documents.download_media(url)
        filename = filename or caption_filename or documents.default_filename(content_type, message_sid)
        result = documents.ingest(phone, data, content_type, filename)
    except documents.DocumentError as e:
        return f"[Document: the user attached a file ({content_type}) that was NOT saved. Reason: {e}]"
    except Exception:
        logger.exception("Attachment ingest failed")
        return f"[Document: the user attached a file ({content_type}) that was NOT saved because of a system error. Ask them to try again later.]"

    if result.status == "duplicate":
        return f"[Document: the user re-sent '{result.filename}', already stored as document id {result.document_id}. Nothing new was saved.]"
    replaced = f" It replaces the earlier copy (id {result.supersedes_id}), which is kept but no longer searched." if result.supersedes_id else ""
    search_mode = "" if result.searchable_by_meaning else " Search is keyword-only for now."
    return (
        f"[Document: saved '{result.filename}' as document id {result.document_id} "
        f"({result.char_count:,} characters of text).{replaced}{search_mode}]"
    )


def _looks_like_filename(text: str) -> bool:
    return bool(re.fullmatch(r"[^\n/\\]{1,200}\.(pdf|docx|txt|csv)", text.strip(), re.IGNORECASE))


async def _prepare_message(phone: str, message: str) -> str:
    """Settle, in code, the two things a user can say that must take effect
    whether or not the model cooperates: approving/declining a pending
    booking, and "stop" for repeating reminders. The outcome is reported to
    the agent as a leading [SYSTEM: ...] line. Shared by the WhatsApp path
    and /webhook/test so tests exercise exactly what production runs."""
    system_line = booking_gate.resolve_from_message(phone, message)
    if not system_line and _STOP_WORDS.match(message):
        try:
            stopped = await asyncio.to_thread(db.stop_reminders, phone, True)
        except Exception:
            stopped = 0
        if stopped:
            system_line = f"[SYSTEM: the user replied stop; {stopped} repeating reminder(s) were cancelled. Confirm in one line.]"
    return f"{system_line}\n\n{message}" if system_line else message


async def _process_message(
    phone: str,
    message: str,
    whatsapp_from: str,
    media: list[tuple[str, str]] | None = None,
    message_sid: str | None = None,
):
    if media:
        # WhatsApp sends a document's filename as the message body, and
        # Twilio's media download often has no filename header, so the body
        # is the only place the real name shows up.
        caption_filename = message if len(media) == 1 and _looks_like_filename(message) else None
        notes = [
            await asyncio.to_thread(_ingest_attachment, phone, url, ctype, message_sid, caption_filename)
            for url, ctype in media
        ]
        message = "\n".join(notes) + ("\n\n" + message if message else "")

    message = await _prepare_message(phone, message)

    try:
        await asyncio.to_thread(upsert_user, phone)
    except Exception:
        logger.debug("User upsert skipped (no DB)")

    try:
        await asyncio.to_thread(save_chat_message, phone, "human", message)
    except Exception:
        logger.debug("Chat save skipped (no DB)")

    try:
        response = await assistant.ainvoke(message, user_phone=phone)
    except Exception as e:
        logger.error("Assistant error: %s", e)
        response = "Something went wrong. Please try again."

    try:
        await asyncio.to_thread(save_chat_message, phone, "assistant", response)
    except Exception:
        logger.debug("Chat save skipped (no DB)")

    try:
        await asyncio.to_thread(whatsapp.send_message, whatsapp_from, response, _own_media_urls(response))
        logger.info("Reply sent to %s: %s", phone, response[:100])
    except Exception as e:
        logger.error("Failed to send reply to %s: %s", phone, e)


def _own_media_urls(text: str) -> list[str]:
    """Screenshots the browser tools produced, so they go out as images."""
    if not PUBLIC_BASE_URL:
        return []
    return re.findall(re.escape(PUBLIC_BASE_URL) + r"/media/[0-9a-f]{32}\.png", text)


@app.get("/media/{token}.png")
async def media(token: str):
    png = media_store.get(token)
    if not png:
        raise HTTPException(status_code=404)
    return Response(content=png, media_type="image/png")


async def _reminder_loop():
    """Poll for due reminders once a minute and deliver each in its own task,
    so one slow agent turn doesn't hold up the others."""
    while True:
        try:
            due = await asyncio.to_thread(db.claim_due_reminders)
        except Exception as e:
            logger.warning("Reminder poll failed: %s", e)
            due = []
        for reminder in due:
            asyncio.create_task(_deliver_reminder(reminder))
        await asyncio.sleep(REMINDER_POLL_SECONDS)


async def _deliver_reminder(reminder: dict):
    """Run the agent on the due reminder and send its reply to the user.

    The outcome is recorded by this code from what actually happened (the
    WhatsApp send succeeded or raised), never from what the model says.
    """
    phone = reminder["user_id"]
    when = reminder["due_at"].astimezone(USER_TZ).strftime("%H:%M on %a %d %b")
    if reminder["kind"] == "followup":
        prompt = (
            f"[REMINDER TRIGGER] A follow-up the user scheduled for {when} is due. "
            f"Do this now, then message them the outcome: {reminder['text']}"
        )
    else:
        prompt = f"[REMINDER TRIGGER] The user asked to be reminded at {when}: {reminder['text']}"

    try:
        reply = await assistant.ainvoke(prompt, user_phone=phone)
        if reply == AGENT_ERROR_REPLY:
            if reminder["kind"] != "reminder":
                raise RuntimeError("agent turn failed")
            # A plain reminder must still reach the user even if the model is down.
            reply = f"Reminder: {reminder['text']}"
        if reminder["recurrence"] != "none":
            # The way out is always in the message itself, not left to the model.
            reply += "\n\nReply *stop* to end these reminders."
        await asyncio.to_thread(whatsapp.send_message, f"whatsapp:{phone}", reply)
    except Exception as e:
        logger.error("Reminder %s delivery failed: %s", reminder["id"], e)
        await asyncio.to_thread(db.finish_reminder, reminder["id"], None, str(e))
        return

    try:
        await asyncio.to_thread(save_chat_message, phone, "assistant", reply)
    except Exception:
        logger.debug("Chat save skipped (no DB)")
    following = next_due(reminder["due_at"], reminder["recurrence"])
    await asyncio.to_thread(db.finish_reminder, reminder["id"], following)
    logger.info("Reminder %s sent to user (next: %s)", reminder["id"], following)


@app.post("/webhook/test")
async def test_webhook(
    phone: str = Form("test"),
    message: str = Form(...),
    x_test_token: str = Header(""),
):
    """Runs the agent as `phone` and returns the reply without WhatsApp.
    Requires the X-Test-Token header: it can act as any user."""
    if not TEST_WEBHOOK_TOKEN or x_test_token != TEST_WEBHOOK_TOKEN:
        raise HTTPException(status_code=404)
    message = await _prepare_message(phone, message)
    response = await assistant.ainvoke(message, user_phone=phone)
    return {"phone": phone, "reply": response}


@app.get("/health")
async def health():
    return {"status": "ok"}


def _oauth_redirect_uri() -> str:
    if not PUBLIC_BASE_URL:
        raise RuntimeError(
            "PUBLIC_BASE_URL is not set. Set it to this app's own public HTTPS "
            "URL (e.g. https://your-app.up.railway.app) before using /oauth/google/start."
        )
    return f"{PUBLIC_BASE_URL}/oauth/google/callback"


@app.get("/oauth/google/start")
async def oauth_google_start():
    """Visit this once (in a browser) to connect the shared Google account
    (Calendar + Gmail) this assistant uses. Only needs to be done once per
    token lifetime — the token refresher keeps it alive after that.
    """
    try:
        auth_url = get_authorization_url(_oauth_redirect_uri())
    except Exception as e:
        logger.error("Failed to build Google auth URL: %s", e)
        return PlainTextResponse(f"Could not start Google OAuth: {e}", status_code=500)
    return RedirectResponse(auth_url)


@app.get("/oauth/google/callback")
async def oauth_google_callback(code: str | None = None, error: str | None = None, state: str | None = None):
    # Both params are optional on purpose. When Google refuses the request it
    # redirects back with ?error=... and no ?code=..., so declaring code as
    # required made FastAPI reject the callback with a bare 422 and swallow
    # the reason Google actually gave — which is the one thing worth seeing.
    if error:
        logger.error("Google OAuth returned an error: %s", error)
        return PlainTextResponse(
            f"Google refused the authorization request: {error}\n\n"
            f"redirect_uri used: {_oauth_redirect_uri()}\n"
            "If this is redirect_uri_mismatch, that exact URI must be listed under "
            "Authorized redirect URIs on this OAuth client in Google Cloud Console.",
            status_code=400,
        )
    if not code:
        return PlainTextResponse(
            "Missing ?code. Start the flow at /oauth/google/start rather than "
            "opening this URL directly.",
            status_code=400,
        )
    try:
        await asyncio.to_thread(exchange_code_for_token, code, _oauth_redirect_uri(), state)
    except Exception as e:
        logger.error("Google OAuth callback failed: %s", e)
        return PlainTextResponse(f"Google OAuth failed: {e}", status_code=500)
    return PlainTextResponse("Google account connected. You can close this tab.")


@app.get("/oauth/google/status")
async def oauth_google_status():
    """Report whether a usable Google token exists, so "is Calendar connected?"
    can be answered by asking the app rather than by inferring it from whether
    a tool call happened to fail.
    """
    creds = await asyncio.to_thread(get_google_credentials)
    return {
        "connected": creds is not None,
        "token_file": os.getenv("GOOGLE_TOKEN_FILE", "token.json"),
        "redirect_uri": _oauth_redirect_uri() if PUBLIC_BASE_URL else None,
        "scopes": list(getattr(creds, "scopes", []) or []) if creds else [],
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)
