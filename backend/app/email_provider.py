from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass
class EmailMessage:
    from_email: str
    to_email: str
    subject: str
    html: str
    text: str


class EmailProvider:
    def send(self, message: EmailMessage) -> str:
        raise NotImplementedError


class ResendEmailProvider(EmailProvider):
    def __init__(self, api_key: str, from_email: str) -> None:
        if not api_key:
            raise RuntimeError("RESEND_API_KEY is required for resend provider")
        if not from_email:
            raise RuntimeError("FROM_EMAIL is required for resend provider")

        import resend

        resend.api_key = api_key
        self._client = resend
        self._from_email = from_email

    def send(self, message: EmailMessage) -> str:
        response = self._client.Emails.send(
            {
                "from": message.from_email or self._from_email,
                "to": [message.to_email],
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
            }
        )
        return str(response.get("id", ""))


def build_email_provider() -> EmailProvider:
    if settings.email_provider.lower() != "resend":
        raise RuntimeError("Unsupported EMAIL_PROVIDER. Use 'resend'.")
    return ResendEmailProvider(api_key=settings.resend_api_key, from_email=settings.from_email)
