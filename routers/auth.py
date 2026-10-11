from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from dependencies import get_current_user
from models import User
from schemas import UserCreate, UserLogin, UserPublic, TokenResponse
from security import (
    hash_password,
    verify_password,
    create_access_token,
)
from rate_limit import LoginRateLimiter


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
    current_user: UserPublic = Depends(get_current_user),
):
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
    

@router.post("/login", response_model=TokenResponse)
def login(
    body: UserLogin,
    request: Request,
    session: Session = Depends(get_db),
):
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

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
    }