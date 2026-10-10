import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db import get_db


router = APIRouter(tags=["运行状态"])
logger = logging.getLogger("expense_tracker.health")


@router.get("/health")
def health(session: Session = Depends(get_db)):
    try:
        session.execute(text("SELECT id FROM users LIMIT 1"))
        session.execute(text("SELECT id FROM transactions LIMIT 1"))
    except SQLAlchemyError:
        logger.exception("健康检查失败：数据库读取异常")
        raise HTTPException(
            status_code=503,
            detail="服务暂不可用",
        ) from None

    return {"status": "ok"}