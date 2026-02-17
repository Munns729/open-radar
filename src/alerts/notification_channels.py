import logging
import aiohttp
import json
from typing import Optional
from src.core.config import settings
from src.core.notifications import email_client

logger = logging.getLogger(__name__)

class SlackClient:
    """
    Client for sending Slack notifications via Webhook.
    """
    def __init__(self):
        self.webhook_url = settings.slack_webhook_url
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not set. Slack notifications will be disabled.")

    async def send_message(self, text: str, blocks: Optional[list] = None) -> bool:
        """
        Send a message to Slack.
        """
        if not self.webhook_url:
            logger.info(f"[MOCK SLACK] {text}")
            return True

        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, 
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status in (200, 201, 202):
                        return True
                    else:
                        logger.error(f"Slack API Error: {response.status} - {await response.text()}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

# Singleton instances
slack_client = SlackClient()
# email_client is already imported from src.core.notifications
