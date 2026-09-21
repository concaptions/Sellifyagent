import asyncio
import logging
import os

from fastapi import FastAPI, Form, Response
from fastapi.responses import PlainTextResponse, RedirectResponse
import uvicorn

from src.agents.assistant import PersonalAssistant
from src.channels.whatsapp import WhatsAppChannel
from src.config import PORT, PUBLIC_BASE_URL
from src.database import init_database, upsert_user, save_chat_message
from src.utils.google_auth import get_authorization_url, exchange_code_for_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sellify Personal Assistant")

os.makedirs("db", exist_ok=True)
assistant = PersonalAssistant()
whatsapp = WhatsAppChannel()

try:
    init_database()
except Exception as e:
    logger.warning("Database init skipped (configure DATABASE_URL to enable): %s", e)


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    phone = From.replace("whatsapp:", "")
    message = Body.strip()

    logger.info("Incoming from %s: %s", phone, message[:100])

    asyncio.create_task(_process_message(phone, message, From))

    return Response(content="", media_type="text/xml")


async def _process_message(phone: str, message: str, whatsapp_from: str):
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
        await asyncio.to_thread(whatsapp.send_message, whatsapp_from, response)
        logger.info("Reply sent to %s: %s", phone, response[:100])
    except Exception as e:
        logger.error("Failed to send reply to %s: %s", phone, e)


@app.post("/webhook/test")
async def test_webhook(phone: str = Form("test"), message: str = Form(...)):
    """Test endpoint that returns the reply directly without sending via WhatsApp."""
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
async def oauth_google_callback(code: str):
    try:
        await asyncio.to_thread(exchange_code_for_token, code, _oauth_redirect_uri())
    except Exception as e:
        logger.error("Google OAuth callback failed: %s", e)
        return PlainTextResponse(f"Google OAuth failed: {e}", status_code=500)
    return PlainTextResponse("Google account connected. You can close this tab.")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)
