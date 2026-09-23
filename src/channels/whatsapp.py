import logging

from twilio.rest import Client

from src.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, FROM_WHATSAPP_NUMBER
from src.utils.message_splitter import split_message

logger = logging.getLogger(__name__)


class WhatsAppChannel:
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.from_number = FROM_WHATSAPP_NUMBER

    def send_message(self, to_number: str, body: str, media_urls: list[str] | None = None):
        parts = split_message(body)
        for i, part in enumerate(parts):
            try:
                kwargs = {"from_": self.from_number, "to": to_number, "body": part}
                if media_urls and i == 0:
                    # WhatsApp takes one media item per message.
                    kwargs["media_url"] = media_urls[:1]
                self.client.messages.create(**kwargs)
            except Exception as e:
                logger.error("Failed to send WhatsApp message to %s: %s", to_number, e)
                raise
