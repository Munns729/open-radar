import logging
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from src.core.config import settings

logger = logging.getLogger(__name__)

class EmailClient:
    def __init__(self):
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.sendgrid_from_email
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not set. Emailing will be disabled.")
            self.sg = None
        else:
            self.sg = sendgrid.SendGridAPIClient(api_key=self.api_key)

    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        if not self.sg:
            logger.info(f"[MOCK EMAIL] To: {to_email} | Subject: {subject}")
            return True

        from_email = Email(self.from_email or "radar@example.com")
        to_email = To(to_email)
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email, subject, content)

        try:
            response = self.sg.client.mail.send.post(request_body=mail.get())
            logger.info(f"Email sent to {to_email}. Status: {response.status_code}")
            return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

# Singleton instance
email_client = EmailClient()
