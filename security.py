from pwdlib import PasswordHash

from config import settings
from datetime import datetime, timedelta, timezone

import jwt

from jwt.exceptions import InvalidTokenError


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


JWT_SECRET = settings.jwt_secret.get_secret_value()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )

    subject = payload["sub"]

    if not isinstance(subject, str):
        raise InvalidTokenError("用户标识格式错误")

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise InvalidTokenError("用户标识格式错误") from exc

    if not 1 <= user_id <= 9223372036854775807:
        raise InvalidTokenError("用户标识超出范围")

    return user_id


