"""Email OTP issuance, delivery hook, and verification.

Security properties:
  - Only the SHA-256 hash of a code is persisted; plaintext codes live only in
    the delivery channel (SMTP email, or the dev-only API response).
  - Codes expire after OTP_TTL_SECONDS (default 10 minutes).
  - One active code per (email, purpose); re-requests inside the cooldown
    window are rejected with 429 instead of issuing a new code.
  - At most OTP_MAX_ATTEMPTS verification attempts per code; the code is
    single-use (consumed on first success).
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.otp import EmailOTP

log = logging.getLogger(__name__)

PURPOSE_SIGNUP = 'signup_verify'
PURPOSE_LOGIN = 'login_otp'

OTP_TTL_SECONDS = int(getattr(settings, 'OTP_TTL_SECONDS', 600) or 600)
OTP_COOLDOWN_SECONDS = int(getattr(settings, 'OTP_COOLDOWN_SECONDS', 60) or 60)
OTP_MAX_ATTEMPTS = int(getattr(settings, 'OTP_MAX_ATTEMPTS', 5) or 5)
OTP_LENGTH = 6


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def _generate_code() -> str:
    return ''.join(secrets.choice('0123456789') for _ in range(OTP_LENGTH))


def _as_aware(value: datetime) -> datetime:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _latest_active(db: Session, email: str, purpose: str) -> EmailOTP | None:
    return (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed.is_(False),
        )
        .order_by(EmailOTP.id.desc())
        .first()
    )


def send_otp_email(email: str, code: str, purpose: str) -> bool:
    """Deliver the code. Returns True when an SMTP attempt was made.

    When no SMTP host is configured (local/dev default) the code is logged so
    the flow stays testable, and the API layer additionally returns it in the
    dev-only `dev_otp` field. Production refuses to run this path without
    SMTP configured (see auth router guard).
    """
    subject = (
        'Verify your Fleet Tracker email'
        if purpose == PURPOSE_SIGNUP
        else 'Your Fleet Tracker login code'
    )
    body = (
        f'Your Fleet Tracker verification code is: {code}\n'
        f'It expires in {OTP_TTL_SECONDS // 60} minutes. '
        'If you did not request this, ignore this email.'
    )
    host = (getattr(settings, 'SMTP_HOST', '') or '').strip()
    if not host:
        log.warning('SMTP not configured — OTP for %s (%s): %s', email, purpose, code)
        return False
    import smtplib
    from email.message import EmailMessage

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = getattr(settings, 'SMTP_FROM', '') or 'no-reply@localhost'
    message['To'] = email
    message.set_content(body)
    port = int(getattr(settings, 'SMTP_PORT', 587) or 587)
    username = getattr(settings, 'SMTP_USER', '') or ''
    password = getattr(settings, 'SMTP_PASSWORD', '') or ''
    use_tls = str(getattr(settings, 'SMTP_TLS', 'true')).lower() not in ('0', 'false', 'no')
    with smtplib.SMTP(host, port, timeout=15) as client:
        if use_tls:
            client.starttls()
        if username:
            client.login(username, password)
        client.send_message(message)
    return True


def issue_otp(db: Session, email: str, purpose: str) -> tuple[EmailOTP, str, bool]:
    """Issue a fresh code, invalidating any previous active one.

    Returns (record, plaintext_code, delivered_via_smtp).
    Raises ValueError('cooldown') when a code was issued inside the window.
    """
    now = _utcnow()
    previous = _latest_active(db, email, purpose)
    if previous is not None:
        created = _as_aware(previous.created_at)
        if (now - created).total_seconds() < OTP_COOLDOWN_SECONDS:
            raise ValueError('cooldown')
        previous.consumed = True

    code = _generate_code()
    record = EmailOTP(
        email=email,
        purpose=purpose,
        code_hash=_hash_code(code),
        expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    delivered = send_otp_email(email, code, purpose)
    return record, code, delivered


def check_otp(db: Session, email: str, code: str, purpose: str) -> EmailOTP:
    """Validate a code. Consumes it on success.

    Raises ValueError with one of: 'missing', 'expired', 'locked',
    'mismatch'. Wrong guesses increment the attempt counter and lock the
    code once OTP_MAX_ATTEMPTS is reached.
    """
    record = _latest_active(db, email, purpose)
    if record is None:
        raise ValueError('missing')
    if _as_aware(record.expires_at) < _utcnow():
        raise ValueError('expired')
    if record.attempts >= OTP_MAX_ATTEMPTS:
        raise ValueError('locked')
    if _hash_code(code or '') != record.code_hash:
        record.attempts += 1
        db.commit()
        raise ValueError('mismatch')
    record.consumed = True
    db.commit()
    return record
