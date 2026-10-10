from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db import get_db
from dependencies import get_current_user
from models import Transaction
from schemas import UserPublic


router = APIRouter(
    prefix="/statistics",
    tags=["统计"],
)

    
@router.get("/monthly")
def get_monthly_statistics(
    session: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
    month: str = Query(
        ...,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    ),
):
    year, month_number = map(int, month.split("-"))

    if not 1 <= year <= 9998:
        raise HTTPException(
            status_code=422,
            detail="年份必须在 0001 到 9998 之间",
        )

    start_date = date(year, month_number, 1)

    if month_number == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month_number + 1, 1)

    statement = (
        select(
            Transaction.kind,
            func.sum(Transaction.amount_cents),
        )
        .where(
            Transaction.user_id == current_user.id,
            Transaction.occurred_on >= start_date,
            Transaction.occurred_on < end_date,
        )
        .group_by(Transaction.kind)
    )


    rows = session.execute(statement).all()

    totals = {
        "income": 0,
        "expense": 0,
    }

    for kind, total in rows:
        totals[kind] = total

    income = totals["income"]
    expense = totals["expense"]

    return {
        "month": month,
        "income_cents": income,
        "expense_cents": expense,
        "balance_cents": income - expense,
    }