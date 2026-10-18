import hashlib
import re
import secrets
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import LoginSession


SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


def now_timestamp() -> int:
    return int(time.time())


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_login_session(
    db: Session,
    user_id: int,
) -> str:
    token = secrets.token_urlsafe(32)
    now = now_timestamp()

    login_session = LoginSession(
        token_hash=hash_session_token(token),
        user_id=user_id,
        created_at=now,
        expires_at=now + SESSION_TTL_SECONDS,
        revoked_at=None,
    )

    db.add(login_session)
    db.flush()

    return token


def get_active_session(
    db: Session,
    token: str,
) -> LoginSession | None:
    # token_urlsafe(32) 生成 43 个 URL 安全字符。
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return None

    return db.scalar(
        select(LoginSession).where(
            LoginSession.token_hash == hash_session_token(token),
            LoginSession.revoked_at.is_(None),
            LoginSession.expires_at > now_timestamp(),
        )
    )


def revoke_login_session(
    db: Session,
    token: str,
) -> None:
    login_session = get_active_session(db, token)

    if login_session is not None:
        login_session.revoked_at = now_timestamp()
        db.flush()