import logging

from twilio.rest import Client

from src.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, FROM_WHATSAPP_NUMBER
from src.utils.message_splitter import split_message

logger = logging.getLogger(__name__)


class WhatsAppChannel:
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.from_number = FROM_WHATSAPP_NUMBER

    def send_message(self, to_number: str, body: str):
        parts = split_message(body)
        for part in parts:
            try:
                self.client.messages.create(
                    from_=self.from_number,
                    to=to_number,
                    body=part,
                )
            except Exception as e:
                logger.error("Failed to send WhatsApp message to %s: %s", to_number, e)
                raise
