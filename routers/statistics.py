from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session

from db import get_db
from dependencies import get_current_user
from models import Transaction
from schemas import UserPublic


router = APIRouter(
    prefix="/statistics",
    tags=["统计"],
)


@router.get("/yearly")
def get_yearly_statistics(
    year: int = Query(..., ge=1, le=9998),
    session: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    month_number = extract("month", Transaction.occurred_on)
    rows = session.execute(
        select(month_number, Transaction.kind, func.sum(Transaction.amount_cents))
        .where(
            Transaction.user_id == current_user.id,
            Transaction.occurred_on >= date(year, 1, 1),
            Transaction.occurred_on < date(year + 1, 1, 1),
        )
        .group_by(month_number, Transaction.kind)
    ).all()

    months = [
        {"month": f"{year:04d}-{month:02d}", "income_cents": 0,
         "expense_cents": 0, "balance_cents": 0}
        for month in range(1, 13)
    ]
    for month, kind, amount in rows:
        months[int(month) - 1][f"{kind}_cents"] = amount
    for month in months:
        month["balance_cents"] = month["income_cents"] - month["expense_cents"]

    income = sum(month["income_cents"] for month in months)
    expense = sum(month["expense_cents"] for month in months)
    return {
        "year": year,
        "income_cents": income,
        "expense_cents": expense,
        "balance_cents": income - expense,
        "months": months,
    }

    
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
