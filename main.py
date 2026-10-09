from fastapi import FastAPI, HTTPException,Response,Query, Depends
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict

from sqlalchemy.orm import Session
from sqlalchemy import select,func

from db import engine
from models import Transaction,User

from sqlalchemy.exc import IntegrityError
from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError


app = FastAPI(title="个人记账 API")


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(
        min_length=1,
        max_length=128,
        repr=False,
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[a-z0-9_]+$",
    )
    password: str = Field(
        min_length=7,
        max_length=128,
        repr=False,
    )


class UserPublic(BaseModel):
    id: int
    username: str


DUMMY_PASSWORD_HASH = hash_password(
    "dummy-password-for-login-timing"
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
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

    with Session(engine) as session:
        user = session.get(User, user_id)

        if user is None:
            raise unauthorized

        return UserPublic(
            id=user.id,
            username=user.username,
        )
    
@app.get("/auth/me", response_model=UserPublic)
def get_me(
    current_user: UserPublic = Depends(get_current_user),
):
    return current_user





@app.get("/")
def home():
    return {"message": "欢迎使用个人记账 API"}




@app.get("/transactions/{id}")
def get_transaction(id: int,current_user: UserPublic = Depends(get_current_user),):
    with Session(engine) as session:
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


class TransactionCreate(BaseModel):
    kind: Literal["income", "expense"]
    amount_cents: int = Field(gt=0, strict=True)
    category: Literal["餐饮", "交通", "购物", "工资", "其他"]
    occurred_on: date
    note: str = Field(default="", max_length=200)
    model_config = ConfigDict(extra="forbid")

class TransactionUpdate(BaseModel):
    kind: Literal["income", "expense"] | None = None
    amount_cents: int | None = Field(
        default=None,
        gt=0,
        strict=True,
    )
    model_config = ConfigDict(extra="forbid")
    category: Literal["餐饮", "交通", "购物", "工资", "其他"] | None = None
    occurred_on: date | None = None
    note: str | None = Field(default=None, max_length=200)



@app.post("/transactions", status_code=201)
def create_transaction(body: TransactionCreate,current_user: UserPublic = Depends(get_current_user),):
    with Session(engine) as session:
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
def delete_transaction(id: int,current_user: UserPublic = Depends(get_current_user),):
    with Session(engine) as session:
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
def update_transaction(id: int, body: TransactionUpdate,current_user: UserPublic = Depends(get_current_user),):
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

    with Session(engine) as session:
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

    with Session(engine) as session:
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

    with Session(engine) as session:
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


@app.post(
    "/auth/register",
    status_code=201,
    response_model=UserPublic,
)
def register(body: UserCreate):
    hashed_password = hash_password(body.password)

    with Session(engine) as session:
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
    

@app.post("/auth/login", response_model=TokenResponse)
def login(body: UserLogin):
    with Session(engine) as session:
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

        if user is None or not password_valid:
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误",
            )

        token = create_access_token(user.id)

        return {
            "access_token": token,
            "token_type": "bearer",
        }