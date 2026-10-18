from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from dependencies import get_current_user, get_current_session_token
from models import User
from schemas import UserCreate, UserLogin, UserPublic, TokenResponse
from security import (
    hash_password,
    verify_password,
)
from rate_limit import LoginRateLimiter
from login_sessions import create_login_session, revoke_login_session
from browser_session import (
    COOKIE_NAME, require_browser_request, set_session_cookie, clear_session_cookie,
)


router = APIRouter(
    prefix="/auth",
    tags=["认证"],
)
login_limiter = LoginRateLimiter(limit=5, window_seconds=60)

DUMMY_PASSWORD_HASH = hash_password(
    "dummy-password-for-login-timing"
)

    
@router.get("/me", response_model=UserPublic)
def get_me(
    response: Response,
    current_user: UserPublic = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"
    return current_user



@router.post(
    "/register",
    status_code=201,
    response_model=UserPublic,
)
def register(body: UserCreate,session: Session = Depends(get_db),):
    hashed_password = hash_password(body.password)

    user = User(
        username=body.username,
        password_hash=hashed_password,
    )

    session.add(user)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()

        existing_user = session.scalar(
            select(User).where(
                User.username == body.username
            )
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=409,
                detail="用户名已存在",
            )

        raise

    session.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
    }
    

def authenticate_password(
    body: UserLogin,
    request: Request,
    session: Session,
) -> User:
    source = request.client.host if request.client else "unknown"
    allowed, retry_after = login_limiter.check(source)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="登录请求过于频繁，请稍后重试",
            headers={"Retry-After": str(retry_after)},
        )

    user = session.scalar(
        select(User).where(
            User.username == body.username
        )
    )

    stored_hash = (
        user.password_hash
        if user is not None
        else DUMMY_PASSWORD_HASH
    )

    password_valid = verify_password(
        body.password,
        stored_hash,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="用户名不存在，请先注册",
        )

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="密码错误",
        )

    return user


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, request: Request, response: Response,
          session: Session = Depends(get_db)):
    user = authenticate_password(body, request, session)
    token = create_login_session(session, user.id)
    session.commit()
    response.headers["Cache-Control"] = "no-store"

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=204)
def logout(
    token: str = Depends(get_current_session_token),
    session: Session = Depends(get_db),
):
    revoke_login_session(session, token)
    session.commit()

    return Response(status_code=204)


@router.post("/browser/login", response_model=UserPublic,
             dependencies=[Depends(require_browser_request)])
def browser_login(body: UserLogin, request: Request, response: Response,
                  session: Session = Depends(get_db)):
    user = authenticate_password(body, request, session)
    # 成功登录时轮换当前浏览器凭证；密码错误不会撤销原会话。
    revoke_login_session(session, request.cookies.get(COOKIE_NAME, ""))
    token = create_login_session(session, user.id)
    session.commit()
    set_session_cookie(response, token)
    return UserPublic(id=user.id, username=user.username)


@router.post("/browser/logout", status_code=204,
             dependencies=[Depends(require_browser_request)])
def browser_logout(request: Request, session: Session = Depends(get_db)):
    # 即使会话已过期，也清掉浏览器 Cookie，重复退出仍成功。
    revoke_login_session(session, request.cookies.get(COOKIE_NAME, ""))
    session.commit()
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response
