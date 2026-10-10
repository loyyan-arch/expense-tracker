from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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

class TransactionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: Literal["income", "expense"]
    amount_cents: int
    category: Literal["餐饮", "交通", "购物", "工资", "其他"]
    occurred_on: date
    note: str
    created_at: datetime

