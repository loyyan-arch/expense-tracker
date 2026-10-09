from datetime import date, datetime

from sqlalchemy import CheckConstraint, String, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="positive_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_transactions_user_id_users"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str]
    amount_cents: Mapped[int]
    category: Mapped[str]
    occurred_on: Mapped[date]
    note: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp()
    )

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(32),
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp()
    )

