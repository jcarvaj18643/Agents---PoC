from __future__ import annotations

import requests

from app.config import settings


class SendGridClient:
    API_URL = "https://api.sendgrid.com/v3/mail/send"

    def send_email(
        self,
        to_emails: list[str],
        from_email: str,
        from_name: str,
        subject: str,
        plain_text: str,
        html: str,
    ) -> None:
        if not settings.sendgrid_api_key:
            raise ValueError("SENDGRID_API_KEY is not configured.")
        if not to_emails:
            raise ValueError("At least one recipient email is required.")

        payload = {
            "personalizations": [
                {
                    "to": [{"email": email} for email in to_emails],
                }
            ],
            "from": {"email": from_email, "name": from_name},
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": plain_text},
                {"type": "text/html", "value": html},
            ],
        }

        response = requests.post(
            self.API_URL,
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code >= 300:
            raise RuntimeError(f"SendGrid error {response.status_code}: {response.text}")
