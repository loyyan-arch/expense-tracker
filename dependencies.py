from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from db import get_db
from models import User
from schemas import UserPublic
from security import decode_access_token



bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    session: Session = Depends(get_db),
) -> UserPublic:
    unauthorized = HTTPException(
        status_code=401,
        detail="未登录或登录凭证无效",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise unauthorized


    user = session.get(User, user_id)

    if user is None:
        raise unauthorized

    return UserPublic(
        id=user.id,
        username=user.username,
    )