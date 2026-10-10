from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Response, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db import get_db
from dependencies import get_current_user
from models import Transaction
from routers import auth
from schemas import (
    UserPublic,
    TransactionCreate,
    TransactionUpdate,
)


app = FastAPI(title="个人记账 API")

app.include_router(auth.router)


@app.get("/")
def home():
    return {"message": "欢迎使用个人记账 API"}




@app.get("/transactions/{id}")
def get_transaction(id: int,current_user: UserPublic = Depends(get_current_user),
                    session: Session = Depends(get_db),):

    transaction = session.scalar(
        select(Transaction).where(
            Transaction.id == id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="账单不存在",
        )

    return {
        "id": transaction.id,
        "kind": transaction.kind,
        "amount_cents": transaction.amount_cents,
        "category": transaction.category,
        "occurred_on": transaction.occurred_on,
        "note": transaction.note,
        "created_at": transaction.created_at,
    }



@app.post("/transactions", status_code=201)
def create_transaction(body: TransactionCreate,current_user: UserPublic = Depends(get_current_user),
                       session: Session = Depends(get_db),):

    transaction = Transaction(
        **body.model_dump(),
        user_id=current_user.id,
    )

    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    return {
        "id": transaction.id,
        "kind": transaction.kind,
        "amount_cents": transaction.amount_cents,
        "category": transaction.category,
        "occurred_on": transaction.occurred_on,
        "note": transaction.note,
        "created_at": transaction.created_at,
    }
    

@app.delete("/transactions/{id}", status_code=204)
def delete_transaction(
    id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    transaction = session.scalar(
        select(Transaction).where(
            Transaction.id == id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="账单不存在",
        )

    session.delete(transaction)
    session.commit()

    return Response(status_code=204)


@app.patch("/transactions/{id}")
def update_transaction(id: int, body: TransactionUpdate,current_user: UserPublic = Depends(get_current_user),
                       session: Session = Depends(get_db),):
    changes = body.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=422,
            detail="请至少提交一个要修改的字段",
        )

    if any(value is None for value in changes.values()):
        raise HTTPException(
            status_code=422,
            detail="修改字段不能为 null",
        )


    transaction = session.scalar(
        select(Transaction).where(
            Transaction.id == id,
            Transaction.user_id == current_user.id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="账单不存在",
        )

    for field, value in changes.items():
        setattr(transaction, field, value)

    session.commit()
    session.refresh(transaction)

    return {
        "id": transaction.id,
        "kind": transaction.kind,
        "amount_cents": transaction.amount_cents,
        "category": transaction.category,
        "occurred_on": transaction.occurred_on,
        "note": transaction.note,
        "created_at": transaction.created_at,
    }
    

@app.get("/transactions")
def list_transactions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
    category: Literal[
        "餐饮", "交通", "购物", "工资", "其他"
    ] | None = None,
    month: str | None = Query(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    ),
):
    statement = select(Transaction).where(
        Transaction.user_id == current_user.id
    )

    if category is not None:
        statement = statement.where(
            Transaction.category == category
        )

    if month is not None:
        year, month_number = map(int, month.split("-"))

        # 本接口限定年份范围，确保能够计算下个月的第一天。
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

        statement = statement.where(
            Transaction.occurred_on >= start_date,
            Transaction.occurred_on < end_date,
        )

    statement = (
        statement
        .order_by(Transaction.id.desc())
        .offset(offset)
        .limit(limit)
    )


    transactions = session.scalars(statement).all()

    return [
        {
            "id": transaction.id,
            "kind": transaction.kind,
            "amount_cents": transaction.amount_cents,
            "category": transaction.category,
            "occurred_on": transaction.occurred_on,
            "note": transaction.note,
            "created_at": transaction.created_at,
        }
        for transaction in transactions
    ]
    
@app.get("/statistics/monthly")
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

