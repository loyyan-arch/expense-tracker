from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from dependencies import get_current_user
from models import Transaction
from schemas import (
    TransactionCreate,
    TransactionUpdate,
    UserPublic,
    TransactionPublic,
)


router = APIRouter(
    prefix="/transactions",
    tags=["账单"],
)


@router.get("/{id}", response_model=TransactionPublic)
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

    return transaction



@router.post("", status_code=201, response_model=TransactionPublic)
def create_transaction(body: TransactionCreate,current_user: UserPublic = Depends(get_current_user),
                       session: Session = Depends(get_db),):

    transaction = Transaction(
        **body.model_dump(),
        user_id=current_user.id,
    )

    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    return transaction
    

@router.delete("/{id}", status_code=204)
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


@router.patch("/{id}", response_model=TransactionPublic)
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

    return transaction
    

@router.get("", response_model=list[TransactionPublic])
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

    return transactions
