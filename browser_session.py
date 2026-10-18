"""浏览器会话的 Cookie 和 CSRF 策略。"""
from fastapi import HTTPException, Request, Response

from config import settings
from login_sessions import SESSION_TTL_SECONDS

COOKIE_NAME = "expense_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def require_browser_request(request: Request) -> None:
    # 自定义头使跨域请求必须预检；本应用不开放跨域 CORS。
    # Origin 额外按浏览器访问地址校验，不信任代理转发的 Host。
    origin = request.headers.get("origin")
    if (
        request.headers.get("x-csrf-protection") != "1"
        or (origin is not None and origin not in settings.browser_origins)
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(status_code=403, detail="请求来源校验失败，请刷新后重试")


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_TTL_SECONDS,
        httponly=True, secure=settings.session_cookie_secure,
        samesite="lax", path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME, path="/", httponly=True,
        secure=settings.session_cookie_secure, samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
