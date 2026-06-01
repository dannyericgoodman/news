"""Email delivery. Gmail SMTP is the proven, no-domain-needed backend and is
tried first; Resend is an optional fallback if you later verify a domain.

Returns True only when a backend accepted the message.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)


def recipient() -> str:
    return (os.getenv("NEWSLETTER_TO") or os.getenv("GMAIL_ADDRESS")
            or "danny.eric.goodman@gmail.com").strip()


def _send_gmail(subject, html_body, text_body) -> bool:
    user = (os.getenv("GMAIL_ADDRESS") or "").strip()
    password = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")  # Gmail shows it with spaces
    if not user or not password:
        return False
    to = recipient()
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"], msg["Reply-To"] = subject, f"The VC Reading Room <{user}>", to, user
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(user, password)
            s.sendmail(user, [r.strip() for r in to.split(",")], msg.as_string())
        logger.info("Email sent via Gmail to %s", to)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("Gmail auth FAILED (need 2FA + a 16-char App Password): %s", exc)
    except Exception as exc:
        logger.error("Gmail send FAILED: %s", exc)
    return False


def _send_resend(subject, html_body, text_body) -> bool:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        return False
    sender = os.getenv("RESEND_FROM", "The VC Reading Room <onboarding@resend.dev>").strip()
    to = [r.strip() for r in recipient().split(",")]
    try:
        r = requests.post("https://api.resend.com/emails",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"from": sender, "to": to, "subject": subject, "html": html_body, "text": text_body},
                          timeout=30)
        if r.status_code in (200, 201):
            logger.info("Email sent via Resend to %s", to)
            return True
        logger.error("Resend send FAILED: HTTP %s — %s", r.status_code, r.text[:300])
    except Exception as exc:
        logger.error("Resend send FAILED: %s", exc)
    return False


def send_newsletter(subject, html_body, text_body) -> bool:
    """Try Gmail (proven), then Resend. Never sends twice."""
    tried = []
    if os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"):
        tried.append("Gmail")
        if _send_gmail(subject, html_body, text_body):
            return True
    if os.getenv("RESEND_API_KEY"):
        tried.append("Resend")
        if _send_resend(subject, html_body, text_body):
            return True
    if not tried:
        logger.error("Email NOT sent: set GMAIL_ADDRESS + GMAIL_APP_PASSWORD (recommended).")
    else:
        logger.error("Email NOT sent: all backends failed (%s).", ", ".join(tried))
    return False
