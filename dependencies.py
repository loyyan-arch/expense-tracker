from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db import get_db
from login_sessions import get_active_session
from models import User
from schemas import UserPublic
from browser_session import COOKIE_NAME, SAFE_METHODS, require_browser_request


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_session_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    session: Session = Depends(get_db),
) -> str:
    unauthorized = HTTPException(
        status_code=401,
        detail="未登录或登录凭证无效",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if "authorization" in request.headers:
        # 显式提交错误的 Authorization 时，不能回退到 Cookie。
        if credentials is None:
            raise unauthorized
        token = credentials.credentials
    else:
        token = request.cookies.get(COOKIE_NAME, "")
        if token and request.method not in SAFE_METHODS:
            require_browser_request(request)
    active_session = get_active_session(session, token)

    if active_session is None:
        raise unauthorized

    return token


def get_current_user(
    token: str = Depends(get_current_session_token),
    session: Session = Depends(get_db),
) -> UserPublic:
    unauthorized = HTTPException(
        status_code=401,
        detail="未登录或登录凭证无效",
        headers={"WWW-Authenticate": "Bearer"},
    )

    active_session = get_active_session(session, token)

    if active_session is None:
        raise unauthorized

    user = session.get(User, active_session.user_id)

    if user is None:
        raise unauthorized

    return UserPublic(
        id=user.id,
        username=user.username,
    )
